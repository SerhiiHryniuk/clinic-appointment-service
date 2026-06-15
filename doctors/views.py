from datetime import timedelta

from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    extend_schema_view,
    extend_schema,
    OpenApiParameter
)
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


@extend_schema_view(
    list=extend_schema(
        summary="Retrieve a list of all doctors",
        tags=["Doctors"],
        parameters=[
            OpenApiParameter(
                name="specialization",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by specialization id or code",
                required=False,
            )
        ],
    ),
    retrieve=extend_schema(
        summary="Get details of a specific doctor",
        tags=["Doctors"],
    ),
    create=extend_schema(
        summary="Create a new doctor (Admin Only)",
        tags=["Doctors"],
    ),
    update=extend_schema(
        summary="Fully update a doctor (Admin Only)",
        tags=["Doctors"],
    ),
    partial_update=extend_schema(
        summary="Partially update a doctor (Admin Only)",
        tags=["Doctors"],
    ),
    destroy=extend_schema(
        summary="Delete a doctor (Admin Only)",
        tags=["Doctors"],
    ),
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


@extend_schema_view(
    list=extend_schema(
        summary="Retrieve a list of all doctor slots",
        tags=["Doctor Slots"],
        parameters=[
            OpenApiParameter(
                name="from",
                type=OpenApiTypes.DATETIME,
                location=OpenApiParameter.QUERY,
                description="Filter slots starting from this datetime",
                required=False,
            ),
            OpenApiParameter(
                name="to",
                type=OpenApiTypes.DATETIME,
                location=OpenApiParameter.QUERY,
                description="Filter slots ending before this datetime",
                required=False,
            ),
            OpenApiParameter(
                name="available_only",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Pass 'true' to return only slots "
                            "with no booked appointment",
                required=False,
                enum=["true", "false"],
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Get details of a specific doctor slot",
        tags=["Doctor Slots"],
    ),
    create=extend_schema(
        summary="Create a new doctor slot (Admin Only)",
        tags=["Doctor Slots"],
    ),
    update=extend_schema(
        summary="Fully update a doctor slot (Admin Only)",
        tags=["Doctor Slots"],
    ),
    partial_update=extend_schema(
        summary="Partially update a doctor slot (Admin Only)",
        tags=["Doctor Slots"],
    ),
    destroy=extend_schema(
        summary="Delete a slot if no appointment exists (Admin Only)",
        tags=["Doctor Slots"],
    ),
)
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


@extend_schema_view(
    get=extend_schema(
        summary="List slots for a specific doctor",
        tags=["Doctor Slots"],
        parameters=[
            OpenApiParameter(
                name="from",
                type=OpenApiTypes.DATETIME,
                location=OpenApiParameter.QUERY,
                description="Filter slots starting from this datetime",
                required=False,
            ),
            OpenApiParameter(
                name="to",
                type=OpenApiTypes.DATETIME,
                location=OpenApiParameter.QUERY,
                description="Filter slots ending before this datetime",
                required=False,
            ),
            OpenApiParameter(
                name="available_only",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Pass 'true' to return only slots "
                            "with no booked appointment",
                required=False,
                enum=["true", "false"],
            ),
        ],
        responses=DoctorSlotListSerializer(many=True),
    ),
    post=extend_schema(
        summary="Bulk create slots for a specific doctor (Admin Only)",
        tags=["Doctor Slots"],
        request=DoctorSlotBulkCreateSerializer,
        responses={200: {"type": "object", "properties": {
            "created": {"type": "integer"}
        }}},
    ),
)
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
