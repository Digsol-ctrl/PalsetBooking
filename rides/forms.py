from django import forms
from django.core.exceptions import ValidationError
from .models import RideBooking
from .services.distance import DistanceService


class BookingForm(forms.Form):
    pickup_address = forms.CharField(max_length=512)
    pickup_lat = forms.FloatField(required=False)
    pickup_lng = forms.FloatField(required=False)
    dropoff_address = forms.CharField(max_length=512)
    dropoff_lat = forms.FloatField(required=False)
    dropoff_lng = forms.FloatField(required=False)

    distance_km = forms.FloatField(required=False)

    num_adults = forms.IntegerField(min_value=1, initial=1)
    num_kids_seated = forms.IntegerField(min_value=0, initial=0)
    num_kids_carried = forms.IntegerField(min_value=0, initial=0)
    luggage_count = forms.IntegerField(min_value=0, initial=0)

    phone = forms.CharField(max_length=32)
    email = forms.EmailField()

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
