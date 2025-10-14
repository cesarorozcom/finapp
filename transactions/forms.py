from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Transaction, Category
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, ButtonHolder, Submit, Div, HTML
from crispy_forms.bootstrap import TabHolder, Tab, InlineCheckboxes

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['date', 'description', 'category', 'amount']
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter transaction description'
            }),
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '0.00'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Fieldset(
                'Transaction Details',
                'date',
                'description',
                'category',
                Div(
                    HTML('<small class="form-text text-muted">Use negative amounts for income, positive for expenses</small>'),
                    'amount',
                    css_class='mb-3'
                ),
            ),
            ButtonHolder(
                Submit('submit', 'Save Transaction', css_class='btn btn-primary'),
                HTML('<a href="{% url "dashboard" %}" class="btn btn-secondary">Cancel</a>')
            )
        )

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter category name'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Fieldset(
                'Category Details',
                'name',
            ),
            ButtonHolder(
                Submit('submit', 'Save Category', css_class='btn btn-primary'),
                HTML('<a href="{% url "dashboard" %}" class="btn btn-secondary">Cancel</a>')
            )
        )

class CSVImportForm(forms.Form):
    file = forms.FileField(
        label='CSV File',
        help_text='Select a CSV file to import transactions',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv'
        })
    )
    date_column = forms.CharField(
        label='Date Column',
        initial='date',
        help_text='Name of the column containing dates',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'date'
        })
    )
    description_column = forms.CharField(
        label='Description Column',
        initial='description',
        help_text='Name of the column containing descriptions',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'description'
        })
    )
    amount_column = forms.CharField(
        label='Amount Column',
        initial='amount',
        help_text='Name of the column containing amounts',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'amount'
        })
    )
    category_column = forms.CharField(
        label='Category Column (Optional)',
        required=False,
        help_text='Name of the column containing categories (leave empty for auto-categorization)',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'category'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.attrs = {'enctype': 'multipart/form-data'}
        self.helper.layout = Layout(
            Fieldset(
                'CSV Import Settings',
                'file',
                Div(
                    HTML('<h6 class="mt-3">Column Mapping</h6>'),
                    css_class='mb-3'
                ),
                Div(
                    Div('date_column', css_class='col-md-6'),
                    Div('description_column', css_class='col-md-6'),
                    css_class='row'
                ),
                Div(
                    Div('amount_column', css_class='col-md-6'),
                    Div('category_column', css_class='col-md-6'),
                    css_class='row'
                ),
                Div(
                    HTML('<small class="form-text text-muted">Tip: If your CSV has headers, use those exact column names above</small>'),
                    css_class='mb-3'
                ),
            ),
            ButtonHolder(
                Submit('submit', 'Import CSV', css_class='btn btn-success'),
                HTML('<a href="{% url "dashboard" %}" class="btn btn-secondary">Cancel</a>')
            )
        )

class PDFImportForm(forms.Form):
    file = forms.FileField(
        label='PDF File',
        help_text='Select a PDF file to import transactions from',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.attrs = {'enctype': 'multipart/form-data'}
        self.helper.layout = Layout(
            Fieldset(
                'PDF Import',
                'file',
                Div(
                    HTML('<small class="form-text text-muted">The system will automatically extract transactions from the PDF using intelligent text parsing</small>'),
                    css_class='mb-3'
                ),
            ),
            ButtonHolder(
                Submit('submit', 'Import PDF', css_class='btn btn-success'),
                HTML('<a href="{% url "dashboard" %}" class="btn btn-secondary">Cancel</a>')
            )
        )

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email'
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Choose a username'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Fieldset(
                'Create Account',
                'username',
                'email',
                'password1',
                'password2',
            ),
            ButtonHolder(
                Submit('submit', 'Register', css_class='btn btn-primary'),
                HTML('<a href="{% url "login" %}" class="btn btn-link">Already have an account?</a>')
            )
        )