from datetime import datetime, timezone

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from doctors.models import Doctor, DoctorSlot
from specializations.models import Specialization

User = get_user_model()


def make_dt(hour, minute=0, day=1):
    return datetime(2024, 6, day, hour, minute, tzinfo=timezone.utc)


def make_specialization(code="CARD", name="Cardiology"):
    return Specialization.objects.create(code=code, name=name)


def make_doctor(first="John", last="Doe", price="100.00", specs=()):
    doctor = Doctor.objects.create(
        first_name=first,
        last_name=last,
        price_per_visit=price,
    )
    for spec in specs:
        doctor.specializations.add(spec)
    return doctor


def make_slot(doctor, start_hour=9, end_hour=10, day=1):
    return DoctorSlot.objects.create(
        doctor=doctor,
        start=make_dt(start_hour, day=day),
        end=make_dt(end_hour, day=day),
    )


class BaseAPITest(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            email="admin@admin.com", password="admin123"
        )
        self.user = User.objects.create_user(
            email="user@user.com", password="user123"
        )
        self.spec = make_specialization()
        self.doctor = make_doctor(specs=[self.spec])

    def as_admin(self):
        self.client.force_authenticate(self.admin)

    def as_user(self):
        self.client.force_authenticate(self.user)

    def as_anon(self):
        self.client.logout()
