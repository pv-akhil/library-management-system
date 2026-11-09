from functools import wraps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from rest_framework import permissions


# Django View Decorators
def admin_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_admin_role:
            return view_func(request, *args, **kwargs)
        messages.error(request, "Access denied: Administrator privileges required.")
        return redirect('dashboard:index')
    return _wrapped_view


def librarian_or_admin_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_staff_member:
            return view_func(request, *args, **kwargs)
        messages.error(request, "Access denied: Librarian or Administrator privileges required.")
        return redirect('dashboard:index')
    return _wrapped_view


def student_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_student_role:
            return view_func(request, *args, **kwargs)
        messages.error(request, "Access denied: Student access only.")
        return redirect('dashboard:index')
    return _wrapped_view


# DRF Permission Classes
class IsAdminUserRole(permissions.BasePermission):
    """Allows access only to Admin users."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_admin_role)


class IsLibrarianOrAdminUser(permissions.BasePermission):
    """Allows access to Librarians and Administrators."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff_member)


class IsStudentUser(permissions.BasePermission):
    """Allows access only to Student users."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_student_role)


class IsOwnerOrStaff(permissions.BasePermission):
    """Allows users to view/edit their own profile/records, while staff can view/edit any."""
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_staff_member:
            return True
        # If object is a User instance
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return obj == request.user
