from django.urls import path, include
from rest_framework.routers import SimpleRouter

from .views import PaymentViewSet, PaymentSuccessView, PaymentCancelView
from .webhook import stripe_webhook

router = SimpleRouter()
router.register("payments", PaymentViewSet, basename="payment")

urlpatterns = [
    path("payments/success/", PaymentSuccessView.as_view(), name="payment-success"),
    path("payments/cancel/", PaymentCancelView.as_view(), name="payment-cancel"),
    path("", include(router.urls)),
    path("webhooks/stripe/", stripe_webhook, name="stripe-webhook"),
]

app_name = "payments"
