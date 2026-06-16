from decimal import Decimal, ROUND_HALF_UP

import stripe
from django.conf import settings
from django.urls import reverse

from payments.models import Payment

stripe.api_key = settings.STRIPE_SECRET_KEY

MULTIPLIERS = {
    Payment.Type.CONSULTATION: Decimal("1"),
    Payment.Type.CANCELLATION_FEE: Decimal("0.5"),
    Payment.Type.NO_SHOW_FEE: Decimal("1.2"),
}


def _round(amount: Decimal) -> Decimal:
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_money_to_pay(appointment, payment_type: str) -> Decimal:
    price = Decimal(appointment.price)

    if payment_type == Payment.Type.CANCELLATION_FEE:
        if not appointment.is_late_cancellation():
            return Decimal("0.00")

    return _round(price * MULTIPLIERS[payment_type])


def create_payment_session(appointment, payment_type: str, request=None):
    money_to_pay = calculate_money_to_pay(appointment, payment_type)

    if money_to_pay <= Decimal("0.00"):
        return None

    if request is not None:
        success_url = (
            request.build_absolute_uri(
                reverse("payments:payment-success")
            )
            + "?session_id={CHECKOUT_SESSION_ID}"
        )
        cancel_url = (
            request.build_absolute_uri(
                reverse("payments:payment-cancel")
            )
            + "?session_id={CHECKOUT_SESSION_ID}"
        )
    else:
        success_url = "https://example.com/success/?session_id={CHECKOUT_SESSION_ID}"
        cancel_url = "https://example.com/cancel/?session_id={CHECKOUT_SESSION_ID}"

    session = stripe.checkout.Session.create(
        mode="payment",
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "unit_amount": int(money_to_pay * 100),
                    "product_data": {
                        "name": (
                            f"{payment_type.replace('_', ' ').title()} "
                            f"— Appointment #{appointment.id}"
                        ),
                    },
                },
                "quantity": 1,
            }
        ],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "appointment_id": str(appointment.id),
            "payment_type": payment_type,
        },
    )

    return Payment.objects.create(
        appointment=appointment,
        type=payment_type,
        status=Payment.Status.PENDING,
        money_to_pay=money_to_pay,
        session_id=session.id,
        session_url=session.url,
    )
