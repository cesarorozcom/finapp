from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q, Count
from django.db.models.functions import TruncMonth
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from plotly.offline import plot
import pandas as pd
from transactions.models import Transaction, Category

@login_required
def dashboard(request):
    user = request.user

    # Get selected month/year from request parameters, default to current month
    now = datetime.now()
    selected_month = int(request.GET.get('month', now.month))
    selected_year = int(request.GET.get('year', now.year))

    # Validate month and year ranges
    if not (1 <= selected_month <= 12):
        selected_month = now.month
    if not (2000 <= selected_year <= now.year + 1):  # Allow future year for planning
        selected_year = now.year

    # Monthly summary for selected period
    monthly_transactions = Transaction.objects.filter(
        user=user,
        date__year=selected_year,
        date__month=selected_month
    )

    total_income = monthly_transactions.filter(amount__lt=0).aggregate(Sum('amount'))['amount__sum'] or 0
    total_expenses = monthly_transactions.filter(amount__gt=0).aggregate(Sum('amount'))['amount__sum'] or 0

    # Category breakdown for expenses
    category_expenses = monthly_transactions.filter(amount__gt=0).values('category__name').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')

    # Monthly trends for last 12 months centered around selected period
    selected_date = datetime(selected_year, selected_month, 1)
    # Show 6 months before and 5 months after selected month for 12-month view
    start_date = (selected_date - timedelta(days=180)).replace(day=1)
    end_date = (selected_date + timedelta(days=150)).replace(day=1) + timedelta(days=32)
    end_date = end_date.replace(day=1) - timedelta(days=1)  # Last day of the month

    monthly_trends = Transaction.objects.filter(
        user=user,
        date__range=[start_date, end_date]
    ).annotate(
        month=TruncMonth('date')
    ).values('month').annotate(
        income=Sum('amount', filter=Q(amount__lt=0)),
        expenses=Sum('amount', filter=Q(amount__gt=0))
    ).order_by('month')

    # Create month/year options for dropdowns
    months = [
        {'value': i, 'name': datetime(2000, i, 1).strftime('%B'), 'selected': i == selected_month}
        for i in range(1, 13)
    ]
    years = [
        {'value': y, 'selected': y == selected_year}
        for y in range(now.year - 2, now.year + 2)  # Last 2 years + current + next year
    ]

    # Create visualizations
    context = {
        'total_income': abs(total_income),
        'total_expenses': total_expenses,
        'net_amount': abs(total_income) - total_expenses,
        'category_expenses': list(category_expenses),
        'selected_month': selected_month,
        'selected_year': selected_year,
        'months': months,
        'years': years,
        'current_month': now.month,
        'current_year': now.year,
    }

    # Pie chart for category expenses
    if category_expenses:
        df_categories = pd.DataFrame(list(category_expenses))
        fig_pie = px.pie(df_categories, values='total', names='category__name', title='Expenses by Category')
        context['pie_chart'] = plot(fig_pie, output_type='div', include_plotlyjs=False)

    # Line chart for monthly trends
    if monthly_trends:
        df_trends = pd.DataFrame(list(monthly_trends))
        df_trends['month'] = pd.to_datetime(df_trends['month'])
        df_trends['income'] = df_trends['income'].fillna(0).abs()
        df_trends['expenses'] = df_trends['expenses'].fillna(0)

        fig_trends = go.Figure()
        fig_trends.add_trace(go.Scatter(x=df_trends['month'], y=df_trends['income'], mode='lines+markers', name='Income'))
        fig_trends.add_trace(go.Scatter(x=df_trends['month'], y=df_trends['expenses'], mode='lines+markers', name='Expenses'))
        fig_trends.update_layout(title='Monthly Income vs Expenses', xaxis_title='Month', yaxis_title='Amount')
        context['trends_chart'] = plot(fig_trends, output_type='div', include_plotlyjs=False)

    # "Where does my money go?" insight
    top_categories = category_expenses[:5]  # Top 5 expense categories
    total_top_expenses = sum(cat['total'] for cat in top_categories)
    percentage_top = (total_top_expenses / total_expenses * 100) if total_expenses > 0 else 0

    context['money_goes_insight'] = {
        'top_categories': top_categories,
        'total_top_expenses': total_top_expenses,
        'percentage_top': round(percentage_top, 1),
        'remaining_percentage': round(100 - percentage_top, 1)
    }

    return render(request, 'budget_dashboard/dashboard.html', context)