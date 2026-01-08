import hmac
import hashlib
from django.conf import settings
import pytest
from rest_framework.test import APIClient
from django.urls import reverse

from rides.models import RideBooking, Payment


@pytest.mark.django_db
def test_paynow_result_verification_valid(monkeypatch):
    client = APIClient()

    # Setup booking and payment
    booking = RideBooking.objects.create(
        pickup_address='Start',
        dropoff_address='End',
        distance_km=40.0,
        num_adults=1,
        phone='+263789000000',
        email='test@example.com',
        payment_option=RideBooking.PAYMENT_PAYNOW,
        price_breakdown={},
        total_amount=46.5,
        status=RideBooking.STATUS_PENDING,
    )

    payment = Payment.objects.create(booking=booking, method='PAYNOW', amount=46.5, status=Payment.STATUS_PENDING, paynow_reference='fake-ref-123')

    # Prevent emails from being sent
    monkeypatch.setattr('rides.services.email_service.EmailService.send_payment_confirmation', lambda b: None)
    monkeypatch.setattr('rides.services.email_service.EmailService.send_owner_notification', lambda b, payment_status='': None)

    # Ensure integration key exists in settings for signature generation
    monkeypatch.setattr(settings, 'PAYNOW_INTEGRATION_KEY', 'secret-key')

    payload = 'reference=fake-ref-123&status=Paid'.encode()
    signature = hmac.new(b'secret-key', payload, hashlib.sha256).hexdigest()

    resp = client.post(reverse('rides:paynow_result'), data=payload, content_type='application/x-www-form-urlencoded', HTTP_X_PAYNOW_SIGNATURE=signature)
    assert resp.status_code == 200
    assert resp.json().get('ok') is True

    payment.refresh_from_db()
    booking.refresh_from_db()

    assert payment.status == Payment.STATUS_PAID
    assert booking.status == RideBooking.STATUS_CONFIRMED


@pytest.mark.django_db
def test_paynow_result_verification_invalid(monkeypatch):
    client = APIClient()

    booking = RideBooking.objects.create(
        pickup_address='Start',
        dropoff_address='End',
        distance_km=40.0,
        num_adults=1,
        phone='+263789000000',
        email='test@example.com',
        payment_option=RideBooking.PAYMENT_PAYNOW,
        price_breakdown={},
        total_amount=46.5,
        status=RideBooking.STATUS_PENDING,
    )

    payment = Payment.objects.create(booking=booking, method='PAYNOW', amount=46.5, status=Payment.STATUS_PENDING, paynow_reference='fake-ref-123')

    monkeypatch.setattr(settings, 'PAYNOW_INTEGRATION_KEY', 'secret-key')

    payload = 'reference=fake-ref-123&status=Paid'.encode()
    bad_signature = 'bad-signature'

    resp = client.post(reverse('rides:paynow_result'), data=payload, content_type='application/x-www-form-urlencoded', HTTP_X_PAYNOW_SIGNATURE=bad_signature)
    assert resp.status_code == 403
    assert resp.json().get('detail') == 'Invalid signature'

    payment.refresh_from_db()
    booking.refresh_from_db()

    # Should remain pending since signature invalid
    assert payment.status == Payment.STATUS_PENDING
    assert booking.status == RideBooking.STATUS_PENDING


@pytest.mark.django_db
def test_paynow_webhook_intermediate_status_keeps_pending(monkeypatch):
    client = APIClient()

    booking = RideBooking.objects.create(
        pickup_address='Start',
        dropoff_address='End',
        distance_km=40.0,
        num_adults=1,
        phone='+263789000000',
        email='test@example.com',
        payment_option=RideBooking.PAYMENT_PAYNOW,
        price_breakdown={},
        total_amount=46.5,
        status=RideBooking.STATUS_PENDING,
    )

    payment = Payment.objects.create(booking=booking, method='PAYNOW', amount=46.5, status=Payment.STATUS_PENDING, paynow_reference='fake-ref-456')

    monkeypatch.setattr(settings, 'PAYNOW_INTEGRATION_KEY', 'secret-key')

    payload = 'reference=fake-ref-456&status=Awaiting+Delivery'.encode()
    signature = hmac.new(b'secret-key', payload, hashlib.sha256).hexdigest()

    resp = client.post(reverse('rides:paynow_result'), data=payload, content_type='application/x-www-form-urlencoded', HTTP_X_PAYNOW_SIGNATURE=signature)
    assert resp.status_code == 200

    payment.refresh_from_db()
    booking.refresh_from_db()

    # Should remain pending because status is intermediate
    assert payment.status == Payment.STATUS_PENDING
    assert booking.status == RideBooking.STATUS_PENDING


@pytest.mark.django_db
def test_paynow_webhook_paid_amount_mismatch_marks_failed(monkeypatch):
    client = APIClient()

    booking = RideBooking.objects.create(
        pickup_address='Start',
        dropoff_address='End',
        distance_km=40.0,
        num_adults=1,
        phone='+263789000000',
        email='test@example.com',
        payment_option=RideBooking.PAYMENT_PAYNOW,
        price_breakdown={},
        total_amount=46.5,
        status=RideBooking.STATUS_PENDING,
    )

    payment = Payment.objects.create(booking=booking, method='PAYNOW', amount=46.5, status=Payment.STATUS_PENDING, paynow_reference='fake-ref-789')

    monkeypatch.setattr(settings, 'PAYNOW_INTEGRATION_KEY', 'secret-key')

    # Incoming webhook reports Paid but amount is wrong
    payload = 'reference=fake-ref-789&status=Paid&amount=10.00'.encode()
    signature = hmac.new(b'secret-key', payload, hashlib.sha256).hexdigest()

    resp = client.post(reverse('rides:paynow_result'), data=payload, content_type='application/x-www-form-urlencoded', HTTP_X_PAYNOW_SIGNATURE=signature)
    assert resp.status_code == 200

    payment.refresh_from_db()
    booking.refresh_from_db()

    # Because amounts didn't match, we mark payment FAILED for manual review
    assert payment.status == Payment.STATUS_FAILED
    # Booking should remain pending because payment did not actually confirm
    assert booking.status == RideBooking.STATUS_PENDING
