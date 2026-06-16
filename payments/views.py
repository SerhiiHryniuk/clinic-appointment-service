import stripe
from django.conf import settings
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.pagination import PageNumberPagination

from payments.models import Payment
from payments.serializers import PaymentSerializer


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


@extend_schema(
    tags=["Payments"],
    summary="Stripe payment success",
    description=(
        "Stripe redirects here after a successful checkout. "
        "Verifies the session status via the Stripe API and marks "
        "the Payment record as PAID."
    ),
    parameters=[
        OpenApiParameter(
            "session_id",
            type=str,
            location=OpenApiParameter.QUERY,
            description=(
                "Stripe Checkout Session ID — appended automatically "
                "by Stripe via the {CHECKOUT_SESSION_ID} template variable."
            ),
            required=True,
        )
    ],
    responses={
        200: {
            "type": "object",
            "properties": {
                "detail": {"type": "string"},
                "payment_id": {"type": "integer"},
                "status": {"type": "string"},
            },
        },
        400: {"type": "object", "properties": {"detail": {"type": "string"}}},
        404: {"type": "object", "properties": {"detail": {"type": "string"}}},
    },
)
class PaymentSuccessView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        session_id = request.query_params.get("session_id")
        if not session_id:
            return Response(
                {"detail": "Missing session_id query parameter."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        stripe.api_key = settings.STRIPE_SECRET_KEY
        try:
            session = stripe.checkout.Session.retrieve(session_id)
        except stripe.error.InvalidRequestError:
            return Response(
                {"detail": "Invalid Stripe session ID."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if session.payment_status != "paid":
            return Response(
                {"detail": "Payment has not been completed yet."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment = Payment.objects.filter(session_id=session_id).first()
        if not payment:
            return Response(
                {"detail": "Payment record not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if payment.status != Payment.Status.PAID:
            payment.status = Payment.Status.PAID
            payment.save(update_fields=["status"])

        return Response(
            {
                "detail": "Payment confirmed successfully.",
                "payment_id": payment.id,
                "status": payment.status,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["Payments"],
    summary="Stripe payment cancelled / paused",
    description=(
        "Stripe redirects here when the customer closes the checkout page. "
        "The session remains open for 24 hours, so the patient can retry "
        "payment using the original session_url."
    ),
    parameters=[
        OpenApiParameter(
            "session_id",
            type=str,
            location=OpenApiParameter.QUERY,
            description="Stripe Checkout Session ID (optional).",
            required=False,
        )
    ],
    responses={
        200: {
            "type": "object",
            "properties": {
                "detail": {"type": "string"},
                "session_url": {"type": "string"},
            },
        },
    },
)
class PaymentCancelView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        session_id = request.query_params.get("session_id")
        payment = None
        if session_id:
            payment = Payment.objects.filter(session_id=session_id).first()

        if payment:
            return Response(
                {
                    "detail": (
                        "Payment was not completed. "
                        "You can finish it using the link below — "
                        "the session remains active for 24 hours."
                    ),
                    "session_url": payment.session_url,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "detail": (
                    "Payment was not completed. "
                    "Please return to your appointment and try again. "
                    "Your session is available for 24 hours."
                ),
            },
            status=status.HTTP_200_OK,
        )
