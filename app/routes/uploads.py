import os
from pathlib import Path
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from app.extensions import db
from app.models import Project, MediaAsset
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
    # Replace separators with spaces
    stem = re.sub(r'[-_]+', ' ', stem)
    stem = re.sub(r'\s+', ' ', stem).strip()
    generic_words = {"audio", "track", "recording", "voice", "sound", "master", "master_audio", "input", "sample", "song"}
    if not stem or stem.lower() in generic_words:
        return "Untitled Song"
    return stem.title()

@uploads_bp.route("/projects", methods=["POST"])
def create_project():
    """
    Project Ingestion Endpoint (Specification Section 4.1).
    Ingests audio, applies chosen studio background template or custom video, probes media,
    and automatically executes initial transcription pipeline before opening studio.
    """
    if "audio" not in request.files:
        return jsonify({
            "success": False,
            "error": {
                "code": "AUDIO_REQUIRED",
                "message": "Audio file is required.",
                "retryable": False
            }
        }), 400

    audio_file = request.files["audio"]
    video_file = request.files.get("video")
    has_video = bool(video_file and video_file.filename)
    raw_name = request.form.get("name", "").strip()
    is_auto_title = not raw_name or raw_name.lower() in ("untitled", "untitled song", "untitled song project")
    project_name = raw_name if not is_auto_title else derive_title_from_filename(audio_file.filename or "")
    aspect_ratio = request.form.get("aspect_ratio", "16:9").strip() or "16:9"
    selected_template = request.form.get("template", "burgundy_studio").strip() or "burgundy_studio"
    t_width, t_height = BackgroundGenerator.get_dimensions(aspect_ratio)

    if not audio_file.filename:
        return jsonify({
            "success": False,
            "error": {
                "code": "INVALID_FILENAME",
                "message": "Audio file must have a valid filename.",
                "retryable": False
            }
        }), 400

    # Read lengths or stream to disk
    audio_bytes = audio_file.read()
    audio_file.seek(0)

    # Validate audio
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
        # Generate studio pattern background video with chosen aspect ratio
        video_saved_path = proj_dir / "background_video.mp4"
        BackgroundGenerator.generate_background_video(
            audio_path=audio_saved_path,
            output_video_path=video_saved_path,
            duration=audio_dur,
            pattern_type=selected_template,
            aspect_ratio=aspect_ratio
        )
        v_probe = {"duration": audio_dur, "width": t_width, "height": t_height, "fps": 30.0}
        video_bytes = video_saved_path.read_bytes()

    video_dur = v_probe.get("duration", audio_dur)

    project = Project(
        id=proj_id,
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

    # Initialize canonical JSON
    canonical = project.get_canonical_json()
    canonical["media"]["audio_path"] = str(audio_saved_path.resolve())
    canonical["media"]["video_path"] = str(video_saved_path.resolve())
    canonical["media"]["audio_duration"] = audio_dur
    canonical["media"]["video_duration"] = video_dur
    canonical["media"]["fps"] = v_probe.get("fps", 30.0)
    canonical["media"]["width"] = v_probe.get("width", t_width)
    canonical["media"]["height"] = v_probe.get("height", t_height)
    canonical.setdefault("meta", {})["background_template"] = selected_template
    canonical.setdefault("meta", {})["auto_title"] = is_auto_title
    canonical.setdefault("render", {})["aspect_ratio"] = aspect_ratio
    canonical.setdefault("style", {})["aspectRatio"] = aspect_ratio
    project.set_canonical_json(canonical)

    db.session.commit()

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
            try:
                run_transcription_pipeline(current_app._get_current_object(), proj_id)
                db.session.refresh(project)
            except Exception as te:
                current_app.logger.error(f"Post-ingestion transcription warning: {te}")
                project.status = "ready"
                db.session.commit()
    else:
        # Automatic Post-Ingestion Transcription Pipeline (runs before opening studio)
        try:
            run_transcription_pipeline(current_app._get_current_object(), proj_id)
            db.session.refresh(project)
        except Exception as e:
            current_app.logger.error(f"Post-ingestion transcription warning: {e}")
            project.status = "ready"
            db.session.commit()

    return jsonify({
        "success": True,
        "project": {
            "id": project.id,
            "name": project.name,
            "status": project.status,
            "audio": {"duration": audio_dur},
            "video": {"duration": video_dur, "width": project.width, "height": project.height, "fps": project.fps},
            "lyrics_revision": project.current_revision,
            "lyrics_count": len(project.lyric_lines) if project.lyric_lines else 0
        }
    }), 201
