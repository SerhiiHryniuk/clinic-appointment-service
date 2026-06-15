from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser, AllowAny

from specializations.models import Specialization
from specializations.serializers import SpecializationSerializer


class SpecializationViewSet(viewsets.ModelViewSet):
    queryset = Specialization.objects.all()
    serializer_class = SpecializationSerializer

    def get_permissions(self):
        admin_actions = ["create", "update", "partial_update", "destroy"]

        if self.action in admin_actions:
            return [IsAdminUser()]

        return [AllowAny()]