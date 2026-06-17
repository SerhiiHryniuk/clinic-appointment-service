from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from drf_spectacular.utils import (
    extend_schema_view,
    extend_schema,
    OpenApiParameter,
)

from payments.models import Payment
from payments.services import create_payment_session
from .models import Appointment
from .serializers import AppointmentSerializer, AppointmentCreateSerializer


@extend_schema(tags=["Appointments"])
@extend_schema_view(
    list=extend_schema(
        summary="List appointments with filters",
        parameters=[
            OpenApiParameter(
                "status",
                type=str,
                description="Filter by status (BOOKED, COMPLETED, ...)",
            ),
            OpenApiParameter(
                "doctor_id", type=int, description="Filter by Doctor ID"
            ),
            OpenApiParameter(
                "patient_id",
                type=int,
                description="Filter by Patient ID (Staff/Admin Only)",
            ),
            OpenApiParameter(
                "from",
                type=str,
                description="Filter by start timestamp (ISO format)",
            ),
            OpenApiParameter(
                "to",
                type=str,
                description="Filter up to start timestamp (ISO format)",
            ),
        ],
    )
)
class AppointmentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return AppointmentCreateSerializer
        return AppointmentSerializer

    def get_queryset(self):
        user = self.request.user

        if user.is_staff:
            queryset = Appointment.objects.all()
            patient_id = self.request.query_params.get("patient_id")
            if patient_id:
                queryset = queryset.filter(patient_id=patient_id)
        else:
            queryset = Appointment.objects.filter(patient=user)

        status_param = self.request.query_params.get("status")
        doctor_id = self.request.query_params.get("doctor_id")
        from_date = self.request.query_params.get("from")
        to_date = self.request.query_params.get("to")

        if status_param:
            queryset = queryset.filter(status=status_param)
        if doctor_id:
            queryset = queryset.filter(doctor_slot__doctor_id=doctor_id)

        if from_date:
            queryset = queryset.filter(doctor_slot__start__gte=from_date)
        if to_date:
            queryset = queryset.filter(doctor_slot__start__lte=to_date)

        return queryset.select_related(
            "doctor_slot", "doctor_slot__doctor", "patient"
        ).prefetch_related("payments")

    def get_object(self):
        queryset = self.get_queryset()
        obj = get_object_or_404(queryset, pk=self.kwargs["pk"])
        self.check_object_permissions(self.request, obj)
        return obj

    @extend_schema(
        summary="Cancel an appointment",
        description=(
            "Allows patients to cancel their own appointment, "
            "or staff to cancel any appointment. "
            "Only booked appointments can be cancelled."
        ),
        responses={
            200: AppointmentSerializer,
            400: {
                "type": "object",
                "properties": {"detail": {"type": "string"}},
            },
        },
    )
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        appointment = self.get_object()

        if appointment.status != Appointment.Status.BOOKED:
            return Response(
                {"detail": "Only booked appointments can be cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        appointment.status = Appointment.Status.CANCELLED
        appointment.save()

        if appointment.is_late_cancellation():
            create_payment_session(
                appointment, Payment.Type.CANCELLATION_FEE, request=request
            )

        serializer = self.get_serializer(appointment)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Complete an appointment",
        description=(
            "Allows staff members to mark an appointment as completed. "
            "Sets the completion timestamp."
        ),
        responses={
            200: AppointmentSerializer,
            400: {
                "type": "object",
                "properties": {"detail": {"type": "string"}},
            },
            403: {
                "type": "object",
                "properties": {"detail": {"type": "string"}},
            },
        },
    )
    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        appointment = self.get_object()

        if not request.user.is_staff:
            return Response(
                {
                    "detail": (
                        "You do not have permission to perform this action."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if appointment.status != Appointment.Status.BOOKED:
            return Response(
                {"detail": "Only booked appointments can be completed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        appointment.status = Appointment.Status.COMPLETED
        appointment.completed_at = timezone.now()
        appointment.save()
        create_payment_session(
            appointment, Payment.Type.CONSULTATION, request=request
        )
        serializer = self.get_serializer(appointment)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Mark an appointment as no-show",
        description=(
            "Allows staff members to manually mark an appointment "
            "as no-show if the patient did not arrive."
        ),
        responses={
            200: AppointmentSerializer,
            400: {
                "type": "object",
                "properties": {"detail": {"type": "string"}},
            },
            403: {
                "type": "object",
                "properties": {"detail": {"type": "string"}},
            },
        },
    )
    @action(detail=True, methods=["post"])
    def no_show(self, request, pk=None):
        appointment = self.get_object()

        if not request.user.is_staff:
            return Response(
                {
                    "detail": (
                        "You do not have permission to perform this action."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if appointment.status != Appointment.Status.BOOKED:
            return Response(
                {
                    "detail": (
                        "Only booked appointments can be marked as no-show."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        appointment.status = Appointment.Status.NO_SHOW
        appointment.save()
        create_payment_session(
            appointment, Payment.Type.NO_SHOW_FEE, request=request
        )
        serializer = self.get_serializer(appointment)
        return Response(serializer.data, status=status.HTTP_200_OK)
