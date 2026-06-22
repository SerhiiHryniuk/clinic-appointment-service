from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


User = get_user_model()


class UsersApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse("users:register")
        self.token_url = reverse("users:token_obtain_pair")
        self.me_url = reverse("users:me")
        self.user_data = {
            "email": "test@test.com",
            "password": "testpassword",
            "first_name": "test_first",
            "last_name": "test_last",
        }
        self.user = User.objects.create_user(**self.user_data)

    def test_register_user_success(self):
        new_user_data = {
            "email": "test_new@test.com",
            "password": "testpassword_new",
            "first_name": "test_first_new",
            "last_name": "test_last_new",
        }
        response = self.client.post(self.register_url, new_user_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["email"], new_user_data["email"])
        self.assertNotIn("password", response.data)

    def test_register_user_weak_password_fails(self):
        weak_user_data = {
            "email": "test_weak@test.com",
            "password": "12345",
            "first_name": "test_first_weak",
            "last_name": "test_last_weak",
        }
        response = self.client.post(self.register_url, weak_user_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_jwt_token_success(self):
        data = {
            "email": self.user_data["email"],
            "password": self.user_data["password"],
        }
        response = self.client.post(self.token_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_get_profile_with_custom_authorize_header(self):
        token_response = self.client.post(
            self.token_url,
            {
                "email": self.user_data["email"],
                "password": self.user_data["password"],
            },
        )
        access_token = token_response.data["access"]
        self.client.credentials(HTTP_AUTHORIZE=f"Bearer {access_token}")
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], self.user.email)

    def test_get_profile_unauthorized_fails(self):
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_profile_success(self):
        token_response = self.client.post(
            self.token_url,
            {
                "email": self.user_data["email"],
                "password": self.user_data["password"],
            },
        )
        access_token = token_response.data["access"]
        self.client.credentials(HTTP_AUTHORIZE=f"Bearer {access_token}")
        update_data = {
            "first_name": "test_first_updated",
            "last_name": "test_last_updated",
        }
        response = self.client.patch(self.me_url, update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["first_name"], "test_first_updated")
        self.assertEqual(response.data["last_name"], "test_last_updated")
