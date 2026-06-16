import telebot
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from appointment.models import Appointment


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


@shared_task
def check_and_mark_noshow_appointments_daily_task() -> None:
    now = timezone.now()
    expired_appointments = Appointment.objects.filter(
        status=Appointment.Status.BOOKED, doctor_slot__end__lt=now
    )

    count = expired_appointments.count()

    if count > 0:
        expired_appointments.update(status=Appointment.Status.NO_SHOW)
        msg = f"<b>Daily Report:</b> System processed {count} no-shows."
        send_telegram_message_task.delay(msg)
    else:
        send_telegram_message_task.delay(
            "<b>Daily Report:</b> No missed appointments today!"
        )
