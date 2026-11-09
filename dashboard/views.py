from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from accounts.models import User
from accounts.permissions import librarian_or_admin_required
from library.models import Book, BookCopy, Category
from reservations.models import Reservation
from transactions.models import Fine, Transaction
from . import reports


@login_required
def dashboard_index_view(request):
    """
    Main portal view showing role-tailored dashboard:
    Librarians/Admins see institution KPIs, charts, and circulation alerts.
    Students see active borrowings, due dates, reservations, and recommendations.
    """
    now = timezone.now()

    # Update overdue statuses
    Transaction.objects.filter(
        status=Transaction.Status.ISSUED,
        due_date__lt=now
    ).update(status=Transaction.Status.OVERDUE)

    if request.user.is_staff_member:
        # Staff Analytics
        total_books = Book.objects.count()
        total_copies = BookCopy.objects.count()
        available_copies = BookCopy.objects.filter(status=BookCopy.Status.AVAILABLE).count()
        issued_copies = BookCopy.objects.filter(status=BookCopy.Status.ISSUED).count()
        overdue_loans = Transaction.objects.filter(status=Transaction.Status.OVERDUE).count()
        total_members = User.objects.filter(role=User.Role.STUDENT).count()
        pending_reservations = Reservation.objects.filter(status=Reservation.Status.PENDING).count()

        fines_unpaid_total = Fine.objects.filter(is_paid=False).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        fines_collected_total = Fine.objects.filter(is_paid=True).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        recent_transactions = Transaction.objects.select_related('user', 'book_copy__book').order_by('-issue_date')[:8]
        critical_overdue = Transaction.objects.select_related('user', 'book_copy__book').filter(
            status=Transaction.Status.OVERDUE
        ).order_by('due_date')[:6]

        context = {
            'is_staff': True,
            'total_books': total_books,
            'total_copies': total_copies,
            'available_copies': available_copies,
            'issued_copies': issued_copies,
            'overdue_loans': overdue_loans,
            'total_members': total_members,
            'pending_reservations': pending_reservations,
            'fines_unpaid_total': fines_unpaid_total,
            'fines_collected_total': fines_collected_total,
            'recent_transactions': recent_transactions,
            'critical_overdue': critical_overdue,
        }
        return render(request, 'dashboard/staff_dashboard.html', context)

    else:
        # Student Dashboard
        my_active_loans = Transaction.objects.select_related('book_copy__book').filter(
            user=request.user,
            status__in=[Transaction.Status.ISSUED, Transaction.Status.OVERDUE]
        ).order_by('due_date')

        my_reservations = Reservation.objects.select_related('book').filter(
            user=request.user,
            status__in=[Reservation.Status.PENDING, Reservation.Status.APPROVED]
        ).order_by('queue_position')

        my_unpaid_fines = Fine.objects.filter(
            transaction__user=request.user,
            is_paid=False,
            amount__gt=0
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        recent_books = Book.objects.select_related('category').prefetch_related('authors', 'copies').order_by('-created_at')[:6]

        context = {
            'is_staff': False,
            'my_active_loans': my_active_loans,
            'my_reservations': my_reservations,
            'my_unpaid_fines': my_unpaid_fines,
            'recent_books': recent_books,
        }
        return render(request, 'dashboard/student_dashboard.html', context)


@librarian_or_admin_required
def chart_data_api(request):
    """
    JSON endpoint for Chart.js rendering on staff dashboard.
    """
    # 1. Books per Category
    categories = Category.objects.annotate(count=Count('books')).filter(count__gt=0).order_by('-count')[:6]
    cat_labels = [c.name for c in categories]
    cat_counts = [c.count for c in categories]

    # 2. Circulation Monthly Trends (Last 6 months)
    six_months_ago = timezone.now() - timezone.timedelta(days=180)
    monthly_loans = (
        Transaction.objects.filter(issue_date__gte=six_months_ago)
        .annotate(month=TruncMonth('issue_date'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    month_labels = [m['month'].strftime('%b %Y') for m in monthly_loans]
    month_counts = [m['count'] for m in monthly_loans]

    # 3. Copies Status Breakdown
    statuses = BookCopy.objects.values('status').annotate(count=Count('id'))
    status_map = {item['status']: item['count'] for item in statuses}

    return JsonResponse({
        'categories': {
            'labels': cat_labels,
            'counts': cat_counts,
        },
        'trends': {
            'labels': month_labels,
            'counts': month_counts,
        },
        'status_breakdown': {
            'available': status_map.get(BookCopy.Status.AVAILABLE, 0),
            'issued': status_map.get(BookCopy.Status.ISSUED, 0),
            'reserved': status_map.get(BookCopy.Status.RESERVED, 0),
            'maintenance': status_map.get(BookCopy.Status.MAINTENANCE, 0),
            'lost': status_map.get(BookCopy.Status.LOST, 0),
        }
    })


# -------------------------------------------------------------
# Report Exports
# -------------------------------------------------------------

@librarian_or_admin_required
def export_books_csv_view(request):
    return reports.export_books_csv()


@librarian_or_admin_required
def export_transactions_csv_view(request):
    return reports.export_transactions_csv()


@librarian_or_admin_required
def export_overdue_pdf_view(request):
    return reports.export_overdue_pdf()
