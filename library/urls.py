from django.urls import path
from . import views

app_name = 'library'

urlpatterns = [
    path('', views.book_catalog_view, name='catalog'),
    path('books/add/', views.book_create_view, name='book_create'),
    path('books/<int:book_id>/', views.book_detail_view, name='book_detail'),
    path('books/<int:book_id>/edit/', views.book_edit_view, name='book_edit'),
    path('books/<int:book_id>/delete/', views.book_delete_view, name='book_delete'),
    path('books/<int:book_id>/copies/add/', views.copy_add_view, name='copy_add'),
    path('copies/<int:copy_id>/edit/', views.copy_edit_view, name='copy_edit'),
    path('copies/<int:copy_id>/delete/', views.copy_delete_view, name='copy_delete'),
    path('categories/', views.category_list_view, name='category_list'),
]
