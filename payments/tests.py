from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from django.test import TestCase

from appointment.models import Appointment
from doctors.models import Doctor, DoctorSlot
from payments.models import Payment
from payments.serializers import PaymentSerializer

User = get_user_model()


class PaymentApiTests(APITestCase):

    def setUp(self):
        Payment.objects.all().delete()
        Appointment.objects.all().delete()

        self.admin_user = User.objects.create_user(
            email="admin@test.com",
            password="password123",
            is_staff=True
        )
        self.regular_user = User.objects.create_user(
            email="p1@test.com",
            password="password123",
            is_staff=False
        )
        self.other_user = User.objects.create_user(
            email="p2@test.com",
            password="password123",
            is_staff=False
        )

        self.doctor = Doctor.objects.create(
            first_name="Test First",
            last_name="Test Last",
            price_per_visit=100.00
        )

        now = timezone.now()
        start1 = now + timezone.timedelta(days=1)
        end1 = start1 + timezone.timedelta(hours=1)

        start2 = now + timezone.timedelta(days=1, hours=2)
        end2 = start2 + timezone.timedelta(hours=1)

        self.slot_regular = DoctorSlot.objects.create(
            doctor=self.doctor,
            start=start1,
            end=end1
        )
        self.slot_other = DoctorSlot.objects.create(
            doctor=self.doctor,
            start=start2,
            end=end2
        )

        self.app_regular = Appointment.objects.create(
            patient=self.regular_user,
            doctor_slot=self.slot_regular,
            price=100.00
        )
        self.app_other = Appointment.objects.create(
            patient=self.other_user,
            doctor_slot=self.slot_other,
            price=150.00
        )

        self.payment_regular = Payment.objects.create(
            appointment=self.app_regular,
            money_to_pay=100.00,
            status=Payment.Status.PENDING,
            type=Payment.Type.CONSULTATION,
            session_id="sess_regular_123",
            session_url="https://example.com/pay/1"
        )
        self.payment_other = Payment.objects.create(
            appointment=self.app_other,
            money_to_pay=150.00,
            status=Payment.Status.PAID,
            type=Payment.Type.CONSULTATION,
            session_id="sess_other_456",
            session_url="https://example.com/pay/2"
        )

        self.list_url = reverse("payments:payment-list")
        self.detail_url = reverse(
            "payments:payment-detail",
            args=[self.payment_regular.id]
        )

    def test_anonymous_user_cannot_access_payments(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_regular_user_sees_only_own_payments(self):
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get("results")
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["session_id"], "sess_regular_123")

    def test_admin_user_sees_all_payments(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get("results")
        self.assertEqual(len(data), 2)

    def test_regular_user_can_view_own_payment_detail(self):
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(self.detail_url)
        serializer = PaymentSerializer(self.payment_regular)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_regular_user_cannot_view_others_payment_detail(self):
        self.client.force_authenticate(user=self.regular_user)
        other_detail_url = reverse(
            "payments:payment-detail",
            args=[self.payment_other.id]
        )
        response = self.client.get(other_detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class StripeWebhookTests(TestCase):
    def setUp(self):
        self.webhook_url = "/api/v1/webhooks/stripe/"

    @patch("stripe.Webhook.construct_event")
    @patch("notifications.tasks.send_telegram_message_task.delay")
    @patch("payments.models.Payment.objects.select_for_update")
    def test_stripe_webhook_checkout_completed(
        self,
        mock_select_for_update,
        mock_task_delay,
        mock_construct_event
    ):
        mock_payment = MagicMock()
        mock_payment.status = "PENDING"
        mock_payment.appointment_id = 1
        mock_payment.money_to_pay = 100.00

        mock_filter = MagicMock()
        mock_filter.filter.return_value = [mock_payment]
        mock_select_for_update.return_value = mock_filter

        mock_construct_event.return_value = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_123"
                }
            }
        }

        response = self.client.post(
            self.webhook_url,
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="valid_sig"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_payment.status, "PAID")
        mock_payment.save.assert_called_once()
        mock_task_delay.assert_called_once()

    @patch("stripe.Webhook.construct_event")
    @patch("payments.models.Payment.objects.select_for_update")
    def test_stripe_webhook_checkout_expired(
        self,
        mock_select_for_update,
        mock_construct_event
    ):
        mock_filter = MagicMock()
        mock_select_for_update.return_value = mock_filter

        mock_construct_event.return_value = {
            "type": "checkout.session.expired",
            "data": {
                "object": {
                    "id": "cs_test_456"
                }
            }
        }

        response = self.client.post(
            self.webhook_url,
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="valid_sig"
        )

        self.assertEqual(response.status_code, 200)
        mock_filter.filter.assert_called_once()
        mock_filter.filter().update.assert_called_once_with(status="EXPIRED")
