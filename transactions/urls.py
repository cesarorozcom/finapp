from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'categories', views.CategoryViewSet)
router.register(r'transactions', views.TransactionViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # Web UI URLs
    path('web/transactions/', views.transaction_list, name='transaction_list'),
    path('web/transactions/add/', views.transaction_create, name='transaction_create'),
    path('web/transactions/<int:pk>/edit/', views.transaction_update, name='transaction_update'),
    path('web/transactions/<int:pk>/delete/', views.transaction_delete, name='transaction_delete'),
    path('web/categories/', views.category_list, name='category_list'),
    path('web/categories/add/', views.category_create, name='category_create'),
    path('web/import/csv/', views.import_csv_view, name='import_csv'),
    path('web/import/pdf/', views.import_pdf_view, name='import_pdf'),
]