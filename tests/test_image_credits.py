from app.extensions import db
from app.models.user import User, ADMIN_EMAIL
from app.services.image_credits import (
    consume_image_credit,
    credits_payload,
    ensure_user_can_generate,
    grant_premium_credits,
)


def test_new_user_gets_free_image_credits(app):
    with app.app_context():
        free = int(app.config.get("IMAGE_FREE_CREDITS", 2))
        user = User(email="credits@example.com", display_name="Credit User")
        user.set_password("Secret123!")
        user.email_verified = True
        db.session.add(user)
        db.session.commit()
        assert user.image_credits == free
        assert user.has_image_credits is True
        assert user.to_dict()["image_credits"] == free


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


def test_free_user_consumes_and_locks(app):
    with app.app_context():
        user = User(email="spender@example.com", display_name="Spender", image_credits=2)
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


def test_premium_grant_adds_pack(app):
    with app.app_context():
        user = User(email="premium@example.com", display_name="Prem", image_credits=0)
        db.session.add(user)
        db.session.commit()
        pack = int(app.config.get("IMAGE_PREMIUM_CREDITS", 100))
        payload = grant_premium_credits(user)
        assert user.is_premium is True
        assert user.image_credits == pack
        assert payload["can_generate"] is True


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

        user = User(email="locked@example.com", display_name="Locked", image_credits=0)
        user.set_password("Secret123!")
        user.email_verified = True
        db.session.add(user)
        db.session.commit()

        login = client.post("/api/auth/login", json={
            "email": "locked@example.com",
            "password": "Secret123!",
        })
        assert login.status_code == 200
        assert login.get_json()["user"]["image_credits"] == 0

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

        checkout = client.post("/api/billing/checkout")
        assert checkout.status_code == 503
        assert checkout.get_json()["error"]["code"] == "STRIPE_NOT_CONFIGURED"


def test_credits_payload_guest(app):
    with app.app_context():
        payload = credits_payload(None)
        assert payload["authenticated"] is False
        assert payload["can_generate"] is False
