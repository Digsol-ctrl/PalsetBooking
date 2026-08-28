"""End-to-end coverage of the multi-step booking wizard.

These replace two older tests that pointed at `rides:home`, the single-page
booking form that was removed when the wizard took over.
"""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from rides.models import RideBooking, Payment


def _future(days=2):
    return timezone.localtime() + timedelta(days=days)


@pytest.mark.django_db
def test_get_service_selector(client):
    resp = client.get(reverse('rides:service_selector'))
    assert resp.status_code == 200
    assert b'Book a Ride' in resp.content or b'Book a ride' in resp.content


@pytest.mark.django_db
def test_get_wizard_step_one(client):
    resp = client.get(reverse('rides:booking_wizard', kwargs={'step': 1}))
    assert resp.status_code == 200
    assert b'pickup_address' in resp.content


@pytest.mark.django_db
def test_wizard_creates_pay_on_arrival_booking(monkeypatch, client):
    monkeypatch.setattr(
        'rides.services.distance.DistanceService.get_distance_km',
        lambda o, d, use_cache=True: 14.0,
    )
    monkeypatch.setattr(
        'rides.services.email_service.EmailService.send_owner_notification',
        lambda b, payment_status='': None,
    )
    monkeypatch.setattr(
        'rides.services.email_service.EmailService.send_customer_notification',
        lambda b, payment_status='': None,
    )

    pickup = _future()

    resp = client.post(reverse('rides:booking_wizard', kwargs={'step': 1}), {
        'pickup_address': 'Start',
        'dropoff_address': 'End',
        'pickup_latitude': -17.8,
        'pickup_longitude': 31.0,
        'dropoff_latitude': -17.9,
        'dropoff_longitude': 31.1,
        'distance_km': 14.0,
        'pickup_date': pickup.date().isoformat(),
        'pickup_time': '10:00',
    })
    assert resp.status_code == 302

    resp = client.post(reverse('rides:booking_wizard', kwargs={'step': 2}), {
        'num_adults': 1,
        'baby_car_seater': 0,
        'num_kids_carried': 0,
        'luggage_count': 0,
        'hand_luggage_count': 0,
        'passenger_full_name': 'Test Passenger',
        'salutation': 'Mr',
    })
    assert resp.status_code == 302

    resp = client.post(reverse('rides:booking_wizard', kwargs={'step': 3}), {
        'phone': '+263789000000',
        'email': 'test@example.com',
    })
    assert resp.status_code == 302

    resp = client.post(
        reverse('rides:booking_wizard', kwargs={'step': 4}),
        {'payment_method': RideBooking.PAYMENT_ON_ARRIVAL},
        follow=True,
    )
    assert resp.status_code == 200
    assert b'Booking Confirmed' in resp.content

    assert RideBooking.objects.count() == 1
    booking = RideBooking.objects.first()
    assert booking.status == RideBooking.STATUS_CONFIRMED
    assert booking.total_amount > 0
    assert booking.passenger_full_name == 'Test Passenger'

    payments = list(booking.payments.all())
    assert len(payments) == 1
    assert payments[0].method == RideBooking.PAYMENT_ON_ARRIVAL
    assert payments[0].status == Payment.STATUS_PENDING


@pytest.mark.django_db
def test_wizard_rejects_lapsed_pickup(client):
    past = timezone.localtime() - timedelta(days=1)

    resp = client.post(reverse('rides:booking_wizard', kwargs={'step': 1}), {
        'pickup_address': 'Start',
        'dropoff_address': 'End',
        'pickup_latitude': -17.8,
        'pickup_longitude': 31.0,
        'dropoff_latitude': -17.9,
        'dropoff_longitude': 31.1,
        'distance_km': 14.0,
        'pickup_date': past.date().isoformat(),
        'pickup_time': '10:00',
    })

    # Re-renders step 1 with the error rather than moving on
    assert resp.status_code == 200
    assert b'already passed' in resp.content
    assert RideBooking.objects.count() == 0
