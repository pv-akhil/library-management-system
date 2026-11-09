from django.urls import path
from . import views

app_name = 'transactions'

urlpatterns = [
    path('', views.circulation_list_view, name='circulation_list'),
    path('issue/', views.issue_book_view, name='issue_book'),
    path('return/', views.return_book_view, name='return_book'),
    path('my-loans/', views.my_loans_view, name='my_loans'),
    path('fines/', views.fines_list_view, name='fines_list'),
    path('fines/<int:fine_id>/pay/', views.pay_fine_view, name='pay_fine'),
]
