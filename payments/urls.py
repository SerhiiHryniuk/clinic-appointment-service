from django.urls import path, include
from rest_framework.routers import SimpleRouter

from .views import PaymentViewSet
from .webhook import stripe_webhook

router = SimpleRouter()
router.register("payments", PaymentViewSet, basename="payment")

urlpatterns = [
    path("", include(router.urls)),
    path("webhooks/stripe/", stripe_webhook, name="stripe-webhook"),
]

app_name = "payments"
