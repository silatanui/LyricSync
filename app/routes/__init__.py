from app.routes.views import views_bp
from app.routes.uploads import uploads_bp
from app.routes.projects import projects_bp
from app.routes.lyrics import lyrics_bp
from app.routes.renders import renders_bp
from app.routes.auth import auth_bp
from app.routes.billing import billing_bp
from app.routes.media import media_bp

__all__ = [
    "views_bp",
    "uploads_bp",
    "projects_bp",
    "lyrics_bp",
    "renders_bp",
    "auth_bp",
    "billing_bp",
    "media_bp",
]
