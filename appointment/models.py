from django.db import models
from django.conf import settings


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

    def __str__(self):
        return (f"Appointment {self.id} ({self.status}) - "
                f"Patient: {self.patient.email}")
