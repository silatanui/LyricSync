"""Freemium image-credit helpers for AI lyric scene generation."""
from __future__ import annotations

from flask import current_app
from flask_login import current_user

from app.extensions import db
from app.models.user import User


def free_image_credits() -> int:
    return int(current_app.config.get("IMAGE_FREE_CREDITS", 2))


def premium_image_credits() -> int:
    return int(current_app.config.get("IMAGE_PREMIUM_CREDITS", 100))


def premium_price_label() -> str:
    return str(current_app.config.get("IMAGE_PREMIUM_PRICE_LABEL", "$5/month"))


def credits_payload(user: User | None = None) -> dict:
    """Public credit status for API + editor UI."""
    u = user
    if u is None:
        try:
            if getattr(current_user, "is_authenticated", False):
                u = current_user
        except Exception:
            u = None

    if u is None:
        return {
            "authenticated": False,
            "is_admin": False,
            "is_premium": False,
            "unlimited": False,
            "image_credits": 0,
            "can_generate": False,
            "free_allowance": free_image_credits(),
            "premium_credits": premium_image_credits(),
            "premium_price_label": premium_price_label(),
            "stripe_enabled": bool(current_app.config.get("STRIPE_SECRET_KEY")),
        }

    unlimited = bool(u.is_admin)
    remaining = None if unlimited else int(u.image_credits or 0)
    can_generate = unlimited or remaining > 0
    return {
        "authenticated": True,
        "is_admin": bool(u.is_admin),
        "is_premium": bool(u.is_premium),
        "unlimited": unlimited,
        "image_credits": remaining if remaining is not None else -1,
        "can_generate": can_generate,
        "free_allowance": free_image_credits(),
        "premium_credits": premium_image_credits(),
        "premium_price_label": premium_price_label(),
        "stripe_enabled": bool(current_app.config.get("STRIPE_SECRET_KEY")),
    }


def ensure_user_can_generate(user: User) -> tuple[bool, dict | None]:
    """
    Return (ok, error_payload).
    Admins always pass. Everyone else needs image_credits > 0.
    """
    if user.is_admin:
        return True, None
    if int(user.image_credits or 0) > 0:
        return True, None
    return False, {
        "code": "IMAGE_CREDITS_EXHAUSTED",
        "message": (
            f"You've used your free AI image credits. "
            f"Upgrade to Premium ({premium_price_label()} for {premium_image_credits()} images) to keep generating."
        ),
        "retryable": False,
        "credits": credits_payload(user),
    }


def consume_image_credit(user: User) -> dict:
    """Decrement one credit after a successful AI image generation. Admins are free."""
    if user.is_admin:
        return credits_payload(user)
    remaining = int(user.image_credits or 0)
    if remaining > 0:
        user.image_credits = remaining - 1
        db.session.commit()
    return credits_payload(user)


def grant_premium_credits(user: User, credits: int | None = None) -> dict:
    """Mark premium and add a monthly credit pack."""
    pack = int(credits if credits is not None else premium_image_credits())
    user.is_premium = True
    user.image_credits = int(user.image_credits or 0) + pack
    db.session.commit()
    return credits_payload(user)
