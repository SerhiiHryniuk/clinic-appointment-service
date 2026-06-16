from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import AppointmentViewSet

app_name = "appointment"
router = SimpleRouter()
router.register("appointments", AppointmentViewSet, basename="appointment")

urlpatterns = [
    path("", include(router.urls)),
]
