import pytest
from app.models.user import User
from app.extensions import db

def test_user_initials_computation():
    # Two words display name
    u1 = User(email="test@example.com", display_name="Sila Kipngetich")
    assert u1.initials == "SK"

    # Single word display name
    u2 = User(email="test@example.com", display_name="Sila")
    assert u2.initials == "SI"

    # No display name, email with dots
    u3 = User(email="sila.kipngetich@tanuisila.dev")
    assert u3.initials == "SK"

    # No display name, email with underscore
    u4 = User(email="john_doe@studio.com")
    assert u4.initials == "JD"

    # No display name, email with hyphen
    u5 = User(email="mary-jane@studio.com")
    assert u5.initials == "MJ"

    # Plain single-part email prefix
    u6 = User(email="admin@studio.com")
    assert u6.initials == "AD"

    # Monogram in to_dict
    assert u1.to_dict()["initials"] == "SK"


def test_logout_routes(client, app):
    with app.app_context():
        user = User(email="artist@lyricsync.studio", display_name="Studio Artist")
        user.set_password("Secret123!")
        db.session.add(user)
        db.session.commit()

        # Login
        login_res = client.post("/api/auth/login", json={
            "email": "artist@lyricsync.studio",
            "password": "Secret123!"
        })
        assert login_res.status_code == 200
        assert login_res.get_json()["user"]["initials"] == "SA"

        # Verify home page renders user initials in navbar
        home_res = client.get("/")
        assert home_res.status_code == 200
        html = home_res.get_data(as_text=True)
        assert "SA" in html
        assert "user-nav-dropdown" in html
        assert "user-dropdown-menu" in html
        assert "userProfileModal" in html
        assert "Sign Out" in html

        # GET /logout
        logout_res = client.get("/logout", follow_redirects=False)
        assert logout_res.status_code == 302
        assert logout_res.headers["Location"].endswith("/")

        # Re-login
        client.post("/api/auth/login", json={
            "email": "artist@lyricsync.studio",
            "password": "Secret123!"
        })

        # POST /api/auth/logout
        api_logout_res = client.post("/api/auth/logout")
        assert api_logout_res.status_code == 200
        assert api_logout_res.get_json()["success"] is True
