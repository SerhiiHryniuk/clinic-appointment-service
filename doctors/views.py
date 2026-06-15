from datetime import timedelta

from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, generics
from rest_framework.response import Response

from config.permissions import IsAdminOrReadOnly
from doctors.models import Doctor, DoctorSlot
from doctors.serializers import (
    DoctorListSerializer,
    DoctorDetailSerializer,
    DoctorSlotDetailSerializer,
    DoctorSlotCreateSerializer,
    DoctorSlotListSerializer,
    DoctorSlotBulkCreateSerializer,
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


class DoctorSlotBulkCreateView(generics.GenericAPIView):
    serializer_class = DoctorSlotBulkCreateSerializer
    permission_classes = [IsAdminOrReadOnly]
    queryset = DoctorSlot.objects.none()

    def post(self, request, doctor_id):
        doctor = get_object_or_404(Doctor, pk=doctor_id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        start = serializer.validated_data["start"]
        end = serializer.validated_data["end"]
        interval = serializer.validated_data["interval"]
        existing_slots = DoctorSlot.objects.filter(
            doctor=doctor,
            start__lt=end,
            end__gt=start,
        )
        slots = []
        current = start

        while current < end:
            next_time = current + timedelta(minutes=interval)
            if next_time > end:
                break
            overlap = any(
                slot.start < next_time and slot.end > current
                for slot in existing_slots
            )
            if not overlap:
                slots.append(
                    DoctorSlot(
                        doctor=doctor,
                        start=current,
                        end=next_time,
                    )
                )
            current = next_time
        DoctorSlot.objects.bulk_create(slots)

        return Response({
            "created": len(slots)
        })

    def get(self, request, doctor_id):
        doctor = get_object_or_404(Doctor, pk=doctor_id)
        queryset = DoctorSlot.objects.filter(
            doctor=doctor
        ).select_related("doctor")
        start = request.query_params.get("from")
        end = request.query_params.get("to")
        available_only = request.query_params.get("available_only")
        if start:
            queryset = queryset.filter(start__gte=start)
        if end:
            queryset = queryset.filter(end__lte=end)
        if available_only == "true":
            queryset = queryset.filter(appointment__isnull=True)
        serializer = DoctorSlotListSerializer(queryset, many=True)

        return Response(serializer.data)
