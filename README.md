# Money-based Budget Tracker

A comprehensive financial management application built with Django, FastAPI, and modern web technologies. Features full Spanish localization and deployment-ready for Vercel.

## 🚀 Features

### Core Functionality
- ✅ **Manual Transaction Entry**: Add income and expenses with detailed categorization
- ✅ **CSV Import**: Flexible column mapping for various CSV formats
- ✅ **PDF Import**: OCR-powered document processing for bank statements
- ✅ **Automatic Categorization**: Smart keyword-based expense categorization
- ✅ **Multi-user Support**: Secure user authentication and data isolation

### Analytics & Insights
- ✅ **Monthly Income vs Expense Tracking**: Comprehensive financial overview
- ✅ **Category-wise Summaries**: Detailed spending breakdowns
- ✅ **Interactive Visualizations**: Pie charts and trend graphs using Plotly
- ✅ **"Where Does My Money Go?" Analysis**: Top spending insights

### Technical Features
- ✅ **REST API**: Full CRUD operations via Django REST Framework
- ✅ **FastAPI Integration**: High-performance API endpoints
- ✅ **Spanish Localization**: Complete i18n support for Spanish-speaking users
- ✅ **Vercel Deployment**: Production-ready configuration
- ✅ **Database Flexibility**: PostgreSQL for production, SQLite for development

## 🛠️ Technology Stack

- **Backend**: Django 4.2.8 + FastAPI
- **Database**: PostgreSQL (production) / SQLite (development)
- **API**: Django REST Framework + FastAPI
- **Frontend**: Django Templates + Plotly.js
- **Deployment**: Vercel (serverless)
- **Data Processing**: Pandas, OpenCV, PyPDF2, Tesseract OCR

## 📦 Installation

### Local Development

1. **Clone and setup**:
```bash
cd finapp
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Database setup**:
```bash
python manage.py migrate
python manage.py createsuperuser
```

3. **Run development server**:
```bash
python manage.py runserver
```

4. **Access the application**:
- Main app: http://127.0.0.1:8000/
- API: http://127.0.0.1:8000/api/
- Admin: http://127.0.0.1:8000/admin/

### Vercel Deployment

1. **Connect to Vercel**:
```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
vercel --prod
```

2. **Environment Variables** (in Vercel dashboard):
```
DJANGO_SETTINGS_MODULE=budget_tracker.settings
DB_NAME=your_postgres_db
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=your_db_host
DB_PORT=5432
SECRET_KEY=your_secret_key
```

## 🌐 API Endpoints

### Transactions
- `GET /api/transactions/` - List user transactions
- `POST /api/transactions/` - Create new transaction
- `GET /api/transactions/{id}/` - Get transaction details
- `PUT /api/transactions/{id}/` - Update transaction
- `DELETE /api/transactions/{id}/` - Delete transaction
- `POST /api/transactions/import_csv/` - Import CSV file
- `GET /api/transactions/summary/` - Get financial summary
- `GET /api/transactions/monthly_trends/` - Get monthly trends

### Categories
- `GET /api/categories/` - List categories
- `POST /api/categories/` - Create category
- `GET /api/categories/{id}/` - Get category details
- `PUT /api/categories/{id}/` - Update category
- `DELETE /api/categories/{id}/` - Delete category

## 📊 Data Model

### Transaction
```python
{
    "id": "integer",
    "user": "User",
    "date": "2025-01-15",
    "description": "Grocery shopping",
    "category": "Category",
    "amount": -45.67,  # Negative for income, positive for expenses
    "created_at": "datetime",
    "updated_at": "datetime"
}
```

### Category
```python
{
    "id": "integer",
    "name": "Food & Dining",
    "created_at": "datetime",
    "updated_at": "datetime"
}
```

## 🔧 Configuration

### Spanish Localization
- Default language: Spanish (`es`)
- Timezone: Colombia (`America/Bogota`)
- Translation files: `locale/es/LC_MESSAGES/django.po`

### Database Configuration
- **Development**: SQLite (automatic fallback)
- **Production**: PostgreSQL via environment variables

## 📈 Usage Examples

### Adding a Transaction
```python
# Via API
POST /api/transactions/
{
    "date": "2025-01-15",
    "description": "Weekly groceries",
    "amount": 85.50,
    "category": 1
}
```

### Importing CSV
```python
# Via API with form data
POST /api/transactions/import_csv/
- file: transactions.csv
- date_column: date
- description_column: description
- amount_column: amount
- category_column: category  # optional
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Django community for the excellent framework
- FastAPI for high-performance API development
- Plotly for beautiful data visualizations
- Vercel for seamless deployment

---

**Built with ❤️ for financial freedom and data-driven decision making**
