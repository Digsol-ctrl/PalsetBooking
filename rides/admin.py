from django.contrib import admin
from .models import RideBooking, Payment


@admin.register(RideBooking)
class RideBookingAdmin(admin.ModelAdmin):
    list_display = ("id", "pickup_address", "dropoff_address", "distance_km", "total_amount", "status", "created_at")
    readonly_fields = ("created_at", "updated_at")
    search_fields = ("pickup_address", "dropoff_address", "phone", "email")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "booking", "amount", "status", "paynow_reference", "created_at")
    readonly_fields = ("created_at", "updated_at")
    search_fields = ("paynow_reference",)
