from django.db.models import Q
from rest_framework import viewsets

from config.permissions import IsAdminOrReadOnly
from doctors.models import Doctor
from doctors.serializers import (
    DoctorListSerializer,
    DoctorDetailSerializer,
)


class DoctorViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        queryset = Doctor.objects.prefetch_related("specializations")
        specialization = self.request.query_params.get("specialization")
        if specialization:
            q = Q(specializations__code=specialization)
            if specialization.isdigit():
                q |= Q(specializations__id=specialization)
            queryset = queryset.filter(q).distinct()
        return queryset

    def get_serializer_class(self):
        if self.action == "retrieve":
            return DoctorDetailSerializer

        return DoctorListSerializer
