from rest_framework import serializers
from .models import RideBooking, Payment


class RideBookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = RideBooking
        fields = [
            'id', 'pickup_address', 'pickup_lat', 'pickup_lng', 'dropoff_address', 'dropoff_lat', 'dropoff_lng',
            'distance_km', 'num_adults', 'num_kids_seated', 'num_kids_carried', 'luggage_count', 'phone', 'email', 'payment_option', 'status', 'price_breakdown', 'total_amount', 'created_at'
        ]
        read_only_fields = ('id', 'status', 'price_breakdown', 'total_amount', 'created_at')


class CreateBookingSerializer(serializers.Serializer):
    pickup_address = serializers.CharField(max_length=512)
    pickup_lat = serializers.FloatField(required=False, allow_null=True)
    pickup_lng = serializers.FloatField(required=False, allow_null=True)
    dropoff_address = serializers.CharField(max_length=512)
    dropoff_lat = serializers.FloatField(required=False, allow_null=True)
    dropoff_lng = serializers.FloatField(required=False, allow_null=True)

    distance_km = serializers.FloatField(required=False, allow_null=True)

    num_adults = serializers.IntegerField(min_value=1, default=1)

    def validate(self, data):
        # If distance not provided server-side we require valid coordinates to compute it
        if data.get('distance_km') is None:
            required_coords = ('pickup_lat', 'pickup_lng', 'dropoff_lat', 'dropoff_lng')
            missing = [k for k in required_coords if data.get(k) is None]
            if missing:
                raise serializers.ValidationError(f"Either 'distance_km' or coordinates ({', '.join(required_coords)}) are required. Missing: {', '.join(missing)}")
        return data
    num_kids_seated = serializers.IntegerField(min_value=0, default=0)
    num_kids_carried = serializers.IntegerField(min_value=0, default=0)
    luggage_count = serializers.IntegerField(min_value=0, default=0)

    phone = serializers.CharField(max_length=32)
    email = serializers.EmailField()

    payment_option = serializers.ChoiceField(choices=[(RideBooking.PAYMENT_ON_ARRIVAL, 'Pay on Arrival'), (RideBooking.PAYMENT_PAYNOW, 'Pay Online')])


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class PriceEstimateSerializer(serializers.Serializer):
    distance_km = serializers.FloatField(required=False, allow_null=True)
    pickup_lat = serializers.FloatField(required=False, allow_null=True)
    pickup_lng = serializers.FloatField(required=False, allow_null=True)
    dropoff_lat = serializers.FloatField(required=False, allow_null=True)
    dropoff_lng = serializers.FloatField(required=False, allow_null=True)

    num_adults = serializers.IntegerField(min_value=1, default=1)
    num_kids_seated = serializers.IntegerField(min_value=0, default=0)
    num_kids_carried = serializers.IntegerField(min_value=0, default=0)
    luggage_count = serializers.IntegerField(min_value=0, default=0)

    def validate(self, data):
        if data.get('distance_km') is None:
            coords = ('pickup_lat', 'pickup_lng', 'dropoff_lat', 'dropoff_lng')
            missing = [c for c in coords if data.get(c) is None]
            if missing:
                raise serializers.ValidationError("Either 'distance_km' or full coordinates are required to estimate price")
        return data
