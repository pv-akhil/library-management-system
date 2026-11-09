from django.urls import path
from . import views

app_name = 'reservations'

urlpatterns = [
    path('', views.reservation_list_view, name='reservation_list'),
    path('book/<int:book_id>/reserve/', views.reserve_book_view, name='reserve_book'),
    path('<int:reservation_id>/cancel/', views.cancel_reservation_view, name='cancel_reservation'),
    path('<int:reservation_id>/approve/', views.approve_reservation_view, name='approve_reservation'),
]
