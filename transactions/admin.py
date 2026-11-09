from django.contrib import admin
from .models import Fine, Transaction


class FineInline(admin.StackedInline):
    model = Fine
    extra = 0


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'book_copy', 'issue_date', 'due_date', 'return_date', 'status', 'is_overdue')
    list_filter = ('status', 'issue_date', 'due_date')
    search_fields = ('user__username', 'user__member_id', 'book_copy__barcode', 'book_copy__book__title')
    inlines = [FineInline]


@admin.register(Fine)
class FineAdmin(admin.ModelAdmin):
    list_display = ('transaction', 'amount', 'is_paid', 'payment_method', 'paid_at', 'collected_by')
    list_filter = ('is_paid', 'payment_method')
    search_fields = ('transaction__user__username', 'transaction__user__member_id')
