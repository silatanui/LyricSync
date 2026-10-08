import pytest
from app.models.user import User
from app.extensions import db

def test_user_initials_and_admin_computation():
    # Two words display name
    u1 = User(email="test@example.com", display_name="Sila Kipngetich")
    assert u1.initials == "SK"
    assert u1.is_admin is False

    # Single word display name
    u2 = User(email="test@example.com", display_name="Sila")
    assert u2.initials == "SI"
    assert u2.is_admin is False

    # Admin email alone is not enough — mailbox must be verified (or Google-linked).
    admin_unverified = User(email="silatanuikipngetich@gmail.com", display_name="Sila Kipngetich")
    assert admin_unverified.is_admin is False

    admin_user = User(
        email="silatanuikipngetich@gmail.com",
        display_name="Sila Kipngetich",
        email_verified=True,
    )
    assert admin_user.is_admin is True
    assert admin_user.initials == "SK"
    assert admin_user.to_dict()["is_admin"] is True

    admin_upper = User(email="SILATANUIKIPNGETICH@GMAIL.COM ", email_verified=True)
    assert admin_upper.is_admin is True

    admin_google = User(email="silatanuikipngetich@gmail.com", google_id="google-sub-1")
    assert admin_google.is_admin is True

    # No display name, email with dots
    u3 = User(email="sila.kipngetich@tanuisila.dev")
    assert u3.initials == "SK"
    assert u3.is_admin is False

    # Monogram in to_dict
    assert u1.to_dict()["initials"] == "SK"


def test_logout_routes_and_normal_user_ui(client, app):
    with app.app_context():
        user = User(email="artist@lyricsync.studio", display_name="Studio Artist")
        user.set_password("Secret123!")
        user.email_verified = True  # Pre-verify so login isn't blocked by activation check
        db.session.add(user)
        db.session.commit()

        # Login as normal user
        login_res = client.post("/api/auth/login", json={
            "email": "artist@lyricsync.studio",
            "password": "Secret123!"
        })
        assert login_res.status_code == 200
        assert login_res.get_json()["user"]["initials"] == "SA"
        assert login_res.get_json()["user"]["is_admin"] is False

        # Verify home page renders user initials in navbar without modals or technicalities
        home_res = client.get("/")
        assert home_res.status_code == 200
        html = home_res.get_data(as_text=True)
        assert "SA" in html
        assert "user-nav-dropdown" in html
        assert "user-dropdown-menu" in html
        assert "Sign Out" in html
        # Minimized modals: userProfileModal is not used
        assert "userProfileModal" not in html
        # Technical health link and admin diagnostics are hidden from normal users
        assert "Admin Diagnostics" not in html
        assert "/health" not in html

        # Normal user health check access hides deep technical server internals
        health_res = client.get("/health")
        assert health_res.status_code == 200
        health_data = health_res.get_json()
        assert health_data["status"] == "healthy"
        assert health_data["database"] == "connected"
        assert "database_tables" not in health_data
        assert "ffmpeg_binary" not in health_data
        assert "storage_path" not in health_data

        # GET /logout
        logout_res = client.get("/logout", follow_redirects=False)
        assert logout_res.status_code == 302
        assert logout_res.headers["Location"].endswith("/")


def test_registering_admin_email_requires_activation(client, app, monkeypatch):
    """Knowing the admin address must not skip inbox verification."""
    from app.models.user import ADMIN_EMAIL

    sent = {}

    def _fake_send(email, display_name, activation_url):
        sent["email"] = email
        sent["url"] = activation_url
        return True

    monkeypatch.setattr("app.routes.auth.send_activation_email", _fake_send)

    with app.app_context():
        existing = db.session.query(User).filter_by(email=ADMIN_EMAIL).first()
        if existing:
            db.session.delete(existing)
            db.session.commit()

        res = client.post("/api/auth/register", json={
            "email": ADMIN_EMAIL,
            "password": "HackerPass1!",
            "display_name": "Intruder",
        })
        assert res.status_code == 201
        body = res.get_json()
        assert body["needs_activation"] is True
        assert "user" not in body or body.get("user") is None

        user = db.session.query(User).filter_by(email=ADMIN_EMAIL).first()
        assert user is not None
        assert user.email_verified is False
        assert user.is_admin is False
        assert sent.get("email") == ADMIN_EMAIL

        blocked = client.post("/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": "HackerPass1!",
        })
        assert blocked.status_code == 403
        assert blocked.get_json()["error"]["code"] == "EMAIL_NOT_VERIFIED"


def test_admin_user_technicalities_access(client, app):
    with app.app_context():
        admin = User(email="silatanuikipngetich@gmail.com", display_name="Sila Tanui")
        admin.set_password("AdminPass123!")
        admin.email_verified = True
        db.session.add(admin)
        db.session.commit()

        # Login as admin
        login_res = client.post("/api/auth/login", json={
            "email": "silatanuikipngetich@gmail.com",
            "password": "AdminPass123!"
        })
        assert login_res.status_code == 200
        assert login_res.get_json()["user"]["is_admin"] is True

        # Admin navbar includes Admin Diagnostics and Health Link
        home_res = client.get("/")
        assert home_res.status_code == 200
        html = home_res.get_data(as_text=True)
        assert "System Admin" in html
        assert "Admin Diagnostics" in html
        assert "Whisper-1" in html
        assert "FFmpeg (libass)" in html
        assert "/health" in html

        # Admin health check endpoint returns full technical diagnostics
        health_res = client.get("/health")
        assert health_res.status_code == 200
        health_data = health_res.get_json()
        assert health_data["admin_access"] is True
        assert "database_tables" in health_data
        assert "ffmpeg_binary" in health_data
        assert "ai_model" in health_data
        assert "rendering_engine" in health_data
