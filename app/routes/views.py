from flask import Blueprint, render_template, abort
from app.extensions import db
from app.models import Project
from app.services.media_probe import get_ffmpeg_binary, get_ffprobe_binary
import shutil

views_bp = Blueprint("views", __name__)

@views_bp.route("/")
def home():
    """Public portfolio and product homepage."""
    projects = []
    for project in db.session.query(Project).order_by(Project.created_at.desc()).all():
        canonical = project.get_canonical_json()
        if canonical.get("meta", {}).get("is_public") is True:
            projects.append(project)
    return render_template("home.html", project_count=len(projects), public_projects=projects)

@views_bp.route("/terms")
def terms_page():
    return render_template("terms.html")

@views_bp.route("/privacy")
def privacy_page():
    return render_template("privacy.html")

@views_bp.route("/projects")
def dashboard():
    """Projects dashboard page."""
    projects = db.session.query(Project).order_by(Project.created_at.desc()).all()
    return render_template("dashboard.html", projects=projects)

@views_bp.route("/upload")
def upload_page():
    """Media upload interface."""
    return render_template("upload.html")

@views_bp.route("/editor/<project_id>")
def editor_page(project_id: str):
    """Studio synchronized editor page."""
    project = db.session.get(Project, project_id)
    if not project:
        abort(404)
    return render_template("editor.html", project=project, canonical=project.get_canonical_json())

@views_bp.route("/public/project/<project_id>")
def public_project_page(project_id: str):
    """Read-only view for projects explicitly published by their owner."""
    project = db.session.get(Project, project_id)
    if not project or project.get_canonical_json().get("meta", {}).get("is_public") is not True:
        abort(404)
    return render_template("public_project.html", project=project, canonical=project.get_canonical_json())

@views_bp.route("/health")
def health_check():
    """Health check endpoint (Section 20.3 of specification)."""
    # Check DB
    db_ok = True
    try:
        db.session.execute(db.text("SELECT 1"))
    except Exception:
        db_ok = False

    ffmpeg_path = get_ffmpeg_binary()
    ffmpeg_ok = bool(ffmpeg_path and shutil.which(ffmpeg_path))

    return {
        "status": "healthy" if db_ok else "unhealthy",
        "database": "connected" if db_ok else "disconnected",
        "ffmpeg": "available" if ffmpeg_ok else "not_found",
        "ffmpeg_binary": ffmpeg_path
    }
