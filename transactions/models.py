from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone


class Transaction(models.Model):
    """
    Circulation record tracking book issues and returns with automatic due-date & overdue fine calculations.
    """
    class Status(models.TextChoices):
        ISSUED = 'ISSUED', 'Issued / On Loan'
        RETURNED = 'RETURNED', 'Returned'
        OVERDUE = 'OVERDUE', 'Overdue'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='transactions',
        help_text="Student or member borrowing the book"
    )
    book_copy = models.ForeignKey(
        'library.BookCopy',
        on_delete=models.CASCADE,
        related_name='transactions',
        help_text="Physical inventory copy borrowed"
    )
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='issued_transactions',
        help_text="Librarian who handled the checkout"
    )
    issue_date = models.DateTimeField(default=timezone.now)
    due_date = models.DateTimeField()
    return_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ISSUED,
        db_index=True
    )
    remarks = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-issue_date']
        indexes = [
            models.Index(fields=['status', 'due_date']),
        ]

    def __str__(self):
        return f"{self.user.username} borrowed {self.book_copy.book.title} ({self.status})"

    def save(self, *args, **kwargs):
        # Default due-date to configured days if not provided
        if not self.due_date and not self.pk:
            default_days = getattr(settings, 'DEFAULT_BORROW_DAYS', 14)
            self.due_date = timezone.now() + timezone.timedelta(days=default_days)

        # Update status to OVERDUE if applicable
        if self.status == self.Status.ISSUED and timezone.now() > self.due_date:
            self.status = self.Status.OVERDUE

        super().save(*args, **kwargs)

    @property
    def is_overdue(self) -> bool:
        if self.return_date:
            return self.return_date > self.due_date
        return timezone.now() > self.due_date

    @property
    def overdue_days(self) -> int:
        if not self.is_overdue:
            return 0
        end_time = self.return_date if self.return_date else timezone.now()
        delta = end_time - self.due_date
        return max(0, delta.days)

    def calculate_fine_amount(self) -> Decimal:
        """Calculates fine based on days overdue and system configuration."""
        days = self.overdue_days
        if days <= 0:
            return Decimal('0.00')
        fine_rate = getattr(settings, 'FINE_PER_DAY', Decimal('1.00'))
        return Decimal(days) * fine_rate


class Fine(models.Model):
    """
    Financial fine record incurred on an overdue or damaged book loan.
    """
    class PaymentMethod(models.TextChoices):
        CASH = 'CASH', 'Cash'
        CARD = 'CARD', 'Credit / Debit Card'
        ONLINE = 'ONLINE', 'Online Payment'
        WAIVED = 'WAIVED', 'Waived by Librarian'

    transaction = models.OneToOneField(
        Transaction,
        on_delete=models.CASCADE,
        related_name='fine'
    )
    amount = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    is_paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        blank=True,
        default=''
    )
    collected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='collected_fines'
    )
    notes = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-transaction__issue_date']

    def __str__(self):
        status = "Paid" if self.is_paid else "Unpaid"
        return f"Fine: ${self.amount} for {self.transaction} ({status})"

    def mark_as_paid(self, staff_user, method=PaymentMethod.CASH, note=''):
        self.is_paid = True
        self.paid_at = timezone.now()
        self.payment_method = method
        self.collected_by = staff_user
        if note:
            self.notes = note
        self.save()
