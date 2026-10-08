import shutil
import time
from pathlib import Path
from flask import Blueprint, jsonify, send_file, request, current_app, url_for
from flask_login import current_user
from app.extensions import db
from app.models import Project, MediaAsset, RenderJob
from app.utils.files import get_project_dir, get_project_output_dir, resolve_project_media, resolve_rendered_video
from app.services.background_generator import BackgroundGenerator
from app.services.project_privacy import (
    normalize_is_public,
    project_is_public,
    user_can_access_project,
    user_can_edit_project,
    visible_projects_query,
)

projects_bp = Blueprint("projects", __name__, url_prefix="/api/projects")


def _forbidden(message: str = "You do not have access to this project."):
    return jsonify({
        "success": False,
        "error": {"code": "FORBIDDEN", "message": message, "retryable": False},
    }), 403


@projects_bp.route("", methods=["GET"])
def list_projects():
    """List projects visible to the current user (admin sees all)."""
    if not current_user.is_authenticated:
        return jsonify({"success": True, "projects": []})
    projects = (
        visible_projects_query(db.session.query(Project))
        .order_by(Project.created_at.desc())
        .all()
    )
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
    if not user_can_access_project(current_user, project):
        return _forbidden()

    rendered_file = resolve_rendered_video(project)
    has_render = rendered_file is not None
    download_url = url_for("projects.download_project_render", project_id=project.id) if has_render else None
    canonical = project.get_canonical_json()

    return jsonify({
        "success": True,
        "project": project.to_dict(),
        "canonical": canonical,
        "is_public": project_is_public(canonical),
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
    if not user_can_edit_project(current_user, project):
        return _forbidden("Sign in as the project owner to change visibility or details.")

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
        # Strict parse so accidental truthy strings never publish a project.
        canonical.setdefault("meta", {})["is_public"] = normalize_is_public(data.get("is_public"))
    project.set_canonical_json(canonical)
    db.session.commit()
    return jsonify({
        "success": True,
        "project": project.to_dict(),
        "is_public": project_is_public(canonical),
    })

@projects_bp.route("/<project_id>/media/<kind>", methods=["GET"])
def stream_project_media(project_id: str, kind: str):
    """Stream media (audio/video) for preview in browser player."""
    project = db.session.get(Project, project_id)
    if not project:
        return "Project not found", 404
    if not user_can_access_project(current_user, project):
        return "Forbidden", 403

    if kind in ("rendered", "output"):
        path = resolve_rendered_video(project)
    else:
        path = resolve_project_media(project, kind)
    if not path or not path.exists():
        return f"Media file not found for kind '{kind}'", 404

    from app.utils.files import detect_mime_type
    response = send_file(str(path), mimetype=detect_mime_type(path), conditional=True)
    # Avoid sticky browser caches showing a previous theme after AI/custom swaps.
    response.headers["Cache-Control"] = "private, max-age=60, must-revalidate"
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
    if not user_can_access_project(current_user, project):
        return _forbidden()

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


def _file_entry_from_asset(asset: MediaAsset, project_id: str) -> dict:
    """Serialize a media asset for the Files drawer."""
    from app.utils.files import detect_mime_type

    path = Path(asset.file_path) if asset.file_path else None
    exists = bool(path and path.exists())
    size = int(asset.size_bytes or 0)
    if exists and not size:
        try:
            size = path.stat().st_size
        except Exception:
            size = 0
    kind = (asset.kind or "").lower()
    section = "audio" if kind == "audio" else ("images" if kind == "image" else "videos")
    if kind not in ("audio", "image") and path:
        suffix = path.suffix.lower()
        if suffix in {".webp", ".png", ".jpg", ".jpeg", ".gif"}:
            section = "images"
            kind = "image"
        elif suffix in {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac"}:
            section = "audio"
            kind = "audio"
        else:
            section = "videos"
            kind = "video"
    label = asset.storage_key or (path.name if path else asset.id)
    if label.startswith("files/"):
        label = label.split("/", 1)[-1]
    return {
        "id": asset.id,
        "kind": kind,
        "section": section,
        "name": label,
        "mime_type": asset.mime_type or (detect_mime_type(path) if path else "application/octet-stream"),
        "size_bytes": size,
        "duration": asset.duration,
        "created_at": asset.created_at.isoformat() if asset.created_at else None,
        "url": url_for(
            "projects.stream_project_file",
            project_id=project_id,
            asset_id=asset.id,
            t=int(time.time() * 1000),
        ),
        "source": "generated" if "ai_lyric_scene_" in label else ("upload" if kind in ("audio", "image", "video") else "project"),
        "scope": "project",
    }


def _ensure_asset_for_path(project: Project, path: Path, kind: str, storage_key: str | None = None) -> MediaAsset | None:
    """Create or refresh a MediaAsset row for an on-disk project file."""
    if not path or not path.exists() or not path.is_file():
        return None
    key = storage_key or path.name
    existing = (
        db.session.query(MediaAsset)
        .filter_by(project_id=project.id, storage_key=key)
        .first()
    )
    from app.utils.files import detect_mime_type
    mime = detect_mime_type(path)
    size = path.stat().st_size
    if existing:
        existing.kind = kind
        existing.file_path = str(path.resolve())
        existing.mime_type = mime
        existing.size_bytes = size
        return existing
    asset = MediaAsset(
        project_id=project.id,
        kind=kind,
        storage_key=key,
        file_path=str(path.resolve()),
        mime_type=mime,
        size_bytes=size,
        duration=project.audio_duration if kind == "audio" else None,
    )
    db.session.add(asset)
    return asset


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
    # Touch updated_at so editor reload cache-busts the media stream URL.
    from datetime import datetime, timezone
    project.updated_at = datetime.now(timezone.utc)
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
    The special `ai_lyric_scene` theme builds a custom still from lyrics or a user draft via OpenAI.
    """
    from app.services.theme_catalog import get_theme
    from app.services.ai_background import (
        AI_THEME_ID,
        USER_PROMPT_MIN_CHARS,
        generate_ai_background,
        sanitize_user_prompt,
    )

    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({
            "success": False,
            "error": {"code": "PROJECT_NOT_FOUND", "message": "Project not found.", "retryable": False}
        }), 404
    if not user_can_edit_project(current_user, project):
        return jsonify({
            "success": False,
            "error": {
                "code": "FORBIDDEN",
                "message": "Only the project owner can change backgrounds.",
                "retryable": False,
            },
        }), 403

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

        user_prompt = sanitize_user_prompt(
            data.get("user_prompt") or data.get("custom_prompt") or data.get("prompt")
        )
        prompt_mode = str(data.get("prompt_mode") or "").strip().lower()
        if prompt_mode in ("draft", "user", "custom", "user_draft") and not user_prompt:
            return jsonify({
                "success": False,
                "error": {
                    "code": "USER_PROMPT_REQUIRED",
                    "message": (
                        f"Write a short scene description (at least {USER_PROMPT_MIN_CHARS} "
                        "characters), or switch back to Generate from lyrics."
                    ),
                    "retryable": False,
                    "credits": credits_payload(current_user),
                },
            }), 400
        if user_prompt and len(user_prompt) < USER_PROMPT_MIN_CHARS:
            return jsonify({
                "success": False,
                "error": {
                    "code": "USER_PROMPT_TOO_SHORT",
                    "message": (
                        f"Describe the scene in at least {USER_PROMPT_MIN_CHARS} characters."
                    ),
                    "retryable": False,
                    "credits": credits_payload(current_user),
                },
            }), 400

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
            files_dir = proj_dir / "files"
            files_dir.mkdir(parents=True, exist_ok=True)
            archive_name = f"ai_lyric_scene_{int(time.time() * 1000)}.webp"
            archive_path = files_dir / archive_name
            ai_meta = generate_ai_background(
                output_path=archive_path,
                title=title,
                artist=artist,
                lyrics=canonical.get("lyrics") or [],
                language=language,
                aspect_ratio=aspect_ratio,
                width=w,
                height=h,
                user_prompt=user_prompt or None,
            )
            # Keep a stable active background path while preserving every generation in Files.
            bg_file = proj_dir / f"background_{AI_THEME_ID}.webp"
            try:
                shutil.copy2(archive_path, bg_file)
            except Exception:
                bg_file = archive_path

            image_asset = MediaAsset(
                project_id=project.id,
                kind="image",
                storage_key=f"files/{archive_name}",
                file_path=str(archive_path.resolve()),
                mime_type="image/webp",
                size_bytes=archive_path.stat().st_size if archive_path.exists() else 0,
            )
            db.session.add(image_asset)
            try:
                from app.services.user_media_library import register_user_media
                register_user_media(
                    project.user_id,
                    archive_path,
                    "image",
                    display_name=archive_name,
                    source_project_id=project.id,
                )
            except Exception as lib_err:
                current_app.logger.warning("User media library register failed: %s", lib_err)

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
                        "user_prompt": ai_meta.get("user_prompt"),
                        "prompt_source": ai_meta.get("prompt_source"),
                        "model": ai_meta.get("model"),
                        "chat_model": ai_meta.get("chat_model"),
                        "api_size": ai_meta.get("api_size"),
                        "generated_at": ai_meta.get("generated_at"),
                        "file_asset_id": image_asset.id,
                        "archive_path": str(archive_path.resolve()),
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
                    "user_prompt": ai_meta.get("user_prompt"),
                    "prompt_source": ai_meta.get("prompt_source"),
                    "model": ai_meta.get("model"),
                    "api_size": ai_meta.get("api_size"),
                    "file_asset_id": image_asset.id,
                },
                "credits": credits,
                "file": _file_entry_from_asset(image_asset, project_id),
            })
        except ValueError as e:
            return jsonify({
                "success": False,
                "error": {
                    "code": "USER_PROMPT_INVALID",
                    "message": str(e),
                    "retryable": False,
                    "credits": credits_payload(current_user),
                },
            }), 400
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
    if not user_can_edit_project(current_user, project):
        return jsonify({
            "success": False,
            "error": {
                "code": "FORBIDDEN",
                "message": "Only the project owner can upload custom video backgrounds.",
                "retryable": False,
            },
        }), 403

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
    files_dir = proj_dir / "files"
    files_dir.mkdir(parents=True, exist_ok=True)
    video_ext = Path(video_file.filename).suffix.lower() or ".mp4"
    archive_name = f"upload_{int(time.time() * 1000)}{video_ext}"
    archive_path = files_dir / archive_name
    video_file.save(str(archive_path))
    bg_file = proj_dir / f"background_custom{video_ext}"
    try:
        shutil.copy2(archive_path, bg_file)
    except Exception:
        bg_file = archive_path

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

    library_video = MediaAsset(
        project_id=project.id,
        kind="library_video",
        storage_key=f"files/{archive_name}",
        file_path=str(archive_path.resolve()),
        mime_type="video/mp4" if video_ext == ".mp4" else f"video/{video_ext.lstrip('.')}",
        size_bytes=archive_path.stat().st_size if archive_path.exists() else 0,
        duration=project.video_duration,
    )
    db.session.add(library_video)
    try:
        from app.services.user_media_library import register_user_media
        register_user_media(
            project.user_id,
            archive_path,
            "video",
            display_name=video_file.filename or archive_name,
            source_project_id=project.id,
            duration=project.video_duration,
        )
    except Exception as lib_err:
        current_app.logger.warning("User media library register failed: %s", lib_err)
    db.session.commit()

    return jsonify({
        "success": True,
        "template": "custom_video",
        "video_url": url_for("projects.stream_project_media", project_id=project_id, kind="video", t=int(time.time() * 1000)),
        "is_image": False,
        "media_type": "video",
        "filename": video_file.filename,
        "file": _file_entry_from_asset(library_video, project_id),
    })


@projects_bp.route("/<project_id>/files", methods=["GET"])
def list_project_files(project_id: str):
    """List project audio, generated/uploaded images, and videos for the Files drawer."""
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({
            "success": False,
            "error": {"code": "PROJECT_NOT_FOUND", "message": "Project not found.", "retryable": False}
        }), 404
    # Library is always private to the owner — even if the project is public.
    if not user_can_edit_project(current_user, project):
        return jsonify({
            "success": False,
            "error": {
                "code": "FORBIDDEN",
                "message": "Project files are private to the owner.",
                "retryable": False,
            },
        }), 403

    proj_dir = get_project_dir(project_id)
    files_dir = proj_dir / "files"
    files_dir.mkdir(parents=True, exist_ok=True)

    # Ensure primary audio is represented.
    audio_path = resolve_project_media(project, "audio")
    if audio_path:
        _ensure_asset_for_path(project, audio_path, "audio", audio_path.name)

    # Index anything already saved under files/.
    image_exts = {".webp", ".png", ".jpg", ".jpeg", ".gif"}
    video_exts = {".mp4", ".mov", ".webm", ".mkv", ".avi"}
    if files_dir.exists():
        for path in sorted(files_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if not path.is_file():
                continue
            suffix = path.suffix.lower()
            if suffix in image_exts:
                _ensure_asset_for_path(project, path, "image", f"files/{path.name}")
            elif suffix in video_exts:
                _ensure_asset_for_path(project, path, "library_video", f"files/{path.name}")

    db.session.commit()

    assets = (
        db.session.query(MediaAsset)
        .filter(
            MediaAsset.project_id == project_id,
            MediaAsset.kind.in_(("audio", "image", "library_video")),
        )
        .order_by(MediaAsset.created_at.desc())
        .all()
    )
    entries = []
    seen_keys = set()
    for asset in assets:
        path = Path(asset.file_path) if asset.file_path else None
        key = None
        if path and path.exists():
            key = str(path.resolve())
        if key and key in seen_keys:
            continue
        if key:
            seen_keys.add(key)
        if getattr(asset, "checksum", None):
            seen_keys.add(f"ck:{asset.checksum}")
        entry = _file_entry_from_asset(asset, project_id)
        if entry["section"] == "videos" or asset.kind == "library_video":
            entry["section"] = "videos"
            entry["kind"] = "video"
        entries.append(entry)

    # Merge the owner's persistent library so earlier uploads appear in every project.
    try:
        from app.services.user_media_library import list_user_library
        if current_user.is_authenticated and getattr(current_user, "id", None) == project.user_id:
            library = list_user_library(current_user.id, backfill=True)
            for section in ("audio", "images", "videos"):
                for entry in library.get(section, []):
                    if any(e.get("id") == entry["id"] for e in entries):
                        continue
                    if entry.get("name") and any(
                        e.get("name") == entry["name"]
                        and e.get("section") == entry["section"]
                        and e.get("size_bytes") == entry.get("size_bytes")
                        for e in entries
                    ):
                        continue
                    entries.append(entry)
    except Exception as lib_err:
        current_app.logger.warning("Could not merge user media library: %s", lib_err)

    return jsonify({
        "success": True,
        "files": {
            "audio": [e for e in entries if e["section"] == "audio"],
            "images": [e for e in entries if e["section"] == "images"],
            "videos": [e for e in entries if e["section"] == "videos"],
        },
        "counts": {
            "audio": sum(1 for e in entries if e["section"] == "audio"),
            "images": sum(1 for e in entries if e["section"] == "images"),
            "videos": sum(1 for e in entries if e["section"] == "videos"),
        },
    })


@projects_bp.route("/<project_id>/files/<asset_id>/stream", methods=["GET"])
def stream_project_file(project_id: str, asset_id: str):
    """Stream a library file (audio / image / video) by asset id."""
    project = db.session.get(Project, project_id)
    if not project:
        return "Project not found", 404
    # Never expose library assets to non-owners (public projects only share the active background).
    if not user_can_edit_project(current_user, project):
        return "Forbidden", 403
    asset = db.session.get(MediaAsset, asset_id)
    if not asset or asset.project_id != project_id:
        return "File not found", 404
    path = Path(asset.file_path) if asset.file_path else None
    if (not path or not path.exists()) and asset.storage_key:
        path = get_project_dir(project_id) / asset.storage_key
    if not path or not path.exists():
        return "File missing on disk", 404
    from app.utils.files import detect_mime_type
    response = send_file(str(path), mimetype=asset.mime_type or detect_mime_type(path), conditional=True)
    response.headers["Cache-Control"] = "private, max-age=3600"
    response.headers["Accept-Ranges"] = "bytes"
    return response


@projects_bp.route("/<project_id>/files/<asset_id>/apply", methods=["POST"])
def apply_project_file(project_id: str, asset_id: str):
    """Use a library image/video as the active project background."""
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({
            "success": False,
            "error": {"code": "PROJECT_NOT_FOUND", "message": "Project not found.", "retryable": False}
        }), 404
    if not user_can_edit_project(current_user, project):
        return jsonify({
            "success": False,
            "error": {
                "code": "FORBIDDEN",
                "message": "Only the project owner can apply library files.",
                "retryable": False,
            },
        }), 403
    asset = db.session.get(MediaAsset, asset_id)
    if not asset or asset.project_id != project_id:
        return jsonify({
            "success": False,
            "error": {"code": "FILE_NOT_FOUND", "message": "File not found in this project.", "retryable": False}
        }), 404

    src = Path(asset.file_path) if asset.file_path else None
    if (not src or not src.exists()) and asset.storage_key:
        src = get_project_dir(project_id) / asset.storage_key
    if not src or not src.exists():
        return jsonify({
            "success": False,
            "error": {"code": "FILE_MISSING", "message": "File is missing on disk.", "retryable": False}
        }), 404

    suffix = src.suffix.lower()
    is_image = suffix in {".webp", ".png", ".jpg", ".jpeg", ".gif"} or asset.kind == "image"
    canonical = project.get_canonical_json()
    aspect_ratio = canonical.get("render", {}).get("aspect_ratio", "16:9")
    from app.services.background_generator import BackgroundGenerator
    w, h = BackgroundGenerator.get_dimensions(aspect_ratio)
    proj_dir = get_project_dir(project_id)
    if is_image:
        dest = proj_dir / f"background_library{suffix or '.webp'}"
        shutil.copy2(src, dest)
        _apply_background_file(project, dest, "library_image", aspect_ratio, w, h, True)
        media_type = "image"
    else:
        dest = proj_dir / f"background_custom{suffix or '.mp4'}"
        shutil.copy2(src, dest)
        _apply_background_file(project, dest, "library_video", aspect_ratio, w, h, False)
        media_type = "video"

    return jsonify({
        "success": True,
        "template": "library_image" if is_image else "library_video",
        "video_url": url_for(
            "projects.stream_project_media",
            project_id=project_id,
            kind="video",
            t=int(time.time() * 1000),
        ),
        "is_image": is_image,
        "media_type": media_type,
        "file": _file_entry_from_asset(asset, project_id),
    })


@projects_bp.route("/<project_id>/files/upload", methods=["POST"])
def upload_project_file(project_id: str):
    """Upload an image (or video) into the project Files library."""
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({
            "success": False,
            "error": {"code": "PROJECT_NOT_FOUND", "message": "Project not found.", "retryable": False}
        }), 404
    if not user_can_edit_project(current_user, project):
        return jsonify({
            "success": False,
            "error": {
                "code": "FORBIDDEN",
                "message": "Only the project owner can upload files to this library.",
                "retryable": False,
            },
        }), 403

    upload = request.files.get("file") or request.files.get("image") or request.files.get("video")
    if not upload or not upload.filename:
        return jsonify({
            "success": False,
            "error": {"code": "FILE_REQUIRED", "message": "Choose an image or video to upload.", "retryable": False}
        }), 400

    suffix = Path(upload.filename).suffix.lower()
    image_exts = {".webp", ".png", ".jpg", ".jpeg", ".gif"}
    video_exts = {".mp4", ".mov", ".webm", ".mkv"}
    if suffix not in image_exts and suffix not in video_exts:
        return jsonify({
            "success": False,
            "error": {"code": "FILE_TYPE", "message": "Upload a PNG, JPG, WEBP, GIF, MP4, MOV, or WEBM file.", "retryable": False}
        }), 400

    proj_dir = get_project_dir(project_id)
    files_dir = proj_dir / "files"
    files_dir.mkdir(parents=True, exist_ok=True)
    archive_name = f"upload_{int(time.time() * 1000)}{suffix}"
    archive_path = files_dir / archive_name
    upload.save(str(archive_path))

    kind = "image" if suffix in image_exts else "library_video"
    from app.utils.files import detect_mime_type
    asset = MediaAsset(
        project_id=project.id,
        kind=kind,
        storage_key=f"files/{archive_name}",
        file_path=str(archive_path.resolve()),
        mime_type=detect_mime_type(archive_path),
        size_bytes=archive_path.stat().st_size,
    )
    db.session.add(asset)
    try:
        from app.services.user_media_library import register_user_media
        register_user_media(
            project.user_id,
            archive_path,
            "image" if kind == "image" else "video",
            display_name=upload.filename or archive_name,
            source_project_id=project.id,
        )
    except Exception as lib_err:
        current_app.logger.warning("User media library register failed: %s", lib_err)
    db.session.commit()

    return jsonify({
        "success": True,
        "file": _file_entry_from_asset(asset, project_id),
    })

