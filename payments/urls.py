from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import PaymentViewSet


router = SimpleRouter()
router.register("payments", PaymentViewSet, basename="payment")

urlpatterns = [
    path("", include(router.urls)),
]

app_name = "payments"
