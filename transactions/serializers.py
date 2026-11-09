from rest_framework import serializers
from .models import Fine, Transaction
from library.serializers import BookCopySerializer
from accounts.serializers import UserSerializer


class FineSerializer(serializers.ModelSerializer):
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    collected_by_name = serializers.CharField(source='collected_by.get_full_name', read_only=True)

    class Meta:
        model = Fine
        fields = (
            'id', 'transaction', 'amount', 'is_paid', 'paid_at',
            'payment_method', 'payment_method_display', 'collected_by',
            'collected_by_name', 'notes'
        )
        read_only_fields = ('id', 'paid_at', 'collected_by')


class TransactionSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    member_id = serializers.CharField(source='user.member_id', read_only=True)
    book_title = serializers.CharField(source='book_copy.book.title', read_only=True)
    book_isbn = serializers.CharField(source='book_copy.book.isbn', read_only=True)
    barcode = serializers.CharField(source='book_copy.barcode', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    fine = FineSerializer(read_only=True)
    overdue_days = serializers.ReadOnlyField()

    class Meta:
        model = Transaction
        fields = (
            'id', 'user', 'user_name', 'member_id', 'book_copy',
            'book_title', 'book_isbn', 'barcode', 'issued_by',
            'issue_date', 'due_date', 'return_date', 'status',
            'status_display', 'remarks', 'fine', 'overdue_days',
            'is_overdue'
        )
        read_only_fields = ('id', 'issue_date', 'return_date', 'status')


class IssueActionSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=True)
    barcode = serializers.CharField(required=True)
    due_days = serializers.IntegerField(default=14, min_value=1, max_value=90)
    remarks = serializers.CharField(required=False, allow_blank=True)


class ReturnActionSerializer(serializers.Serializer):
    barcode = serializers.CharField(required=True)
    condition = serializers.CharField(default='GOOD')
    remarks = serializers.CharField(required=False, allow_blank=True)
