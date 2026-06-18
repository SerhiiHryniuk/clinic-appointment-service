from unittest.mock import patch
from django.test import TestCase
from django.conf import settings
from notifications.tasks import send_telegram_message_task


class NotificationTasksTests(TestCase):
    @patch("telebot.TeleBot.send_message")
    def test_send_telegram_message_task_success(self, mock_send_message):
        expected_chat_id = getattr(settings, "TELEGRAM_CHAT_ID", "test_chat_id")

        send_telegram_message_task("Test Message")

        mock_send_message.assert_called_once_with(
            chat_id=expected_chat_id,
            text="Test Message",
            parse_mode="HTML",
            disable_web_page_preview=True
        )
