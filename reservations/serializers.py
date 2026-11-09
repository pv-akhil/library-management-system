from rest_framework import serializers
from .models import Reservation


class ReservationSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    member_id = serializers.CharField(source='user.member_id', read_only=True)
    book_title = serializers.CharField(source='book.title', read_only=True)
    book_isbn = serializers.CharField(source='book.isbn', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Reservation
        fields = (
            'id', 'user', 'user_name', 'member_id', 'book',
            'book_title', 'book_isbn', 'reserved_at', 'expiry_date',
            'queue_position', 'status', 'status_display', 'notified', 'notes'
        )
        read_only_fields = ('id', 'reserved_at', 'expiry_date', 'queue_position', 'status', 'notified')


class CreateReservationSerializer(serializers.Serializer):
    book_id = serializers.IntegerField(required=True)
    notes = serializers.CharField(required=False, allow_blank=True)
