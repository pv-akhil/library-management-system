from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import (
    IsLibrarianOrAdminUser,
    librarian_or_admin_required,
)
from library.models import Book
from .models import Reservation
from .serializers import CreateReservationSerializer, ReservationSerializer


# -------------------------------------------------------------
# Web Views (Reservations)
# -------------------------------------------------------------

@login_required
def reserve_book_view(request, book_id):
    """Student self-service action to place a reservation on a book."""
    book = get_object_or_404(Book, id=book_id)

    # Check max reservations limit for student
    max_res = getattr(settings, 'MAX_RESERVATIONS_STUDENT', 3)
    active_count = request.user.reservations.filter(
        status__in=[Reservation.Status.PENDING, Reservation.Status.APPROVED]
    ).count()

    if active_count >= max_res:
        messages.error(request, f"You have reached your reservation limit of {max_res} books.")
        return redirect('library:book_detail', book_id=book.id)

    # Check if user already reserved this book
    already_reserved = request.user.reservations.filter(
        book=book,
        status__in=[Reservation.Status.PENDING, Reservation.Status.APPROVED]
    ).exists()

    if already_reserved:
        messages.warning(request, f"You already have an active reservation for '{book.title}'.")
        return redirect('library:book_detail', book_id=book.id)

    # Create reservation
    res = Reservation.objects.create(
        user=request.user,
        book=book,
        status=Reservation.Status.PENDING
    )

    messages.success(
        request,
        f"Reservation placed for '{book.title}'! You are #{res.queue_position} in the queue."
    )
    return redirect('reservations:reservation_list')


@login_required
def reservation_list_view(request):
    """View active and past reservations (staff sees all, students see their own)."""
    # Auto-expire outdated APPROVED reservations
    now = timezone.now()
    expired = Reservation.objects.filter(
        status=Reservation.Status.APPROVED,
        expiry_date__lt=now
    )
    for exp_res in expired:
        exp_res.status = Reservation.Status.EXPIRED
        exp_res.save()

    status_filter = request.GET.get('status', '').strip()

    if request.user.is_staff_member:
        reservations = Reservation.objects.select_related('user', 'book').all()
    else:
        reservations = Reservation.objects.select_related('user', 'book').filter(user=request.user)

    if status_filter and status_filter in Reservation.Status.values:
        reservations = reservations.filter(status=status_filter)

    paginator = Paginator(reservations, 15)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'statuses': Reservation.Status.choices,
    }

    if request.headers.get('HX-Request'):
        return render(request, 'reservations/partials/reservation_rows.html', context)

    return render(request, 'reservations/reservation_list.html', context)


@login_required
def cancel_reservation_view(request, reservation_id):
    """Cancel a pending reservation."""
    res = get_object_or_404(Reservation, id=reservation_id)

    # Permission check: owner or staff
    if not (request.user.is_staff_member or res.user == request.user):
        messages.error(request, "Permission denied.")
        return redirect('reservations:reservation_list')

    if res.status not in [Reservation.Status.PENDING, Reservation.Status.APPROVED]:
        messages.warning(request, f"Cannot cancel reservation with status '{res.get_status_display()}'.")
        return redirect('reservations:reservation_list')

    res.cancel(reason=f"Cancelled by {request.user.username}")
    messages.success(request, f"Reservation for '{res.book.title}' cancelled.")
    return redirect('reservations:reservation_list')


@librarian_or_admin_required
def approve_reservation_view(request, reservation_id):
    """Staff action to approve reservation and set expiry pickup window."""
    res = get_object_or_404(Reservation, id=reservation_id)
    expiry_days = getattr(settings, 'RESERVATION_EXPIRY_DAYS', 3)

    res.status = Reservation.Status.APPROVED
    res.expiry_date = timezone.now() + timezone.timedelta(days=expiry_days)
    res.save()

    messages.success(
        request,
        f"Reservation for '{res.user.get_full_name()}' approved! Pickup window set until {res.expiry_date.strftime('%b %d, %Y')}."
    )
    return redirect('reservations:reservation_list')


# -------------------------------------------------------------
# REST API Endpoints (DRF)
# -------------------------------------------------------------

class ReservationViewSet(viewsets.ReadOnlyModelViewSet):
    """API for reservations."""
    serializer_class = ReservationSerializer
    filterset_fields = ['status', 'book']
    search_fields = ['book__title', 'book__isbn', 'user__username', 'user__member_id']

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Reservation.objects.none()
        if user.is_staff_member:
            return Reservation.objects.select_related('user', 'book').all()
        return Reservation.objects.select_related('user', 'book').filter(user=user)


class ReserveBookAPIView(APIView):
    """API endpoint to place a book reservation."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CreateReservationSerializer

    def post(self, request):
        serializer = CreateReservationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        book = get_object_or_404(Book, id=serializer.validated_data['book_id'])

        # Check existing
        if Reservation.objects.filter(
            user=request.user,
            book=book,
            status__in=[Reservation.Status.PENDING, Reservation.Status.APPROVED]
        ).exists():
            return Response(
                {"error": "You already have an active reservation for this book."},
                status=status.HTTP_400_BAD_REQUEST
            )

        res = Reservation.objects.create(
            user=request.user,
            book=book,
            notes=serializer.validated_data.get('notes', '')
        )
        return Response(ReservationSerializer(res).data, status=status.HTTP_201_CREATED)
