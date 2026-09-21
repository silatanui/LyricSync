from flask import Flask, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix
from config import Config
from app.extensions import db

def create_app(config_class=Config):
    flask_app = Flask(__name__, template_folder="../templates", static_folder="../static")
    # Preserve HTTPS host and URL prefixes supplied by Apache/Nginx/Passenger.
    flask_app.wsgi_app = ProxyFix(flask_app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    flask_app.config.from_object(config_class)

    # Ensure required runtime storage directories exist
    Config.ensure_directories()

    # Initialize extensions
    db.init_app(flask_app)

    # Register blueprints
    from app.routes import views_bp, uploads_bp, projects_bp, lyrics_bp, renders_bp
    flask_app.register_blueprint(views_bp)
    flask_app.register_blueprint(uploads_bp)
    flask_app.register_blueprint(projects_bp)
    flask_app.register_blueprint(lyrics_bp)
    flask_app.register_blueprint(renders_bp)

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
