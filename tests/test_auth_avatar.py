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

    # Admin email check (case-insensitive)
    admin_user = User(email="silatanuikipngetich@gmail.com", display_name="Sila Kipngetich")
    assert admin_user.is_admin is True
    assert admin_user.initials == "SK"
    assert admin_user.to_dict()["is_admin"] is True

    admin_upper = User(email="SILATANUIKIPNGETICH@GMAIL.COM ")
    assert admin_upper.is_admin is True

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


def test_admin_user_technicalities_access(client, app):
    with app.app_context():
        admin = User(email="silatanuikipngetich@gmail.com", display_name="Sila Tanui")
        admin.set_password("AdminPass123!")
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
