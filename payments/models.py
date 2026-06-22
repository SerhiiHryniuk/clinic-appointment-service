from django.db import models
from appointment.models import Appointment


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        EXPIRED = "EXPIRED", "Expired"

    class Type(models.TextChoices):
        CONSULTATION = "CONSULTATION", "Consultation"
        CANCELLATION_FEE = "CANCELLATION_FEE", "Cancellation Fee"
        NO_SHOW_FEE = "NO_SHOW_FEE", "No Show Fee"

    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PENDING
    )
    type = models.CharField(
        max_length=20,
        choices=Type.choices
    )
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name="payments"
    )
    session_url = models.URLField(max_length=2048, null=True, blank=True)
    session_id = models.CharField(max_length=255, null=True, blank=True)
    money_to_pay = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"Payment {self.id} ({self.status}) - Type: {self.type}"
