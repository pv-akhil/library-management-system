from decimal import Decimal
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction as db_transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import (
    IsLibrarianOrAdminUser,
    librarian_or_admin_required,
)
from library.models import BookCopy
from reservations.models import Reservation
from .forms import IssueBookForm, PayFineForm, ReturnBookForm
from .models import Fine, Transaction
from .serializers import (
    FineSerializer,
    IssueActionSerializer,
    ReturnActionSerializer,
    TransactionSerializer,
)


# -------------------------------------------------------------
# Web Views (Circulation & Loans)
# -------------------------------------------------------------

@librarian_or_admin_required
def issue_book_view(request):
    """Staff view to issue a book copy to a member."""
    if request.method == 'POST':
        form = IssueBookForm(request.POST)
        if form.is_valid():
            member = form.cleaned_data['member']
            book_copy = form.cleaned_data['book_copy']
            due_days = form.cleaned_data['due_days']
            remarks = form.cleaned_data.get('remarks', '')

            with db_transaction.atomic():
                due_date = timezone.now() + timezone.timedelta(days=due_days)
                trans = Transaction.objects.create(
                    user=member,
                    book_copy=book_copy,
                    issued_by=request.user,
                    due_date=due_date,
                    status=Transaction.Status.ISSUED,
                    remarks=remarks
                )
                book_copy.status = BookCopy.Status.ISSUED
                book_copy.save()

                # If this user had a reservation for this book, mark it fulfilled
                Reservation.objects.filter(
                    user=member,
                    book=book_copy.book,
                    status__in=[Reservation.Status.PENDING, Reservation.Status.APPROVED]
                ).update(status=Reservation.Status.FULFILLED)

            messages.success(
                request,
                f"Successfully issued '{book_copy.book.title}' (Barcode: {book_copy.barcode}) to {member.get_full_name() or member.username}. Due on {due_date.strftime('%b %d, %Y')}."
            )
            return redirect('transactions:circulation_list')
    else:
        # Prepopulate barcode if coming from copy details
        barcode = request.GET.get('barcode', '')
        initial = {'barcode': barcode} if barcode else {}
        form = IssueBookForm(initial=initial)

    return render(request, 'transactions/issue_book.html', {'form': form})


@librarian_or_admin_required
def return_book_view(request):
    """Staff view to check in a returned book copy and compute fines if overdue."""
    fine_generated = None
    if request.method == 'POST':
        form = ReturnBookForm(request.POST)
        if form.is_valid():
            trans = form.cleaned_data['active_transaction']
            book_copy = form.cleaned_data['book_copy']
            condition = form.cleaned_data['condition']
            remarks = form.cleaned_data.get('remarks', '')

            with db_transaction.atomic():
                trans.return_date = timezone.now()
                trans.status = Transaction.Status.RETURNED
                if remarks:
                    trans.remarks = f"{trans.remarks} | Return remarks: {remarks}".strip(" | ")
                trans.save()

                # Update copy condition and check reservations
                book_copy.condition = condition

                # Check if there is a pending reservation for this book
                pending_res = Reservation.objects.filter(
                    book=book_copy.book,
                    status=Reservation.Status.PENDING
                ).order_by('queue_position', 'reserved_at').first()

                if pending_res:
                    book_copy.status = BookCopy.Status.RESERVED
                    book_copy.save()

                    expiry_days = getattr(settings, 'RESERVATION_EXPIRY_DAYS', 3)
                    pending_res.status = Reservation.Status.APPROVED
                    pending_res.expiry_date = timezone.now() + timezone.timedelta(days=expiry_days)
                    pending_res.save()
                    res_note = f" Reserved for {pending_res.user.get_full_name()} (until {pending_res.expiry_date.strftime('%b %d')})."
                else:
                    book_copy.status = BookCopy.Status.AVAILABLE
                    book_copy.save()
                    res_note = ""

                # Calculate fine if overdue
                fine_amount = trans.calculate_fine_amount()
                if fine_amount > Decimal('0.00'):
                    fine_generated, _ = Fine.objects.get_or_create(
                        transaction=trans,
                        defaults={'amount': fine_amount}
                    )

            msg = f"Book '{book_copy.book.title}' checked in successfully.{res_note}"
            if fine_generated:
                msg += f" Overdue fine generated: ${fine_generated.amount:.2f}."
            messages.success(request, msg)
            return redirect('transactions:circulation_list')
    else:
        barcode = request.GET.get('barcode', '')
        initial = {'barcode': barcode} if barcode else {}
        form = ReturnBookForm(initial=initial)

    return render(request, 'transactions/return_book.html', {'form': form})


@login_required
def circulation_list_view(request):
    """
    Circulation management for librarians/admins, or student's own borrowing history.
    """
    status_filter = request.GET.get('status', '').strip()
    query = request.GET.get('q', '').strip()

    # Refresh overdue statuses
    Transaction.objects.filter(
        status=Transaction.Status.ISSUED,
        due_date__lt=timezone.now()
    ).update(status=Transaction.Status.OVERDUE)

    if request.user.is_staff_member:
        transactions = Transaction.objects.select_related('user', 'book_copy__book').all()
    else:
        transactions = Transaction.objects.select_related('user', 'book_copy__book').filter(user=request.user)

    if status_filter and status_filter in Transaction.Status.values:
        transactions = transactions.filter(status=status_filter)

    if query:
        transactions = transactions.filter(
            Q(book_copy__book__title__icontains=query) |
            Q(book_copy__barcode__icontains=query) |
            Q(user__username__icontains=query) |
            Q(user__member_id__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query)
        )

    paginator = Paginator(transactions, 15)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'query': query,
        'statuses': Transaction.Status.choices,
        'total_count': paginator.count,
    }

    if request.headers.get('HX-Request'):
        return render(request, 'transactions/partials/transaction_rows.html', context)

    return render(request, 'transactions/circulation_list.html', context)


@login_required
def my_loans_view(request):
    """Student self-service dashboard to view currently borrowed books and due dates."""
    # Refresh overdue status
    Transaction.objects.filter(
        user=request.user,
        status=Transaction.Status.ISSUED,
        due_date__lt=timezone.now()
    ).update(status=Transaction.Status.OVERDUE)

    active_loans = Transaction.objects.select_related('book_copy__book').filter(
        user=request.user,
        status__in=[Transaction.Status.ISSUED, Transaction.Status.OVERDUE]
    ).order_by('due_date')

    history_loans = Transaction.objects.select_related('book_copy__book').filter(
        user=request.user,
        status=Transaction.Status.RETURNED
    ).order_by('-return_date')[:20]

    unpaid_fines = Fine.objects.select_related('transaction__book_copy__book').filter(
        transaction__user=request.user,
        is_paid=False,
        amount__gt=0
    )

    context = {
        'active_loans': active_loans,
        'history_loans': history_loans,
        'unpaid_fines': unpaid_fines,
    }
    return render(request, 'transactions/my_loans.html', context)


@login_required
def fines_list_view(request):
    """Staff view to manage all fines or student view of personal fines."""
    if request.user.is_staff_member:
        fines = Fine.objects.select_related('transaction__user', 'transaction__book_copy__book').all()
    else:
        fines = Fine.objects.select_related('transaction__user', 'transaction__book_copy__book').filter(
            transaction__user=request.user
        )

    paid_filter = request.GET.get('paid')
    if paid_filter == 'true':
        fines = fines.filter(is_paid=True)
    elif paid_filter == 'false':
        fines = fines.filter(is_paid=False)

    paginator = Paginator(fines, 15)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        'page_obj': page_obj,
        'paid_filter': paid_filter,
    }
    return render(request, 'transactions/fines_list.html', context)


@librarian_or_admin_required
def pay_fine_view(request, fine_id):
    """Staff action to record fine payment."""
    fine = get_object_or_404(Fine.objects.select_related('transaction__user'), id=fine_id)

    if request.method == 'POST':
        form = PayFineForm(request.POST, instance=fine)
        if form.is_valid():
            fine_obj = form.save(commit=False)
            fine_obj.mark_as_paid(
                staff_user=request.user,
                method=form.cleaned_data['payment_method'],
                note=form.cleaned_data.get('notes', '')
            )
            messages.success(request, f"Payment of ${fine.amount:.2f} recorded for {fine.transaction.user.get_full_name()}.")
            return redirect('transactions:fines_list')
    else:
        form = PayFineForm(instance=fine)

    return render(request, 'transactions/pay_fine.html', {
        'form': form,
        'fine': fine
    })


# -------------------------------------------------------------
# REST API Endpoints (DRF)
# -------------------------------------------------------------

class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """API for viewing circulation transactions."""
    serializer_class = TransactionSerializer
    filterset_fields = ['status', 'user']
    search_fields = ['book_copy__book__title', 'book_copy__barcode', 'user__username', 'user__member_id']
    ordering_fields = ['issue_date', 'due_date']

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Transaction.objects.none()
        if user.is_staff_member:
            return Transaction.objects.select_related('user', 'book_copy__book').all()
        return Transaction.objects.select_related('user', 'book_copy__book').filter(user=user)


class FineViewSet(viewsets.ReadOnlyModelViewSet):
    """API for viewing fine records."""
    serializer_class = FineSerializer
    filterset_fields = ['is_paid']

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Fine.objects.none()
        if user.is_staff_member:
            return Fine.objects.select_related('transaction__user', 'transaction__book_copy__book').all()
        return Fine.objects.select_related('transaction__user', 'transaction__book_copy__book').filter(transaction__user=user)


class IssueBookAPIView(APIView):
    """API endpoint to issue a book copy to a member."""
    permission_classes = [permissions.IsAuthenticated, IsLibrarianOrAdminUser]
    serializer_class = IssueActionSerializer

    def post(self, request):
        serializer = IssueActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = get_object_or_404(User, id=data['user_id'])
        copy = get_object_or_404(BookCopy, barcode=data['barcode'])

        if copy.status != BookCopy.Status.AVAILABLE:
            return Response(
                {"error": f"Copy '{copy.barcode}' is currently {copy.get_status_display()} and cannot be issued."},
                status=status.HTTP_400_BAD_REQUEST
            )

        due_date = timezone.now() + timezone.timedelta(days=data.get('due_days', 14))
        trans = Transaction.objects.create(
            user=user,
            book_copy=copy,
            issued_by=request.user,
            due_date=due_date,
            status=Transaction.Status.ISSUED,
            remarks=data.get('remarks', '')
        )
        copy.status = BookCopy.Status.ISSUED
        copy.save()

        return Response(TransactionSerializer(trans).data, status=status.HTTP_201_CREATED)


class ReturnBookAPIView(APIView):
    """API endpoint to return a book copy."""
    permission_classes = [permissions.IsAuthenticated, IsLibrarianOrAdminUser]
    serializer_class = ReturnActionSerializer

    def post(self, request):
        serializer = ReturnActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        barcode = serializer.validated_data['barcode']

        copy = get_object_or_404(BookCopy, barcode=barcode)
        trans = Transaction.objects.filter(
            book_copy=copy,
            status__in=[Transaction.Status.ISSUED, Transaction.Status.OVERDUE]
        ).first()

        if not trans:
            return Response({"error": "No active loan found for this book copy."}, status=status.HTTP_400_BAD_REQUEST)

        with db_transaction.atomic():
            trans.return_date = timezone.now()
            trans.status = Transaction.Status.RETURNED
            trans.save()

            copy.status = BookCopy.Status.AVAILABLE
            copy.condition = serializer.validated_data.get('condition', copy.condition)
            copy.save()

            fine_amount = trans.calculate_fine_amount()
            fine_data = None
            if fine_amount > Decimal('0.00'):
                fine_obj, _ = Fine.objects.get_or_create(transaction=trans, defaults={'amount': fine_amount})
                fine_data = FineSerializer(fine_obj).data

        return Response({
            "message": "Book successfully returned.",
            "transaction": TransactionSerializer(trans).data,
            "fine": fine_data
        }, status=status.HTTP_200_OK)
