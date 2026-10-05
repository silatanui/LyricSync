"""Daily AI image-credit helpers for lyric scene generation."""
from __future__ import annotations

from datetime import datetime, timezone

from flask import current_app
from flask_login import current_user

from app.extensions import db
from app.models.user import User


def daily_image_credits() -> int:
    return int(
        current_app.config.get("IMAGE_DAILY_CREDITS")
        or current_app.config.get("IMAGE_FREE_CREDITS")
        or 2
    )


def free_image_credits() -> int:
    """Legacy alias for daily allowance."""
    return daily_image_credits()


def premium_image_credits() -> int:
    return int(current_app.config.get("IMAGE_PREMIUM_CREDITS", 100))


def premium_price_label() -> str:
    return str(current_app.config.get("IMAGE_PREMIUM_PRICE_LABEL", "$5/100"))


def _utc_today():
    return datetime.now(timezone.utc).date()


def refresh_daily_credits(user: User, *, commit: bool = False) -> User:
    """
    Reset the user's daily AI image allowance when the UTC calendar day changes.
    Bonus/premium credits are never wiped by this refresh.
    """
    if user is None or user.is_admin:
        return user

    today = _utc_today()
    reset_on = getattr(user, "image_credits_reset_on", None)
    if hasattr(reset_on, "date") and callable(getattr(reset_on, "date", None)):
        # Normalize datetime -> date when drivers return datetime.
        try:
            reset_on = reset_on.date()
        except Exception:
            pass

    if reset_on != today:
        user.image_credits = daily_image_credits()
        user.image_credits_reset_on = today
        if commit:
            db.session.commit()
    return user


def remaining_credits(user: User) -> int:
    """Total remaining generations (daily + bonus)."""
    if user.is_admin:
        return -1
    refresh_daily_credits(user)
    return int(user.image_credits or 0) + int(getattr(user, "bonus_image_credits", 0) or 0)


def credits_payload(user: User | None = None) -> dict:
    """Public credit status for API + editor UI."""
    u = user
    if u is None:
        try:
            if getattr(current_user, "is_authenticated", False):
                u = current_user
        except Exception:
            u = None

    daily_allowance = daily_image_credits()
    if u is None:
        return {
            "authenticated": False,
            "is_admin": False,
            "is_premium": False,
            "unlimited": False,
            "image_credits": 0,
            "daily_credits": 0,
            "bonus_credits": 0,
            "daily_allowance": daily_allowance,
            "can_generate": False,
            "resets": "daily",
            "free_allowance": daily_allowance,
            "premium_credits": premium_image_credits(),
            "premium_price_label": premium_price_label(),
            "stripe_enabled": bool(current_app.config.get("STRIPE_SECRET_KEY")),
        }

    unlimited = bool(u.is_admin)
    if not unlimited:
        refresh_daily_credits(u, commit=True)

    daily = None if unlimited else int(u.image_credits or 0)
    bonus = 0 if unlimited else int(getattr(u, "bonus_image_credits", 0) or 0)
    remaining = None if unlimited else (daily + bonus)
    can_generate = unlimited or (remaining or 0) > 0
    return {
        "authenticated": True,
        "is_admin": bool(u.is_admin),
        "is_premium": bool(u.is_premium),
        "unlimited": unlimited,
        "image_credits": remaining if remaining is not None else -1,
        "daily_credits": daily if daily is not None else -1,
        "bonus_credits": bonus,
        "daily_allowance": daily_allowance,
        "can_generate": can_generate,
        "resets": "daily",
        "free_allowance": daily_allowance,
        "premium_credits": premium_image_credits(),
        "premium_price_label": premium_price_label(),
        "stripe_enabled": bool(current_app.config.get("STRIPE_SECRET_KEY")),
    }


def ensure_user_can_generate(user: User) -> tuple[bool, dict | None]:
    """
    Return (ok, error_payload).
    Admins always pass. Everyone else needs remaining daily or bonus credits.
    """
    if user.is_admin:
        return True, None
    refresh_daily_credits(user, commit=True)
    if remaining_credits(user) > 0:
        return True, None
    daily = daily_image_credits()
    return False, {
        "code": "IMAGE_CREDITS_EXHAUSTED",
        "message": (
            f"You've used today's {daily} free AI image"
            f"{'s' if daily != 1 else ''}. "
            f"Come back tomorrow for {daily} more, or upgrade to Premium "
            f"({premium_price_label()})."
        ),
        "retryable": False,
        "credits": credits_payload(user),
    }


def consume_image_credit(user: User) -> dict:
    """Spend one daily credit first, then bonus. Admins are free."""
    if user.is_admin:
        return credits_payload(user)
    refresh_daily_credits(user)
    daily = int(user.image_credits or 0)
    bonus = int(getattr(user, "bonus_image_credits", 0) or 0)
    if daily > 0:
        user.image_credits = daily - 1
    elif bonus > 0:
        user.bonus_image_credits = bonus - 1
    db.session.commit()
    return credits_payload(user)


def grant_premium_credits(user: User, credits: int | None = None) -> dict:
    """Mark premium and add a bonus pack that does not reset daily."""
    pack = int(credits if credits is not None else premium_image_credits())
    refresh_daily_credits(user)
    user.is_premium = True
    user.bonus_image_credits = int(getattr(user, "bonus_image_credits", 0) or 0) + pack
    db.session.commit()
    try:
        return credits_payload(user)
    except Exception:
        # Credits already persisted; payload is best-effort for API callers.
        return {
            "authenticated": True,
            "is_admin": bool(user.is_admin),
            "is_premium": True,
            "unlimited": bool(user.is_admin),
            "image_credits": int(user.image_credits or 0)
            + int(getattr(user, "bonus_image_credits", 0) or 0),
            "bonus_credits": int(getattr(user, "bonus_image_credits", 0) or 0),
            "can_generate": True,
        }


def revoke_premium_credits(user: User, *, clear_customer: bool = True) -> dict:
    """Remove Premium flag and bonus image credits (does not cancel Stripe itself)."""
    user.is_premium = False
    user.bonus_image_credits = 0
    if clear_customer:
        user.stripe_customer_id = None
    db.session.commit()
    return credits_payload(user)
