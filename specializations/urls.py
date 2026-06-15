from django.urls import include, path
from rest_framework.routers import SimpleRouter

from specializations.views import SpecializationViewSet

app_name = "specializations"
router = SimpleRouter()

router.register(
    "specializations",
    SpecializationViewSet,
    basename="specializations"
)

urlpatterns = [
    path("", include(router.urls))
]
