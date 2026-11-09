from django.conf import settings
from django.db import models
from django.utils import timezone


class Reservation(models.Model):
    """
    Queue-based book reservation model for student self-service bookings.
    """
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending (In Queue)'
        APPROVED = 'APPROVED', 'Ready for Pickup'
        FULFILLED = 'FULFILLED', 'Fulfilled / Checked Out'
        CANCELLED = 'CANCELLED', 'Cancelled'
        EXPIRED = 'EXPIRED', 'Expired'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reservations'
    )
    book = models.ForeignKey(
        'library.Book',
        on_delete=models.CASCADE,
        related_name='reservations'
    )
    reserved_at = models.DateTimeField(default=timezone.now)
    expiry_date = models.DateTimeField(null=True, blank=True)
    queue_position = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )
    notified = models.BooleanField(default=False)
    notes = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['queue_position', 'reserved_at']
        indexes = [
            models.Index(fields=['status', 'book']),
        ]

    def __str__(self):
        return f"Reservation: {self.book.title} for {self.user.username} (#{self.queue_position} - {self.get_status_display()})"

    def save(self, *args, **kwargs):
        # Calculate queue position when creating a new pending reservation
        if not self.pk and self.status == self.Status.PENDING:
            existing_count = Reservation.objects.filter(
                book=self.book,
                status=self.Status.PENDING
            ).count()
            self.queue_position = existing_count + 1

        super().save(*args, **kwargs)

    def cancel(self, reason=''):
        self.status = self.Status.CANCELLED
        if reason:
            self.notes = f"{self.notes} | Cancel reason: {reason}".strip(" | ")
        self.save()

        # Re-index remaining pending reservations for this book
        pending_reservations = Reservation.objects.filter(
            book=self.book,
            status=self.Status.PENDING
        ).order_by('reserved_at')
        for index, res in enumerate(pending_reservations, start=1):
            if res.queue_position != index:
                res.queue_position = index
                res.save(update_fields=['queue_position'])
