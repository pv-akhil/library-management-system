from django.contrib import admin
from .models import Reservation


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('book', 'user', 'queue_position', 'status', 'reserved_at', 'expiry_date')
    list_filter = ('status', 'reserved_at')
    search_fields = ('book__title', 'user__username', 'user__member_id')
