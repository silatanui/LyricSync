from flask import Blueprint, request, jsonify, current_app, Response, stream_with_context
import json
import time
from app.extensions import db
from app.models import Project, RenderJob, LyricLine, LyricWord
from app.tasks.job_queue import submit_task
from app.tasks.transcription_tasks import run_transcription_pipeline
from app.services.openai_transcription import normalize_language_code, language_display_name

lyrics_bp = Blueprint("lyrics", __name__, url_prefix="/api/projects")


def _stream_payload(project: Project, transcription: dict | None = None) -> dict:
    canonical = project.get_canonical_json()
    transcription = transcription if transcription is not None else (canonical.get("transcription") or {})
    meta = canonical.get("meta") or {}
    recognition = meta.get("recognition") or {}
    return {
        "partial": bool(transcription.get("partial")),
        "preview": bool(transcription.get("preview") or transcription.get("partial")),
        "language": transcription.get("language") or "",
        "language_name": transcription.get("language_name") or "",
        "transcribed_until": transcription.get("transcribed_until") or 0,
        "duration": transcription.get("duration") or project.audio_duration or 0,
        "chunk_index": transcription.get("chunk_index") or 0,
        "chunk_count": transcription.get("chunk_count") or 0,
        "source": transcription.get("provider") or meta.get("lyrics_source") or "",
        "artist": meta.get("artist") or recognition.get("artist") or "",
        "title": meta.get("title") or recognition.get("title") or "",
        "synced": bool(recognition.get("synced")),
    }


def _active_transcription_job(project_id: str):
    return (
        db.session.query(RenderJob)
        .filter_by(project_id=project_id)
        .filter(RenderJob.status.in_(["queued", "transcribing"]))
        .order_by(RenderJob.created_at.desc())
        .first()
    )


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

    body = request.get_json(silent=True) or {}
    language = normalize_language_code(body.get("language"))

    # Create RenderJob record to track progress
    job = RenderJob(
        project_id=project.id,
        status="queued",
        stage="Preparing opening preview",
        progress=6,
        detail_json=json.dumps({
            "partial": True,
            "preview": True,
            "language": language or "",
            "language_name": language_display_name(language) if language else "",
            "transcribed_until": 0,
            "duration": float(project.audio_duration or 0),
            "chunk_index": 0,
            "chunk_count": 0,
        }),
    )
    try:
        db.session.add(job)
        project.status = "transcribing"
        canonical = project.get_canonical_json()
        canonical.setdefault("meta", {})
        if language:
            canonical["meta"]["preferred_language"] = language
        elif "preferred_language" in body and not body.get("language"):
            canonical["meta"].pop("preferred_language", None)
        canonical.setdefault("transcription", {})
        canonical["transcription"]["partial"] = True
        canonical["transcription"]["preview"] = True
        canonical["transcription"]["transcribed_until"] = 0
        canonical["transcription"]["duration"] = float(project.audio_duration or 0)
        if language:
            canonical["transcription"]["language"] = language
            canonical["transcription"]["language_name"] = language_display_name(language)
        project.set_canonical_json(canonical)
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
    submit_task(run_transcription_pipeline, app, project.id, job.id, language)

    return jsonify({
        "success": True,
        "job_id": job.id,
        "language": language or "auto",
        "message": "Transcription job queued. Opening preview unlocks as soon as the first lines land."
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
    active_job = _active_transcription_job(project.id)
    return jsonify({
        "success": True,
        "lyrics": canonical.get("lyrics", []),
        "revision": project.current_revision,
        "style": canonical.get("style", {}),
        "stream": _stream_payload(project),
        "active_job_id": active_job.id if active_job else None,
        "preferred_language": (canonical.get("meta") or {}).get("preferred_language") or "",
    })


@lyrics_bp.route("/<project_id>/lyrics/events", methods=["GET"])
def stream_lyrics_events(project_id: str):
    """Server-sent events for progressive lyric snapshots while transcription runs."""
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({
            "success": False,
            "error": {"code": "PROJECT_NOT_FOUND", "message": "Project not found.", "retryable": False}
        }), 404

    app = current_app._get_current_object()

    def event_stream():
        last_until = -1.0
        last_partial = True
        idle_ticks = 0
        with app.app_context():
            while idle_ticks < 450:
                db.session.remove()
                project_row = db.session.get(Project, project_id)
                if not project_row:
                    yield "event: error\ndata: {\"message\":\"Project missing\"}\n\n"
                    break
                canonical = project_row.get_canonical_json()
                stream = _stream_payload(project_row, canonical.get("transcription") or {})
                until = float(stream.get("transcribed_until") or 0)
                partial = bool(stream.get("partial"))
                changed = until != last_until or partial != last_partial
                if changed:
                    last_until = until
                    last_partial = partial
                    idle_ticks = 0
                    payload = {
                        "success": True,
                        "lyrics": canonical.get("lyrics", []),
                        "revision": project_row.current_revision,
                        "stream": stream,
                    }
                    yield f"event: lyrics\ndata: {json.dumps(payload)}\n\n"
                    if not partial and until > 0:
                        yield "event: done\ndata: {\"partial\":false}\n\n"
                        break
                else:
                    idle_ticks += 1
                    yield ": keepalive\n\n"
                time.sleep(0.85)

    return Response(
        stream_with_context(event_stream()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )

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
                preferred = normalize_language_code(
                    (request.get_json(silent=True) or {}).get("language")
                    or (project.get_canonical_json().get("meta") or {}).get("preferred_language")
                )
                transcript = transcriber.transcribe_word_timestamps(project.audio_path, language=preferred)
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
    from app.services.style_normalize import normalize_style_payload

    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({
            "success": False,
            "error": {"code": "PROJECT_NOT_FOUND", "message": "Project not found.", "retryable": False}
        }), 404

    data = request.get_json() or {}
    style_data = normalize_style_payload(data.get("style", {}))
    render_data = data.get("render", {})

    canonical = project.get_canonical_json()
    if style_data:
        # Drop stale camelCase keys so export always reads snake_case fields.
        style_block = canonical.setdefault("style", {})
        for camel in (
            "fontSize", "lineHeight", "letterSpacing", "fontWeight", "fontStyle",
            "textCase", "effectStrength", "primaryColor", "highlightColor", "textAlign",
            "outlineEnabled", "outlineColor", "outlineSoftness",
            "shadowEnabled", "shadowColor", "shadowOpacity", "shadowDistance",
            "shadowAngle", "shadowBlur", "bevelEnabled", "bevelSize",
            "bevelSoftness", "bevelAngle", "bevelHighlightColor",
            "bevelHighlightOpacity", "bevelShadowColor", "bevelShadowOpacity",
            "aspectRatio",
        ):
            style_block.pop(camel, None)
        style_block.update(style_data)
    if render_data:
        canonical.setdefault("render", {}).update(render_data)

    project.set_canonical_json(canonical)
    db.session.commit()

    return jsonify({
        "success": True,
        "style": canonical.get("style"),
        "render": canonical.get("render")
    })
