import telebot
from celery import shared_task
from django.conf import settings


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 5, "countdown": 60},
)
def send_telegram_message_task(self, message: str) -> None:
    token = getattr(settings, "TELEGRAM_TOKEN", None)
    chat_id = getattr(settings, "TELEGRAM_CHAT_ID", None)

    if not token or not chat_id:
        return

    bot = telebot.TeleBot(token)
    bot.send_message(
        chat_id=chat_id,
        text=message,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    