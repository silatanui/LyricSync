from flask import Blueprint, render_template, abort, current_app
from flask_login import current_user
from pathlib import Path
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
    """Health check endpoint.
    Deep technical diagnostic details (database tables, ffmpeg binary paths,
    storage paths, AI model, rendering engine) are restricted to admin silatanuikipngetich@gmail.com.
    Normal users receive a clean operational status without server internals.
    """
    # Check DB
    db_ok = True
    db_error = None
    try:
        db.session.execute(db.text("SELECT 1"))
    except Exception as error:
        db_ok = False
        db_error = str(error).splitlines()[0][:200]
        db.session.rollback()

    ffmpeg_path = get_ffmpeg_binary()
    ffmpeg_ok = bool(ffmpeg_path and (shutil.which(ffmpeg_path) or Path(ffmpeg_path).is_file()))

    # Check storage directory writability
    storage_ok = True
    storage_error = None
    try:
        media_root = Path(current_app.config.get("MEDIA_ROOT", "data/media"))
        media_root.mkdir(parents=True, exist_ok=True)
        test_file = media_root / ".health_check"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink(missing_ok=True)
    except Exception as se:
        storage_ok = False
        storage_error = str(se)

    all_ok = db_ok and storage_ok

    is_admin = bool(
        current_user.is_authenticated and
        current_user.email and
        current_user.email.strip().lower() == "silatanuikipngetich@gmail.com"
    )

    if not is_admin:
        # Clean, human-friendly status for normal users without internal details
        return {
            "status": "healthy" if all_ok else "unhealthy",
            "database": "connected" if db_ok else "disconnected",
            "service": "LyricSync Studio",
            "message": "LyricSync Studio is operational." if all_ok else "Service temporarily degraded."
        }, (200 if all_ok else 503)

    # Check database tables only for admin
    tables = []
    try:
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
    except Exception:
        pass

    # Full technical diagnostics for admin silatanuikipngetich@gmail.com
    return {
        "status": "healthy" if all_ok else "unhealthy",
        "database": "connected" if db_ok else "disconnected",
        "database_error": db_error,
        "database_tables": tables,
        "storage": "writable" if storage_ok else "error",
        "storage_error": storage_error,
        "storage_path": str(current_app.config.get("MEDIA_ROOT")),
        "ffmpeg": "available" if ffmpeg_ok else "not_found",
        "ffmpeg_binary": ffmpeg_path,
        "ai_model": current_app.config.get("OPENAI_TRANSCRIPTION_MODEL", "whisper-1"),
        "rendering_engine": "FFmpeg (libass + h264 + aac)",
        "admin_access": True
    }, (200 if all_ok else 503)

