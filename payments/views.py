from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated
from payments.models import Payment
from payments.serializers import PaymentSerializer
from rest_framework.pagination import PageNumberPagination


class PaymentPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


@extend_schema(tags=["Payments"])
@extend_schema_view(
    list=extend_schema(
        summary="List payments",
        description="Patients see only their own payments; Staff see all."
    ),
    retrieve=extend_schema(
        summary="Payment details",
        description="Detailed information about a specific payment."
    )
)
class PaymentViewSet(ReadOnlyModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PaymentPagination

    def get_queryset(self):
        queryset = Payment.objects.select_related("appointment__patient")
        if not self.request.user.is_staff:
            return queryset.filter(appointment__patient=self.request.user)
        return queryset
