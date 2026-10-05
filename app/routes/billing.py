"""Image-credit status + Stripe Checkout for Premium packs."""
from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import User
from app.services.image_credits import (
    credits_payload,
    grant_premium_credits,
    premium_image_credits,
    premium_price_label,
)

billing_bp = Blueprint("billing", __name__, url_prefix="/api/billing")


@billing_bp.route("/image-credits", methods=["GET"])
def image_credits_status():
    return jsonify({"success": True, "credits": credits_payload()})


@billing_bp.route("/checkout", methods=["POST"])
@login_required
def create_checkout_session():
    """
    Start a Stripe Checkout session for Premium image credits.
    Requires STRIPE_SECRET_KEY. Prefer STRIPE_PRICE_ID for a recurring $5/mo Price;
    otherwise creates a one-time payment for IMAGE_PREMIUM_PRICE_CENTS.
    """
    if current_user.is_admin:
        return jsonify({
            "success": True,
            "skipped": True,
            "message": "Admin accounts have unlimited AI image generation.",
            "credits": credits_payload(current_user),
        })

    secret = current_app.config.get("STRIPE_SECRET_KEY") or ""
    if not secret:
        return jsonify({
            "success": False,
            "error": {
                "code": "STRIPE_NOT_CONFIGURED",
                "message": (
                    "Card payments are not enabled yet. Add STRIPE_SECRET_KEY "
                    "(and ideally STRIPE_PRICE_ID) to your environment, then restart the app."
                ),
                "retryable": False,
                "setup": {
                    "docs": "https://stripe.com/docs/checkout/quickstart",
                    "env_keys": [
                        "STRIPE_SECRET_KEY",
                        "STRIPE_PUBLISHABLE_KEY",
                        "STRIPE_WEBHOOK_SECRET",
                        "STRIPE_PRICE_ID",
                    ],
                },
            },
        }), 503

    try:
        import stripe
    except ImportError:
        return jsonify({
            "success": False,
            "error": {
                "code": "STRIPE_SDK_MISSING",
                "message": "Install the stripe package (`pip install stripe`) to enable card checkout.",
                "retryable": False,
            },
        }), 503

    stripe.api_key = secret
    price_id = (current_app.config.get("STRIPE_PRICE_ID") or "").strip()
    success_url = url_for("views.dashboard", _external=True) + "?billing=success"
    cancel_url = url_for("views.dashboard", _external=True) + "?billing=cancelled"

    try:
        customer_kwargs = {}
        if current_user.stripe_customer_id:
            customer_kwargs["customer"] = current_user.stripe_customer_id
        else:
            customer_kwargs["customer_email"] = current_user.email

        if price_id:
            session = stripe.checkout.Session.create(
                mode="subscription",
                line_items=[{"price": price_id, "quantity": 1}],
                success_url=success_url,
                cancel_url=cancel_url,
                client_reference_id=current_user.id,
                metadata={
                    "user_id": current_user.id,
                    "product": "image_premium",
                    "credits": str(premium_image_credits()),
                },
                **customer_kwargs,
            )
        else:
            session = stripe.checkout.Session.create(
                mode="payment",
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": int(current_app.config.get("IMAGE_PREMIUM_PRICE_CENTS", 500)),
                        "product_data": {
                            "name": current_app.config.get(
                                "IMAGE_PREMIUM_PRODUCT_NAME",
                                "LyricSync Premium — 100 AI images",
                            ),
                            "description": (
                                f"{premium_image_credits()} AI lyric scene credits "
                                f"({premium_price_label()})"
                            ),
                        },
                    },
                    "quantity": 1,
                }],
                success_url=success_url,
                cancel_url=cancel_url,
                client_reference_id=current_user.id,
                metadata={
                    "user_id": current_user.id,
                    "product": "image_premium",
                    "credits": str(premium_image_credits()),
                },
                **customer_kwargs,
            )
    except Exception as exc:
        current_app.logger.exception("Stripe checkout failed: %s", exc)
        return jsonify({
            "success": False,
            "error": {
                "code": "STRIPE_CHECKOUT_FAILED",
                "message": f"Could not start card checkout: {exc}",
                "retryable": True,
            },
        }), 502

    return jsonify({
        "success": True,
        "checkout_url": session.url,
        "session_id": session.id,
    })


@billing_bp.route("/webhook/stripe", methods=["POST"])
def stripe_webhook():
    """Stripe webhook: grant Premium credits after successful payment/subscription."""
    secret = current_app.config.get("STRIPE_SECRET_KEY") or ""
    wh_secret = current_app.config.get("STRIPE_WEBHOOK_SECRET") or ""
    if not secret:
        return jsonify({"success": False}), 503

    try:
        import stripe
    except ImportError:
        return jsonify({"success": False}), 503

    stripe.api_key = secret
    payload = request.get_data()
    sig = request.headers.get("Stripe-Signature", "")

    try:
        if wh_secret:
            event = stripe.Webhook.construct_event(payload, sig, wh_secret)
        else:
            # Dev fallback when webhook signing is not configured yet
            event = stripe.Event.construct_from(
                request.get_json(force=True, silent=True) or {},
                stripe.api_key,
            )
    except Exception as exc:
        current_app.logger.warning("Stripe webhook verify failed: %s", exc)
        return jsonify({"success": False, "error": "invalid_payload"}), 400

    event_type = event.get("type") if isinstance(event, dict) else event["type"]
    data_object = event["data"]["object"] if not isinstance(event, dict) else event["data"]["object"]

    if event_type in ("checkout.session.completed", "invoice.paid"):
        meta = data_object.get("metadata") or {}
        user_id = meta.get("user_id") or data_object.get("client_reference_id")
        customer_id = data_object.get("customer")
        if user_id:
            user = db.session.get(User, user_id)
            if user:
                if customer_id and not user.stripe_customer_id:
                    user.stripe_customer_id = customer_id
                grant_premium_credits(user)
                current_app.logger.info(
                    "Granted premium image credits to user %s via Stripe %s",
                    user_id,
                    event_type,
                )

    return jsonify({"success": True, "received": True})
