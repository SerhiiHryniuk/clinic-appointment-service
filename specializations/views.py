from rest_framework import viewsets
from drf_spectacular.utils import extend_schema, extend_schema_view

from specializations.models import Specialization
from config.permissions import IsAdminOrReadOnly
from specializations.serializers import SpecializationSerializer


@extend_schema_view(
    list=extend_schema(
        summary="Retrieve a list of all medical specializations",
        tags=["Specializations"]
    ),
    retrieve=extend_schema(
        summary="Get details of a specific specialization by code",
        tags=["Specializations"]
    ),
    create=extend_schema(
        summary="Create a new specialization (Admin Only)",
        tags=["Specializations"]
    ),
    update=extend_schema(
        summary="Fully update a specialization (Admin Only)",
        tags=["Specializations"]
    ),
    partial_update=extend_schema(
        summary="Partially update a specialization (Admin Only)",
        tags=["Specializations"]
    ),
    destroy=extend_schema(
        summary="Delete a specialization (Admin Only)",
        tags=["Specializations"]
    ),
)
class SpecializationViewSet(viewsets.ModelViewSet):
    queryset = Specialization.objects.all()
    serializer_class = SpecializationSerializer
    lookup_field = "code"
    permission_classes = [IsAdminOrReadOnly]
