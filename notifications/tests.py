from unittest.mock import patch
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
