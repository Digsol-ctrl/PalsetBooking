"""Signed magic links that let a customer manage their own booking.

There are no customer accounts, so access is proved by a signed token emailed with
the confirmation. The token carries only the booking id — it is signed, not
encrypted, so it must never carry anything secret — and it is rejected once it is
older than MAX_TOKEN_AGE_DAYS.
"""

from datetime import datetime, timedelta

from django.conf import settings
from django.core import signing
from django.utils import timezone

# Namespace so a token minted here cannot be replayed against another signer
SALT = 'rides.booking_access'

# A link stays usable for this long. Bookings are normally days away, so this is
# generous; the pickup cut-off below is what actually governs changes.
MAX_TOKEN_AGE_DAYS = 180


def make_token(booking) -> str:
    """Signed token identifying a single booking."""
    return signing.dumps({'booking_id': str(booking.id)}, salt=SALT)


def manage_url(booking) -> str:
    """Absolute 'manage my booking' URL to email to the customer."""
    from django.urls import reverse
    base = getattr(settings, 'BASE_URL', '').rstrip('/')
    return f"{base}{reverse('rides:manage_booking', kwargs={'token': make_token(booking)})}"


def load_booking(token):
    """Resolve a token to its booking, or None if invalid, tampered, or expired."""
    from rides.models import RideBooking
    try:
        data = signing.loads(token, salt=SALT, max_age=timedelta(days=MAX_TOKEN_AGE_DAYS))
    except signing.BadSignature:
        return None
    except Exception:
        return None

    booking_id = (data or {}).get('booking_id')
    if not booking_id:
        return None
    try:
        return RideBooking.objects.get(pk=booking_id)
    except (RideBooking.DoesNotExist, ValueError, TypeError):
        return None


def scheduled_datetime(booking):
    """Timezone-aware pickup datetime for the booking, or None if not scheduled."""
    if not booking.pickup_date or not booking.pickup_time:
        return None
    naive = datetime.combine(booking.pickup_date, booking.pickup_time)
    if not settings.USE_TZ:
        return naive
    try:
        return timezone.make_aware(naive, timezone.get_current_timezone())
    except Exception:
        # DST edge — treat as naive rather than refusing the whole page
        return naive


def self_service_state(booking):
    """What the customer is allowed to do with this booking right now.

    Returns a dict the template renders directly, so every reason a change is
    blocked is spelled out in one place.
    """
    from rides.models import RideBooking
    from rides.services.pricing import _get_self_service_cfg

    cfg = _get_self_service_cfg()
    cutoff_hours = int(cfg.get('CUTOFF_HOURS', 12))

    state = {
        'cutoff_hours': cutoff_hours,
        'can_reschedule': bool(cfg.get('ALLOW_RESCHEDULE', True)),
        'can_cancel': bool(cfg.get('ALLOW_CANCELLATION', True)),
        'blocked_reason': '',
    }

    if booking.status == RideBooking.STATUS_CANCELLED:
        state.update(can_reschedule=False, can_cancel=False,
                     blocked_reason='This booking has already been cancelled.')
        return state

    scheduled = scheduled_datetime(booking)
    if scheduled is None:
        return state

    now = timezone.localtime() if timezone.is_aware(scheduled) else datetime.now()

    if scheduled <= now:
        state.update(can_reschedule=False, can_cancel=False,
                     blocked_reason='This trip has already taken place.')
        return state

    if cutoff_hours and scheduled - timedelta(hours=cutoff_hours) <= now:
        plural = '' if cutoff_hours == 1 else 's'
        state.update(
            can_reschedule=False,
            can_cancel=False,
            blocked_reason=(
                f'Your pickup is less than {cutoff_hours} hour{plural} away, so it can no '
                f'longer be changed online. Please call us instead.'
            ),
        )

    return state
