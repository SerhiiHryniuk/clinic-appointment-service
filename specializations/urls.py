from django.urls import include, path
from rest_framework.routers import DefaultRouter

from specializations.views import SpecializationViewSet

app_name = "specializations"
router = DefaultRouter()

router.register(
    "specializations",
    SpecializationViewSet,
    basename="specializations"
)

urlpatterns = [
    path("", include(router.urls))
]
