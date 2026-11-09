from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from rest_framework import generics, permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .forms import (
    LoginForm,
    MemberCreateForm,
    MemberEditForm,
    StudentRegistrationForm,
    UserProfileUpdateForm,
)
from .models import User
from .permissions import (
    IsAdminUserRole,
    IsLibrarianOrAdminUser,
    admin_required,
    librarian_or_admin_required,
)
from .serializers import StudentRegisterSerializer, UserSerializer


# -------------------------------------------------------------
# Web Views (Django Templates & HTMX)
# -------------------------------------------------------------

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:index')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            login(request, user)
            if not form.cleaned_data.get('remember_me'):
                request.session.set_expiry(0)  # expires on browser close
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            next_url = request.GET.get('next')
            return redirect(next_url if next_url else 'dashboard:index')
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, "You have been securely logged out.")
    return redirect('login')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:index')

    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"Registration successful! Your Member ID is {user.member_id}. Please log in.")
            return redirect('login')
    else:
        form = StudentRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


@login_required
def profile_view(request):
    if request.method == 'POST':
        form = UserProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been successfully updated.")
            return redirect('accounts:profile')
    else:
        form = UserProfileUpdateForm(instance=request.user)

    return render(request, 'accounts/profile.html', {'form': form})


@librarian_or_admin_required
def member_list_view(request):
    query = request.GET.get('q', '').strip()
    role_filter = request.GET.get('role', '').strip()

    users = User.objects.all()

    if query:
        users = users.filter(
            Q(username__icontains=query) |
            Q(email__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(member_id__icontains=query)
        )

    if role_filter and role_filter in User.Role.values:
        users = users.filter(role=role_filter)

    paginator = Paginator(users, 15)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'query': query,
        'role_filter': role_filter,
        'roles': User.Role.choices,
        'total_count': paginator.count,
    }

    # Support HTMX partial swap for fast searching
    if request.headers.get('HX-Request'):
        return render(request, 'accounts/partials/member_rows.html', context)

    return render(request, 'accounts/member_list.html', context)


@librarian_or_admin_required
def member_detail_view(request, user_id):
    member = get_object_or_404(User, id=user_id)
    # Get member transactions and reservations
    recent_transactions = member.transactions.select_related('book_copy__book').order_by('-issue_date')[:10]
    active_reservations = member.reservations.select_related('book').order_by('-reserved_at')[:10]

    context = {
        'member': member,
        'recent_transactions': recent_transactions,
        'active_reservations': active_reservations,
    }
    return render(request, 'accounts/member_detail.html', context)


@librarian_or_admin_required
def member_create_view(request):
    if request.method == 'POST':
        form = MemberCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"New member '{user.username}' created successfully (Member ID: {user.member_id}).")
            return redirect('accounts:member_list')
    else:
        form = MemberCreateForm()

    return render(request, 'accounts/member_form.html', {'form': form, 'title': 'Create Member'})


@librarian_or_admin_required
def member_edit_view(request, user_id):
    member = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        form = MemberEditForm(request.POST, instance=member)
        if form.is_valid():
            form.save()
            messages.success(request, f"Member '{member.username}' updated successfully.")
            return redirect('accounts:member_list')
    else:
        form = MemberEditForm(instance=member)

    return render(request, 'accounts/member_form.html', {
        'form': form,
        'member': member,
        'title': f'Edit Member: {member.username}'
    })


# -------------------------------------------------------------
# REST API Endpoints (DRF)
# -------------------------------------------------------------

class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint for User CRUD.
    Staff can view all users, regular students can view only themselves.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsLibrarianOrAdminUser]
    filterset_fields = ['role', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'member_id']
    ordering_fields = ['date_joined', 'username', 'last_name']


class RegisterAPIView(generics.CreateAPIView):
    """Public student registration API."""
    permission_classes = [permissions.AllowAny]
    serializer_class = StudentRegisterSerializer


class CurrentUserAPIView(APIView):
    """Get current authenticated user info."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
