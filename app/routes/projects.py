import shutil
import time
from pathlib import Path
from flask import Blueprint, jsonify, send_file, request, current_app, url_for
from flask_login import current_user
from app.extensions import db
from app.models import Project, MediaAsset, RenderJob
from app.utils.files import get_project_dir, get_project_output_dir, resolve_project_media, resolve_rendered_video
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

    rendered_file = resolve_rendered_video(project)
    has_render = rendered_file is not None
    download_url = url_for("projects.download_project_render", project_id=project.id) if has_render else None

    return jsonify({
        "success": True,
        "project": project.to_dict(),
        "canonical": project.get_canonical_json(),
        "has_render": has_render,
        "download_url": download_url
    })


@projects_bp.route("/<project_id>", methods=["DELETE"])
def delete_project(project_id: str):
    """Delete project and remove associated files. Restricted strictly to administrator."""
    if not (current_user.is_authenticated and current_user.is_admin):
        return jsonify({
            "success": False,
            "error": {
                "code": "FORBIDDEN",
                "message": "Only the administrator can delete projects.",
                "retryable": False
            }
        }), 403

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

    if kind in ("rendered", "output"):
        path = resolve_rendered_video(project)
    else:
        path = resolve_project_media(project, kind)
    if not path or not path.exists():
        return f"Media file not found for kind '{kind}'", 404

    from app.utils.files import detect_mime_type
    response = send_file(str(path), mimetype=detect_mime_type(path), conditional=True)
    response.headers["Cache-Control"] = "public, max-age=86400, stale-while-revalidate=3600"
    response.headers["Accept-Ranges"] = "bytes"
    return response

@projects_bp.route("/<project_id>/download", methods=["GET"])
def download_project_render(project_id: str):
    """Download final rendered video MP4."""
    import re
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({
            "success": False,
            "error": {"code": "PROJECT_NOT_FOUND", "message": "Project not found", "retryable": False}
        }), 404

    job_path = resolve_rendered_video(project)
    if not job_path or not job_path.exists():
        return jsonify({
            "success": False,
            "error": {"code": "OUTPUT_NOT_FOUND", "message": "No completed render available for download. Click Export Video to generate it.", "retryable": False}
        }), 404

    clean_name = re.sub(r'[^\w\s-]', '', project.name).strip()
    clean_name = re.sub(r'[-\s]+', '_', clean_name) or "lyricsync"
    download_name = f"{clean_name}_lyrics.mp4"

    response = send_file(
        str(job_path),
        as_attachment=True,
        download_name=download_name,
        mimetype="video/mp4",
        conditional=True
    )
    response.headers["Accept-Ranges"] = "bytes"
    response.headers["Content-Disposition"] = f'attachment; filename="{download_name}"'
    return response


@projects_bp.route("/templates", methods=["GET"])
def get_background_templates():
    """Returns the list of available studio background templates."""
    mood = (request.args.get("mood") or "").strip().lower()
    q = (request.args.get("q") or "").strip().lower()
    media = (request.args.get("media") or "").strip().lower()  # image|video|all
    templates = BackgroundGenerator.get_templates()
    if mood and mood != "all":
        templates = [t for t in templates if mood in (t.get("moods") or [])]
    if media in ("image", "video"):
        templates = [t for t in templates if (t.get("media_type") or "image") == media]
    if q:
        templates = [
            t for t in templates
            if q in (t.get("name") or "").lower()
            or q in (t.get("tagline") or "").lower()
            or any(q in m for m in (t.get("moods") or []))
        ]
    return jsonify({
        "success": True,
        "templates": templates,
        "moods": BackgroundGenerator.get_moods(),
        "count": len(templates),
    })


@projects_bp.route("/templates/preview/<template_id>", methods=["GET"])
def preview_background_template(template_id: str):
    """On-demand thumbnail for theme cards (cached under static/img/templates/)."""
    from io import BytesIO
    from config import BASE_DIR
    theme_id = (template_id or "").strip().lower()
    cache_dir = Path(BASE_DIR) / "static" / "img" / "templates"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{theme_id}.webp"
    legacy_png = cache_dir / f"{theme_id}.png"
    if cache_path.exists():
        return send_file(cache_path, mimetype="image/webp", max_age=86400)
    if legacy_png.exists():
        return send_file(legacy_png, mimetype="image/png", max_age=86400)
    try:
        BackgroundGenerator.generate_template_asset(
            pattern_type=theme_id,
            output_path=cache_path,
            width=640,
            height=360,
            fmt="WEBP",
        )
        return send_file(cache_path, mimetype="image/webp", max_age=86400)
    except Exception:
        img = BackgroundGenerator.generate_pattern_image(theme_id, 640, 360)
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return send_file(buf, mimetype="image/png", max_age=3600)


def _apply_background_file(project, bg_file: Path, template_id: str, aspect_ratio: str, w: int, h: int, is_image: bool, extra_meta: dict | None = None):
    """Persist a generated/uploaded background onto the project + canonical JSON."""
    project.video_path = str(bg_file.resolve())
    project.video_duration = project.audio_duration
    project.width = w
    project.height = h

    canonical = project.get_canonical_json()
    canonical["media"]["video_path"] = str(bg_file.resolve())
    canonical["media"]["video_duration"] = project.audio_duration
    canonical["media"]["width"] = w
    canonical["media"]["height"] = h
    canonical.setdefault("meta", {})["background_template"] = template_id
    canonical.setdefault("meta", {})["background_media_type"] = "image" if is_image else "video"
    if extra_meta:
        canonical["meta"].update(extra_meta)
    canonical.setdefault("render", {})["aspect_ratio"] = aspect_ratio
    canonical.setdefault("style", {})["aspectRatio"] = aspect_ratio
    project.set_canonical_json(canonical)

    video_asset = db.session.query(MediaAsset).filter_by(project_id=project.id, kind="video").first()
    if video_asset:
        video_asset.file_path = str(bg_file.resolve())
        video_asset.storage_key = bg_file.name
        video_asset.duration = project.audio_duration
        try:
            video_asset.size_bytes = bg_file.stat().st_size
        except Exception:
            pass

    db.session.commit()
    return canonical


@projects_bp.route("/<project_id>/background", methods=["POST"])
def update_project_background(project_id: str):
    """
    Re-generates the background for an existing project using a chosen template.
    Image themes produce WebP stills; video themes produce short looping MP4 beds.
    The special `ai_lyric_scene` theme builds a custom still from the song lyrics via OpenAI.
    """
    from app.services.theme_catalog import get_theme
    from app.services.ai_background import AI_THEME_ID, generate_ai_background

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
    theme = get_theme(template_id) or {}
    is_video_theme = (theme.get("media_type") == "video")

    audio_path = resolve_project_media(project, "audio")
    if not audio_path or not audio_path.exists():
        return jsonify({
            "success": False,
            "error": {"code": "AUDIO_MISSING", "message": "Project audio file not found on disk.", "retryable": False}
        }), 400

    proj_dir = get_project_dir(project_id)
    is_image = True

    # —— AI lyric scene: chat prompt from lyrics + gpt-image still ——
    if template_id == AI_THEME_ID or (theme.get("extras") or {}).get("ai"):
        from app.services.image_credits import (
            consume_image_credit,
            credits_payload,
            ensure_user_can_generate,
        )

        if not current_user.is_authenticated:
            return jsonify({
                "success": False,
                "error": {
                    "code": "AUTH_REQUIRED",
                    "message": "Sign in to generate AI lyric scenes. New accounts get free image credits.",
                    "retryable": False,
                    "credits": credits_payload(None),
                },
            }), 401

        ok, credit_err = ensure_user_can_generate(current_user)
        if not ok:
            return jsonify({"success": False, "error": credit_err}), 402

        try:
            meta = canonical.get("meta") or {}
            credit = project.preview_credit()
            title = credit.get("title") or meta.get("title") or project.name or "Untitled Song"
            artist = credit.get("artist") or meta.get("artist") or ""
            language = (
                (canonical.get("transcription") or {}).get("language")
                or meta.get("preferred_language")
                or ""
            )
            bg_file = proj_dir / f"background_{AI_THEME_ID}.webp"
            ai_meta = generate_ai_background(
                output_path=bg_file,
                title=title,
                artist=artist,
                lyrics=canonical.get("lyrics") or [],
                language=language,
                aspect_ratio=aspect_ratio,
                width=w,
                height=h,
            )
            _apply_background_file(
                project,
                bg_file,
                AI_THEME_ID,
                aspect_ratio,
                w,
                h,
                True,
                extra_meta={
                    "ai_background": {
                        "prompt": ai_meta.get("prompt"),
                        "model": ai_meta.get("model"),
                        "chat_model": ai_meta.get("chat_model"),
                        "api_size": ai_meta.get("api_size"),
                        "generated_at": ai_meta.get("generated_at"),
                    }
                },
            )
            # Charge a credit only after a successful OpenAI image write.
            credits = consume_image_credit(current_user)
            return jsonify({
                "success": True,
                "template": AI_THEME_ID,
                "video_url": url_for(
                    "projects.stream_project_media",
                    project_id=project_id,
                    kind="video",
                    t=int(time.time() * 1000),
                ),
                "is_image": True,
                "media_type": "image",
                "ai": {
                    "prompt": ai_meta.get("prompt"),
                    "model": ai_meta.get("model"),
                    "api_size": ai_meta.get("api_size"),
                },
                "credits": credits,
            })
        except Exception as e:
            current_app.logger.exception("AI lyric background failed: %s", e)
            return jsonify({
                "success": False,
                "error": {
                    "code": "AI_BACKGROUND_FAILED",
                    "message": f"Could not generate AI lyric scene: {e}",
                    "retryable": True,
                    "credits": credits_payload(current_user),
                },
            }), 500

    try:
        if is_video_theme:
            bg_file = proj_dir / f"background_{template_id}.mp4"
            motion = (theme.get("motion") or "visualizer").lower()
            loop_seconds = 5.0 if motion == "visualizer" else 6.0
            BackgroundGenerator.generate_theme_video_loop(
                pattern_type=template_id,
                output_path=bg_file,
                width=w,
                height=h,
                seconds=loop_seconds,
            )
            # Keep a still poster next to the motion bed so reloads always have an image fallback.
            try:
                BackgroundGenerator.generate_template_asset(
                    pattern_type=template_id,
                    output_path=proj_dir / f"background_{template_id}.webp",
                    width=w,
                    height=h,
                    fmt="WEBP",
                )
            except Exception:
                pass
            is_image = False
        else:
            bg_file = proj_dir / f"background_{template_id}.webp"
            try:
                BackgroundGenerator.generate_template_asset(
                    pattern_type=template_id,
                    output_path=bg_file,
                    width=w,
                    height=h,
                    fmt="WEBP",
                )
            except Exception:
                bg_file = proj_dir / f"background_{template_id}.png"
                BackgroundGenerator.generate_template_asset(
                    pattern_type=template_id,
                    output_path=bg_file,
                    width=w,
                    height=h,
                    fmt="PNG",
                )
            is_image = True
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
    canonical.setdefault("meta", {})["background_media_type"] = "video" if not is_image else "image"
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
        "is_image": is_image,
        "media_type": "image" if is_image else "video",
    })


@projects_bp.route("/<project_id>/background/video", methods=["POST"])
def upload_custom_background_video(project_id: str):
    """Upload a custom video background that overrides the aesthetic theme."""
    from app.services.media_probe import MediaProbe
    from app.utils.validation import validate_video_file

    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({
            "success": False,
            "error": {"code": "PROJECT_NOT_FOUND", "message": "Project not found.", "retryable": False}
        }), 404

    video_file = request.files.get("video")
    if not video_file or not video_file.filename:
        return jsonify({
            "success": False,
            "error": {"code": "VIDEO_REQUIRED", "message": "Please choose a video file.", "retryable": False}
        }), 400

    video_bytes = video_file.read()
    video_file.seek(0)
    is_valid_video, err = validate_video_file(video_file.filename, len(video_bytes))
    if not is_valid_video:
        return jsonify({
            "success": False,
            "error": {"code": "VIDEO_INVALID", "message": err, "retryable": False}
        }), 400

    proj_dir = get_project_dir(project_id)
    video_ext = Path(video_file.filename).suffix.lower() or ".mp4"
    bg_file = proj_dir / f"background_custom{video_ext}"
    video_file.save(str(bg_file))

    try:
        v_probe = MediaProbe.probe(bg_file)
    except Exception:
        v_probe = {
            "duration": project.audio_duration or 0,
            "width": project.width or 1920,
            "height": project.height or 1080,
            "fps": project.fps or 30.0,
        }

    project.video_path = str(bg_file.resolve())
    project.video_duration = v_probe.get("duration", project.audio_duration)
    if v_probe.get("width"):
        project.width = v_probe["width"]
    if v_probe.get("height"):
        project.height = v_probe["height"]
    if v_probe.get("fps"):
        project.fps = v_probe["fps"]

    canonical = project.get_canonical_json()
    canonical.setdefault("media", {})
    canonical["media"]["video_path"] = str(bg_file.resolve())
    canonical["media"]["video_duration"] = project.video_duration
    canonical["media"]["width"] = project.width
    canonical["media"]["height"] = project.height
    canonical.setdefault("meta", {})["background_template"] = "custom_video"
    canonical.setdefault("meta", {})["background_media_type"] = "video"
    project.set_canonical_json(canonical)

    video_asset = db.session.query(MediaAsset).filter_by(project_id=project_id, kind="video").first()
    if video_asset:
        video_asset.file_path = str(bg_file.resolve())
        video_asset.storage_key = bg_file.name
        video_asset.duration = project.video_duration
        try:
            video_asset.size_bytes = bg_file.stat().st_size
        except Exception:
            pass

    db.session.commit()

    return jsonify({
        "success": True,
        "template": "custom_video",
        "video_url": url_for("projects.stream_project_media", project_id=project_id, kind="video", t=int(time.time() * 1000)),
        "is_image": False,
        "media_type": "video",
        "filename": video_file.filename,
    })

