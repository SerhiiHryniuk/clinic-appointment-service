from django.db import transaction
from django.utils import timezone
from loguru import logger
from rest_framework import serializers

from doctors.models import DoctorSlot
from payments.serializers import PaymentSerializer
from .models import Appointment


class AppointmentSerializer(serializers.ModelSerializer):
    payments = PaymentSerializer(many=True, read_only=True)

    class Meta:
        model = Appointment
        fields = [
            "id",
            "doctor_slot",
            "patient",
            "status",
            "booked_at",
            "completed_at",
            "price",
            "payments",
        ]
        read_only_fields = fields


class AppointmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = ["doctor_slot"]

    def validate_doctor_slot(self, value):
        if value.start <= timezone.now():
            raise serializers.ValidationError(
                "Cannot book a slot that has already started or passed."
            )

        if Appointment.objects.filter(
                doctor_slot=value,
                status=Appointment.Status.BOOKED
        ).exists():
            raise serializers.ValidationError(
                "This doctor slot has already been booked."
            )

        return value

    def create(self, validated_data):
        request = self.context.get("request")
        patient = request.user
        doctor_slot_id = validated_data["doctor_slot"].id

        with transaction.atomic():
            doctor_slot = DoctorSlot.objects.select_for_update().get(
                id=doctor_slot_id
            )

            if Appointment.objects.filter(
                    doctor_slot=doctor_slot,
                    status=Appointment.Status.BOOKED
            ).exists():
                logger.warning(
                    f"Concurrency Conflict: "
                    f"Patient {patient.email} blocked from booking "
                    f"Slot #{doctor_slot_id}. "
                    f"Another request acquired the row lock first."
                )
                raise serializers.ValidationError(
                    {
                        "doctor_slot": "This doctor slot was just booked "
                                       "by someone else."
                    }
                )

            price_at_booking = getattr(
                doctor_slot.doctor,
                "price_per_visit",
                0.00
            )

            appointment = Appointment.objects.create(
                doctor_slot=doctor_slot,
                patient=patient,
                price=price_at_booking,
                status=Appointment.Status.BOOKED
            )

            logger.info(
                f"Appointment #{appointment.id} successfully booked | "
                f"Patient: {patient.email} | "
                f"Slot: #{doctor_slot_id} | Price: {price_at_booking}"
            )

            return appointment
