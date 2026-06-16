from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import (
    extend_schema_view,
    extend_schema,
    OpenApiParameter
)

from .models import Appointment
from .serializers import (
    AppointmentSerializer,
    AppointmentCreateSerializer
)


@extend_schema(tags=["Appointments"])
@extend_schema_view(
    list=extend_schema(
        summary="List appointments with filters",
        parameters=[
            OpenApiParameter("status",
                             type=str,
                             description="Filter by status ("
                                         "BOOKED, "
                                         "COMPLETED, "
                                         "CANCELLED, "
                                         "NO_SHOW)"
                             ),
            OpenApiParameter("doctor_id",
                             type=int,
                             description="Filter by Doctor ID"
                             ),
            OpenApiParameter("patient_id",
                             type=int,
                             description="Filter by Patient ID "
                                         "(Staff/Admin Only)"
                             ),
            OpenApiParameter("from",
                             type=str,
                             description="Filter appointments starting "
                                         "from this timestamp (ISO format)"
                             ),
            OpenApiParameter("to",
                             type=str,
                             description="Filter appointments starting up "
                                         "to this timestamp (ISO format)"
                             ),
        ]
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

        status = self.request.query_params.get("status")
        doctor_id = self.request.query_params.get("doctor_id")
        from_date = self.request.query_params.get("from")
        to_date = self.request.query_params.get("to")

        if status:
            queryset = queryset.filter(status=status)
        if doctor_id:
            queryset = queryset.filter(doctor_slot__doctor_id=doctor_id)

        if from_date:
            queryset = queryset.filter(doctor_slot__start__gte=from_date)
        if to_date:
            queryset = queryset.filter(doctor_slot__start__lte=to_date)

        return queryset.select_related(
            "doctor_slot",
            "doctor_slot__doctor",
            "patient"
        )
