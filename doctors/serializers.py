from rest_framework import serializers

from doctors.models import Doctor
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
