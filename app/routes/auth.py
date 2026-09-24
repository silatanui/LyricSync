import re
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db, oauth
from app.models import User
from app.models.user import ADMIN_EMAIL
from app.services.email_service import generate_activation_token, verify_activation_token, send_activation_email

auth_bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validates tighter password requirements:
    - Minimum 8 characters
    - At least one uppercase letter (A-Z)
    - At least one lowercase letter (a-z)
    - At least one digit (0-9)
    - At least one special symbol
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must include at least one uppercase letter (A-Z)."
    if not re.search(r"[a-z]", password):
        return False, "Password must include at least one lowercase letter (a-z)."
    if not re.search(r"[0-9]", password):
        return False, "Password must include at least one number (0-9)."
    if not re.search(r"[\W_]", password):
        return False, "Password must include at least one special character (e.g. !@#$%^&*)."
    return True, ""


def _wants_json() -> bool:
    return request.is_json or request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json"


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

    valid, password_msg = validate_password_strength(password)
    if not valid:
        return jsonify({
            "success": False,
            "error": {"code": "WEAK_PASSWORD", "message": password_msg, "retryable": False}
        }), 400

    existing = db.session.query(User).filter_by(email=email).first()
    if existing:
        return jsonify({
            "success": False,
            "error": {"code": "EMAIL_TAKEN", "message": "An account with this email already exists.", "retryable": False}
        }), 409

    # Admin email is auto-verified for administrative operations
    is_admin_user = (email == ADMIN_EMAIL.lower())
    user = User(
        email=email,
        display_name=display_name or email.split("@")[0],
        email_verified=is_admin_user
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    if is_admin_user:
        login_user(user)
        if _wants_json():
            return jsonify({"success": True, "user": user.to_dict(), "needs_activation": False}), 201
        return redirect(url_for("views.dashboard"))

    # Send activation token link via email
    token = generate_activation_token(user.id, user.email)
    activation_url = url_for("auth.activate_account", token=token, _external=True)
    send_activation_email(user.email, user.display_name, activation_url)

    if _wants_json():
        return jsonify({
            "success": True,
            "needs_activation": True,
            "email": user.email,
            "message": "Account created! An activation link has been sent to your email. Please check your inbox to activate your account."
        }), 201

    flash("Account created! Please check your email for the activation link before signing in.", "info")
    return redirect(url_for("auth.login_page"))


@auth_bp.route("/activate/<token>", methods=["GET"])
@auth_bp.route("/auth/activate/<token>", methods=["GET"])
def activate_account(token: str):
    data = verify_activation_token(token)
    if not data or not data.get("user_id"):
        flash("The activation link is invalid or has expired. Please sign in or request a new activation link.", "danger")
        return redirect(url_for("auth.login_page"))

    user = db.session.get(User, data["user_id"])
    if not user or user.email.lower() != data.get("email", "").lower():
        flash("Invalid activation link.", "danger")
        return redirect(url_for("auth.login_page"))

    if not user.email_verified:
        user.email_verified = True
        db.session.commit()

    login_user(user)
    flash("Your email has been successfully verified! Welcome to LyricSync Studio.", "success")
    return redirect(url_for("views.dashboard"))


@auth_bp.route("/api/auth/resend-activation", methods=["POST"])
def resend_activation():
    data = request.get_json(silent=True) or request.form
    email = (data.get("email") or "").strip().lower()
    if not email or not EMAIL_RE.match(email):
        return jsonify({
            "success": False,
            "error": {"code": "INVALID_EMAIL", "message": "A valid email address is required.", "retryable": False}
        }), 400

    user = db.session.query(User).filter_by(email=email).first()
    if user and not user.email_verified:
        token = generate_activation_token(user.id, user.email)
        activation_url = url_for("auth.activate_account", token=token, _external=True)
        send_activation_email(user.email, user.display_name, activation_url)

    return jsonify({
        "success": True,
        "message": "If an unverified account exists with that email, an activation link has been sent."
    })


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

    # Block unverified accounts unless admin or google account
    if not user.email_verified and not user.is_admin and not user.google_id:
        if _wants_json():
            return jsonify({
                "success": False,
                "error": {
                    "code": "EMAIL_NOT_VERIFIED",
                    "message": "Your account has not been activated. Please check your email for the activation link.",
                    "retryable": False
                },
                "needs_activation": True,
                "email": user.email
            }), 403
        flash("Your account has not been activated. Please check your email for the activation link.", "warning")
        return redirect(url_for("auth.login_page"))

    login_user(user, remember=remember)

    if _wants_json():
        return jsonify({"success": True, "user": user.to_dict()})
    return redirect(url_for("views.dashboard"))


@auth_bp.route("/logout", methods=["GET", "POST"])
@auth_bp.route("/api/auth/logout", methods=["POST"])
def logout():
    if current_user.is_authenticated:
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
            user = User(email=email, display_name=userinfo.get("name") or email.split("@")[0], email_verified=True)
            db.session.add(user)
        user.google_id = google_id
        user.avatar_url = userinfo.get("picture")
        user.email_verified = True
        if not user.display_name:
            user.display_name = userinfo.get("name") or email.split("@")[0]
        db.session.commit()
    else:
        # Google sign-in guarantees verified email ownership
        if not user.email_verified:
            user.email_verified = True
            db.session.commit()

    login_user(user)
    return redirect(url_for("views.dashboard"))


@auth_bp.route("/api/auth/me", methods=["GET"])
def me():
    if not current_user.is_authenticated:
        return jsonify({"success": True, "user": None})
    return jsonify({"success": True, "user": current_user.to_dict()})
