from django.test import TestCase, override_settings
from django.urls import reverse
from rides.models import RideBooking, Payment
from rides.services.paynow import PaynowService
from unittest.mock import patch
import hashlib
import hmac

@override_settings(PAYNOW_INTEGRATION_KEY='test-key-123')
class PaynowEndToEndTest(TestCase):
    def setUp(self):
        self.create_url = reverse('rides:create_booking')
        self.result_url = reverse('rides:paynow_result')

    # Use unittest.mock.patch inside TestCase methods because pytest fixtures are not injected into unittest.TestCase methods
    from unittest.mock import patch

    def _make_booking_payload(self):
        return {
            'pickup_address': 'A',
            'dropoff_address': 'B',
            'distance_km': 20,
            'phone': '0771111111',
            'email': 'mufambisitendaiblessed@gmail.com',
            'payment_option': 'PAYNOW',
        }

    def test_booking_then_webhook_marks_paid(self):
        # Mock create_transaction to return a poll URL flow
        poll_url = 'https://www.paynow.co.zw/Interface/CheckPayment/?guid=test-guid-123'
        def fake_create(amount, reference, email, phone, return_url=None):
            return {
                'reference': reference,
                'redirectUrl': None,
                'pollUrl': poll_url,
                'response': {'poll_url': poll_url, 'data': {'paynowreference': 'PAYREF123'}}
            }

        with patch.object(PaynowService, 'create_transaction', lambda self, amount, reference, email, phone, return_url=None: fake_create(amount, reference, email, phone, return_url)):
            # Create booking via API
            resp = self.client.post(self.create_url, data=self._make_booking_payload(), content_type='application/json')
            self.assertEqual(resp.status_code, 201)
            payment_id = resp.json()['payment']['id']

            payment = Payment.objects.get(id=payment_id)
            self.assertEqual(payment.status, Payment.STATUS_PENDING)
            self.assertTrue(payment.paynow_reference)
        # Sanity: the return view should not crash if Paynow redirects without reference
        resp_no_ref = self.client.get(reverse('rides:paynow_return'))
        self.assertEqual(resp_no_ref.status_code, 200)
        self.assertTrue(('payment' in (resp_no_ref.context or {})) or ('message' in (resp_no_ref.context or {})))
        # Simulate Paynow webhook (signed)
        payload = {
            'reference': payment.paynow_reference,
            'paynowreference': 'PAYREF123',
            'amount': f"{payment.amount:.2f}",
            'status': 'Paid',
            'pollurl': poll_url,
        }
        # Compute HMAC-SHA256 signature (the scheme used by verify_notification)
        key = 'test-key-123'
        from urllib.parse import urlencode
        raw = urlencode(payload).encode('utf-8')
        sign = hmac.new(key.encode('utf-8'), raw, hashlib.sha256).hexdigest()

        # Send raw encoded body so signature matches request.body exactly
        webhook_resp = self.client.post(self.result_url, data=raw, content_type='application/x-www-form-urlencoded', HTTP_X_PAYNOW_SIGNATURE=sign)
        self.assertEqual(webhook_resp.status_code, 200)

        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.STATUS_PAID)
        booking = payment.booking
        self.assertEqual(booking.status, RideBooking.STATUS_CONFIRMED)

    def test_poll_endpoint_marks_paid(self):
        # Simulate create_transaction returning a poll URL
        poll_url = 'https://www.paynow.co.zw/Interface/CheckPayment/?guid=test-guid-456'
        def fake_create(amount, reference, email, phone, return_url=None):
            return {
                'reference': reference,
                'redirectUrl': None,
                'pollUrl': poll_url,
                'response': {'poll_url': poll_url, 'data': {'paynowreference': 'PAYREF456'}}
            }
        with patch.object(PaynowService, 'create_transaction', lambda self, amount, reference, email, phone, return_url=None: fake_create(amount, reference, email, phone, return_url)):
            # Create booking via API
            resp = self.client.post(self.create_url, data=self._make_booking_payload(), content_type='application/json')
            self.assertEqual(resp.status_code, 201)
            payment_id = resp.json()['payment']['id']

            payment = Payment.objects.get(id=payment_id)
            self.assertEqual(payment.status, Payment.STATUS_PENDING)

        # Monkeypatch verify_payment to simulate Paynow reporting paid
        with patch.object(PaynowService, 'verify_payment', lambda self, poll_url: {'paid': True, 'status': 'Paid'}):
            # Call poll endpoint
            poll_url = reverse('rides:paynow_poll', kwargs={'pk': payment.id})
            poll_resp = self.client.get(poll_url)
            self.assertEqual(poll_resp.status_code, 200)
            self.assertTrue(poll_resp.json().get('paid'))

        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.STATUS_PAID)
        booking = payment.booking
        self.assertEqual(booking.status, RideBooking.STATUS_CONFIRMED)

    def test_sdk_send_used_instead_of_send_mobile(self):
        """Ensure create_transaction uses generic send() and does not force a payment method."""
        calls = {}

        class FakePaynow:
            def __init__(self, integration_id, integration_key, return_url, result_url):
                calls['inited'] = True

            def create_payment(self, reference, email):
                calls['create_payment'] = True
                class P:
                    def __init__(self, ref):
                        self.reference = ref
                    def add(self, desc, amt):
                        calls['payment_add'] = True
                return P(reference)

            def send(self, payment):
                calls['send'] = True
                class R:
                    success = True
                    data = {'paynowreference': 'SDKREF'}
                    redirect_url = 'https://paynow.example/redirect'
                    poll_url = 'https://paynow.example/poll'
                return R()

            def send_mobile(self, payment, phone, method):
                calls['send_mobile_called'] = method
                class R:
                    success = True
                    data = {'paynowreference': 'SDKREFMOBILE'}
                    redirect_url = 'https://paynow.example/redirect'
                    poll_url = 'https://paynow.example/poll'
                return R()

        # Monkeypatch the Paynow SDK class (so create_transaction uses our fake implementation)
        with patch('paynow.Paynow', FakePaynow, create=True):
            svc = PaynowService()
            out = svc.create_transaction(amount=10.0, reference='ref-1', email='a@b.com', phone='+263123')

        assert calls.get('send') is True
        assert 'send_mobile_called' not in calls

    def test_paynow_return_disambiguates_and_handles_missing(self):
        # Many payments with null paynow_reference should not cause a 500 when return is hit without reference
        b = RideBooking.objects.create(pickup_address='a', dropoff_address='b', distance_km=1.0, phone='077', email='x@y.com', payment_option=RideBooking.PAYMENT_PAYNOW, price_breakdown={}, total_amount=10.0)
        # Create many payments without paynow_reference
        for i in range(5):
            Payment.objects.create(booking=b, method='PAYNOW', amount=10.0, status=Payment.STATUS_PENDING)

        # No reference param
        resp = self.client.get(reverse('rides:paynow_return'))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue('message' in (resp.context or {}))

        # If the user's session contains the last payment id we used for redirecting to Paynow,
        # the return page should be able to show a booking summary even without a 'reference' param.
        session = self.client.session
        session['last_payment_id'] = str(payment.id)
        session.save()

        resp_sess = self.client.get(reverse('rides:paynow_return'))
        self.assertEqual(resp_sess.status_code, 200)
        self.assertIn('payment', resp_sess.context)
        self.assertIn('eta_minutes', resp_sess.context)
        self.assertIsNotNone(resp_sess.context.get('maps_url'))
        self.assertIn('poll_url', resp_sess.context)

        # Now create multiple payments with the same paynow_reference and ensure the most recent is chosen
        Payment.objects.create(booking=b, method='PAYNOW', amount=10.0, status=Payment.STATUS_PENDING, paynow_reference='DUPREF')
        p2 = Payment.objects.create(booking=b, method='PAYNOW', amount=10.0, status=Payment.STATUS_PENDING, paynow_reference='DUPREF')

        resp2 = self.client.get(reverse('rides:paynow_return') + '?reference=DUPREF')
        self.assertEqual(resp2.status_code, 200)
        # The view should return the most-recent pending payment in context when found
        self.assertEqual(resp2.context.get('payment').id, p2.id)
        # We should include a simple ETA estimate and maps/poll URLs to improve the return UX
        self.assertIn('eta_minutes', resp2.context)
        self.assertIsNotNone(resp2.context.get('maps_url'))
        self.assertIn('poll_url', resp2.context)

