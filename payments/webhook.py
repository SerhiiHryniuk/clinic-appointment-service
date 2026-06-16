import stripe
from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from notifications.tasks import send_telegram_message_task
from payments.models import Payment


@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    if not sig_header:
        return HttpResponse("Missing Stripe signature", status=400)

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return HttpResponse("Invalid payload", status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse("Invalid signature", status=400)

    session = event["data"]["object"]
    session_id = session["id"]

    if event["type"] == "checkout.session.completed":
        with transaction.atomic():
            payments = Payment.objects.select_for_update().filter(
                session_id=session_id,
                status=Payment.Status.PENDING,
            )

            for payment in payments:
                payment.status = Payment.Status.PAID
                payment.save()

                message = (
                    f"✅ <b>Payment successful!</b>\n"
                    f"Appointment ID: #{payment.appointment_id}\n"
                    f"Amount: {payment.money_to_pay} USD"
                )
                send_telegram_message_task.delay(message)

    elif event["type"] == "checkout.session.expired":
        with transaction.atomic():
            Payment.objects.select_for_update().filter(
                session_id=session_id,
                status=Payment.Status.PENDING,
            ).update(status=Payment.Status.EXPIRED)

    return HttpResponse(status=200)
