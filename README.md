# Money-based Budget Tracker

A comprehensive personal finance management application built with Django and FastAPI, featuring a modern Bootstrap 5 interface and powerful data import capabilities.

## ✨ Features

### 💰 Core Functionality
- **Manual Transaction Entry**: Add income and expenses with detailed descriptions and automatic categorization
- **CSV Import**: Flexible column mapping for importing transaction data from various sources
- **PDF Import**: Intelligent text parsing and OCR support for bank statements and financial documents
- **Automatic Categorization**: Smart keyword-based categorization with expandable AI/ML support
- **Monthly Tracking**: Comprehensive income vs expense analysis with monthly summaries
- **Category Analysis**: Detailed breakdowns by spending categories with visual insights

### 📊 Dashboard & Visualizations
- **Interactive Charts**: Beautiful pie charts for expense categories, line charts for spending trends over time
- **"Where Does My Money Go?" Insights**: AI-powered analysis of top spending categories with percentage breakdowns
- **Financial Summary Cards**: Visual overview of income, expenses, and net amount with color-coded indicators
- **Real-time Data**: Dynamic updates and responsive visualizations using Plotly.js
- **Progress Bars**: Visual percentage representation of spending by category

### 🛠️ Technical Features
- **Dual API Architecture**: Django REST Framework + FastAPI for maximum flexibility
- **User Authentication**: Secure multi-user support with Django's authentication system
- **Data Validation**: Comprehensive input validation and error handling
- **Responsive Design**: Modern Bootstrap 5 web interface that works perfectly on all devices
- **Professional UI**: Consistent design language with intuitive navigation and user experience
- **Database**: SQLite with SQLAlchemy ORM support for easy migration to other databases

## Quick Start

### Prerequisites
- Python 3.9+
- pip

### Installation

1. **Navigate to the project directory**:
   ```bash
   cd finapp
   ```

2. **Install dependencies**:
   ```bash
   pip3 install django fastapi uvicorn sqlalchemy pandas matplotlib plotly djangorestframework django-crispy-forms crispy-bootstrap5 pdfplumber pytesseract opencv-python
   ```

3. **Run database migrations**:
   ```bash
   python3 manage.py makemigrations
   python3 manage.py migrate
   ```

4. **Create superuser account**:
   ```bash
   python3 manage.py createsuperuser
   ```

5. **Start the Django development server**:
   ```bash
   python3 manage.py runserver
   ```

### Access Points

- **🏠 Dashboard**: http://127.0.0.1:8000/ - Main financial overview with charts and insights
- **💰 Transactions**: http://127.0.0.1:8000/api/web/transactions/ - Manage transactions
- **📁 Categories**: http://127.0.0.1:8000/api/web/categories/ - Manage categories
- **📤 Import CSV**: http://127.0.0.1:8000/api/web/import/csv/ - Import CSV files
- **📤 Import PDF**: http://127.0.0.1:8000/api/web/import/pdf/ - Import PDF documents
- **🔧 Django API**: http://127.0.0.1:8000/api/ - REST API endpoints
- **⚙️ Admin Panel**: http://127.0.0.1:8000/admin/ - Django administration
- **🚀 FastAPI**: http://127.0.0.1:8001/ - Additional API endpoints (run separately)

## 🚀 Usage Guide

### Web Interface

The application provides a modern, responsive web interface accessible at http://127.0.0.1:8000/

#### Dashboard Features
- **Financial Summary**: Visual cards showing income, expenses, and net amount
- **Spending Insights**: "Where does my money go?" analysis with top categories
- **Interactive Charts**: Pie charts for categories, line charts for monthly trends
- **Category Breakdown**: Detailed table with percentages and transaction counts
- **Quick Actions**: Direct access to add transactions and import data

#### Transaction Management
- **List View**: Filterable and paginated transaction list with search
- **Add/Edit Forms**: User-friendly forms with automatic categorization
- **Delete Confirmation**: Safe deletion with transaction preview
- **Bulk Import**: CSV and PDF import with flexible column mapping

#### Data Import
- **CSV Import**: Map columns flexibly, supports various formats
- **PDF Import**: Intelligent text parsing from bank statements
- **Auto-Categorization**: Smart keyword matching for transaction categories

### API Usage

#### Django REST Framework API (Port 8000)

**Transactions**:
```bash
# List transactions
GET /api/transactions/

# Create transaction
POST /api/transactions/
{
    "date": "2023-01-01",
    "description": "Grocery shopping",
    "category": 1,
    "amount": 50.00
}

# Import CSV
POST /api/transactions/import_csv/
Content-Type: multipart/form-data
file: transactions.csv
date_column: date
description_column: description
amount_column: amount

# Import PDF
POST /api/transactions/import_pdf/
Content-Type: multipart/form-data
file: bank_statement.pdf

# Get summary
GET /api/transactions/summary/?month=1&year=2024

# Get monthly trends
GET /api/transactions/monthly_trends/?months=12
```

**Categories**:
```bash
# List categories
GET /api/categories/

# Create category
POST /api/categories/
{
    "name": "Food & Dining"
}
```

#### FastAPI (Port 8001)

**Health Check**:
```bash
GET /health
```

**Transactions**:
```bash
GET /transactions/
POST /transactions/
GET /transactions/{id}
PUT /transactions/{id}
DELETE /transactions/{id}
```

**Import Operations**:
```bash
POST /import/csv/
POST /import/pdf/
```

## Data Model

### Transaction
- **ID**: Unique identifier
- **Date**: Transaction date
- **Description**: Transaction details
- **Category**: Spending category (optional)
- **Amount**: Transaction amount (positive = expense, negative = income)
- **User**: Associated user

### Category
- **ID**: Unique identifier
- **Name**: Category name
- **Timestamps**: Created/updated dates

## Testing

Run the test suite:
```bash
python3 manage.py test transactions.tests -v 2
```

## 📋 API Reference

### Django REST Framework Endpoints (Port 8000)

#### Transactions
- `GET /api/transactions/` - List user transactions with filtering
- `POST /api/transactions/` - Create new transaction
- `GET /api/transactions/{id}/` - Get transaction details
- `PUT /api/transactions/{id}/` - Update transaction
- `DELETE /api/transactions/{id}/` - Delete transaction
- `POST /api/transactions/import_csv/` - Import CSV with column mapping
- `POST /api/transactions/import_pdf/` - Import PDF documents
- `GET /api/transactions/summary/` - Get financial summary by month/year
- `GET /api/transactions/monthly_trends/` - Get spending trends over time

#### Categories
- `GET /api/categories/` - List all categories
- `POST /api/categories/` - Create new category
- `GET /api/categories/{id}/` - Get category details
- `PUT /api/categories/{id}/` - Update category
- `DELETE /api/categories/{id}/` - Delete category

### FastAPI Endpoints (Port 8001)

#### Health & Status
- `GET /health` - Application health check

#### Transactions
- `GET /transactions/` - List transactions with pagination
- `POST /transactions/` - Create transaction
- `GET /transactions/{id}` - Get specific transaction
- `PUT /transactions/{id}` - Update transaction
- `DELETE /transactions/{id}` - Delete transaction

#### Categories
- `GET /categories/` - List categories
- `POST /categories/` - Create category
- `GET /categories/{id}` - Get category
- `PUT /categories/{id}` - Update category
- `DELETE /categories/{id}` - Delete category

#### Analytics
- `GET /summary/` - Financial summary
- `POST /import/csv/` - CSV import (FastAPI style)
- `POST /import/pdf/` - PDF import (FastAPI style)

## Running Both Servers

1. **Django Server** (Web interface + DRF API):
   ```bash
   python3 manage.py runserver
   # Runs on http://127.0.0.1:8000
   ```

2. **FastAPI Server** (Additional API endpoints):
   ```bash
   python3 run_fastapi.py
   # Runs on http://127.0.0.1:8001
   ```

## 🔮 Future Enhancements

### Planned Features
- **🤖 AI-Powered Categorization**: Machine learning models for intelligent transaction categorization
- **📊 Advanced Analytics**: Spending predictions, anomaly detection, and financial insights
- **🎯 Budget Planning**: Create and track budgets with alerts and recommendations
- **📤 Enhanced Export**: Export data in PDF, Excel, and other formats
- **💱 Multi-Currency Support**: Handle multiple currencies with automatic conversion
- **🔄 Recurring Transactions**: Automated recurring expense and income tracking
- **📱 Mobile App**: React Native mobile application
- **🔗 Bank Integrations**: Direct connection to bank APIs for automatic transaction import
- **📈 Investment Tracking**: Portfolio management and investment performance
- **🏷️ Receipt Scanning**: OCR for receipt digitization and automatic entry
- **👥 Multi-User Households**: Shared budgets and expense splitting
- **📧 Email Reports**: Automated financial reports and summaries
- **🔒 Enhanced Security**: Two-factor authentication and data encryption
- **☁️ Cloud Sync**: Cross-device synchronization and backup

### Technical Improvements
- **Microservices Architecture**: Separate services for better scalability
- **GraphQL API**: More flexible API queries
- **Real-time Updates**: WebSocket support for live dashboard updates
- **Caching Layer**: Redis for improved performance
- **Containerization**: Docker support for easy deployment
- **CI/CD Pipeline**: Automated testing and deployment

## 🧪 Testing

Run the comprehensive test suite:
```bash
# Run all tests
python3 manage.py test transactions.tests -v 2

# Run specific test
python3 manage.py test transactions.tests.test_models -v 2

# Run with coverage
pip3 install coverage
coverage run manage.py test
coverage report
```

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes** following our coding standards
4. **Run tests**: `python3 manage.py test`
5. **Update documentation** if needed
6. **Commit your changes**: `git commit -m 'Add amazing feature'`
7. **Push to branch**: `git push origin feature/amazing-feature`
8. **Submit a pull request**

### Development Guidelines
- Follow PEP 8 style guidelines
- Write comprehensive tests for new features
- Update documentation for API changes
- Ensure all tests pass before submitting PR
- Use meaningful commit messages

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Django** - The web framework that makes development joyful
- **FastAPI** - For the additional API capabilities
- **Bootstrap 5** - For the beautiful, responsive UI
- **Plotly** - For interactive data visualizations
- **Pandas** - For powerful data manipulation
- **SQLAlchemy** - For robust database operations

## 📞 Support

If you have questions, issues, or feature requests:

1. Check the [Issues](https://github.com/yourusername/budget-tracker/issues) page
2. Create a new issue with detailed information
3. Join our community discussions

---

**Happy budgeting!** 💰📊🎯
