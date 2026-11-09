from django import forms
from django.conf import settings
from django.utils import timezone
from accounts.models import User
from library.models import BookCopy
from .models import Fine, Transaction


class IssueBookForm(forms.Form):
    member = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select select2'}),
        help_text="Select student or member"
    )
    barcode = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Scan or type book copy barcode (e.g., BC-XXXXXX)',
            'autofocus': True,
        }),
        help_text="Accession barcode of physical copy"
    )
    due_days = forms.IntegerField(
        initial=14,
        min_value=1,
        max_value=90,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        help_text="Loan duration in days"
    )
    remarks = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control', 'placeholder': 'Optional notes...'})
    )

    def clean_member(self):
        member = self.cleaned_data['member']
        # Check active borrowed count limit for student
        if member.role == User.Role.STUDENT:
            max_limit = getattr(settings, 'MAX_BOOKS_BORROWED_STUDENT', 3)
            active_loans_count = member.transactions.filter(
                status__in=[Transaction.Status.ISSUED, Transaction.Status.OVERDUE]
            ).count()
            if active_loans_count >= max_limit:
                raise forms.ValidationError(
                    f"Student has reached the maximum borrowing limit ({max_limit} books). Please return a book first."
                )

            # Check unpaid fines limit
            unpaid_fines = Fine.objects.filter(
                transaction__user=member,
                is_paid=False,
                amount__gt=0
            ).exists()
            if unpaid_fines:
                raise forms.ValidationError(
                    "Member has outstanding unpaid fines. Please clear fines before issuing new books."
                )

        return member

    def clean_barcode(self):
        barcode = self.cleaned_data['barcode'].strip()
        try:
            copy = BookCopy.objects.select_related('book').get(barcode=barcode)
        except BookCopy.DoesNotExist:
            raise forms.ValidationError(f"No book copy found with barcode '{barcode}'.")

        if copy.status != BookCopy.Status.AVAILABLE:
            raise forms.ValidationError(
                f"Copy '{barcode}' ({copy.book.title}) is currently '{copy.get_status_display()}' and cannot be issued."
            )

        self.cleaned_data['book_copy'] = copy
        return barcode


class ReturnBookForm(forms.Form):
    barcode = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Scan or type book barcode to return...',
            'autofocus': True,
        })
    )
    condition = forms.ChoiceField(
        choices=BookCopy.Condition.choices,
        initial=BookCopy.Condition.GOOD,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    remarks = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control', 'placeholder': 'Optional return notes...'})
    )

    def clean_barcode(self):
        barcode = self.cleaned_data['barcode'].strip()
        try:
            copy = BookCopy.objects.select_related('book').get(barcode=barcode)
        except BookCopy.DoesNotExist:
            raise forms.ValidationError(f"No book copy found with barcode '{barcode}'.")

        # Find active transaction for this copy
        active_trans = Transaction.objects.filter(
            book_copy=copy,
            status__in=[Transaction.Status.ISSUED, Transaction.Status.OVERDUE]
        ).first()

        if not active_trans:
            raise forms.ValidationError(f"No active loan found for copy '{barcode}'. Current status: {copy.get_status_display()}.")

        self.cleaned_data['active_transaction'] = active_trans
        self.cleaned_data['book_copy'] = copy
        return barcode


class PayFineForm(forms.ModelForm):
    class Meta:
        model = Fine
        fields = ('payment_method', 'notes')
        widgets = {
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Receipt or reference note...'}),
        }
