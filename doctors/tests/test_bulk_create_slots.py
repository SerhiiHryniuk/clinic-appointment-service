from django.urls import reverse

from doctors.models import DoctorSlot
from doctors.tests.helpers import make_slot, make_dt, BaseAPITest


class DoctorSlotBulkCreateTest(BaseAPITest):
    def url(self, doctor_id=None):
        return reverse(
            "doctors:doctor-slot-bulk-create",
            args=[doctor_id or self.doctor.pk],
        )

    def test_bulk_create_as_admin(self):
        self.as_admin()
        payload = {
            "start": "2024-06-01T09:00:00Z",
            "end": "2024-06-01T11:00:00Z",
            "interval": 30,
        }
        r = self.client.post(
            self.url(),
            payload,
            content_type="application/json"
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["created"], 4)
        self.assertEqual(DoctorSlot.objects.count(), 4)

    def test_bulk_create_default_interval(self):
        self.as_admin()
        payload = {
            "start": "2024-06-01T09:00:00Z",
            "end": "2024-06-01T10:00:00Z",
        }
        r = self.client.post(
            self.url(),
            payload,
            content_type="application/json"
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["created"], 2)

    def test_bulk_create_skips_overlapping_slots(self):
        self.as_admin()
        DoctorSlot.objects.create(
            doctor=self.doctor,
            start=make_dt(9, 0),
            end=make_dt(9, 30),
        )
        payload = {
            "start": "2024-06-01T09:00:00Z",
            "end": "2024-06-01T10:00:00Z",
            "interval": 30,
        }
        r = self.client.post(
            self.url(),
            payload,
            content_type="application/json"
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["created"], 1)
        self.assertEqual(DoctorSlot.objects.count(), 2)

    def test_bulk_create_end_before_start_invalid(self):
        self.as_admin()
        payload = {
            "start": "2024-06-01T11:00:00Z",
            "end": "2024-06-01T09:00:00Z",
            "interval": 30,
        }
        r = self.client.post(
            self.url(),
            payload,
            content_type="application/json"
        )
        self.assertEqual(r.status_code, 400)

    def test_bulk_create_invalid_interval(self):
        self.as_admin()
        payload = {
            "start": "2024-06-01T09:00:00Z",
            "end": "2024-06-01T11:00:00Z",
            "interval": 0,
        }
        r = self.client.post(
            self.url(),
            payload,
            content_type="application/json"
        )
        self.assertEqual(r.status_code, 400)

    def test_bulk_create_as_regular_user_forbidden(self):
        self.as_user()
        payload = {
            "start": "2024-06-01T09:00:00Z",
            "end": "2024-06-01T11:00:00Z",
        }
        r = self.client.post(
            self.url(),
            payload,
            content_type="application/json"
        )
        self.assertEqual(r.status_code, 403)

    def test_bulk_create_nonexistent_doctor(self):
        self.as_admin()
        r = self.client.post(
            self.url(doctor_id=9999),
            {"start": "2024-06-01T09:00:00Z", "end": "2024-06-01T10:00:00Z"},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 404)

    def test_list_doctor_slots(self):
        make_slot(self.doctor, start_hour=9, end_hour=10)
        make_slot(self.doctor, start_hour=10, end_hour=11)
        self.as_anon()
        r = self.client.get(self.url())
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data), 2)

    def test_filter_slots_by_from(self):
        make_slot(self.doctor, start_hour=9, end_hour=10, day=1)
        make_slot(self.doctor, start_hour=9, end_hour=10, day=2)
        self.as_anon()
        r = self.client.get(self.url(), {"from": "2024-06-02T00:00:00Z"})
        self.assertEqual(len(r.data), 1)

    def test_filter_slots_by_to(self):
        make_slot(self.doctor, start_hour=9, end_hour=10, day=1)
        make_slot(self.doctor, start_hour=9, end_hour=10, day=3)
        self.as_anon()
        r = self.client.get(self.url(), {"to": "2024-06-02T00:00:00Z"})
        self.assertEqual(len(r.data), 1)
