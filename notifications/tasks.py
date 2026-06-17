import telebot
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from appointment.models import Appointment
from payments.services import create_payment_session
from payments.models import Payment


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
        status=Appointment.Status.BOOKED,
        doctor_slot__end__lt=now
    )

    count = 0
    for appointment in expired_appointments:
        appointment.status = Appointment.Status.NO_SHOW
        appointment.save()

        try:
            create_payment_session(
                appointment,
                Payment.Type.NO_SHOW_FEE,
                request=None
            )
        except Exception:
            pass

        count += 1

    if count > 0:
        msg = (
            f"<b>Daily Report:</b> System processed {count} "
            f"no-shows and generated penalties."
        )
        send_telegram_message_task.delay(msg)
    else:
        send_telegram_message_task.delay(
            "<b>Daily Report:</b> No missed appointments today!"
        )
