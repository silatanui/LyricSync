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

    # Register blueprints
    from app.routes import views_bp, uploads_bp, projects_bp, lyrics_bp, renders_bp, auth_bp
    flask_app.register_blueprint(views_bp)
    flask_app.register_blueprint(uploads_bp)
    flask_app.register_blueprint(projects_bp)
    flask_app.register_blueprint(lyrics_bp)
    flask_app.register_blueprint(renders_bp)
    flask_app.register_blueprint(auth_bp)

    # Create tables automatically for development
    with flask_app.app_context():
        import app.models  # load models
        try:
            db.create_all()
        except Exception as db_err:
            flask_app.logger.warning(f"db.create_all() warning on startup: {db_err}")

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
