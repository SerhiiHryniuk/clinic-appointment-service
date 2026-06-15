from django.urls import path
from rest_framework.routers import SimpleRouter

from doctors.views import (
    DoctorViewSet,
    DoctorSlotViewSet,
    DoctorSlotBulkCreateView
)

router = SimpleRouter()

router.register(
    "doctors",
    DoctorViewSet,
    basename="doctor"
)
router.register(
    "slots",
    DoctorSlotViewSet,
    basename="slot"
)

urlpatterns = [
    path(
        "doctors/<int:doctor_id>/slots/",
        DoctorSlotBulkCreateView.as_view(),
        name="doctor-slot-bulk-create",
    ),
] + router.urls

app_name = "doctors"
