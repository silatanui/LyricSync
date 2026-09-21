from flask import Blueprint, request, jsonify, current_app
from app.extensions import db
from app.models import Project, RenderJob, LyricLine, LyricWord
from app.tasks.job_queue import submit_task
from app.tasks.transcription_tasks import run_transcription_pipeline

lyrics_bp = Blueprint("lyrics", __name__, url_prefix="/api/projects")

@lyrics_bp.route("/<project_id>/transcribe", methods=["POST"])
def trigger_transcription(project_id: str):
    """Queue transcription job for a project."""
    try:
        project = db.session.get(Project, project_id)
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Database error while loading project for transcription")
        return jsonify({
            "success": False,
            "error": {"code": "DATABASE_UNAVAILABLE", "message": "The project database is unavailable. Please try again after the app restarts.", "retryable": True}
        }), 503
    if not project:
        return jsonify({
            "success": False,
            "error": {"code": "PROJECT_NOT_FOUND", "message": "Project not found.", "retryable": False}
        }), 404

    if not project.audio_path:
        return jsonify({
            "success": False,
            "error": {"code": "NO_AUDIO", "message": "Project does not have an audio track.", "retryable": False}
        }), 400

    # Cancel any previous stale in-flight jobs for this project
    stale_jobs = db.session.query(RenderJob).filter_by(project_id=project.id).filter(RenderJob.status.in_(["queued", "transcribing"])).all()
    for sj in stale_jobs:
        sj.status = "failed"
        sj.error_message = "Superseded by new transcription request"

    # Create RenderJob record to track progress
    job = RenderJob(
        project_id=project.id,
        status="queued",
        stage="Connecting to OpenAI Whisper API",
        progress=10,
    )
    try:
        db.session.add(job)
        project.status = "transcribing"
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Database error while creating transcription job")
        return jsonify({
            "success": False,
            "error": {"code": "JOB_CREATE_FAILED", "message": "The transcription job could not be saved. Check the database connection and try again.", "retryable": True}
        }), 503

    # Launch background task
    app = current_app._get_current_object()
    submit_task(run_transcription_pipeline, app, project.id, job.id)

    return jsonify({
        "success": True,
        "job_id": job.id,
        "message": "Transcription job queued successfully."
    }), 202

@lyrics_bp.route("/<project_id>/lyrics", methods=["GET"])
def get_canonical_lyrics(project_id: str):
    """Return canonical lyrics JSON."""
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({
            "success": False,
            "error": {"code": "PROJECT_NOT_FOUND", "message": "Project not found.", "retryable": False}
        }), 404

    canonical = project.get_canonical_json()
    return jsonify({
        "success": True,
        "lyrics": canonical.get("lyrics", []),
        "revision": project.current_revision,
        "style": canonical.get("style", {})
    })

@lyrics_bp.route("/<project_id>/lyrics", methods=["PUT"])
def update_canonical_lyrics(project_id: str):
    """Save edited lyric revision."""
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({
            "success": False,
            "error": {"code": "PROJECT_NOT_FOUND", "message": "Project not found.", "retryable": False}
        }), 404

    data = request.get_json() or {}
    lyrics = data.get("lyrics")

    if lyrics is None or not isinstance(lyrics, list):
        return jsonify({
            "success": False,
            "error": {"code": "INVALID_DATA", "message": "'lyrics' array is required.", "retryable": False}
        }), 400

    # Validate data integrity (Section 17.2: times monotonically increasing, words inside line)
    for idx, line in enumerate(lyrics):
        line.setdefault("confidence", 0.55)
        l_start = float(line.get("start", 0.0))
        l_end = float(line.get("end", 0.0))
        if l_start < 0 or l_end <= l_start:
            return jsonify({
                "success": False,
                "error": {"code": "INVALID_TIMESTAMPS", "message": f"Line {idx+1} has invalid start/end timestamps.", "retryable": False}
            }), 400

        words = line.get("words", [])
        last_w_end = l_start
        for w_idx, w in enumerate(words):
            w_start = float(w.get("start", 0.0))
            w_end = float(w.get("end", 0.0))
            if w_start < l_start or w_end > l_end + 0.05:
                # auto-clamp words inside line
                w["start"] = max(l_start, w_start)
                w["end"] = min(l_end, max(w["start"] + 0.05, w_end))

    new_rev = save_lyrics_revision(project, lyrics)

    return jsonify({
        "success": True,
        "revision": new_rev,
        "message": f"Saved revision {new_rev}"
    })

def save_lyrics_revision(project: Project, lyrics: list) -> int:
    """Helper to persist new lyrics revision to database and canonical JSON."""
    project.current_revision += 1
    canonical = project.get_canonical_json()
    canonical["lyrics"] = lyrics
    project.set_canonical_json(canonical)

    # Sync to relational tables
    for old_line in list(project.lyric_lines):
        db.session.delete(old_line)

    for line_idx, l in enumerate(lyrics):
        l_model = LyricLine(
            project_id=project.id,
            revision=project.current_revision,
            line_index=line_idx,
            text=l.get("text", ""),
            start=float(l.get("start", 0.0)),
            end=float(l.get("end", 0.0)),
        )
        db.session.add(l_model)
        db.session.flush()

        for w_idx, w in enumerate(l.get("words", [])):
            w_model = LyricWord(
                line_id=l_model.id,
                word_index=w_idx,
                text=w.get("text", ""),
                start=float(w.get("start", 0.0)),
                end=float(w.get("end", 0.0)),
            )
            db.session.add(w_model)

    db.session.commit()
    return project.current_revision

@lyrics_bp.route("/<project_id>/lyrics/custom", methods=["POST"])
def import_custom_lyrics_route(project_id: str):
    """
    Import custom user lyrics (plain text or LRC file/text) for a project.
    """
    from app.services.lyrics_importer import LyricsImporter

    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({
            "success": False,
            "error": {"code": "PROJECT_NOT_FOUND", "message": "Project not found.", "retryable": False}
        }), 404

    content = ""
    if request.is_json:
        data = request.get_json() or {}
        content = data.get("lyrics_text", "").strip()
    else:
        if "lyrics_file" in request.files:
            f = request.files["lyrics_file"]
            if f and f.filename:
                content = f.read().decode("utf-8", errors="replace").strip()
        if not content and "lyrics_text" in request.form:
            content = request.form.get("lyrics_text", "").strip()

    if not content:
        return jsonify({
            "success": False,
            "error": {"code": "EMPTY_LYRICS", "message": "No lyric text or file provided.", "retryable": False}
        }), 400

    total_dur = project.audio_duration or 180.0
    try:
        new_lyrics = LyricsImporter.import_lyrics(content, total_duration=total_dur)
        if not LyricsImporter.is_lrc(content) and project.audio_path:
            try:
                from app.services.openai_transcription import OpenAITranscriber
                from app.services.alignment import AlignmentEngine
                transcriber = OpenAITranscriber()
                transcript = transcriber.transcribe_word_timestamps(project.audio_path)
                ordered_text = transcriber.order_uploaded_lyrics(content, transcript.get("text", ""))
                if ordered_text.strip() != content.strip():
                    new_lyrics = LyricsImporter.import_lyrics(ordered_text, total_duration=total_dur)
                new_lyrics = AlignmentEngine.align_custom_lines(new_lyrics, transcript.get("words", []), total_dur)
            except Exception as alignment_error:
                current_app.logger.warning("Audio alignment unavailable; retaining evenly spaced custom lyrics: %s", alignment_error)
        for line in new_lyrics:
            line.setdefault("confidence", 0.85 if LyricsImporter.is_lrc(content) else 0.55)
    except Exception as e:
        return jsonify({
            "success": False,
            "error": {"code": "PARSE_ERROR", "message": str(e), "retryable": False}
        }), 400

    new_rev = save_lyrics_revision(project, new_lyrics)
    return jsonify({
        "success": True,
        "revision": new_rev,
        "lyrics": new_lyrics,
        "message": f"Successfully imported {len(new_lyrics)} custom lyric lines."
    })


@lyrics_bp.route("/<project_id>/style", methods=["PUT"])
def update_project_style(project_id: str):
    """Update style configuration in canonical document."""
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({
            "success": False,
            "error": {"code": "PROJECT_NOT_FOUND", "message": "Project not found.", "retryable": False}
        }), 404

    data = request.get_json() or {}
    style_data = data.get("style", {})
    render_data = data.get("render", {})

    canonical = project.get_canonical_json()
    if style_data:
        canonical.setdefault("style", {}).update(style_data)
    if render_data:
        canonical.setdefault("render", {}).update(render_data)

    project.set_canonical_json(canonical)
    db.session.commit()

    return jsonify({
        "success": True,
        "style": canonical.get("style"),
        "render": canonical.get("render")
    })
