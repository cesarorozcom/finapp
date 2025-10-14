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
            import pdfplumber
            import re
            from datetime import datetime

            transactions = []

            with pdfplumber.open(file) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        # Parse transactions from PDF text
                        # This is a flexible parser that can be adapted to different PDF formats
                        lines = text.split('\n')
                        for line in lines:
                            # Look for patterns like: Date Description Amount
                            # Example patterns to match:
                            # "2023-01-15 Grocery Store $45.67"
                            # "01/15/2023 RESTAURANT -25.50"
                            # "15-Jan-2023 Online Purchase 123.45"

                            # Try different date formats and amount patterns
                            date_patterns = [
                                r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD
                                r'(\d{2}/\d{2}/\d{4})',  # MM/DD/YYYY
                                r'(\d{2}-\w{3}-\d{4})',  # DD-MMM-YYYY
                            ]

                            amount_patterns = [
                                r'\$?(-?\d+\.?\d{0,2})',  # $45.67 or -25.50
                                r'(-?\d+\.?\d{0,2})\s*\$?',  # 45.67$ or -25.50
                            ]

                            for date_pattern in date_patterns:
                                date_match = re.search(date_pattern, line)
                                if date_match:
                                    date_str = date_match.group(1)
                                    # Convert to standard format
                                    try:
                                        if '-' in date_str and len(date_str.split('-')[0]) == 4:
                                            parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                                        elif '/' in date_str:
                                            parsed_date = datetime.strptime(date_str, '%m/%d/%Y').date()
                                        elif '-' in date_str and len(date_str.split('-')[2]) == 4:
                                            parsed_date = datetime.strptime(date_str, '%d-%b-%Y').date()
                                        else:
                                            continue

                                        # Extract description and amount
                                        # Remove the date from the line
                                        remaining = re.sub(date_pattern, '', line).strip()

                                        # Find amount
                                        amount = None
                                        for amount_pattern in amount_patterns:
                                            amount_match = re.search(amount_pattern, remaining)
                                            if amount_match:
                                                amount_str = amount_match.group(1)
                                                try:
                                                    amount = float(amount_str)
                                                    # Remove amount from remaining text
                                                    remaining = re.sub(amount_pattern, '', remaining).strip()
                                                    break
                                                except ValueError:
                                                    continue

                                        if amount is not None:
                                            description = remaining.strip()
                                            if description:
                                                transaction_data = {
                                                    'date': parsed_date,
                                                    'description': description,
                                                    'amount': amount,
                                                    'user': request.user
                                                }

                                                # Auto-categorize
                                                transaction_data['category'] = self._auto_categorize(description)

                                                transactions.append(Transaction(**transaction_data))
                                    except ValueError:
                                        continue
                                    break

            Transaction.objects.bulk_create(transactions)
            return Response({'message': f'Imported {len(transactions)} transactions from PDF'}, status=status.HTTP_201_CREATED)

        except ImportError:
            return Response({'error': 'PDF processing libraries not installed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
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
            date_col = form.cleaned_data['date_column']
            desc_col = form.cleaned_data['description_column']
            amount_col = form.cleaned_data['amount_column']
            category_col = form.cleaned_data.get('category_column')

            try:
                df = pd.read_csv(io.StringIO(file.read().decode('utf-8')))
                transactions = []

                for _, row in df.iterrows():
                    transaction_data = {
                        'date': row[date_col],
                        'description': row[desc_col],
                        'amount': float(row[amount_col]),
                        'user': request.user
                    }

                    if category_col and category_col in row:
                        category, _ = Category.objects.get_or_create(name=str(row[category_col]))
                        transaction_data['category'] = category
                    else:
                        # Auto-categorize
                        transaction_data['category'] = auto_categorize(transaction_data['description'])

                    transactions.append(Transaction(**transaction_data))

                Transaction.objects.bulk_create(transactions)
                messages.success(request, f'Successfully imported {len(transactions)} transactions!')
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
                import pdfplumber
                import re
                from datetime import datetime

                transactions = []

                with pdfplumber.open(file) as pdf:
                    for page in pdf.pages:
                        text = page.extract_text()
                        if text:
                            lines = text.split('\n')
                            for line in lines:
                                date_patterns = [
                                    r'(\d{4}-\d{2}-\d{2})',
                                    r'(\d{2}/\d{2}/\d{4})',
                                    r'(\d{2}-\w{3}-\d{4})',
                                ]

                                amount_patterns = [
                                    r'\$?(-?\d+\.?\d{0,2})',
                                    r'(-?\d+\.?\d{0,2})\s*\$?',
                                ]

                                for date_pattern in date_patterns:
                                    date_match = re.search(date_pattern, line)
                                    if date_match:
                                        date_str = date_match.group(1)
                                        try:
                                            if '-' in date_str and len(date_str.split('-')[0]) == 4:
                                                parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                                            elif '/' in date_str:
                                                parsed_date = datetime.strptime(date_str, '%m/%d/%Y').date()
                                            elif '-' in date_str and len(date_str.split('-')[2]) == 4:
                                                parsed_date = datetime.strptime(date_str, '%d-%b-%Y').date()
                                            else:
                                                continue

                                            remaining = re.sub(date_pattern, '', line).strip()

                                            amount = None
                                            for amount_pattern in amount_patterns:
                                                amount_match = re.search(amount_pattern, remaining)
                                                if amount_match:
                                                    amount_str = amount_match.group(1)
                                                    try:
                                                        amount = float(amount_str)
                                                        remaining = re.sub(amount_pattern, '', remaining).strip()
                                                        break
                                                    except ValueError:
                                                        continue

                                            if amount is not None:
                                                description = remaining.strip()
                                                if description:
                                                    transaction_data = {
                                                        'date': parsed_date,
                                                        'description': description,
                                                        'amount': amount,
                                                        'user': request.user,
                                                        'category': auto_categorize(description)
                                                    }
                                                    transactions.append(Transaction(**transaction_data))
                                        except ValueError:
                                            continue
                                        break

                Transaction.objects.bulk_create(transactions)
                messages.success(request, f'Successfully imported {len(transactions)} transactions from PDF!')
                return redirect('dashboard')

            except ImportError:
                messages.error(request, 'PDF processing libraries not available')
            except Exception as e:
                messages.error(request, f'PDF processing failed: {str(e)}')
    else:
        form = PDFImportForm()

    return render(request, 'transactions/import_pdf.html', {
        'form': form,
        'title': 'Import PDF'
    })

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
