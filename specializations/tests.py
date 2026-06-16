from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from specializations.models import Specialization

User = get_user_model()


class SpecializationAPITestCase(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.admin_user = User.objects.create_superuser(
            email="admin@admin.com", password="testpassword123"
        )
        self.regular_user = User.objects.create_user(
            email="user@user.com", password="testpassword123"
        )

        self.specialization = Specialization.objects.create(
            name="Cardiology",
            code="cardiology",
            description="Treats disorders of the heart."
        )

        self.list_url = reverse("specializations:specializations-list")
        self.detail_url = reverse(
            "specializations:specializations-detail",
            args=[self.specialization.code]
        )
        self.valid_payload = {
            "name": "Neurology",
            "code": "neurology"
        }

    def test_anonymous_user_can_list_specializations(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_anonymous_user_cannot_create(self):
        response = self.client.post(self.list_url, self.valid_payload)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_regular_user_cannot_create(self):
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.post(self.list_url, self.valid_payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_regular_user_cannot_delete(self):
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_returns_201(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(self.list_url, self.valid_payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_admin_create_adds_to_database(self):
        self.client.force_authenticate(user=self.admin_user)
        self.client.post(self.list_url, self.valid_payload)
        self.assertEqual(Specialization.objects.count(), 2)

    def test_admin_can_update_returns_200(self):
        self.client.force_authenticate(user=self.admin_user)
        payload = {"name": "Advanced Cardiology", "code": "cardiology"}
        response = self.client.put(self.detail_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_can_partial_update_returns_200(self):
        self.client.force_authenticate(user=self.admin_user)
        payload = {"description": "Updated description"}
        response = self.client.patch(self.detail_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_can_delete_returns_204(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_admin_delete_removes_from_database(self):
        self.client.force_authenticate(user=self.admin_user)
        self.client.delete(self.detail_url)
        self.assertEqual(Specialization.objects.count(), 0)
