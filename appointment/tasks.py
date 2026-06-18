from celery import shared_task
from django.utils import timezone
from loguru import logger

from appointment.models import Appointment
from payments.services import create_payment_session
from payments.models import Payment
from notifications.tasks import send_telegram_message_task


@shared_task
def check_and_mark_noshow_appointments_daily_task() -> None:
    now = timezone.now()

    logger.info("Daily no-show check task started.")

    expired_appointments = Appointment.objects.filter(
        status=Appointment.Status.BOOKED,
        doctor_slot__end__lt=now
    )

    total_found = expired_appointments.count()
    logger.info(f"Found {total_found} expired appointments to process.")

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
            logger.info(
                f"Generated No-Show penalty session for "
                f"Appointment #{appointment.id} "
                f"(Patient: {appointment.patient.email})"
            )
        except Exception as e:
            logger.exception(
                f"Failed to generate Stripe payment session for "
                f"Appointment #{appointment.id}. "
                f"Reason: {e}"
            )

        count += 1

    logger.info(f"Daily no-show cleanup finished. "
                f"Total processed: {count}/{total_found}")

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
