from rest_framework import serializers

from doctors.models import Doctor, DoctorSlot
from specializations.models import Specialization
from specializations.serializers import SpecializationSerializer


class DoctorListSerializer(serializers.ModelSerializer):
    specializations = serializers.SlugRelatedField(
        slug_field="code",
        many=True,
        queryset=Specialization.objects.all()
    )

    class Meta:
        model = Doctor
        fields = [
            "id",
            "first_name",
            "last_name",
            "specializations",
            "price_per_visit",
        ]


class DoctorDetailSerializer(serializers.ModelSerializer):
    specializations = SpecializationSerializer(many=True)

    class Meta:
        model = Doctor
        fields = [
            "id",
            "first_name",
            "last_name",
            "specializations",
            "price_per_visit",
        ]


class DoctorSlotListSerializer(serializers.ModelSerializer):
    doctor = serializers.StringRelatedField()

    class Meta:
        model = DoctorSlot
        fields = [
            "id",
            "doctor",
            "start",
            "end",
        ]


class DoctorSlotDetailSerializer(serializers.ModelSerializer):
    doctor = DoctorListSerializer()

    class Meta:
        model = DoctorSlot
        fields = [
            "id",
            "doctor",
            "start",
            "end",
        ]


class DoctorSlotCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorSlot
        fields = [
            "doctor",
            "start",
            "end"
        ]

    def validate(self, data):
        if data["end"] <= data["start"]:
            raise serializers.ValidationError(
                {"end": "End time must be later than start time"}
            )
        return data


class DoctorSlotBulkCreateSerializer(serializers.Serializer):
    start = serializers.DateTimeField()
    end = serializers.DateTimeField()
    interval = serializers.IntegerField(default=30)

    def validate(self, data):
        if data["end"] <= data["start"]:
            raise serializers.ValidationError(
                {"end": "End time must be later than start time"}
            )
        if data.get("interval", 30) <= 0:
            raise serializers.ValidationError(
                {"interval": "Interval must be a positive integer"}
            )
        return data
