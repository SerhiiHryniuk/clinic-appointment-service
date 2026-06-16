from unittest.mock import patch, MagicMock
from django.test import TestCase
from notifications.tasks import send_telegram_message_task


class NotificationTasksTests(TestCase):
    @patch("telebot.TeleBot.send_message")
    def test_send_telegram_message_task_success(self, mock_send_message):
        send_telegram_message_task("Test Message")
        mock_send_message.assert_called_once_with(
            chat_id="-1004385530274",
            text="Test Message",
            parse_mode="HTML",
            disable_web_page_preview=True
        )


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
