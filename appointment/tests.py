from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from appointment.models import Appointment
from doctors.models import Doctor, DoctorSlot

User = get_user_model()


class AppointmentApiTests(APITestCase):
    def setUp(self):
        self.patient_1 = User.objects.create_user(
            email="patient1@example.com",
            password="password123",
            first_name="John",
            last_name="Doe"
        )
        self.patient_2 = User.objects.create_user(
            email="patient2@example.com",
            password="password123",
            first_name="Jane",
            last_name="Smith"
        )
        self.admin_user = User.objects.create_superuser(
            email="admin@clinic.com", password="adminpassword"
        )

        self.doctor = Doctor.objects.create(
            first_name="Gregory",
            last_name="House",
            price_per_visit=150.00
        )

        now = timezone.now()
        self.slot_1 = DoctorSlot.objects.create(
            doctor=self.doctor,
            start=now + timezone.timedelta(days=1, hours=10),
            end=now + timezone.timedelta(days=1, hours=11)
        )
        self.slot_2 = DoctorSlot.objects.create(
            doctor=self.doctor,
            start=now + timezone.timedelta(days=2, hours=14),
            end=now + timezone.timedelta(days=2, hours=15)
        )

        self.list_url = reverse("appointment:appointment-list")

    def test_anonymous_user_cannot_access_appointments(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        response = self.client.post(
            self.list_url,
            data={"doctor_slot": self.slot_1.id}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_patient_can_create_appointment_and_captures_price(self):
        self.client.force_authenticate(user=self.patient_1)
        payload = {"doctor_slot": self.slot_1.id}

        response = self.client.post(self.list_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Appointment.objects.count(), 1)

        appointment = Appointment.objects.first()
        self.assertEqual(appointment.patient, self.patient_1)
        self.assertEqual(appointment.doctor_slot, self.slot_1)
        self.assertEqual(appointment.status, Appointment.Status.BOOKED)
        self.assertEqual(appointment.price, self.doctor.price_per_visit)

    def test_cannot_book_already_booked_slot(self):
        Appointment.objects.create(
            doctor_slot=self.slot_1,
            patient=self.patient_2,
            price=self.doctor.price_per_visit,
            status=Appointment.Status.BOOKED
        )

        self.client.force_authenticate(user=self.patient_1)
        payload = {"doctor_slot": self.slot_1.id}
        response = self.client.post(self.list_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("doctor_slot", response.data)

    def test_patient_can_only_see_own_appointments(self):
        Appointment.objects.create(
            doctor_slot=self.slot_1,
            patient=self.patient_1,
            price=150.00,
            status=Appointment.Status.BOOKED
        )
        Appointment.objects.create(
            doctor_slot=self.slot_2,
            patient=self.patient_2,
            price=150.00,
            status=Appointment.Status.BOOKED
        )

        self.client.force_authenticate(user=self.patient_1)
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["patient"], self.patient_1.id)

    def test_admin_can_see_all_appointments_and_filter_by_patient(self):
        Appointment.objects.create(
            doctor_slot=self.slot_1,
            patient=self.patient_1,
            price=150.00,
            status=Appointment.Status.BOOKED
        )
        Appointment.objects.create(
            doctor_slot=self.slot_2,
            patient=self.patient_2,
            price=150.00,
            status=Appointment.Status.BOOKED
        )

        self.client.force_authenticate(user=self.admin_user)

        response = self.client.get(self.list_url)
        self.assertEqual(len(response.data), 2)

        response = self.client.get(
            self.list_url,
            {"patient_id": self.patient_2.id}
        )
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["patient"], self.patient_2.id)

    def test_filtering_by_status_and_doctor(self):
        appt_match = Appointment.objects.create(
            doctor_slot=self.slot_1,
            patient=self.patient_1,
            price=150.00,
            status=Appointment.Status.BOOKED
        )
        Appointment.objects.create(
            doctor_slot=self.slot_2,
            patient=self.patient_1,
            price=150.00,
            status=Appointment.Status.CANCELLED
        )

        self.client.force_authenticate(user=self.patient_1)

        response = self.client.get(self.list_url, {"status": "BOOKED"})
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], appt_match.id)

        response = self.client.get(
            self.list_url,
            {"doctor_id": self.doctor.id}
        )
        self.assertEqual(len(response.data), 2)

    def test_filtering_by_date_range_from_to(self):
        appt_tomorrow = Appointment.objects.create(
            doctor_slot=self.slot_1,
            patient=self.patient_1,
            price=150.00,
            status=Appointment.Status.BOOKED
        )

        self.client.force_authenticate(user=self.patient_1)

        tomorrow_start = (self.slot_1.start - timezone.timedelta(
            hours=1
        )).isoformat()
        tomorrow_end = (self.slot_1.end + timezone.timedelta(
            hours=1
        )).isoformat()
        future_far = (self.slot_2.start + timezone.timedelta(
            days=5
        )).isoformat()

        response = self.client.get(
            self.list_url,
            {"from": tomorrow_start, "to": tomorrow_end}
        )
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], appt_tomorrow.id)

        response = self.client.get(self.list_url, {"from": future_far})
        self.assertEqual(len(response.data), 0)
