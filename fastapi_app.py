"""
FastAPI integration for the Budget Tracker
This provides additional API endpoints alongside Django REST Framework
"""
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import date
import secrets
import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budget_tracker.settings')
django.setup()

from transactions.models import Transaction, Category
from django.contrib.auth.models import User
from django.db import transaction as db_transaction

# FastAPI app
app = FastAPI(
    title="Budget Tracker API",
    description="FastAPI endpoints for the Money-based Budget Tracker",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:8000"],  # Add your frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBasic()

# Pydantic models
class TransactionBase(BaseModel):
    date: date
    description: str
    amount: float
    category_id: Optional[int] = None

class TransactionCreate(TransactionBase):
    pass

class TransactionResponse(TransactionBase):
    id: int
    category_name: Optional[str] = None

    class Config:
        from_attributes = True

class CategoryBase(BaseModel):
    name: str

class CategoryCreate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    id: int

    class Config:
        from_attributes = True

class SummaryResponse(BaseModel):
    total_income: float
    total_expenses: float
    net_amount: float
    category_summary: List[dict]

# Authentication dependency
def authenticate_user(credentials: HTTPBasicCredentials = Depends(security)):
    """Authenticate user with HTTP Basic Auth"""
    try:
        user = User.objects.get(username=credentials.username)
        if not user.check_password(credentials.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Basic"},
            )
        return user
    except User.DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

# API Routes
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "budget-tracker-fastapi"}

@app.get("/transactions/", response_model=List[TransactionResponse])
async def get_transactions(
    user: User = Depends(authenticate_user),
    skip: int = 0,
    limit: int = 100
):
    """Get user's transactions"""
    transactions = Transaction.objects.filter(user=user).order_by('-date')[skip:skip+limit]
    return [
        TransactionResponse(
            id=t.id,
            date=t.date,
            description=t.description,
            amount=float(t.amount),
            category_id=t.category.id if t.category else None,
            category_name=t.category.name if t.category else None
        )
        for t in transactions
    ]

@app.post("/transactions/", response_model=TransactionResponse)
async def create_transaction(
    transaction: TransactionCreate,
    user: User = Depends(authenticate_user)
):
    """Create a new transaction"""
    # Auto-categorize if no category provided
    category = None
    if transaction.category_id:
        try:
            category = Category.objects.get(id=transaction.category_id)
        except Category.DoesNotExist:
            raise HTTPException(status_code=404, detail="Category not found")
    else:
        # Auto-categorize based on description
        category = auto_categorize(transaction.description)

    db_trans = Transaction.objects.create(
        user=user,
        date=transaction.date,
        description=transaction.description,
        amount=transaction.amount,
        category=category
    )

    return TransactionResponse(
        id=db_trans.id,
        date=db_trans.date,
        description=db_trans.description,
        amount=float(db_trans.amount),
        category_id=db_trans.category.id if db_trans.category else None,
        category_name=db_trans.category.name if db_trans.category else None
    )

@app.get("/transactions/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: int,
    user: User = Depends(authenticate_user)
):
    """Get a specific transaction"""
    try:
        trans = Transaction.objects.get(id=transaction_id, user=user)
        return TransactionResponse(
            id=trans.id,
            date=trans.date,
            description=trans.description,
            amount=float(trans.amount),
            category_id=trans.category.id if trans.category else None,
            category_name=trans.category.name if trans.category else None
        )
    except Transaction.DoesNotExist:
        raise HTTPException(status_code=404, detail="Transaction not found")

@app.put("/transactions/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: int,
    transaction: TransactionCreate,
    user: User = Depends(authenticate_user)
):
    """Update a transaction"""
    try:
        db_trans = Transaction.objects.get(id=transaction_id, user=user)

        category = None
        if transaction.category_id:
            try:
                category = Category.objects.get(id=transaction.category_id)
            except Category.DoesNotExist:
                raise HTTPException(status_code=404, detail="Category not found")

        db_trans.date = transaction.date
        db_trans.description = transaction.description
        db_trans.amount = transaction.amount
        db_trans.category = category
        db_trans.save()

        return TransactionResponse(
            id=db_trans.id,
            date=db_trans.date,
            description=db_trans.description,
            amount=float(db_trans.amount),
            category_id=db_trans.category.id if db_trans.category else None,
            category_name=db_trans.category.name if db_trans.category else None
        )
    except Transaction.DoesNotExist:
        raise HTTPException(status_code=404, detail="Transaction not found")

@app.delete("/transactions/{transaction_id}")
async def delete_transaction(
    transaction_id: int,
    user: User = Depends(authenticate_user)
):
    """Delete a transaction"""
    try:
        trans = Transaction.objects.get(id=transaction_id, user=user)
        trans.delete()
        return {"message": "Transaction deleted successfully"}
    except Transaction.DoesNotExist:
        raise HTTPException(status_code=404, detail="Transaction not found")

@app.get("/categories/", response_model=List[CategoryResponse])
async def get_categories():
    """Get all categories"""
    categories = Category.objects.all()
    return [CategoryResponse(id=c.id, name=c.name) for c in categories]

@app.post("/categories/", response_model=CategoryResponse)
async def create_category(category: CategoryCreate):
    """Create a new category"""
    db_category = Category.objects.create(name=category.name)
    return CategoryResponse(id=db_category.id, name=db_category.name)

@app.get("/summary/")
async def get_summary(
    user: User = Depends(authenticate_user),
    month: Optional[int] = None,
    year: Optional[int] = None
):
    """Get financial summary"""
    queryset = Transaction.objects.filter(user=user)

    if month and year:
        queryset = queryset.filter(date__year=year, date__month=month)

    total_income = queryset.filter(amount__lt=0).aggregate(total=Sum('amount'))['total'] or 0
    total_expenses = queryset.filter(amount__gt=0).aggregate(total=Sum('amount'))['total'] or 0

    category_summary = queryset.filter(amount__gt=0).values('category__name').annotate(
        total=Sum('amount')
    ).order_by('-total')

    return SummaryResponse(
        total_income=abs(float(total_income)),
        total_expenses=float(total_expenses),
        net_amount=abs(float(total_income)) - float(total_expenses),
        category_summary=list(category_summary)
    )

@app.post("/import/csv/")
async def import_csv(
    file: UploadFile = File(...),
    date_column: str = Form(...),
    description_column: str = Form(...),
    amount_column: str = Form(...),
    user: User = Depends(authenticate_user)
):
    """Import transactions from CSV"""
    try:
        import pandas as pd
        import io

        df = pd.read_csv(io.StringIO((await file.read()).decode('utf-8')))

        transactions = []
        for _, row in df.iterrows():
            transaction_data = {
                'date': row[date_column],
                'description': row[description_column],
                'amount': float(row[amount_column]),
                'user': user
            }

            # Auto-categorize
            transaction_data['category'] = auto_categorize(transaction_data['description'])

            transactions.append(Transaction(**transaction_data))

        Transaction.objects.bulk_create(transactions)
        return {"message": f"Imported {len(transactions)} transactions"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Import failed: {str(e)}")

@app.post("/import/pdf/")
async def import_pdf(
    file: UploadFile = File(...),
    user: User = Depends(authenticate_user)
):
    """Import transactions from PDF"""
    try:
        import pdfplumber
        import re
        from datetime import datetime
        import io

        content = await file.read()
        transactions = []

        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    lines = text.split('\n')
                    for line in lines:
                        # Parse transactions (same logic as Django view)
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
                                                'user': user,
                                                'category': auto_categorize(description)
                                            }
                                            transactions.append(Transaction(**transaction_data))
                                except ValueError:
                                    continue
                                break

        Transaction.objects.bulk_create(transactions)
        return {"message": f"Imported {len(transactions)} transactions from PDF"}

    except ImportError:
        raise HTTPException(status_code=500, detail="PDF processing libraries not available")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"PDF processing failed: {str(e)}")

# Helper functions
def auto_categorize(description: str) -> Optional[Category]:
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

# Import Sum for aggregations
from django.db.models import Sum