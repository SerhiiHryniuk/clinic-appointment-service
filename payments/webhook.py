import stripe
from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from loguru import logger

from notifications.tasks import send_telegram_message_task
from payments.models import Payment


@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    if not sig_header:
        logger.warning("Webhook hit rejected: "
                       "Missing HTTP_STRIPE_SIGNATURE header.")
        return HttpResponse("Missing Stripe signature", status=400)

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        logger.error("Webhook construction failed: "
                     "Invalid payload body structure.")
        return HttpResponse("Invalid payload", status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.error(
            f"Webhook signature validation failed. "
            f"Verify your STRIPE_WEBHOOK_SECRET settings. "
            f"Details: {e}"
        )
        return HttpResponse("Invalid signature", status=400)

    event_type = event["type"]
    session = event["data"]["object"]
    session_id = session.get("id")

    logger.info(f"Authenticated Stripe Webhook: Event '{event_type}' "
                f"received for Session {session_id}")

    if event_type == "checkout.session.completed":
        with transaction.atomic():
            payments = Payment.objects.select_for_update().filter(
                session_id=session_id,
                status=Payment.Status.PENDING,
            )

            if not payments.exists():
                logger.warning(
                    f"Received 'checkout.session.completed' for "
                    f"Session {session_id}, "
                    f"but no local matching PENDING payment "
                    f"records were found."
                )

            for payment in payments:
                payment.status = Payment.Status.PAID
                payment.save()

                logger.info(
                    f"Financial Sync Confirmed: "
                    f"Payment #{payment.id} for Appointment "
                    f"#{payment.appointment_id} updated to PAID "
                    f"via Stripe Webhook."
                )

                message = (
                    f"✅ <b>Payment successful!</b>\n"
                    f"Appointment ID: #{payment.appointment_id}\n"
                    f"Amount: {payment.money_to_pay} USD"
                )
                send_telegram_message_task.delay(message)

                logger.info(f"Dispatched Celery Telegram notification task "
                            f"for Payment #{payment.id}.")

    elif event_type == "checkout.session.expired":
        with transaction.atomic():
            updated_count = Payment.objects.select_for_update().filter(
                session_id=session_id,
                status=Payment.Status.PENDING,
            ).update(status=Payment.Status.EXPIRED)

            logger.info(
                f"Stripe Session {session_id} expired. "
                f"Updated {updated_count} matching "
                f"local payment records to EXPIRED."
            )

    else:
        logger.debug(f"Ignoring unhandled "
                     f"Stripe operational event: '{event_type}'")

    return HttpResponse(status=200)
