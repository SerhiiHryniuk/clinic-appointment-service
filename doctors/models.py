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
