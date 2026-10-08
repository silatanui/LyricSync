from flask import Flask, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix
from config import Config
from app.extensions import db, login_manager, oauth

def create_app(config_class=Config):
    flask_app = Flask(__name__, template_folder="../templates", static_folder="../static")
    # Preserve HTTPS host and URL prefixes supplied by Apache/Nginx/Passenger.
    flask_app.wsgi_app = ProxyFix(flask_app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    flask_app.config.from_object(config_class)

    # Ensure required runtime storage directories exist
    Config.ensure_directories()

    # Initialize extensions
    db.init_app(flask_app)
    login_manager.init_app(flask_app)
    oauth.init_app(flask_app)
    if config_class.GOOGLE_CLIENT_ID and config_class.GOOGLE_CLIENT_SECRET:
        oauth.register(
            name="google",
            client_id=config_class.GOOGLE_CLIENT_ID,
            client_secret=config_class.GOOGLE_CLIENT_SECRET,
            server_metadata_url=config_class.GOOGLE_DISCOVERY_URL,
            client_kwargs={"scope": "openid email profile"},
        )

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return db.session.get(User, user_id)

    @flask_app.context_processor
    def inject_admin_context():
        from flask_login import current_user
        from app.services.image_credits import credits_payload
        is_admin = bool(current_user.is_authenticated and getattr(current_user, "is_admin", False))
        return {
            "is_admin": is_admin,
            "image_credits_status": credits_payload(),
        }

    # Register blueprints
    from app.routes import views_bp, uploads_bp, projects_bp, lyrics_bp, renders_bp, auth_bp, billing_bp, media_bp
    flask_app.register_blueprint(views_bp)
    flask_app.register_blueprint(uploads_bp)
    flask_app.register_blueprint(projects_bp)
    flask_app.register_blueprint(lyrics_bp)
    flask_app.register_blueprint(renders_bp)
    flask_app.register_blueprint(auth_bp)
    flask_app.register_blueprint(billing_bp)
    flask_app.register_blueprint(media_bp)

    # Create tables automatically for development
    with flask_app.app_context():
        import app.models  # load models
        try:
            db.create_all()
            inspector = db.inspect(db.engine)
            if "users" in inspector.get_table_names():
                user_cols = [c["name"] for c in inspector.get_columns("users")]
                if "email_verified" not in user_cols:
                    db.session.execute(db.text("ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT 0"))
                    db.session.commit()
                daily_credits = int(
                    flask_app.config.get("IMAGE_DAILY_CREDITS")
                    or flask_app.config.get("IMAGE_FREE_CREDITS")
                    or 2
                )
                if "image_credits" not in user_cols:
                    db.session.execute(db.text(
                        f"ALTER TABLE users ADD COLUMN image_credits INTEGER NOT NULL DEFAULT {daily_credits}"
                    ))
                    db.session.commit()
                    user_cols.append("image_credits")
                if "image_credits_reset_on" not in user_cols:
                    db.session.execute(db.text(
                        "ALTER TABLE users ADD COLUMN image_credits_reset_on DATE NULL"
                    ))
                    db.session.commit()
                    user_cols.append("image_credits_reset_on")
                if "bonus_image_credits" not in user_cols:
                    db.session.execute(db.text(
                        "ALTER TABLE users ADD COLUMN bonus_image_credits INTEGER NOT NULL DEFAULT 0"
                    ))
                    db.session.commit()
                    user_cols.append("bonus_image_credits")
                if "is_premium" not in user_cols:
                    db.session.execute(db.text(
                        "ALTER TABLE users ADD COLUMN is_premium BOOLEAN NOT NULL DEFAULT 0"
                    ))
                    db.session.commit()
                if "stripe_customer_id" not in user_cols:
                    db.session.execute(db.text(
                        "ALTER TABLE users ADD COLUMN stripe_customer_id VARCHAR(128) NULL"
                    ))
                    db.session.commit()
                from app.models.user import ADMIN_EMAIL as _ADMIN_EMAIL
                # Google-linked accounts are verified by Google; do not auto-verify by email alone.
                db.session.execute(db.text("UPDATE users SET email_verified = 1 WHERE google_id IS NOT NULL"))
                db.session.commit()
                # Keep the existing admin mailbox verified once linked (does not grant access without login).
                db.session.execute(
                    db.text("UPDATE users SET email_verified = 1 WHERE lower(email) = :admin AND google_id IS NOT NULL"),
                    {"admin": _ADMIN_EMAIL.lower()},
                )
                db.session.commit()
                # One-shot: clear Premium for the KYU student test account (once per host).
                try:
                    from pathlib import Path as _Path
                    from app.models import User as _User
                    from app.services.image_credits import revoke_premium_credits
                    _clear_email = "tanui.kipngetichsila@students.kyu.ac.ke"
                    _data_root = flask_app.config.get("DATA_ROOT") or flask_app.instance_path
                    _marker = _Path(_data_root) / ".cleared_premium_kyu_2026_04"
                    if not _marker.exists():
                        _target = db.session.query(_User).filter(
                            db.func.lower(_User.email) == _clear_email
                        ).first()
                        if _target:
                            revoke_premium_credits(_target, clear_customer=True)
                            flask_app.logger.info("Cleared Premium for %s", _clear_email)
                        _marker.parent.mkdir(parents=True, exist_ok=True)
                        _marker.write_text(_clear_email + "\n", encoding="utf-8")
                except Exception as clear_err:
                    db.session.rollback()
                    flask_app.logger.warning("Premium clear warning: %s", clear_err)
                # Legacy projects were created without an owner and appeared in every
                # dashboard. Assign orphans to the admin account and keep them private
                # unless meta.is_public was explicitly set to true.
                try:
                    from app.models import User, Project
                    from app.models.user import ADMIN_EMAIL
                    from app.services.project_privacy import ensure_private_meta, normalize_is_public
                    admin = db.session.query(User).filter(
                        db.func.lower(User.email) == ADMIN_EMAIL.lower()
                    ).first()
                    if admin:
                        orphans = db.session.query(Project).filter(Project.user_id.is_(None)).all()
                        for orphan in orphans:
                            orphan.user_id = admin.id
                    for project in db.session.query(Project).all():
                        canonical = project.get_canonical_json()
                        ensure_private_meta(canonical)
                        # Never treat missing/ambiguous values as public.
                        canonical["meta"]["is_public"] = normalize_is_public(
                            canonical.get("meta", {}).get("is_public")
                        )
                        project.set_canonical_json(canonical)
                    db.session.commit()
                except Exception as privacy_err:
                    db.session.rollback()
                    flask_app.logger.warning(f"Project privacy migration warning: {privacy_err}")
            if "render_jobs" in inspector.get_table_names():
                job_cols = [c["name"] for c in inspector.get_columns("render_jobs")]
                if "detail_json" not in job_cols:
                    db.session.execute(db.text("ALTER TABLE render_jobs ADD COLUMN detail_json TEXT"))
                    db.session.commit()
            # MySQL TEXT (~64KB) truncates full word-timed lyric JSON — widen to MEDIUMTEXT.
            if db.engine.dialect.name == "mysql":
                large_text_columns = (
                    ("projects", "canonical_data"),
                    ("transcriptions", "raw_text"),
                    ("transcriptions", "json_payload"),
                )
                for table_name, column_name in large_text_columns:
                    if table_name not in inspector.get_table_names():
                        continue
                    col_meta = next(
                        (c for c in inspector.get_columns(table_name) if c["name"] == column_name),
                        None,
                    )
                    if not col_meta:
                        continue
                    col_type = str(col_meta.get("type") or "").upper()
                    if "MEDIUMTEXT" in col_type or "LONGTEXT" in col_type:
                        continue
                    db.session.execute(db.text(
                        f"ALTER TABLE {table_name} MODIFY COLUMN {column_name} MEDIUMTEXT"
                    ))
                    db.session.commit()
                    flask_app.logger.info(
                        "Widened %s.%s to MEDIUMTEXT for full lyric storage",
                        table_name,
                        column_name,
                    )
        except Exception as db_err:
            db.session.rollback()
            flask_app.logger.warning(f"Database schema migration warning on startup: {db_err}")


    # Global JSON error handling according to Section 12.3 specification
    @flask_app.errorhandler(404)
    def not_found(e):
        return jsonify({
            "success": False,
            "error": {
                "code": "RESOURCE_NOT_FOUND",
                "message": "The requested resource was not found.",
                "retryable": False
            }
        }), 404

    @flask_app.errorhandler(413)
    def request_entity_too_large(e):
        return jsonify({
            "success": False,
            "error": {
                "code": "PAYLOAD_TOO_LARGE",
                "message": "File exceeds maximum upload size limits.",
                "retryable": False
            }
        }), 413

    @flask_app.errorhandler(500)
    def internal_server_error(e):
        import traceback
        import logging
        logger = logging.getLogger("lyric_sync")
        tb = traceback.format_exc()
        logger.error(f"Internal server error: {e}\n{tb}")

        orig_err = getattr(e, "original_exception", e)
        # In debug mode or if message is available, provide more specific error detail
        message = str(orig_err) if (flask_app.debug or getattr(flask_app.config, "ENV", "") == "development") else "An unexpected server error occurred."
        return jsonify({
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": message,
                "retryable": True
            }
        }), 500

    return flask_app
