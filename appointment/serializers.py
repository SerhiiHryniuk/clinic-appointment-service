from rest_framework import serializers
from .models import Appointment


class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = [
            "id",
            "doctor_slot",
            "patient",
            "status",
            "booked_at",
            "completed_at",
            "price"
        ]
        read_only_fields = fields


class AppointmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = ["doctor_slot"]

    def validate_doctor_slot(self, value):
        if Appointment.objects.filter(doctor_slot=value, status=Appointment.Status.BOOKED).exists():
            raise serializers.ValidationError("This doctor slot has already been booked.")
        return value

    def create(self, validated_data):
        request = self.context.get("request")
        patient = request.user
        doctor_slot = validated_data["doctor_slot"]

        price_at_booking = getattr(doctor_slot.doctor, "price_per_visit", 0.00)

        return Appointment.objects.create(
            doctor_slot=doctor_slot,
            patient=patient,
            price=price_at_booking,
            status=Appointment.Status.BOOKED
        )