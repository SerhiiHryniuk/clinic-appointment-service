import telebot
from celery import shared_task
from django.conf import settings
from loguru import logger


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 5, "countdown": 60},
)
def send_telegram_message_task(self, message: str) -> None:
    token = getattr(settings, "TELEGRAM_TOKEN", None)
    chat_id = getattr(settings, "TELEGRAM_CHAT_ID", None)

    if not token or not chat_id:
        logger.error(
            "Telegram Notification Skipped: Either TELEGRAM_TOKEN or "
            "TELEGRAM_CHAT_ID is missing from your "
            "Django settings configuration."
        )
        return

    bot = telebot.TeleBot(token)

    try:
        bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        logger.info(f"Telegram message successfully "
                    f"dispatched to Chat ID: {chat_id}")

    except Exception as e:
        current_attempt = self.request.retries + 1
        max_attempts = self.retry_kwargs.get("max_retries", 5) + 1

        logger.warning(
            f"Telegram API connection failure on attempt "
            f"{current_attempt}/{max_attempts}. "
            f"Scheduling retry routine in 60s. Reason: {e}"
        )

        raise e
