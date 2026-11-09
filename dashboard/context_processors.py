from django.conf import settings
from transactions.models import Transaction, Fine
from reservations.models import Reservation


def library_settings(request):
    """
    Context processor injecting global library config and alert counters into all templates.
    """
    context = {
        'APP_NAME': 'Apex Library System',
        'APP_VERSION': '1.0.0',
        'DEFAULT_BORROW_DAYS': getattr(settings, 'DEFAULT_BORROW_DAYS', 14),
        'FINE_PER_DAY': getattr(settings, 'FINE_PER_DAY', 1.00),
    }

    if request.user.is_authenticated:
        if request.user.is_staff_member:
            context['staff_overdue_count'] = Transaction.objects.filter(status=Transaction.Status.OVERDUE).count()
            context['staff_pending_res_count'] = Reservation.objects.filter(status=Reservation.Status.PENDING).count()
            context['staff_unpaid_fines_count'] = Fine.objects.filter(is_paid=False, amount__gt=0).count()
        else:
            context['user_active_loans_count'] = request.user.transactions.filter(
                status__in=[Transaction.Status.ISSUED, Transaction.Status.OVERDUE]
            ).count()
            context['user_unpaid_fines_count'] = Fine.objects.filter(
                transaction__user=request.user,
                is_paid=False,
                amount__gt=0
            ).count()

    return context
