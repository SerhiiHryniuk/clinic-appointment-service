from django.test import TestCase
from django.urls import reverse

from doctors.models import Doctor
from doctors.tests.helpers import make_doctor, make_specialization, BaseAPITest


class DoctorModelTest(TestCase):
    def test_str(self):
        doctor = make_doctor()
        self.assertEqual(str(doctor), "John Doe")

    def test_create_doctor(self):
        spec = make_specialization()
        doctor = make_doctor(specs=[spec])
        self.assertEqual(Doctor.objects.count(), 1)
        self.assertIn(spec, doctor.specializations.all())


class DoctorListCreateTest(BaseAPITest):
    def url(self):
        return reverse("doctors:doctor-list")

    def test_list_unauthenticated(self):
        self.as_anon()
        r = self.client.get(self.url())
        self.assertEqual(r.status_code, 200)

    def test_list_returns_doctors(self):
        self.as_anon()
        r = self.client.get(self.url())
        self.assertEqual(len(r.data), 1)

    def test_filter_by_specialization_code(self):
        other = make_doctor(first="Jane", last="Smith", price="80.00")
        self.as_anon()
        r = self.client.get(self.url(), {"specialization": self.spec.code})
        ids = [d["id"] for d in r.data]
        self.assertIn(self.doctor.id, ids)
        self.assertNotIn(other.id, ids)

    def test_filter_by_specialization_id(self):
        self.as_anon()
        r = self.client.get(self.url(), {"specialization": self.spec.id})
        self.assertEqual(len(r.data), 1)

    def test_create_as_admin(self):
        self.as_admin()
        payload = {
            "first_name": "Alice",
            "last_name": "Brown",
            "specializations": [self.spec.code],
            "price_per_visit": "150.00",
        }
        r = self.client.post(
            self.url(),
            payload,
            content_type="application/json"
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Doctor.objects.count(), 2)

    def test_create_as_regular_user_forbidden(self):
        self.as_user()
        payload = {
            "first_name": "Alice",
            "last_name": "Brown",
            "specializations": [self.spec.code],
            "price_per_visit": "150.00",
        }
        r = self.client.post(
            self.url(),
            payload,
            content_type="application/json"
        )
        self.assertEqual(r.status_code, 403)

    def test_create_unauthenticated_unauthorized(self):
        self.as_anon()
        r = self.client.post(self.url(), {}, content_type="application/json")
        self.assertEqual(r.status_code, 401)


class DoctorDetailTest(BaseAPITest):
    def url(self, pk=None):
        return reverse("doctors:doctor-detail", args=[pk or self.doctor.pk])

    def test_retrieve(self):
        self.as_anon()
        r = self.client.get(self.url())
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["id"], self.doctor.id)
        self.assertIsInstance(r.data["specializations"][0], dict)

    def test_update_as_admin(self):
        self.as_admin()
        payload = {
            "first_name": "Updated",
            "last_name": "Doe",
            "specializations": [self.spec.code],
            "price_per_visit": "200.00",
        }
        r = self.client.put(
            self.url(),
            payload,
            content_type="application/json"
        )
        self.assertEqual(r.status_code, 200)
        self.doctor.refresh_from_db()
        self.assertEqual(self.doctor.first_name, "Updated")

    def test_partial_update_as_admin(self):
        self.as_admin()
        r = self.client.patch(
            self.url(),
            {"price_per_visit": "99.00"},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)

    def test_update_as_regular_user_forbidden(self):
        self.as_user()
        r = self.client.put(self.url(), {}, content_type="application/json")
        self.assertEqual(r.status_code, 403)

    def test_delete_as_admin(self):
        self.as_admin()
        r = self.client.delete(self.url())
        self.assertEqual(r.status_code, 204)
        self.assertEqual(Doctor.objects.count(), 0)

    def test_delete_as_regular_user_forbidden(self):
        self.as_user()
        r = self.client.delete(self.url())
        self.assertEqual(r.status_code, 403)

    def test_retrieve_nonexistent(self):
        self.as_anon()
        r = self.client.get(self.url(pk=9999))
        self.assertEqual(r.status_code, 404)
