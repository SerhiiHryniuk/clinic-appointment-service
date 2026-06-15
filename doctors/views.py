from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.response import Response

from config.permissions import IsAdminOrReadOnly
from doctors.models import Doctor, DoctorSlot
from doctors.serializers import (
    DoctorListSerializer,
    DoctorDetailSerializer,
    DoctorSlotDetailSerializer,
    DoctorSlotCreateSerializer,
    DoctorSlotListSerializer,
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


class DoctorSlotViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        queryset = DoctorSlot.objects.select_related("doctor")
        start = self.request.query_params.get("from")
        end = self.request.query_params.get("to")
        available_only = self.request.query_params.get("available_only")
        if start:
            queryset = queryset.filter(start__gte=start)
        if end:
            queryset = queryset.filter(end__lte=end)
        if available_only == "true":
            queryset = queryset.filter(
                appointment__isnull=True
            )

        return queryset

    def get_serializer_class(self):
        if self.action == "retrieve":
            return DoctorSlotDetailSerializer
        if self.action == "create":
            return DoctorSlotCreateSerializer

        return DoctorSlotListSerializer

    def destroy(self, request, *args, **kwargs):
        slot = self.get_object()
        if hasattr(slot, "appointment") and slot.appointment is not None:
            return Response(
                {
                    "detail": "Cannot delete a slot with "
                              "an existing appointment."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)
