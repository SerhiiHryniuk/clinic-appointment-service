from django.conf import settings
from django.db import models
from django.utils import timezone


class Appointment(models.Model):
    class Status(models.TextChoices):
        BOOKED = "BOOKED", "Booked"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"
        NO_SHOW = "NO_SHOW", "No Show"

    doctor_slot = models.ForeignKey(
        "doctors.DoctorSlot",
        on_delete=models.PROTECT,
        related_name="appointments"
    )
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="appointments"
    )
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.BOOKED
    )
    booked_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["-booked_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__original_status = self.status

    def save(self, *args, **kwargs):
        is_created = self.pk is None

        if self.status == self.Status.COMPLETED and not self.completed_at:
            self.completed_at = timezone.now()

        super().save(*args, **kwargs)

        from notifications.tasks import send_telegram_message_task

        if is_created:
            start_time = self.doctor_slot.start.strftime("%d.%m.%Y %H:%M")
            end_time = self.doctor_slot.end.strftime("%H:%M")
            message = (
                f"📅 <b>New Appointment!</b>\n"
                f"Patient: {self.patient.email}\n"
                f"Doctor: {self.doctor_slot.doctor}\n"
                f"Time: {start_time} - {end_time}"
            )
            send_telegram_message_task.delay(message)
        elif self.status != self.__original_status:
            message = (
                f"🔄 <b>Status of appointment #{self.id} updated</b>\n"
                f"New status: <b>{self.get_status_display()}</b>"
            )
            send_telegram_message_task.delay(message)
            self.__original_status = self.status

    def __str__(self):
        return (f"Appointment {self.id} ({self.status}) - "
                f"Patient: {self.patient.email}")

    def is_late_cancellation(self) -> bool:
        time_until_start = self.doctor_slot.start - timezone.now()
        is_after_zero = timezone.timedelta(0) < time_until_start
        is_under_24h = time_until_start < timezone.timedelta(hours=24)
        return is_after_zero and is_under_24h
