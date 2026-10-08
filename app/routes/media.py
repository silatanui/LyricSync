"""User media library API — uploads persist across projects."""
from pathlib import Path
import shutil
import time

from flask import Blueprint, jsonify, send_file, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Project, MediaAsset
from app.routes.projects import _apply_background_file, _file_entry_from_asset
from app.services.project_privacy import user_can_edit_project
from app.services.user_media_library import (
    copy_library_into_project,
    list_user_library,
    resolve_library_asset,
)
from app.utils.files import detect_mime_type, get_project_dir

media_bp = Blueprint("media", __name__, url_prefix="/api/media")


@media_bp.route("/library", methods=["GET"])
@login_required
def get_media_library():
    files = list_user_library(current_user.id, backfill=True)
    return jsonify({
        "success": True,
        "files": files,
        "counts": {
            "audio": len(files["audio"]),
            "images": len(files["images"]),
            "videos": len(files["videos"]),
        },
    })


@media_bp.route("/library/<asset_id>/stream", methods=["GET"])
@login_required
def stream_library_file(asset_id: str):
    asset = resolve_library_asset(current_user.id, asset_id)
    if not asset:
        return "File not found", 404
    path = Path(asset.file_path)
    response = send_file(str(path), mimetype=asset.mime_type or detect_mime_type(path), conditional=True)
    response.headers["Cache-Control"] = "private, max-age=3600"
    response.headers["Accept-Ranges"] = "bytes"
    return response


@media_bp.route("/library/<asset_id>/use", methods=["POST"])
@login_required
def use_library_file_on_project(asset_id: str):
    """Copy a library file into a project; optionally apply as background or master audio."""
    payload = request.get_json(silent=True) or {}
    project_id = (payload.get("project_id") or request.args.get("project_id") or "").strip()
    apply_as = str(payload.get("apply_as") or payload.get("apply") or "background").strip().lower()
    if not project_id:
        return jsonify({
            "success": False,
            "error": {"code": "PROJECT_REQUIRED", "message": "project_id is required.", "retryable": False},
        }), 400

    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({
            "success": False,
            "error": {"code": "PROJECT_NOT_FOUND", "message": "Project not found.", "retryable": False},
        }), 404
    if not user_can_edit_project(current_user, project):
        return jsonify({
            "success": False,
            "error": {"code": "FORBIDDEN", "message": "Only the project owner can use library files.", "retryable": False},
        }), 403

    library_asset = resolve_library_asset(current_user.id, asset_id)
    if not library_asset:
        return jsonify({
            "success": False,
            "error": {"code": "FILE_NOT_FOUND", "message": "Library file not found.", "retryable": False},
        }), 404

    project_asset = copy_library_into_project(project, library_asset)
    src = Path(project_asset.file_path)
    kind = (library_asset.kind or "").lower()

    if apply_as in ("audio", "master_audio") and kind == "audio":
        proj_dir = get_project_dir(project_id)
        dest = proj_dir / f"master_audio{src.suffix.lower() or '.mp3'}"
        shutil.copy2(src, dest)
        project.audio_path = str(dest.resolve())
        if library_asset.duration:
            project.audio_duration = library_asset.duration
        canonical = project.get_canonical_json()
        canonical.setdefault("media", {})["audio_path"] = str(dest.resolve())
        if library_asset.duration:
            canonical["media"]["audio_duration"] = library_asset.duration
        project.set_canonical_json(canonical)
        audio_row = db.session.query(MediaAsset).filter_by(project_id=project.id, kind="audio").first()
        if audio_row:
            audio_row.file_path = str(dest.resolve())
            audio_row.storage_key = dest.name
            audio_row.size_bytes = dest.stat().st_size
            audio_row.checksum = library_asset.checksum
            audio_row.duration = library_asset.duration
        db.session.commit()
        return jsonify({
            "success": True,
            "applied_as": "audio",
            "file": _file_entry_from_asset(project_asset, project_id),
            "audio_url": url_for(
                "projects.stream_project_media",
                project_id=project_id,
                kind="audio",
                t=int(time.time() * 1000),
            ),
        })

    if kind == "audio":
        return jsonify({
            "success": True,
            "applied_as": "file",
            "file": _file_entry_from_asset(project_asset, project_id),
        })

    if kind not in ("image", "video"):
        return jsonify({
            "success": True,
            "applied_as": "file",
            "file": _file_entry_from_asset(project_asset, project_id),
        })

    canonical = project.get_canonical_json()
    aspect_ratio = canonical.get("render", {}).get("aspect_ratio", "16:9")
    from app.services.background_generator import BackgroundGenerator
    w, h = BackgroundGenerator.get_dimensions(aspect_ratio)
    proj_dir = get_project_dir(project_id)
    is_image = kind == "image"
    if is_image:
        dest = proj_dir / f"background_library{src.suffix or '.webp'}"
        shutil.copy2(src, dest)
        _apply_background_file(project, dest, "library_image", aspect_ratio, w, h, True)
        media_type = "image"
        template = "library_image"
    else:
        dest = proj_dir / f"background_custom{src.suffix or '.mp4'}"
        shutil.copy2(src, dest)
        _apply_background_file(project, dest, "library_video", aspect_ratio, w, h, False)
        media_type = "video"
        template = "library_video"

    return jsonify({
        "success": True,
        "applied_as": "background",
        "template": template,
        "video_url": url_for(
            "projects.stream_project_media",
            project_id=project_id,
            kind="video",
            t=int(time.time() * 1000),
        ),
        "is_image": is_image,
        "media_type": media_type,
        "file": _file_entry_from_asset(project_asset, project_id),
    })
