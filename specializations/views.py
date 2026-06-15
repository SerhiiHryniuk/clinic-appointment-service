from rest_framework import viewsets

from specializations.models import Specialization
from config.permissions import IsAdminOrReadOnly
from specializations.serializers import SpecializationSerializer


class SpecializationViewSet(viewsets.ModelViewSet):
    queryset = Specialization.objects.all()
    serializer_class = SpecializationSerializer
    lookup_field = "code"
    permission_classes = [IsAdminOrReadOnly]