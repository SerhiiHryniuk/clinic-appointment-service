from django.urls import reverse

from doctors.models import DoctorSlot
from doctors.tests.helpers import BaseAPITest, make_slot


class SlotDetailDeleteTest(BaseAPITest):
    def setUp(self):
        super().setUp()
        self.slot = make_slot(self.doctor)

    def url(self, pk=None):
        return reverse("doctors:slot-detail", args=[pk or self.slot.pk])

    def test_retrieve_slot(self):
        self.as_anon()
        r = self.client.get(self.url())
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["id"], self.slot.id)
        self.assertIsInstance(r.data["doctor"], dict)

    def test_delete_slot_as_admin(self):
        self.as_admin()
        r = self.client.delete(self.url())
        self.assertEqual(r.status_code, 204)
        self.assertEqual(DoctorSlot.objects.count(), 0)

    def test_delete_slot_as_regular_user_forbidden(self):
        self.as_user()
        r = self.client.delete(self.url())
        self.assertEqual(r.status_code, 403)

    def test_retrieve_nonexistent_slot(self):
        self.as_anon()
        r = self.client.get(self.url(pk=9999))
        self.assertEqual(r.status_code, 404)
