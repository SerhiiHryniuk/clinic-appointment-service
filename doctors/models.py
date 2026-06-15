from django.core.exceptions import ValidationError
from django.db import models

from specializations.models import Specialization


class Doctor(models.Model):
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    specializations = models.ManyToManyField(
        Specialization,
        related_name="doctors"
    )
    price_per_visit = models.DecimalField(
        max_digits=8,
        decimal_places=2
    )

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"


class DoctorSlot(models.Model):
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name="slots"
    )
    start = models.DateTimeField()
    end = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["doctor", "start", "end"],
                name="unique_doctor_slot"
            )
        ]

    def clean(self):
        if self.end <= self.start:
            raise ValidationError(
                {"end": "End time must be later than start time"}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.start:%d.%m.%Y %H:%M} - {self.end:%H:%M}"
