import re
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db, oauth
from app.models import User

auth_bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _wants_json() -> bool:
    return request.is_json or request.accept_mimetypes.best == "application/json"


def _google_enabled() -> bool:
    return bool(current_app.config.get("GOOGLE_CLIENT_ID") and current_app.config.get("GOOGLE_CLIENT_SECRET"))


@auth_bp.app_context_processor
def inject_google_enabled():
    return {"google_auth_enabled": _google_enabled()}


@auth_bp.route("/register", methods=["GET"])
def register_page():
    if current_user.is_authenticated:
        return redirect(url_for("views.dashboard"))
    return render_template("register.html")


@auth_bp.route("/login", methods=["GET"])
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for("views.dashboard"))
    return render_template("login.html")


@auth_bp.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or request.form
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    display_name = (data.get("display_name") or "").strip()

    if not email or not EMAIL_RE.match(email):
        return jsonify({
            "success": False,
            "error": {"code": "INVALID_EMAIL", "message": "A valid email address is required.", "retryable": False}
        }), 400

    if len(password) < 8:
        return jsonify({
            "success": False,
            "error": {"code": "WEAK_PASSWORD", "message": "Password must be at least 8 characters.", "retryable": False}
        }), 400

    existing = db.session.query(User).filter_by(email=email).first()
    if existing:
        return jsonify({
            "success": False,
            "error": {"code": "EMAIL_TAKEN", "message": "An account with this email already exists.", "retryable": False}
        }), 409

    user = User(email=email, display_name=display_name or email.split("@")[0])
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    login_user(user)

    if _wants_json():
        return jsonify({"success": True, "user": user.to_dict()}), 201
    return redirect(url_for("views.dashboard"))


@auth_bp.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or request.form
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    remember = bool(data.get("remember"))

    user = db.session.query(User).filter_by(email=email).first()
    if not user or not user.check_password(password):
        if _wants_json():
            return jsonify({
                "success": False,
                "error": {"code": "INVALID_CREDENTIALS", "message": "Incorrect email or password.", "retryable": False}
            }), 401
        flash("Incorrect email or password.", "danger")
        return redirect(url_for("auth.login_page"))

    login_user(user, remember=remember)

    if _wants_json():
        return jsonify({"success": True, "user": user.to_dict()})
    return redirect(url_for("views.dashboard"))


@auth_bp.route("/api/auth/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    if _wants_json():
        return jsonify({"success": True})
    return redirect(url_for("views.home"))


@auth_bp.route("/login/google", methods=["GET"])
def google_login():
    if not _google_enabled():
        abort_message = "Google sign-in is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET."
        flash(abort_message, "danger")
        return redirect(url_for("auth.login_page"))
    redirect_uri = url_for("auth.google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route("/login/google/callback", methods=["GET"])
def google_callback():
    if not _google_enabled():
        return redirect(url_for("auth.login_page"))

    token = oauth.google.authorize_access_token()
    userinfo = token.get("userinfo") or oauth.google.userinfo(token=token)

    google_id = userinfo.get("sub")
    email = (userinfo.get("email") or "").strip().lower()
    if not google_id or not email:
        flash("Google did not return the required account details.", "danger")
        return redirect(url_for("auth.login_page"))

    user = db.session.query(User).filter_by(google_id=google_id).first()
    if not user:
        # Link to an existing email/password account, or create a new one
        user = db.session.query(User).filter_by(email=email).first()
        if not user:
            user = User(email=email, display_name=userinfo.get("name") or email.split("@")[0])
            db.session.add(user)
        user.google_id = google_id
        user.avatar_url = userinfo.get("picture")
        if not user.display_name:
            user.display_name = userinfo.get("name") or email.split("@")[0]
        db.session.commit()

    login_user(user)
    return redirect(url_for("views.dashboard"))


@auth_bp.route("/api/auth/me", methods=["GET"])
def me():
    if not current_user.is_authenticated:
        return jsonify({"success": True, "user": None})
    return jsonify({"success": True, "user": current_user.to_dict()})
