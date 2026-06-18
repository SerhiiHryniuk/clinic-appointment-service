from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from appointment.models import Appointment
from notifications.tasks import send_telegram_message_task


@receiver(post_save, sender=Appointment)
def appointment_status_notification_signal(sender, instance, created, **kwargs):
    if created:
        start_time = instance.doctor_slot.start.strftime("%d.%m.%Y %H:%M")
        end_time = instance.doctor_slot.end.strftime("%H:%M")
        message = (
            f"📅 <b>New Appointment!</b>\n"
            f"Patient: {instance.patient.email}\n"
            f"Doctor: {instance.doctor_slot.doctor}\n"
            f"Time: {start_time} - {end_time}"
        )
        transaction.on_commit(lambda: send_telegram_message_task.delay(message))
    else:
        original_status = getattr(instance, "_Appointment__original_status", None)
        if instance.status != original_status:
            message = (
                f"🔄 <b>Status of appointment #{instance.id} updated</b>\n"
                f"New status: <b>{instance.get_status_display()}</b>"
            )
            transaction.on_commit(lambda: send_telegram_message_task.delay(message))
