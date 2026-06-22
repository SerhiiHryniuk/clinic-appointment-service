from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("specializations.urls", namespace="specializations")),
    path("api/v1/", include("doctors.urls", namespace="doctors")),
    path("api/v1/", include("appointment.urls", namespace="appointment")),
    path("api/v1/users/", include("users.urls", namespace="users")),
    path("api/v1/", include("payments.urls", namespace="payments")),
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path("api/docs/swagger/", SpectacularSwaggerView.as_view(url_name="api-schema"), name="api-docs"),
]
