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


def _ensure_billing_columns() -> None:
    """Add premium/Stripe columns if a host skipped the startup migration."""
    try:
        inspector = db.inspect(db.engine)
        if "users" not in inspector.get_table_names():
            return
        user_cols = {c["name"] for c in inspector.get_columns("users")}
        altered = False
        if "bonus_image_credits" not in user_cols:
            db.session.execute(db.text(
                "ALTER TABLE users ADD COLUMN bonus_image_credits INTEGER NOT NULL DEFAULT 0"
            ))
            altered = True
        if "is_premium" not in user_cols:
            db.session.execute(db.text(
                "ALTER TABLE users ADD COLUMN is_premium BOOLEAN NOT NULL DEFAULT 0"
            ))
            altered = True
        if "stripe_customer_id" not in user_cols:
            db.session.execute(db.text(
                "ALTER TABLE users ADD COLUMN stripe_customer_id VARCHAR(128) NULL"
            ))
            altered = True
        if "image_credits_reset_on" not in user_cols:
            db.session.execute(db.text(
                "ALTER TABLE users ADD COLUMN image_credits_reset_on DATE NULL"
            ))
            altered = True
        if altered:
            db.session.commit()
    except Exception as exc:
        db.session.rollback()
        current_app.logger.warning("Billing column ensure failed: %s", exc)


def _stripe_obj_get(obj, key, default=None):
    """Safe get for StripeObject / dict payloads."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    try:
        val = obj.get(key, default)
        return default if val is None else val
    except Exception:
        try:
            return obj[key]
        except Exception:
            return default


def _stripe_str(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    # Expanded Stripe objects expose an id field.
    obj_id = _stripe_obj_get(value, "id")
    if isinstance(obj_id, str) and obj_id.strip():
        return obj_id.strip()
    text = str(value).strip()
    return text or None


def _find_user_for_stripe(data_object) -> User | None:
    """Resolve the LyricSync user from Checkout/Invoice fields."""
    meta = _stripe_obj_get(data_object, "metadata") or {}
    user_id = _stripe_str(_stripe_obj_get(meta, "user_id")) or _stripe_str(
        _stripe_obj_get(data_object, "client_reference_id")
    )
    if user_id:
        user = db.session.get(User, user_id)
        if user:
            return user

    customer_id = _stripe_str(_stripe_obj_get(data_object, "customer"))
    if customer_id:
        user = db.session.query(User).filter(User.stripe_customer_id == customer_id).first()
        if user:
            return user

    email = _stripe_str(_stripe_obj_get(data_object, "customer_email"))
    if not email:
        details = _stripe_obj_get(data_object, "customer_details") or {}
        email = _stripe_str(_stripe_obj_get(details, "email"))
    if email:
        user = db.session.query(User).filter(db.func.lower(User.email) == email.lower()).first()
        if user:
            return user
    return None


def _should_grant_for_event(event_type: str, data_object) -> bool:
    """
    Grant on Checkout completion, and on subscription renewals only.
    Skip invoice.paid for subscription_create so the first payment is not double-granted.
    """
    if event_type == "checkout.session.completed":
        return True
    if event_type == "invoice.paid":
        reason = _stripe_str(_stripe_obj_get(data_object, "billing_reason")) or ""
        # Initial sub create is handled by checkout.session.completed.
        if reason == "subscription_create":
            return False
        return reason in ("subscription_cycle", "subscription_update", "manual")
    return False


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

        session_meta = {
            "user_id": current_user.id,
            "product": "image_premium",
            "credits": str(premium_image_credits()),
        }
        if price_id:
            session = stripe.checkout.Session.create(
                mode="subscription",
                line_items=[{"price": price_id, "quantity": 1}],
                success_url=success_url,
                cancel_url=cancel_url,
                client_reference_id=current_user.id,
                metadata=session_meta,
                subscription_data={"metadata": session_meta},
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
                metadata=session_meta,
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

    try:
        event_type = _stripe_str(_stripe_obj_get(event, "type")) or (
            event["type"] if not isinstance(event, dict) else event.get("type")
        )
        data = _stripe_obj_get(event, "data") or {}
        data_object = _stripe_obj_get(data, "object") or {}

        if event_type in ("checkout.session.completed", "invoice.paid"):
            if _should_grant_for_event(event_type, data_object):
                _ensure_billing_columns()
                user = _find_user_for_stripe(data_object)
                if user:
                    customer_id = _stripe_str(_stripe_obj_get(data_object, "customer"))
                    if customer_id and not user.stripe_customer_id:
                        user.stripe_customer_id = customer_id
                    grant_premium_credits(user)
                    current_app.logger.info(
                        "Granted premium image credits to user %s via Stripe %s",
                        user.id,
                        event_type,
                    )
                else:
                    current_app.logger.warning(
                        "Stripe %s had no matching LyricSync user", event_type
                    )
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Stripe webhook processing failed: %s", exc)
        return jsonify({
            "success": False,
            "error": "webhook_processing_failed",
            "message": str(exc)[:300],
        }), 500

    return jsonify({"success": True, "received": True})
