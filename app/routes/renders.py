from flask import Blueprint, request, jsonify, current_app
from app.extensions import db
from app.models import Project, RenderJob
from app.tasks.job_queue import submit_task
from app.tasks.render_tasks import run_render_pipeline

renders_bp = Blueprint("renders", __name__, url_prefix="/api")

@renders_bp.route("/projects/<project_id>/render", methods=["POST"])
def queue_render(project_id: str):
    """Queue background video render for a project."""
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({
            "success": False,
            "error": {"code": "PROJECT_NOT_FOUND", "message": "Project not found.", "retryable": False}
        }), 404

    if not project.audio_path or not project.video_path:
        return jsonify({
            "success": False,
            "error": {"code": "INCOMPLETE_MEDIA", "message": "Both audio and video tracks must be uploaded.", "retryable": False}
        }), 400

    # Optional render overrides from request body (aspect ratio, audio policy, video policy)
    req_body = request.get_json() or {}
    aspect_ratio = req_body.get("aspect_ratio")
    resolution = req_body.get("resolution")
    mode = req_body.get("mode")

    canonical = project.get_canonical_json()
    if aspect_ratio:
        canonical.setdefault("render", {})["aspect_ratio"] = aspect_ratio
    if resolution in {"720", "1080", "2160"}:
        canonical.setdefault("render", {})["resolution"] = resolution
    if mode:
        canonical.setdefault("style", {})["mode"] = mode
    project.set_canonical_json(canonical)

    job = RenderJob(
        project_id=project.id,
        status="queued",
        stage="Queued for rendering",
        progress=50,
    )
    db.session.add(job)
    db.session.commit()

    app = current_app._get_current_object()
    submit_task(run_render_pipeline, app, project.id, job.id)

    return jsonify({
        "success": True,
        "job_id": job.id,
        "status": job.status,
        "message": "Render job dispatched."
    }), 202

@renders_bp.route("/jobs/<job_id>", methods=["GET"])
def get_job_status(job_id: str):
    """Return status, stage, and progress percentage for a background job."""
    try:
        job = db.session.get(RenderJob, job_id)
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Database error while polling job status")
        return jsonify({
            "success": False,
            "error": {"code": "DATABASE temporarily unavailable", "message": "The job database connection is refreshing. Please retry.", "retryable": True}
        }), 503
    if not job:
        return jsonify({
            "success": False,
            "error": {"code": "JOB_NOT_FOUND", "message": "Job not found.", "retryable": False}
        }), 404

    return jsonify({
        "success": True,
        "job": job.to_dict()
    })
