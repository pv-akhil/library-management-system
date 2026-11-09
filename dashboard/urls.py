from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_index_view, name='index'),
    path('api/charts/', views.chart_data_api, name='chart_data'),
    path('reports/books/csv/', views.export_books_csv_view, name='export_books_csv'),
    path('reports/transactions/csv/', views.export_transactions_csv_view, name='export_transactions_csv'),
    path('reports/overdue/pdf/', views.export_overdue_pdf_view, name='export_overdue_pdf'),
]
