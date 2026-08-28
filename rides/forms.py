import json
from datetime import datetime

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import RideBooking
from .services.distance import DistanceService


def _reject_past_pickup(pickup_date, pickup_time, label='pickup'):
    """Raise if the given date/time has already passed.

    Bookings must always be for a future moment; a lapsed date or time is rejected
    server-side so it cannot be bypassed by editing the page.
    """
    if not pickup_date or not pickup_time:
        return

    naive = datetime.combine(pickup_date, pickup_time)
    if settings.USE_TZ:
        try:
            scheduled = timezone.make_aware(naive, timezone.get_current_timezone())
        except Exception:
            # Ambiguous or non-existent local time (DST edge) — compare naively instead
            scheduled, now = naive, datetime.now()
        else:
            now = timezone.localtime()
    else:
        scheduled, now = naive, datetime.now()

    if scheduled < now:
        raise ValidationError(
            f'The {label} date and time have already passed. Please choose a future date and time.'
        )


class Step1PickupDropoffForm(forms.Form):
    """Step 1: Pickup & Dropoff Locations with auto-geolocation."""
    
    pickup_address = forms.CharField(
        max_length=512,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter pickup location',
            'id': 'pickup_address',
        })
    )
    pickup_latitude = forms.FloatField(
        widget=forms.HiddenInput(attrs={'id': 'pickup_latitude'}),
        required=False
    )
    pickup_longitude = forms.FloatField(
        widget=forms.HiddenInput(attrs={'id': 'pickup_longitude'}),
        required=False
    )
    
    dropoff_address = forms.CharField(
        max_length=512,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter dropoff location',
            'id': 'dropoff_address',
        })
    )
    dropoff_latitude = forms.FloatField(
        widget=forms.HiddenInput(attrs={'id': 'dropoff_latitude'}),
        required=False
    )
    dropoff_longitude = forms.FloatField(
        widget=forms.HiddenInput(attrs={'id': 'dropoff_longitude'}),
        required=False
    )
    # Scheduling and airport-specific fields
    pickup_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'id': 'pickup_date'})
    )
    pickup_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time', 'id': 'pickup_time'})
    )
    pickup_is_airport = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'id': 'pickup_is_airport', 'class': 'form-check-input'})
    )
    arrival_airline = forms.CharField(
        max_length=64,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Airlink', 'id': 'id_arrival_airline'})
    )
    arrival_flight_number = forms.CharField(
        max_length=32,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 40Z10', 'id': 'id_arrival_flight_number'})
    )
    arrival_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'id': 'id_arrival_date'}))
    arrival_time = forms.TimeField(required=False, widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time', 'id': 'id_arrival_time'}))

    # Return trip (one booking covering the journey back)
    is_return_trip = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'id': 'is_return_trip', 'class': 'form-check-input'})
    )
    return_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'id': 'return_date'})
    )
    return_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time', 'id': 'return_time'})
    )

    distance_km = forms.FloatField(
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'distance_km'}),
    )

    def clean(self):
        cleaned = super().clean()
        pickup_lat = cleaned.get('pickup_latitude')
        pickup_lng = cleaned.get('pickup_longitude')
        dropoff_lat = cleaned.get('dropoff_latitude')
        dropoff_lng = cleaned.get('dropoff_longitude')
        pickup_is_airport = cleaned.get('pickup_is_airport')
        
        # Validate that coordinates are present after Places Autocomplete
        if not all([pickup_lat, pickup_lng, dropoff_lat, dropoff_lng]):
            raise ValidationError('Please select valid pickup and dropoff locations from the suggestions.')

        # If user indicated airport pickup, require flight details and use arrival date/time as pickup schedule.
        if pickup_is_airport:
            if not cleaned.get('arrival_airline') or not cleaned.get('arrival_flight_number'):
                raise ValidationError('For airport pickups please provide arrival airline and flight number.')
            if not cleaned.get('arrival_date') or not cleaned.get('arrival_time'):
                raise ValidationError('For airport pickups please provide arrival date and arrival time.')

            cleaned['pickup_date'] = cleaned.get('arrival_date')
            cleaned['pickup_time'] = cleaned.get('arrival_time')
            _reject_past_pickup(cleaned.get('arrival_date'), cleaned.get('arrival_time'), label='flight arrival')
        else:
            # Non-airport pickups must provide pickup date/time directly.
            if not cleaned.get('pickup_date') or not cleaned.get('pickup_time'):
                raise ValidationError('Please provide pickup date and pickup time.')
            _reject_past_pickup(cleaned.get('pickup_date'), cleaned.get('pickup_time'))

        # A return trip needs its own date and time, after the outbound pickup.
        if cleaned.get('is_return_trip'):
            return_date = cleaned.get('return_date')
            return_time = cleaned.get('return_time')
            if not return_date or not return_time:
                raise ValidationError('Please provide the return date and return time for your round trip.')

            _reject_past_pickup(return_date, return_time, label='return')

            outbound_date = cleaned.get('pickup_date')
            outbound_time = cleaned.get('pickup_time')
            if outbound_date and outbound_time:
                outbound = datetime.combine(outbound_date, outbound_time)
                back = datetime.combine(return_date, return_time)
                if back <= outbound:
                    raise ValidationError('The return trip must be after the pickup date and time.')
        else:
            cleaned['return_date'] = None
            cleaned['return_time'] = None

        return cleaned


class Step2PassengersLuggageForm(forms.Form):
    """Step 2: Number of seated passengers, kids carried, and luggage."""
    
    num_adults = forms.IntegerField(
        min_value=1,
        initial=1,
        widget=forms.HiddenInput()  # Controlled via JS increment/decrement
    )
    baby_car_seater = forms.IntegerField(
        min_value=0,
        initial=0,
        widget=forms.HiddenInput()
    )
    num_kids_carried = forms.IntegerField(
        min_value=0,
        initial=0,
        widget=forms.HiddenInput()
    )
    luggage_count = forms.IntegerField(
        min_value=0,
        initial=0,
        widget=forms.HiddenInput()
    )
    hand_luggage_count = forms.IntegerField(
        min_value=0,
        initial=0,
        required=False,
        widget=forms.HiddenInput()
    )
    # JSON list of {"description": str, "minutes": int}, built by the stops widget
    stops_json = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )
    salutation = forms.CharField(
        max_length=32,
        required=False,
        widget=forms.Select(choices=[
            ('Mr', 'Mr'), ('Mrs', 'Mrs'), ('Miss', 'Miss'), ('Ms', 'Ms'),
            ('Dr', 'Dr'), ('Professor', 'Professor'), ('Rev', 'Rev'), ('Hon', 'Hon'),
        ])
    )
    passenger_full_name = forms.CharField(
        max_length=256,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name (e.g. John Doe)'})
    )

    @staticmethod
    def _clean_stops(raw):
        """Parse the stops widget payload into [{"description", "minutes"}].

        Anything malformed is dropped rather than failing the whole step; the
        durations are re-priced server-side from the configured tiers regardless
        of what the browser sent.
        """
        if not raw:
            return []
        try:
            data = json.loads(raw)
        except (TypeError, ValueError):
            return []
        if not isinstance(data, list):
            return []

        stops = []
        for entry in data[:20]:  # generous ceiling, guards against a runaway payload
            if not isinstance(entry, dict):
                continue
            try:
                minutes = int(entry.get('minutes') or 0)
            except (TypeError, ValueError):
                continue
            if minutes <= 0:
                continue
            stops.append({
                'description': str(entry.get('description') or '').strip()[:200],
                'minutes': minutes,
            })
        return stops

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('num_adults', 0) < 1:
            raise ValidationError('At least one adult is required.')

        cleaned['hand_luggage_count'] = cleaned.get('hand_luggage_count') or 0
        cleaned['stops'] = self._clean_stops(cleaned.get('stops_json'))

        # Enforce the maximums configured in the dashboard. A limit of 0 means no limit.
        from .services.pricing import PricingService
        limits = PricingService.get_booking_limits()
        checks = (
            ('num_adults', limits.get('MAX_PASSENGERS', 0), 'passengers'),
            ('luggage_count', limits.get('MAX_LUGGAGE', 0), 'luggage bags'),
            ('hand_luggage_count', limits.get('MAX_HAND_LUGGAGE', 0), 'hand luggage items'),
        )
        for field, limit, noun in checks:
            if limit and (cleaned.get(field) or 0) > limit:
                raise ValidationError(f'A maximum of {limit} {noun} can be booked online. Please contact us for larger groups.')

        return cleaned


class Step3ContactExtraForm(forms.Form):
    """Step 3: Contact information and extra instructions."""
    
    phone = forms.CharField(
        max_length=32,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+263 77 000 0000',
            'id': 'phone',
            'type': 'tel',
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your@email.com',
            'id': 'email',
        })
    )
    extra_instructions = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': "E.g., 'Please wait at back gate' or 'I have a pet'",
            'rows': 3,
            'id': 'extra_instructions',
        })
    )
    # Passenger details
    salutation = forms.CharField(
        max_length=32,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mr / Mrs / Dr', 'id': 'id_salutation'})
    )
    passenger_full_name = forms.CharField(
        max_length=256,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name (e.g. John Doe)', 'id': 'id_passenger_full_name'})
    )

    def clean(self):
        cleaned = super().clean()
        phone = cleaned.get('phone', '').strip()

        if not phone:
            raise ValidationError('Phone number is required.')

        if len([c for c in phone if c.isdigit()]) < 5:
            raise ValidationError('Phone number must contain at least 5 digits.')

        if not cleaned.get('email', '').strip():
            raise ValidationError('Email address is required.')

        return cleaned


class Step4FarePaymentForm(forms.Form):
    """Step 4: Fare preview & payment method selection."""
    
    # Distance and fare are displayed but not edited here; they're calculated on backend
    distance_km = forms.FloatField(
        widget=forms.HiddenInput(),
        required=False
    )
    estimated_fare = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        widget=forms.HiddenInput(),
        required=False
    )
    fare_breakdown = forms.CharField(
        widget=forms.HiddenInput(),  # JSON string
        required=False
    )
    
    payment_method = forms.ChoiceField(
        choices=[
            (RideBooking.PAYMENT_ON_ARRIVAL, 'Pay on Arrival (Cash)'),
            (RideBooking.PAYMENT_CARD_ON_ARRIVAL, 'Pay on Arrival (POS/CARD payment)'),
            (RideBooking.PAYMENT_MONEY_TRANSFER, 'Pay Via Money Transfer Agency'),
            (RideBooking.PAYMENT_PAYLINK, 'Paylink'),
            (RideBooking.PAYMENT_PAYNOW, 'Pay Online (Paynow)'),
        ],
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input',
        })
    )

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get('payment_method'):
            raise ValidationError('Please select a payment method.')
        return cleaned


class Step5ConfirmationForm(forms.Form):
    """Step 5: Final confirmation (display-only, no changes)."""
    # This is a summary page; form mainly used for template rendering context
    confirm = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        })
    )


# ============================================================================
# Chauffeur Drive Forms
# ============================================================================

class ChauffeurStep1Form(forms.Form):
    """Chauffeur Step 1: Package duration selection only."""

    chauffeur_hours = forms.IntegerField(
        widget=forms.HiddenInput(attrs={'id': 'chauffeur_hours'}),
        min_value=1,
    )

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get('chauffeur_hours'):
            raise ValidationError('Please select a package duration.')
        return cleaned


class ChauffeurStep2Form(forms.Form):
    """Chauffeur Step 2: Trip details — pickup location, dates, times, and trip summary."""

    pickup_address = forms.CharField(
        max_length=512,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search for your pickup name or starting point',
            'id': 'chauffeur_pickup_address',
            'autocomplete': 'off',
        })
    )
    pickup_latitude = forms.FloatField(
        widget=forms.HiddenInput(attrs={'id': 'chauffeur_pickup_latitude'}),
        required=False,
    )
    pickup_longitude = forms.FloatField(
        widget=forms.HiddenInput(attrs={'id': 'chauffeur_pickup_longitude'}),
        required=False,
    )
    pickup_address_detail = forms.CharField(
        max_length=256,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. Gate 2, Unit 5B, specific street or landmark',
            'id': 'chauffeur_pickup_address_detail',
        })
    )
    pickup_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'id': 'chauffeur_pickup_date'})
    )
    pickup_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time', 'id': 'chauffeur_pickup_time'})
    )
    approximate_end_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time', 'id': 'chauffeur_end_time'})
    )
    trip_summary = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'id': 'trip_summary',
            'placeholder': 'e.g. Airport pickup, then RBZ, Joina City, CBD, Avondale',
        })
    )

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get('pickup_latitude') or not cleaned.get('pickup_longitude'):
            raise ValidationError('Please select a valid pickup location from the suggestions.')
        if not cleaned.get('pickup_date'):
            raise ValidationError('Please provide the pickup date.')
        if not cleaned.get('pickup_time'):
            raise ValidationError('Please provide the start time.')
        _reject_past_pickup(cleaned.get('pickup_date'), cleaned.get('pickup_time'))
        return cleaned


class ChauffeurStep4ContactForm(forms.Form):
    """Chauffeur Step 4: Contact details — phone and email both required."""

    phone = forms.CharField(
        max_length=32,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+263 77 000 0000',
            'id': 'phone',
            'type': 'tel',
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your@email.com',
            'id': 'email',
        })
    )

    def clean(self):
        cleaned = super().clean()
        phone = cleaned.get('phone', '').strip()
        if not phone:
            raise ValidationError('Phone number is required.')
        if len([c for c in phone if c.isdigit()]) < 5:
            raise ValidationError('Phone number must contain at least 5 digits.')
        if not cleaned.get('email'):
            raise ValidationError('Email address is required.')
        return cleaned


# ============================================================================
# Legacy Full Booking Form (kept for backward compatibility)
# ============================================================================

class BookingForm(forms.Form):
    """Legacy full booking form (all fields at once)."""
    
    pickup_address = forms.CharField(max_length=512)
    pickup_lat = forms.FloatField(required=False)
    pickup_lng = forms.FloatField(required=False)
    pickup_date = forms.DateField(required=False)
    pickup_time = forms.TimeField(required=False)
    pickup_is_airport = forms.BooleanField(required=False)
    arrival_airline = forms.CharField(max_length=64, required=False, widget=forms.TextInput(attrs={'placeholder': 'e.g. Airlink'}))
    arrival_flight_number = forms.CharField(max_length=32, required=False, widget=forms.TextInput(attrs={'placeholder': 'e.g. 40Z10'}))
    arrival_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    arrival_time = forms.TimeField(required=False, widget=forms.TimeInput(attrs={'type': 'time'}))
    dropoff_address = forms.CharField(max_length=512)
    dropoff_lat = forms.FloatField(required=False)
    dropoff_lng = forms.FloatField(required=False)

    distance_km = forms.FloatField(required=False)

    num_adults = forms.IntegerField(min_value=1, initial=1)
    num_kids_carried = forms.IntegerField(min_value=0, initial=0)
    luggage_count = forms.IntegerField(min_value=0, initial=0)

    phone = forms.CharField(max_length=32)
    email = forms.EmailField()
    salutation = forms.CharField(max_length=32, required=False)
    salutation = forms.CharField(max_length=32, required=False, widget=forms.TextInput(attrs={'placeholder': 'Mr / Mrs / Dr'}))
    passenger_full_name = forms.CharField(max_length=256, widget=forms.TextInput(attrs={'placeholder': 'Full name (e.g. John Doe)'}))

    payment_option = forms.ChoiceField(choices=[(RideBooking.PAYMENT_ON_ARRIVAL, 'Pay on Arrival'), (RideBooking.PAYMENT_PAYNOW, 'Pay Online')])

    def clean(self):
        cleaned = super().clean()
        distance = cleaned.get('distance_km')
        if distance is None:
            # require coordinates
            coords = ('pickup_lat', 'pickup_lng', 'dropoff_lat', 'dropoff_lng')
            missing = [c for c in coords if cleaned.get(c) is None]
            if missing:
                raise ValidationError(f"Either provide distance_km or coordinates for pickup and dropoff. Missing: {', '.join(missing)}")
            # compute distance via DistanceService
            try:
                distance = DistanceService.get_distance_km((cleaned.get('pickup_lat'), cleaned.get('pickup_lng')),
                                                          (cleaned.get('dropoff_lat'), cleaned.get('dropoff_lng')))
            except Exception as exc:
                raise ValidationError(f"Unable to compute distance: {exc}")

            cleaned['distance_km'] = distance

        if cleaned.get('num_adults') < 1:
            raise ValidationError('At least one adult is required')

        return cleaned


class RescheduleBookingForm(forms.Form):
    """Customer-facing form for moving a booking to a new date and time.

    The return leg is only asked for when the booking actually has one.
    """

    pickup_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'id': 'new_pickup_date'})
    )
    pickup_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time', 'id': 'new_pickup_time'})
    )
    return_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'id': 'new_return_date'})
    )
    return_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time', 'id': 'new_return_time'})
    )

    def __init__(self, *args, booking=None, **kwargs):
        self.booking = booking
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        pickup_date = cleaned.get('pickup_date')
        pickup_time = cleaned.get('pickup_time')

        if not pickup_date or not pickup_time:
            raise ValidationError('Please provide both a new pickup date and a new pickup time.')

        _reject_past_pickup(pickup_date, pickup_time)

        if self.booking is not None and self.booking.is_return_trip:
            return_date = cleaned.get('return_date')
            return_time = cleaned.get('return_time')
            if not return_date or not return_time:
                raise ValidationError('This is a return trip, so please provide the return date and time too.')

            _reject_past_pickup(return_date, return_time, label='return')

            if datetime.combine(return_date, return_time) <= datetime.combine(pickup_date, pickup_time):
                raise ValidationError('The return trip must be after the pickup date and time.')

        return cleaned
