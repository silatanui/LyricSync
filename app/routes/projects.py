import shutil
import time
from pathlib import Path
from flask import Blueprint, jsonify, send_file, request, current_app, url_for
from app.extensions import db
from app.models import Project, MediaAsset, RenderJob
from app.utils.files import get_project_dir, get_project_output_dir
from app.services.background_generator import BackgroundGenerator

projects_bp = Blueprint("projects", __name__, url_prefix="/api/projects")

@projects_bp.route("", methods=["GET"])
def list_projects():
    """List all projects."""
    projects = db.session.query(Project).order_by(Project.created_at.desc()).all()
    return jsonify({
        "success": True,
        "projects": [p.to_dict() for p in projects]
    })

@projects_bp.route("/<project_id>", methods=["GET"])
def get_project(project_id: str):
    """Get project details."""
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({
            "success": False,
            "error": {"code": "PROJECT_NOT_FOUND", "message": "Project not found.", "retryable": False}
        }), 404

    return jsonify({
        "success": True,
        "project": project.to_dict(),
        "canonical": project.get_canonical_json()
    })

@projects_bp.route("/<project_id>", methods=["DELETE"])
def delete_project(project_id: str):
    """Delete project and remove associated files."""
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({
            "success": False,
            "error": {"code": "PROJECT_NOT_FOUND", "message": "Project not found.", "retryable": False}
        }), 404

    # Cleanup disk directories
    try:
        p_dir = get_project_dir(project_id)
        if p_dir.exists():
            shutil.rmtree(p_dir, ignore_errors=True)
        out_dir = get_project_output_dir(project_id)
        if out_dir.exists():
            shutil.rmtree(out_dir, ignore_errors=True)
    except Exception:
        pass

    db.session.delete(project)
    db.session.commit()

    return jsonify({"success": True, "message": "Project deleted successfully."})

@projects_bp.route("/<project_id>", methods=["PUT"])
def update_project(project_id: str):
    """Update editable project metadata."""
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({
            "success": False,
            "error": {"code": "PROJECT_NOT_FOUND", "message": "Project not found.", "retryable": False}
        }), 404

    data = request.get_json() or {}
    name = data.get("name", project.name)
    if not isinstance(name, str) or not name.strip():
        return jsonify({
            "success": False,
            "error": {"code": "INVALID_NAME", "message": "Project name cannot be empty.", "retryable": False}
        }), 400

    project.name = name.strip()[:255]
    canonical = project.get_canonical_json()
    if "is_public" in data:
        canonical.setdefault("meta", {})["is_public"] = bool(data["is_public"])
    project.set_canonical_json(canonical)
    db.session.commit()
    return jsonify({"success": True, "project": project.to_dict(), "is_public": canonical.get("meta", {}).get("is_public", False)})

@projects_bp.route("/<project_id>/media/<kind>", methods=["GET"])
def stream_project_media(project_id: str, kind: str):
    """Stream media (audio/video) for preview in browser player."""
    project = db.session.get(Project, project_id)
    if not project:
        return "Project not found", 404

    file_path_str = project.audio_path if kind == "audio" else project.video_path
    if not file_path_str:
        return "Media file not configured", 404

    path = Path(file_path_str)
    if not path.is_absolute():
        path = (Path(current_app.root_path).parent / path).resolve()

    if not path.exists():
        return f"Media file not found at {path}", 404

    from app.utils.files import detect_mime_type
    response = send_file(str(path), mimetype=detect_mime_type(path), conditional=True)
    response.headers["Cache-Control"] = "public, max-age=86400, stale-while-revalidate=3600"
    response.headers["Accept-Ranges"] = "bytes"
    return response

@projects_bp.route("/<project_id>/download", methods=["GET"])
def download_project_render(project_id: str):
    """Download final rendered video MP4."""
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({
            "success": False,
            "error": {"code": "PROJECT_NOT_FOUND", "message": "Project not found", "retryable": False}
        }), 404

    # Find the latest completed render job or output media asset
    completed_job = db.session.query(RenderJob).filter_by(
        project_id=project_id,
        status="completed"
    ).order_by(RenderJob.created_at.desc()).first()

    if not completed_job or not completed_job.output_file_path:
        return jsonify({
            "success": False,
            "error": {"code": "OUTPUT_NOT_FOUND", "message": "No completed render available for download", "retryable": False}
        }), 404

    job_path = Path(completed_job.output_file_path)
    if not job_path.is_absolute():
        job_path = (Path(current_app.root_path).parent / job_path).resolve()

    if not job_path.exists():
        return jsonify({
            "success": False,
            "error": {"code": "OUTPUT_NOT_FOUND", "message": "Rendered file missing from disk", "retryable": False}
        }), 404

    download_name = f"{project.name.replace(' ', '_')}_lyrics.mp4"
    return send_file(
        str(job_path),
        as_attachment=True,
        download_name=download_name,
        mimetype="video/mp4"
    )

@projects_bp.route("/templates", methods=["GET"])
def get_background_templates():
    """Returns the list of available studio background templates."""
    return jsonify({
        "success": True,
        "templates": BackgroundGenerator.get_templates()
    })

@projects_bp.route("/<project_id>/background", methods=["POST"])
def update_project_background(project_id: str):
    """
    Re-generates the background video for an existing project using a chosen template.
    Fast execution (~1-2s) with ultrafast 1fps x264 muxing.
    """
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({
            "success": False,
            "error": {"code": "PROJECT_NOT_FOUND", "message": "Project not found.", "retryable": False}
        }), 404

    data = request.get_json() or {}
    template_id = data.get("template", "burgundy_studio").strip() or "burgundy_studio"
    canonical = project.get_canonical_json()
    aspect_ratio = data.get("aspect_ratio") or canonical.get("render", {}).get("aspect_ratio", "16:9")
    w, h = BackgroundGenerator.get_dimensions(aspect_ratio)

    audio_path = Path(project.audio_path)
    if not audio_path.is_absolute():
        audio_path = (Path(current_app.root_path).parent / audio_path).resolve()

    if not audio_path.exists():
        return jsonify({
            "success": False,
            "error": {"code": "AUDIO_MISSING", "message": "Project audio file not found on disk.", "retryable": False}
        }), 400

    proj_dir = get_project_dir(project_id)
    bg_file = proj_dir / f"background_{template_id}.webp"

    try:
        BackgroundGenerator.generate_template_asset(
            pattern_type=template_id,
            output_path=bg_file,
            width=w,
            height=h,
            fmt="WEBP"
        )
    except Exception as e:
        bg_file = proj_dir / f"background_{template_id}.png"
        try:
            BackgroundGenerator.generate_template_asset(
                pattern_type=template_id,
                output_path=bg_file,
                width=w,
                height=h,
                fmt="PNG"
            )
        except Exception as e2:
            return jsonify({
                "success": False,
                "error": {"code": "BACKGROUND_GENERATION_FAILED", "message": f"Failed to generate background: {e2}", "retryable": True}
            }), 500

    # Update Project record
    project.video_path = str(bg_file.resolve())
    project.video_duration = project.audio_duration
    project.width = w
    project.height = h

    # Update Canonical JSON
    canonical["media"]["video_path"] = str(bg_file.resolve())
    canonical["media"]["video_duration"] = project.audio_duration
    canonical["media"]["width"] = w
    canonical["media"]["height"] = h
    canonical.setdefault("meta", {})["background_template"] = template_id
    canonical.setdefault("render", {})["aspect_ratio"] = aspect_ratio
    canonical.setdefault("style", {})["aspectRatio"] = aspect_ratio
    project.set_canonical_json(canonical)

    # Update MediaAsset if present
    video_asset = db.session.query(MediaAsset).filter_by(project_id=project_id, kind="video").first()
    if video_asset:
        video_asset.file_path = str(bg_file.resolve())
        video_asset.storage_key = bg_file.name
        video_asset.duration = project.audio_duration
        try:
            video_asset.size_bytes = bg_file.stat().st_size
        except Exception:
            pass

    db.session.commit()

    return jsonify({
        "success": True,
        "template": template_id,
        "video_url": url_for("projects.stream_project_media", project_id=project_id, kind="video", t=int(time.time() * 1000)),
        "is_image": True
    })

