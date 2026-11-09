from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('profile/', views.profile_view, name='profile'),
    path('members/', views.member_list_view, name='member_list'),
    path('members/create/', views.member_create_view, name='member_create'),
    path('members/<int:user_id>/', views.member_detail_view, name='member_detail'),
    path('members/<int:user_id>/edit/', views.member_edit_view, name='member_edit'),
]
