from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Q
from django.db.models.functions import TruncMonth
from datetime import datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
import pandas as pd
import io
from .models import Category, Transaction
from .serializers import CategorySerializer, TransactionSerializer
from .forms import TransactionForm, CategoryForm, CSVImportForm, PDFImportForm

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    queryset = Transaction.objects.all()  # Required for DRF router

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

    @action(detail=False, methods=['post'])
    def import_pdf(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            import tabula
            import pandas as pd
            from datetime import datetime

            transactions = []

            # Extract tables from PDF using tabula
            # For Colombian bank statements, try different table extraction options
            try:
                dfs = tabula.read_pdf(file, pages='all', multiple_tables=True, lattice=True)
                if not dfs:
                    dfs = tabula.read_pdf(file, pages='all', multiple_tables=True, stream=True)
            except:
                dfs = tabula.read_pdf(file, pages='all', multiple_tables=True)

            for df in dfs:
                if df.empty or len(df) < 2:
                    continue

                # Clean column names
                df.columns = df.columns.str.strip().str.lower()

                # For Colombian bank statements, the structure is often:
                # Column 0: Date (DD-MM-YYYY)
                # Column 1: Description
                # Column 2: Amount
                # Column 3: Balance (optional)

                # Process each row
                for _, row in df.iterrows():
                    try:
                        # Extract date from first column or look for date pattern
                        date_str = str(row.iloc[0]).strip() if len(row) > 0 else ""

                        # If first column doesn't look like a date, search all columns
                        if not re.match(r'\d{2}-\d{2}-\d{4}', date_str):
                            for col_val in row.values:
                                col_str = str(col_val).strip()
                                if re.match(r'\d{2}-\d{2}-\d{4}', col_str):
                                    date_str = col_str
                                    break

                        if not date_str or not re.match(r'\d{2}-\d{2}-\d{4}', date_str):
                            continue

                        # Parse date (DD-MM-YYYY format for Colombian statements)
                        try:
                            parsed_date = datetime.strptime(date_str, '%d-%m-%Y').date()
                        except ValueError:
                            continue

                        # Extract description and amount
                        description = ""
                        amount = None

                        # Look through remaining columns for description and amount
                        for i, col_val in enumerate(row.values[1:], 1):  # Skip first column (date)
                            col_str = str(col_val).strip()

                            if not col_str or col_str == 'nan':
                                continue

                            # Check if this looks like an amount (contains numbers and currency symbols)
                            amount_match = re.search(r'[\d,]+\.?\d*', col_str.replace('$', '').replace('.', ''))
                            if amount_match and len(col_str) < 20:  # Amount columns are usually short
                                # Clean amount
                                clean_amount = col_str.replace('$', '').replace(',', '').strip()
                                try:
                                    amount = float(clean_amount)
                                    break  # Found amount, stop looking
                                except ValueError:
                                    pass
                            else:
                                # This might be description
                                if len(col_str) > 3 and not col_str.replace(',', '').replace('.', '').replace('$', '').strip().isdigit():
                                    description = col_str

                        # If we still don't have amount, look for it in the entire row
                        if amount is None:
                            for col_val in row.values:
                                col_str = str(col_val).strip()
                                # Look for patterns like "23,709.00" or "$23,709.00"
                                if re.search(r'[\d,]+\.\d{2}', col_str):
                                    clean_amount = col_str.replace('$', '').replace(',', '').strip()
                                    try:
                                        amount = float(clean_amount)
                                        break
                                    except ValueError:
                                        continue

                        if amount is None or amount == 0:
                            continue

                        # If no description found, create one
                        if not description:
                            description = f"Transaction {parsed_date}"

                        # For Colombian bank statements, amounts are typically expenses (negative)
                        # unless they contain keywords indicating income
                        if amount > 0 and not any(word in description.lower() for word in ['abono', 'deposito', 'transferencia recibida', 'intereses']):
                            amount = -amount  # Convert to negative for expenses

                        transaction_data = {
                            'date': parsed_date,
                            'description': description,
                            'amount': amount,
                            'user': request.user
                        }

                        # Auto-categorize
                        transaction_data['category'] = self._auto_categorize(description)

                        transactions.append(Transaction(**transaction_data))

                    except Exception as e:
                        # Skip problematic rows but continue processing
                        continue

            Transaction.objects.bulk_create(transactions)
            return Response({'message': f'Imported {len(transactions)} transactions from PDF'}, status=status.HTTP_201_CREATED)

        except ImportError as e:
            return Response({'error': f'PDF processing libraries not available. Please install tabula-py: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({'error': f'PDF processing failed: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def import_csv(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            df = pd.read_csv(io.StringIO(file.read().decode('utf-8')))
            transactions = []

            # Flexible column mapping
            column_mapping = {
                'date': request.data.get('date_column', 'date'),
                'description': request.data.get('description_column', 'description'),
                'amount': request.data.get('amount_column', 'amount'),
                'category': request.data.get('category_column', None)
            }

            for _, row in df.iterrows():
                transaction_data = {
                    'date': row[column_mapping['date']],
                    'description': row[column_mapping['description']],
                    'amount': float(row[column_mapping['amount']]),
                    'user': request.user
                }

                if column_mapping['category'] and column_mapping['category'] in row:
                    category_name = row[column_mapping['category']]
                    category, _ = Category.objects.get_or_create(name=category_name)
                    transaction_data['category'] = category

                # Auto-categorize if no category provided
                if 'category' not in transaction_data:
                    transaction_data['category'] = self._auto_categorize(transaction_data['description'])

                transactions.append(Transaction(**transaction_data))

            Transaction.objects.bulk_create(transactions)
            return Response({'message': f'Imported {len(transactions)} transactions'}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def _auto_categorize(self, description):
        # Simple keyword-based categorization
        keywords = {
            'food': ['restaurant', 'grocery', 'food', 'cafe', 'dinner'],
            'transport': ['taxi', 'bus', 'train', 'gas', 'parking'],
            'entertainment': ['movie', 'game', 'concert', 'party'],
            'utilities': ['electricity', 'water', 'internet', 'phone'],
            'shopping': ['clothes', 'shoes', 'amazon', 'store']
        }

        description_lower = description.lower()
        for category_name, words in keywords.items():
            if any(word in description_lower for word in words):
                category, _ = Category.objects.get_or_create(name=category_name.capitalize())
                return category

        # Default category
        category, _ = Category.objects.get_or_create(name='Other')
        return category

    @action(detail=False, methods=['get'])
    def summary(self, request):
        user = request.user
        month = request.query_params.get('month')
        year = request.query_params.get('year')

        queryset = Transaction.objects.filter(user=user)

        if month and year:
            queryset = queryset.filter(date__year=year, date__month=month)

        total_income = queryset.filter(amount__lt=0).aggregate(Sum('amount'))['amount__sum'] or 0
        total_expenses = queryset.filter(amount__gt=0).aggregate(Sum('amount'))['amount__sum'] or 0

        category_summary = queryset.filter(amount__gt=0).values('category__name').annotate(
            total=Sum('amount')
        ).order_by('-total')

        return Response({
            'total_income': abs(total_income),
            'total_expenses': total_expenses,
            'net_amount': abs(total_income) - total_expenses,
            'category_summary': list(category_summary)
        })

    @action(detail=False, methods=['get'])
    def monthly_trends(self, request):
        user = request.user
        months = int(request.query_params.get('months', 12))

        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30*months)

        trends = Transaction.objects.filter(
            user=user,
            date__range=[start_date, end_date]
        ).annotate(
            month=TruncMonth('date')
        ).values('month').annotate(
            income=Sum('amount', filter=Q(amount__lt=0)),
            expenses=Sum('amount', filter=Q(amount__gt=0))
        ).order_by('month')

        return Response(list(trends))

# Web UI Views
@login_required
def transaction_list(request):
    """List all user transactions with filtering and pagination"""
    transactions = Transaction.objects.filter(user=request.user).order_by('-date')

    # Simple filtering
    category_filter = request.GET.get('category')
    if category_filter:
        transactions = transactions.filter(category__name__icontains=category_filter)

    date_from = request.GET.get('date_from')
    if date_from:
        transactions = transactions.filter(date__gte=date_from)

    date_to = request.GET.get('date_to')
    if date_to:
        transactions = transactions.filter(date__lte=date_to)

    # Pagination (simple implementation)
    page = int(request.GET.get('page', 1))
    per_page = 20
    start = (page - 1) * per_page
    end = start + per_page
    total_pages = (transactions.count() + per_page - 1) // per_page

    transactions_page = transactions[start:end]

    context = {
        'transactions': transactions_page,
        'page': page,
        'total_pages': total_pages,
        'has_next': page < total_pages,
        'has_prev': page > 1,
        'categories': Category.objects.all(),
    }

    return render(request, 'transactions/transaction_list.html', context)

@login_required
def transaction_create(request):
    """Create a new transaction"""
    if request.method == 'POST':
        form = TransactionForm(request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.user = request.user
            transaction.save()
            messages.success(request, 'Transaction created successfully!')
            return redirect('transaction_list')
    else:
        form = TransactionForm()

    return render(request, 'transactions/transaction_form.html', {
        'form': form,
        'title': 'Add Transaction'
    })

@login_required
def transaction_update(request, pk):
    """Update an existing transaction"""
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)

    if request.method == 'POST':
        form = TransactionForm(request.POST, instance=transaction)
        if form.is_valid():
            form.save()
            messages.success(request, 'Transaction updated successfully!')
            return redirect('transaction_list')
    else:
        form = TransactionForm(instance=transaction)

    return render(request, 'transactions/transaction_form.html', {
        'form': form,
        'title': 'Edit Transaction'
    })

@login_required
def transaction_delete(request, pk):
    """Delete a transaction"""
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)

    if request.method == 'POST':
        transaction.delete()
        messages.success(request, 'Transaction deleted successfully!')
        return redirect('transaction_list')

    return render(request, 'transactions/transaction_confirm_delete.html', {
        'transaction': transaction
    })

@login_required
def category_list(request):
    """List all categories"""
    categories = Category.objects.all()
    return render(request, 'transactions/category_list.html', {
        'categories': categories
    })

@login_required
def category_create(request):
    """Create a new category"""
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category created successfully!')
            return redirect('category_list')
    else:
        form = CategoryForm()

    return render(request, 'transactions/category_form.html', {
        'form': form,
        'title': 'Add Category'
    })

@login_required
def import_csv_view(request):
    """Import transactions from CSV file"""
    if request.method == 'POST':
        form = CSVImportForm(request.POST, request.FILES)
        if form.is_valid():
            file = form.cleaned_data['file']
            # Apply date format to YYYY-MM-DD if needed based on user input
            date_col = form.cleaned_data['date_column']

            #date_col = form.cleaned_data['date_column']
            desc_col = form.cleaned_data['description_column']
            # remove commas from amount column name if any and trailing zeros
            amount_col = form.cleaned_data['amount_column'].replace(',', '').rstrip('0').rstrip('.')
            category_col = form.cleaned_data.get('category_column')

            try:
                df = pd.read_csv(io.StringIO(file.read().decode('utf-8')))
                transactions = []
                skipped_duplicates = 0

                # Get existing transactions for duplicate checking
                existing_transactions = set(
                    Transaction.objects.filter(user=request.user).values_list(
                        'date', 'description', 'amount'
                    )
                )

                for _, row in df.iterrows():
                    try:
                        # Validate and sanitize inputs
                        raw_description = str(row.get(desc_col, '')).strip()
                        if not raw_description:
                            continue  # Skip rows with empty descriptions

                        raw_amount = str(row.get(amount_col, '')).strip()
                        if not raw_amount:
                            continue  # Skip rows with empty amounts

                        # Clean and parse amount (handle currency symbols and commas)
                        clean_amount = raw_amount.replace('$', '').replace(',', '').strip()
                        try:
                            amount = float(clean_amount)
                        except ValueError:
                            continue  # Skip invalid amounts

                        # Validate amount is not zero (optional, depending on business logic)
                        if amount == 0:
                            continue

                        # Parse date
                        raw_date = str(row.get(date_col, '')).strip()
                        if not raw_date:
                            continue  # Skip rows with empty dates

                        # Convert date format if needed (DD-MM-YYYY to YYYY-MM-DD)
                        formatted_date = convert_dd_mm_yyyy_to_yyyy_mm_dd(raw_date)
                        try:
                            parsed_date = datetime.strptime(formatted_date, '%Y-%m-%d').date()
                        except ValueError:
                            continue  # Skip invalid dates

                        # Check for duplicates
                        transaction_tuple = (parsed_date, raw_description, amount)
                        if transaction_tuple in existing_transactions:
                            skipped_duplicates += 1
                            continue  # Skip duplicate transactions

                        transaction_data = {
                            'date': parsed_date,
                            'description': raw_description,
                            'amount': amount,
                            'user': request.user
                        }
                    except KeyError as e:
                        # Handle missing columns gracefully
                        messages.warning(request, f'Skipping row due to missing column: {e}')
                        continue
                    except Exception as e:
                        # Log and skip problematic rows
                        messages.warning(request, f'Skipping row due to error: {str(e)}')
                        continue

                    if category_col and category_col in row:
                        category, _ = Category.objects.get_or_create(name=str(row[category_col]))
                        transaction_data['category'] = category
                    else:
                        # Auto-categorize
                        transaction_data['category'] = auto_categorize(transaction_data['description'])

                    transactions.append(Transaction(**transaction_data))

                # Bulk create new transactions
                if transactions:
                    Transaction.objects.bulk_create(transactions)

                # Provide feedback on import results
                success_message = f'Successfully imported {len(transactions)} transactions!'
                if skipped_duplicates > 0:
                    success_message += f' Skipped {skipped_duplicates} duplicate transactions.'
                messages.success(request, success_message)

                return redirect('dashboard')

            except Exception as e:
                messages.error(request, f'Import failed: {str(e)}')
    else:
        form = CSVImportForm()

    return render(request, 'transactions/import_csv.html', {
        'form': form,
        'title': 'Import CSV'
    })

@login_required
def import_pdf_view(request):
    """Import transactions from PDF file"""
    if request.method == 'POST':
        form = PDFImportForm(request.POST, request.FILES)
        if form.is_valid():
            file = form.cleaned_data['file']

            try:
                import tabula
                import pandas as pd
                from datetime import datetime

                transactions = []

                # Extract tables from PDF using tabula
                dfs = tabula.read_pdf(file, pages='all', multiple_tables=True)

                for df in dfs:
                    if df.empty:
                        continue

                    # Clean column names
                    df.columns = df.columns.str.strip().str.lower()

                    # Try to identify columns (flexible mapping)
                    column_mapping = {}

                    # Look for date column
                    date_cols = [col for col in df.columns if any(keyword in col.lower() for keyword in ['date', 'fecha', 'fecha_transaccion'])]
                    if date_cols:
                        column_mapping['date'] = date_cols[0]

                    # Look for description column
                    desc_cols = [col for col in df.columns if any(keyword in col.lower() for keyword in ['description', 'desc', 'descripcion', 'concepto', 'detalle'])]
                    if desc_cols:
                        column_mapping['description'] = desc_cols[0]

                    # Look for amount column
                    amount_cols = [col for col in df.columns if any(keyword in col.lower() for keyword in ['amount', 'monto', 'valor', 'importe', 'total'])]
                    if amount_cols:
                        column_mapping['amount'] = amount_cols[0]

                    # Look for category column (optional)
                    category_cols = [col for col in df.columns if any(keyword in col.lower() for keyword in ['category', 'categoria', 'tipo', 'clasificacion'])]
                    if category_cols:
                        column_mapping['category'] = category_cols[0]

                    # Process each row
                    for _, row in df.iterrows():
                        try:
                            # Parse date
                            date_str = str(row[column_mapping.get('date', df.columns[0])]).strip()
                            parsed_date = None

                            # Try different date formats
                            date_formats = ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%Y/%m/%d']
                            for fmt in date_formats:
                                try:
                                    parsed_date = datetime.strptime(date_str, fmt).date()
                                    break
                                except ValueError:
                                    continue

                            if parsed_date is None:
                                continue  # Skip rows without valid dates

                            # Parse amount
                            amount_str = str(row[column_mapping.get('amount', df.columns[-1])]).strip()
                            # Remove currency symbols and clean
                            amount_str = amount_str.replace('$', '').replace(',', '').strip()
                            try:
                                amount = float(amount_str)
                            except ValueError:
                                continue  # Skip rows without valid amounts

                            # Get description
                            description = str(row[column_mapping.get('description', df.columns[1] if len(df.columns) > 1 else df.columns[0])]).strip()
                            if not description:
                                continue

                            transaction_data = {
                                'date': parsed_date,
                                'description': description,
                                'amount': amount,
                                'user': request.user
                            }

                            # Handle category if available
                            if 'category' in column_mapping and column_mapping['category'] in row:
                                category_name = str(row[column_mapping['category']]).strip()
                                if category_name:
                                    category, _ = Category.objects.get_or_create(name=category_name)
                                    transaction_data['category'] = category

                            # Auto-categorize if no category provided
                            if 'category' not in transaction_data:
                                transaction_data['category'] = auto_categorize(description)

                            transactions.append(Transaction(**transaction_data))

                        except Exception as e:
                            # Skip problematic rows but continue processing
                            continue

                Transaction.objects.bulk_create(transactions)
                messages.success(request, f'Successfully imported {len(transactions)} transactions from PDF!')
                return redirect('dashboard')

            except ImportError as e:
                messages.error(request, f'PDF processing libraries not available. Please install tabula-py: {str(e)}')
            except Exception as e:
                messages.error(request, f'PDF processing failed: {str(e)}')
    else:
        form = PDFImportForm()

    return render(request, 'transactions/import_pdf.html', {
        'form': form,
        'title': 'Import PDF'
    })

def convert_dd_mm_yyyy_to_yyyy_mm_dd(date_str):
    """
    Convert a date string from DD-MM-YYYY format to YYYY-MM-DD format.

    Args:
        date_str (str): Date string in DD-MM-YYYY format

    Returns:
        str: Date string in YYYY-MM-DD format, or original string if conversion fails
    """
    try:
        # Parse the date from DD-MM-YYYY format
        date_obj = datetime.strptime(date_str.strip(), '%d-%m-%Y')
        # Convert to YYYY-MM-DD format
        return date_obj.strftime('%Y-%m-%d')
    except ValueError:
        # Return original string if parsing fails
        return date_str

def auto_categorize(description):
    """Auto-categorize transaction based on description"""
    keywords = {
        'food': ['restaurant', 'grocery', 'food', 'cafe', 'dinner'],
        'transport': ['taxi', 'bus', 'train', 'gas', 'parking'],
        'entertainment': ['movie', 'game', 'concert', 'party'],
        'utilities': ['electricity', 'water', 'internet', 'phone'],
        'shopping': ['clothes', 'shoes', 'amazon', 'store']
    }

    description_lower = description.lower()
    for category_name, words in keywords.items():
        if any(word in description_lower for word in words):
            category, _ = Category.objects.get_or_create(name=category_name.capitalize())
            return category

    # Default category
    category, _ = Category.objects.get_or_create(name='Other')
    return category
