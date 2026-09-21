from flask import Flask, jsonify
from config import Config
from app.extensions import db, login_manager, oauth

def _ensure_mysql_database_exists(config_class):
    """Auto-create the MySQL schema (visible in phpMyAdmin) if it doesn't exist yet."""
    uri = getattr(config_class, "SQLALCHEMY_DATABASE_URI", "")
    if not uri.startswith("mysql"):
        return
    try:
        import pymysql
        pymysql.install_as_MySQLdb()
        conn = pymysql.connect(
            host=config_class.MYSQL_HOST,
            port=int(config_class.MYSQL_PORT),
            user=config_class.MYSQL_USER,
            password=config_class.MYSQL_PASSWORD,
        )
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{config_class.MYSQL_DATABASE}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        # If MySQL isn't reachable yet, table creation below will surface the real error.
        pass

def create_app(config_class=Config):
    flask_app = Flask(__name__, template_folder="../templates", static_folder="../static")
    flask_app.config.from_object(config_class)

    # Ensure required runtime storage directories exist
    Config.ensure_directories()
    _ensure_mysql_database_exists(config_class)

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
        db.create_all()

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
        return jsonify({
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected server error occurred.",
                "retryable": True
            }
        }), 500

    return flask_app
