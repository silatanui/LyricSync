from datetime import date, timedelta

from app.extensions import db
from app.models.user import User, ADMIN_EMAIL
from app.services.image_credits import (
    consume_image_credit,
    credits_payload,
    daily_image_credits,
    ensure_user_can_generate,
    grant_premium_credits,
    refresh_daily_credits,
)


def test_new_user_gets_daily_image_credits(app):
    with app.app_context():
        daily = daily_image_credits()
        user = User(email="credits@example.com", display_name="Credit User")
        user.set_password("Secret123!")
        user.email_verified = True
        db.session.add(user)
        db.session.commit()
        assert user.image_credits == daily
        assert user.has_image_credits is True
        assert user.to_dict()["image_credits"] == daily


def test_admin_is_unlimited(app):
    with app.app_context():
        admin = User(email=ADMIN_EMAIL, display_name="Admin")
        admin.image_credits = 0
        db.session.add(admin)
        db.session.commit()
        ok, err = ensure_user_can_generate(admin)
        assert ok is True
        assert err is None
        payload = consume_image_credit(admin)
        assert payload["unlimited"] is True
        assert payload["can_generate"] is True
        assert admin.image_credits == 0  # never decremented


def test_free_user_daily_limit_and_next_day_refresh(app):
    with app.app_context():
        user = User(
            email="spender@example.com",
            display_name="Spender",
            image_credits=2,
            image_credits_reset_on=date.today(),
            bonus_image_credits=0,
        )
        user.email_verified = True
        db.session.add(user)
        db.session.commit()

        ok, err = ensure_user_can_generate(user)
        assert ok is True
        consume_image_credit(user)
        assert user.image_credits == 1
        consume_image_credit(user)
        assert user.image_credits == 0

        ok, err = ensure_user_can_generate(user)
        assert ok is False
        assert err["code"] == "IMAGE_CREDITS_EXHAUSTED"
        assert err["credits"]["can_generate"] is False
        assert "today" in err["message"].lower()

        # Simulate next UTC day — allowance refreshes.
        user.image_credits_reset_on = date.today() - timedelta(days=1)
        db.session.commit()
        refresh_daily_credits(user, commit=True)
        assert user.image_credits == daily_image_credits()
        ok, err = ensure_user_can_generate(user)
        assert ok is True


def test_premium_bonus_survives_daily_reset(app):
    with app.app_context():
        user = User(
            email="premium@example.com",
            display_name="Prem",
            image_credits=0,
            image_credits_reset_on=date.today(),
            bonus_image_credits=0,
        )
        db.session.add(user)
        db.session.commit()
        pack = int(app.config.get("IMAGE_PREMIUM_CREDITS", 100))
        payload = grant_premium_credits(user)
        assert user.is_premium is True
        assert user.bonus_image_credits == pack
        assert payload["can_generate"] is True

        # Exhaust daily (already 0) and spend one bonus.
        consume_image_credit(user)
        assert user.bonus_image_credits == pack - 1

        # Next day restores daily credits without wiping bonus.
        user.image_credits_reset_on = date.today() - timedelta(days=1)
        refresh_daily_credits(user, commit=True)
        assert user.image_credits == daily_image_credits()
        assert user.bonus_image_credits == pack - 1


def test_ai_background_requires_auth_and_credits(client, app, test_media_dir):
    from app.models import Project

    with app.app_context():
        proj = Project(
            id="test_ai_credits_proj",
            name="AI Credits Project",
            audio_path=str(test_media_dir["audio"]),
            video_path=str(test_media_dir["video"]),
            audio_duration=3.0,
            video_duration=3.0,
        )
        db.session.add(proj)
        db.session.commit()

        anon = client.post(
            "/api/projects/test_ai_credits_proj/background",
            json={"template": "ai_lyric_scene"},
        )
        assert anon.status_code == 401
        assert anon.get_json()["error"]["code"] == "AUTH_REQUIRED"

        user = User(
            email="locked@example.com",
            display_name="Locked",
            image_credits=0,
            image_credits_reset_on=date.today(),
            bonus_image_credits=0,
        )
        user.set_password("Secret123!")
        user.email_verified = True
        db.session.add(user)
        db.session.commit()

        login = client.post("/api/auth/login", json={
            "email": "locked@example.com",
            "password": "Secret123!",
        })
        assert login.status_code == 200

        locked = client.post(
            "/api/projects/test_ai_credits_proj/background",
            json={"template": "ai_lyric_scene"},
        )
        assert locked.status_code == 402
        assert locked.get_json()["error"]["code"] == "IMAGE_CREDITS_EXHAUSTED"

        status = client.get("/api/billing/image-credits")
        assert status.status_code == 200
        body = status.get_json()
        assert body["success"] is True
        assert body["credits"]["can_generate"] is False
        assert body["credits"]["resets"] == "daily"


def test_credits_payload_guest(app):
    with app.app_context():
        payload = credits_payload(None)
        assert payload["authenticated"] is False
        assert payload["can_generate"] is False
        assert payload["daily_allowance"] == daily_image_credits()
