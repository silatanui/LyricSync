import os
from pathlib import Path
from flask import Blueprint, request, jsonify, current_app, url_for
from flask_login import current_user
from werkzeug.utils import secure_filename
from app.extensions import db
from app.models import Project, MediaAsset
from app.services.project_privacy import ensure_private_meta
from app.utils.ids import generate_project_id, generate_asset_id
from app.utils.validation import validate_audio_file, validate_video_file
from app.utils.files import get_project_dir, calculate_checksum, detect_mime_type
from app.services.media_probe import MediaProbe
from config import Config

from app.services.background_generator import BackgroundGenerator
from app.tasks.transcription_tasks import run_transcription_pipeline

uploads_bp = Blueprint("uploads", __name__, url_prefix="/api")

import re

def derive_title_from_filename(filename: str) -> str:
    if not filename:
        return "Untitled Song"
    stem = Path(filename).stem
    # Remove track numbers e.g. 01 -, 01., 01_
    stem = re.sub(r'^\s*\d{1,3}\s*[-._]\s*', '', stem)
    # Remove common audio tags like (Official Audio), [Lyrics], etc.
    stem = re.sub(r'[\(\[\{].*?[\)\]\}]', '', stem)
    # Drop trailing genre/marketing clauses after commas.
    stem = re.sub(
        r'[,|]\s*(?:gospel|thanksgiving|anthem|worship|praise|lyric|official|live|skiza)\b.*$',
        '',
        stem,
        flags=re.IGNORECASE,
    )
    # Replace separators with spaces
    stem = re.sub(r'[-_]+', ' ', stem)
    stem = re.sub(r'\s+', ' ', stem).strip(" -_|,")
    generic_words = {"audio", "track", "recording", "voice", "sound", "master", "master_audio", "input", "sample", "song"}
    if not stem or stem.lower() in generic_words:
        return "Untitled Song"
    return stem

@uploads_bp.route("/projects", methods=["POST"])
def create_project():
    """
    Project Ingestion Endpoint (Specification Section 4.1).
    Ingests audio, applies chosen studio background template or custom video, probes media,
    and automatically executes initial transcription pipeline before opening studio.
    """
    if not current_user.is_authenticated:
        return jsonify({
            "success": False,
            "error": {
                "code": "AUTH_REQUIRED",
                "message": "Sign in to create a private project. Only you will see it unless you publish it.",
                "retryable": False,
            },
        }), 401

    library_audio_id = (request.form.get("library_audio_id") or "").strip()
    audio_file = request.files.get("audio")
    has_upload_audio = bool(audio_file and audio_file.filename)
    if not has_upload_audio and not library_audio_id:
        return jsonify({
            "success": False,
            "error": {
                "code": "AUDIO_REQUIRED",
                "message": "Audio file is required.",
                "retryable": False
            }
        }), 400

    video_file = request.files.get("video")
    has_video = bool(video_file and video_file.filename)
    raw_name = request.form.get("name", "").strip()
    is_auto_title = not raw_name or raw_name.lower() in ("untitled", "untitled song", "untitled song project")
    audio_display_name = audio_file.filename if has_upload_audio else ""
    aspect_ratio = request.form.get("aspect_ratio", "16:9").strip() or "16:9"
    selected_template = request.form.get("template", "burgundy_studio").strip() or "burgundy_studio"
    from app.services.openai_transcription import normalize_language_code
    preferred_language = normalize_language_code(
        request.form.get("preferred_language") or request.form.get("language")
    )
    t_width, t_height = BackgroundGenerator.get_dimensions(aspect_ratio)

    library_audio = None
    if library_audio_id and not has_upload_audio:
        from app.services.user_media_library import resolve_library_asset
        library_audio = resolve_library_asset(current_user.id, library_audio_id)
        if not library_audio or library_audio.kind != "audio":
            return jsonify({
                "success": False,
                "error": {
                    "code": "LIBRARY_AUDIO_NOT_FOUND",
                    "message": "That previous upload was not found in your library.",
                    "retryable": False,
                },
            }), 404
        audio_display_name = library_audio.display_name or Path(library_audio.file_path).name

    project_name = raw_name if not is_auto_title else derive_title_from_filename(audio_display_name or "")

    if has_upload_audio and not audio_file.filename:
        return jsonify({
            "success": False,
            "error": {
                "code": "INVALID_FILENAME",
                "message": "Audio file must have a valid filename.",
                "retryable": False
            }
        }), 400

    # Read lengths or stream to disk
    audio_bytes = b""
    if has_upload_audio:
        audio_bytes = audio_file.read()
        audio_file.seek(0)
        is_valid_audio, err = validate_audio_file(audio_file.filename, len(audio_bytes))
        if not is_valid_audio:
            return jsonify({
                "success": False,
                "error": {"code": "AUDIO_INVALID", "message": err, "retryable": False}
            }), 400

    video_bytes = b""
    if has_video:
        video_bytes = video_file.read()
        video_file.seek(0)
        is_valid_video, err = validate_video_file(video_file.filename, len(video_bytes))
        if not is_valid_video:
            return jsonify({
                "success": False,
                "error": {"code": "VIDEO_INVALID", "message": err, "retryable": False}
            }), 400

    proj_id = generate_project_id()
    proj_dir = get_project_dir(proj_id)

    # Store files with secure generated names
    import shutil
    if library_audio and not has_upload_audio:
        src = Path(library_audio.file_path)
        audio_ext = src.suffix.lower() or ".mp3"
        audio_saved_path = proj_dir / f"master_audio{audio_ext}"
        shutil.copy2(src, audio_saved_path)
        audio_bytes = audio_saved_path.read_bytes()
    else:
        audio_ext = Path(audio_file.filename).suffix.lower()
        audio_saved_path = proj_dir / f"master_audio{audio_ext}"
        audio_file.save(str(audio_saved_path))

    # Probe audio duration
    try:
        a_probe = MediaProbe.probe(audio_saved_path)
    except Exception as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "MEDIA_PROBE_FAILED",
                "message": f"Failed to probe audio stream: {e}",
                "retryable": False
            }
        }), 400

    audio_dur = a_probe.get("duration", 0.0)

    if audio_dur > Config.MAX_PROJECT_DURATION_SECONDS:
        return jsonify({
            "success": False,
            "error": {
                "code": "DURATION_LIMIT_EXCEEDED",
                "message": f"Audio duration ({audio_dur:.1f}s) exceeds maximum allowed ({Config.MAX_PROJECT_DURATION_SECONDS}s).",
                "retryable": False
            }
        }), 400

    # Handle background video
    if has_video:
        video_ext = Path(video_file.filename).suffix.lower()
        video_saved_path = proj_dir / f"background_video{video_ext}"
        video_file.save(str(video_saved_path))
        try:
            v_probe = MediaProbe.probe(video_saved_path)
        except Exception:
            v_probe = {"duration": audio_dur, "width": t_width, "height": t_height, "fps": 30.0}
    else:
        # Instant high-efficiency template backdrop (WebP / PNG)
        # Eliminates heavy synchronous 1080p FFmpeg encoding on upload, dropping response time from 30s to <1s.
        video_saved_path = proj_dir / f"background_{selected_template}.webp"
        try:
            BackgroundGenerator.generate_template_asset(
                pattern_type=selected_template,
                output_path=video_saved_path,
                width=t_width,
                height=t_height,
                fmt="WEBP"
            )
        except Exception as error:
            current_app.logger.warning(f"WebP template generation warning, falling back to PNG: {error}")
            video_saved_path = proj_dir / f"background_{selected_template}.png"
            BackgroundGenerator.generate_template_asset(
                pattern_type=selected_template,
                output_path=video_saved_path,
                width=t_width,
                height=t_height,
                fmt="PNG"
            )
        v_probe = {"duration": audio_dur, "width": t_width, "height": t_height, "fps": 30.0}
        video_bytes = video_saved_path.read_bytes() if video_saved_path.exists() else b""

    video_dur = v_probe.get("duration", audio_dur)

    owner_id = current_user.id if current_user.is_authenticated else None
    project = Project(
        id=proj_id,
        user_id=owner_id,
        name=project_name,
        status="ready",
        audio_path=str(audio_saved_path.resolve()),
        video_path=str(video_saved_path.resolve()),
        audio_duration=audio_dur,
        video_duration=video_dur,
        fps=v_probe.get("fps", 30.0),
        width=v_probe.get("width", t_width),
        height=v_probe.get("height", t_height),
    )
    db.session.add(project)

    # Register MediaAsset records
    audio_asset = MediaAsset(
        id=generate_asset_id(),
        project_id=proj_id,
        kind="audio",
        storage_key=audio_saved_path.name,
        file_path=str(audio_saved_path.resolve()),
        mime_type=detect_mime_type(audio_saved_path),
        size_bytes=len(audio_bytes),
        duration=audio_dur,
        checksum=calculate_checksum(audio_saved_path),
    )
    video_asset = MediaAsset(
        id=generate_asset_id(),
        project_id=proj_id,
        kind="video",
        storage_key=video_saved_path.name,
        file_path=str(video_saved_path.resolve()),
        mime_type=detect_mime_type(video_saved_path),
        size_bytes=len(video_bytes),
        duration=video_dur,
        checksum=calculate_checksum(video_saved_path),
    )
    db.session.add(audio_asset)
    db.session.add(video_asset)

    # Persist uploads in the user's cross-project media library.
    try:
        from app.services.user_media_library import register_user_media
        register_user_media(
            owner_id,
            audio_saved_path,
            "audio",
            display_name=audio_display_name or audio_saved_path.name,
            source_project_id=proj_id,
            duration=audio_dur,
        )
        if has_video:
            register_user_media(
                owner_id,
                video_saved_path,
                "video",
                display_name=video_file.filename if video_file else video_saved_path.name,
                source_project_id=proj_id,
                duration=video_dur,
            )
    except Exception as lib_err:
        current_app.logger.warning("User media library register failed: %s", lib_err)

    # Initialize canonical JSON — always private unless the owner later opts in.
    canonical = project.get_canonical_json()
    canonical["media"]["audio_path"] = str(audio_saved_path.resolve())
    canonical["media"]["video_path"] = str(video_saved_path.resolve())
    canonical["media"]["audio_duration"] = audio_dur
    canonical["media"]["video_duration"] = video_dur
    canonical["media"]["fps"] = v_probe.get("fps", 30.0)
    canonical["media"]["width"] = v_probe.get("width", t_width)
    canonical["media"]["height"] = v_probe.get("height", t_height)
    ensure_private_meta(canonical)
    canonical["meta"]["is_public"] = False
    canonical["meta"]["background_template"] = selected_template
    canonical["meta"]["auto_title"] = is_auto_title
    if preferred_language:
        canonical["meta"]["preferred_language"] = preferred_language
        canonical.setdefault("transcription", {})["language"] = preferred_language
    else:
        canonical["meta"].pop("preferred_language", None)
    canonical.setdefault("render", {})["aspect_ratio"] = aspect_ratio
    canonical.setdefault("style", {})["aspectRatio"] = aspect_ratio
    project.set_canonical_json(canonical)

    try:
        db.session.commit()
    except Exception as error:
        db.session.rollback()
        current_app.logger.exception("Database commit failed during project ingestion")
        return jsonify({
            "success": False,
            "error": {
                "code": "PROJECT_SAVE_FAILED",
                "message": f"The project could not be saved to the database: {error}",
                "retryable": True
            }
        }), 503

    # Check for optional custom lyrics upload/paste
    custom_lyrics_text = ""
    if "lyrics_file" in request.files:
        lf = request.files["lyrics_file"]
        if lf and lf.filename:
            try:
                custom_lyrics_text = lf.read().decode("utf-8", errors="replace").strip()
            except Exception:
                pass
    if not custom_lyrics_text and "lyrics_text" in request.form:
        custom_lyrics_text = request.form.get("lyrics_text", "").strip()

    if custom_lyrics_text:
        try:
            from app.services.lyrics_importer import LyricsImporter
            from app.routes.lyrics import save_lyrics_revision
            custom_lines = LyricsImporter.import_lyrics(custom_lyrics_text, total_duration=audio_dur)
            save_lyrics_revision(project, custom_lines)
            project.status = "ready"
            db.session.commit()
        except Exception as e:
            current_app.logger.warning(f"Failed to import custom lyrics on upload: {e}")
            project.status = "ready"
            db.session.commit()

    # Transcription is started by the editor button so upload requests stay reliable on shared hosting.

    return jsonify({
        "success": True,
        "project": {
            "id": project.id,
            "name": project.name,
            "status": project.status,
            "editor_url": url_for("views.editor_page", project_id=project.id, auto_transcribe=1),
            "audio": {"duration": audio_dur},
            "video": {"duration": video_dur, "width": project.width, "height": project.height, "fps": project.fps},
            "lyrics_revision": project.current_revision,
            "lyrics_count": len(project.lyric_lines) if project.lyric_lines else 0
        }
    }), 201
