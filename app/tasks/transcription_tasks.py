import json
import logging
from pathlib import Path
from flask import current_app
from app.extensions import db
from app.models import Project, Transcription, LyricLine, LyricWord, RenderJob
from app.services.openai_transcription import OpenAITranscriber, language_display_name
from app.services.alignment import AlignmentEngine
from app.services.lyrics_importer import LyricsImporter
from app.services.song_catalog import (
    lookup_known_song,
    infer_language_hint,
    choose_transcription_language,
)
from app.utils.files import resolve_project_media

logger = logging.getLogger(__name__)

def generate_song_title_from_lyrics(lyrics_text: str, current_title: str = "Untitled Song") -> str:
    """
    Uses OpenAI to analyze transcribed lyrics and generate a smart, concise song title.
    """
    if not lyrics_text or len(lyrics_text.strip()) < 15:
        return current_title
    try:
        transcriber = OpenAITranscriber()
        if transcriber.client:
            response = transcriber.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a music cataloging expert. Read the song lyrics and generate a concise, evocative song title (2 to 5 words). Return ONLY the title with no quotation marks, no punctuation, and no explanation."
                    },
                    {
                        "role": "user",
                        "content": f"Song lyrics:\n{lyrics_text[:1500]}"
                    }
                ],
                max_tokens=25,
                temperature=0.7,
            )
            title = response.choices[0].message.content.strip().strip('"\'')
            if title and len(title) <= 50 and not title.lower().startswith("here"):
                return title
    except Exception as e:
        logger.warning(f"Could not generate title with AI from lyrics: {e}")
    return current_title

def generate_song_description_from_lyrics(lyrics_text: str) -> str:
    """Generate a short project-card description without exposing model chatter."""
    if not lyrics_text or len(lyrics_text.strip()) < 15:
        return "Synchronized lyric video project"
    try:
        transcriber = OpenAITranscriber()
        if transcriber.client:
            response = transcriber.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Summarize these song lyrics in one vivid sentence of no more than 18 words. Return only the sentence."},
                    {"role": "user", "content": lyrics_text[:4000]},
                ],
                max_tokens=40,
                temperature=0.4,
            )
            return (response.choices[0].message.content or "").strip().strip('"') or "Synchronized lyric video project"
    except Exception as error:
        logger.warning("Could not generate song description: %s", error)
    return "Synchronized lyric video project"

def _clock_label(seconds: float) -> str:
    seconds = max(0, int(float(seconds or 0)))
    return f"{seconds // 60}:{seconds % 60:02d}"


def _update_job_stage(job_id: str, stage: str, progress: int, stream: dict | None = None):
    if not job_id:
        return
    db.session.remove()
    job = db.session.get(RenderJob, job_id)
    if not job:
        return
    job.status = "transcribing"
    job.stage = stage[:64]
    job.progress = int(progress)
    if stream is not None:
        job.detail_json = json.dumps(stream)
    db.session.commit()
    db.session.remove()


def _persist_known_lyrics(project_id: str, job_id: str, match: dict, language: str | None = None) -> bool:
    """Save catalog lyrics immediately so Whisper can be skipped for known songs."""
    from app.services.openai_transcription import normalize_language_code

    db.session.remove()
    project = db.session.get(Project, project_id)
    job = db.session.get(RenderJob, job_id) if job_id else None
    if not project:
        return False

    lyrics_text = (match.get("lyrics_text") or "").strip()
    if not lyrics_text or match.get("instrumental"):
        return False

    duration = float(project.audio_duration or match.get("duration") or 0)
    try:
        segmented_lines = LyricsImporter.import_lyrics(lyrics_text, total_duration=duration or 180.0)
    except Exception as exc:
        logger.warning("Could not parse catalog lyrics: %s", exc)
        return False

    # Optional: snap known plain lyrics onto a timing transcript without trusting ASR text.
    align_words = match.get("align_words") or []
    if align_words and not match.get("synced"):
        try:
            segmented_lines = AlignmentEngine.align_custom_lines(segmented_lines, align_words, duration or 180.0)
        except Exception as exc:
            logger.warning("Could not align known lyrics to audio timings: %s", exc)

    confidence = 0.97 if match.get("synced") else (0.9 if match.get("source") == "local-pack" else 0.78)
    for line in segmented_lines:
        line["confidence"] = line.get("confidence") or confidence
        line["text"] = AlignmentEngine.polish_lyric_text(line.get("text", ""))
        if line.get("words"):
            line["words"][0]["text"] = AlignmentEngine.polish_lyric_text(line["words"][0].get("text", ""))

    language_value = normalize_language_code(language or match.get("language")) or ""
    language_name = language_display_name(language_value) if language_value else ""
    artist = match.get("artist") or ""
    title = match.get("title") or project.name
    raw_text = "\n".join(line.get("text", "") for line in segmented_lines)
    provider = match.get("source") or "lrclib"

    tx_record = (
        db.session.query(Transcription)
        .filter_by(project_id=project.id)
        .order_by(Transcription.created_at.desc())
        .first()
    )
    if tx_record is None:
        tx_record = Transcription(
            project_id=project.id,
            model=provider,
            version=project.current_revision,
        )
        db.session.add(tx_record)
    tx_record.model = provider
    tx_record.language = str(language_value or ("sw" if provider == "local-pack" else "en"))[:16]
    tx_record.raw_text = raw_text
    tx_record.json_payload = json.dumps({
        "text": raw_text,
        "source": provider,
        "external_id": match.get("external_id"),
        "artist": artist,
        "title": title,
        "synced": bool(match.get("synced")),
        "confidence": match.get("confidence"),
    })

    canonical = project.get_canonical_json()
    canonical.setdefault("transcription", {})
    canonical["transcription"].update({
        "provider": provider,
        "model": "catalog",
        "raw_text": raw_text,
        "language": language_value or ("sw" if provider == "local-pack" else "en"),
        "language_name": language_name or ("Swahili" if provider == "local-pack" else "English"),
        "partial": False,
        "preview": False,
        "transcribed_until": duration,
        "duration": duration,
        "chunk_index": 1,
        "chunk_count": 1,
    })
    canonical["lyrics"] = segmented_lines
    meta = canonical.setdefault("meta", {})
    meta["lyrics_source"] = provider
    meta["artist"] = artist
    meta["title"] = title
    meta["recognition"] = {
        "provider": provider,
        "external_id": match.get("external_id"),
        "confidence": match.get("confidence"),
        "synced": bool(match.get("synced")),
        "identified_by": match.get("identified_by") or provider,
    }
    is_auto_title = meta.get("auto_title", False) or project.name.lower() in (
        "untitled song", "untitled song project", "untitled",
    )
    if (is_auto_title or provider == "local-pack") and title:
        display = f"{artist} - {title}" if artist else title
        project.name = display[:255]
        meta["title"] = title
        meta["auto_title"] = False
    if artist and title:
        meta["description"] = f"Known lyrics for {artist} — {title}"
    project.set_canonical_json(canonical)

    for old_line in list(project.lyric_lines):
        db.session.delete(old_line)
    db.session.flush()
    for line_idx, line_data in enumerate(segmented_lines):
        l_model = LyricLine(
            project_id=project.id,
            revision=project.current_revision,
            line_index=line_idx,
            text=line_data["text"],
            start=line_data["start"],
            end=line_data["end"],
        )
        db.session.add(l_model)
        db.session.flush()
        for w_idx, w_data in enumerate(line_data.get("words", [])):
            db.session.add(LyricWord(
                line_id=l_model.id,
                word_index=w_idx,
                text=w_data["text"],
                start=w_data["start"],
                end=w_data["end"],
            ))

    stream = {
        "partial": False,
        "preview": False,
        "language": language_value or ("sw" if provider == "local-pack" else "en"),
        "language_name": language_name or ("Swahili" if provider == "local-pack" else "English"),
        "transcribed_until": duration,
        "duration": duration,
        "chunk_index": 1,
        "chunk_count": 1,
        "source": provider,
        "artist": artist,
        "title": title,
        "synced": bool(match.get("synced")),
    }
    project.status = "ready"
    if job:
        label = f"{artist} — {title}" if artist else title
        job.status = "completed"
        job.stage = f"Known lyrics · {label}"[:64]
        job.progress = 100
        job.detail_json = json.dumps(stream)
    db.session.commit()
    db.session.remove()
    return True


def _try_known_song_lyrics(project, audio_path, job_id, language, song_duration, transcriber):
    """Try catalog lyrics. Returns (saved, language_hint, opening_meta)."""
    project_id = project.id
    project_name = project.name
    language_hint = language or infer_language_hint(project_name)
    opening_meta = {"text": "", "detected": ""}
    _update_job_stage(
        job_id,
        "Checking if this song is already known…",
        12,
        {
            "partial": True,
            "preview": True,
            "language": language_hint or "",
            "language_name": "",
            "transcribed_until": 0,
            "duration": song_duration,
            "chunk_index": 0,
            "chunk_count": 0,
            "source": "catalog",
        },
    )

    match = lookup_known_song(
        project_name,
        song_duration,
        openai_client=getattr(transcriber, "client", None),
        language_hint=language_hint,
    )

    # Weak title / catalog miss — listen from t=0, then ask the catalog again.
    opening_text = ""
    if not match and getattr(transcriber, "client", None):
        _update_job_stage(job_id, "Listening from the start to identify the song…", 18)
        try:
            from app.services.openai_transcription import (
                plan_audio_chunks,
                extract_audio_chunk,
                optimize_audio_for_whisper,
                normalize_language_code,
            )
            import tempfile
            import os
            upload_path, is_temp = optimize_audio_for_whisper(str(audio_path))
            tmp_chunk = None
            try:
                chunks = plan_audio_chunks(song_duration or 30)
                # Always begin at the true start of the audio (never skip an intro).
                start = 0.0
                length = chunks[0][1]
                if length is None:
                    piece_path = upload_path
                else:
                    tmp = tempfile.NamedTemporaryFile(suffix="_id.mp3", delete=False)
                    tmp.close()
                    tmp_chunk = tmp.name
                    extract_audio_chunk(upload_path, start, length or 12.0, tmp_chunk)
                    piece_path = tmp_chunk

                # Probe from t=0. If the user picked a base language, force it
                # so Whisper does not invent Hausa/Japanese for a Swahili song.
                name_lang = language_hint or infer_language_hint(project_name)
                probe_lang = name_lang  # may be None for true auto-detect
                opening = transcriber.transcribe_word_timestamps(piece_path, language=probe_lang)
                opening_text = (opening.get("text") or "").strip()
                opening_detected = normalize_language_code(opening.get("language")) or ""
                opening_meta = {"text": opening_text, "detected": opening_detected or (probe_lang or "")}

                if probe_lang:
                    # User/base language wins; do not re-detect into another tongue.
                    language_hint = probe_lang
                    resolved = probe_lang
                else:
                    resolved = choose_transcription_language(
                        name_language=name_lang,
                        opening_text=opening_text,
                        opening_detected=opening_detected,
                    )
                    if resolved and resolved != opening_detected:
                        _update_job_stage(
                            job_id,
                            f"Using {language_display_name(resolved)} from the song name…"[:64],
                            20,
                        )
                        opening = transcriber.transcribe_word_timestamps(piece_path, language=resolved)
                        opening_text = (opening.get("text") or "").strip()
                        opening_meta = {
                            "text": opening_text,
                            "detected": normalize_language_code(opening.get("language")) or resolved,
                        }
                    language_hint = resolved or name_lang or opening_detected

                if opening_text:
                    _update_job_stage(job_id, "Matching opening lyrics to the catalog…", 24)
                    match = lookup_known_song(
                        project_name,
                        song_duration,
                        openai_client=transcriber.client,
                        opening_lyrics=opening_text,
                        min_confidence=0.58,
                        language_hint=language_hint,
                    )
            finally:
                if tmp_chunk and os.path.exists(tmp_chunk):
                    try:
                        os.unlink(tmp_chunk)
                    except OSError:
                        pass
                if is_temp and Path(upload_path).exists():
                    try:
                        os.unlink(upload_path)
                    except OSError:
                        pass
        except Exception as exc:
            logger.warning("Opening identification pass failed: %s", exc)

    if not match:
        return False, language_hint, opening_meta

    label = f"{match.get('artist')} - {match.get('title')}".strip(" -")
    _update_job_stage(
        job_id,
        f"Found {label}. Loading known lyrics…"[:64],
        55,
        {
            "partial": True,
            "preview": True,
            "language": language_hint or match.get("language") or "",
            "language_name": "",
            "transcribed_until": 0,
            "duration": song_duration,
            "source": match.get("source"),
            "artist": match.get("artist"),
            "title": match.get("title"),
        },
    )
    saved = _persist_known_lyrics(
        project_id,
        job_id,
        match,
        language=language_hint or match.get("language") or language,
    )
    if saved:
        logger.info(
            "Used known lyrics for project %s (%s — %s, synced=%s, source=%s)",
            project_id,
            match.get("artist"),
            match.get("title"),
            match.get("synced"),
            match.get("source"),
        )
    return saved, language_hint, opening_meta


def _persist_transcription_snapshot(project_id: str, job_id: str, snapshot: dict, is_final: bool, model_name: str):
    """Save the lyrics received so far so the studio can play before the song ends."""
    db.session.remove()
    project = db.session.get(Project, project_id)
    job = db.session.get(RenderJob, job_id) if job_id else None
    if not project:
        return

    raw_words = snapshot.get("words", [])
    language_value = snapshot.get("language") or ""
    language_name = snapshot.get("language_name") or ""
    normalized_words = AlignmentEngine.normalize_words(raw_words)
    segmented_lines = AlignmentEngine.segment_lines(normalized_words, language=language_value)
    for line in segmented_lines:
        line["confidence"] = 0.95
        line["text"] = AlignmentEngine.polish_lyric_text(line.get("text", ""))
        if line.get("words"):
            line["words"][0]["text"] = AlignmentEngine.polish_lyric_text(line["words"][0].get("text", ""))
    if segmented_lines and not is_final:
        segmented_lines[-1]["confidence"] = 0.55

    raw_text = str(snapshot.get("text", "")).encode("utf-8", errors="replace").decode("utf-8")
    duration = float(snapshot.get("duration") or project.audio_duration or 0)
    transcribed_until = float(snapshot.get("transcribed_until") or 0)

    tx_record = (
        db.session.query(Transcription)
        .filter_by(project_id=project.id)
        .order_by(Transcription.created_at.desc())
        .first()
    )
    if tx_record is None:
        tx_record = Transcription(
            project_id=project.id,
            model=model_name,
            version=project.current_revision,
        )
        db.session.add(tx_record)
    tx_record.model = model_name
    tx_record.language = str(language_value)[:16]
    tx_record.raw_text = raw_text
    tx_record.json_payload = json.dumps({
        "text": raw_text,
        "language": language_value,
        "words": normalized_words,
    })

    canonical = project.get_canonical_json()
    canonical.setdefault("transcription", {})
    canonical["transcription"]["raw_text"] = raw_text
    canonical["transcription"]["language"] = language_value
    canonical["transcription"]["language_name"] = language_name
    canonical["transcription"]["partial"] = not is_final
    canonical["transcription"]["transcribed_until"] = transcribed_until
    canonical["transcription"]["duration"] = duration
    canonical["transcription"]["chunk_index"] = snapshot.get("chunk_index") or 0
    canonical["transcription"]["chunk_count"] = snapshot.get("chunk_count") or 0
    canonical["transcription"]["preview"] = not is_final
    canonical["lyrics"] = segmented_lines
    canonical.setdefault("meta", {}).setdefault("description", "Synchronized lyric video project")
    if language_value:
        canonical.setdefault("meta", {})["preferred_language"] = language_value
    is_auto_title = canonical.get("meta", {}).get("auto_title", False) or project.name.lower() in ("untitled song", "untitled song project", "untitled")
    if is_final and is_auto_title and raw_text:
        smart_title = generate_song_title_from_lyrics(raw_text, project.name)
        project.name = smart_title
        canonical.setdefault("meta", {})["title"] = smart_title
        canonical["meta"]["description"] = generate_song_description_from_lyrics(raw_text)
    project.set_canonical_json(canonical)

    for old_line in list(project.lyric_lines):
        db.session.delete(old_line)
    db.session.flush()

    for line_idx, line_data in enumerate(segmented_lines):
        l_model = LyricLine(
            project_id=project.id,
            revision=project.current_revision,
            line_index=line_idx,
            text=line_data["text"],
            start=line_data["start"],
            end=line_data["end"],
        )
        db.session.add(l_model)
        db.session.flush()
        for w_idx, w_data in enumerate(line_data.get("words", [])):
            db.session.add(LyricWord(
                line_id=l_model.id,
                word_index=w_idx,
                text=w_data["text"],
                start=w_data["start"],
                end=w_data["end"],
            ))

    stream = {
        "partial": not is_final,
        "language": language_value,
        "language_name": language_name,
        "transcribed_until": transcribed_until,
        "duration": duration,
        "chunk_index": snapshot.get("chunk_index") or 0,
        "chunk_count": snapshot.get("chunk_count") or 0,
    }
    if is_final:
        project.status = "ready"
        if job:
            job.status = "completed"
            job.stage = "Lyric sync complete"
            job.progress = 100
            job.detail_json = json.dumps(stream)
    else:
        project.status = "transcribing"
        covered = transcribed_until / duration if duration else 0
        if job:
            job.status = "transcribing"
            label = language_name or "Detecting language"
            job.stage = f"{label} · {_clock_label(transcribed_until)} / {_clock_label(duration)}"[:64]
            job.progress = min(96, 12 + int(84 * covered))
            job.detail_json = json.dumps(stream)
    db.session.commit()
    db.session.remove()


def run_transcription_pipeline(app, project_id: str, job_id: str = None, language: str = None):
    """
    Executes end-to-end transcription and alignment pipeline.
    Runs inside the application context.
    """
    with app.app_context():
        project = db.session.get(Project, project_id)
        job = db.session.get(RenderJob, job_id) if job_id else None

        if not project or not project.audio_path:
            logger.error(f"Cannot transcribe: project or audio path missing for {project_id}")
            if job:
                job.status = "failed"
                job.error_code = "AUDIO_MISSING"
                job.error_message = "No audio file associated with project"
                db.session.commit()
            return

        try:
            audio_path = resolve_project_media(project, "audio")
            if not audio_path or not audio_path.exists():
                raise FileNotFoundError(f"Project audio file not found on disk for project {project.id}")


            song_duration = float(project.audio_duration or 0)
            if job:
                job.status = "transcribing"
                job.stage = "Checking if this song is already known…"
                job.progress = 8
                job.detail_json = json.dumps({
                    "partial": True,
                    "language": language or "",
                    "language_name": "",
                    "transcribed_until": 0,
                    "duration": song_duration,
                    "chunk_index": 0,
                    "chunk_count": 0,
                })
                db.session.commit()

            project.status = "transcribing"
            db.session.commit()

            from app.services.openai_transcription import normalize_language_code

            project_key = project.id
            project_name = project.name
            user_selected_language = normalize_language_code(language)
            name_language = user_selected_language or infer_language_hint(project_name)
            # Release the DB connection before the first network call.
            db.session.remove()

            transcriber = OpenAITranscriber()

            # Fast path: known commercial tracks load published lyrics instead of full ASR.
            catalog_saved = False
            opening_meta = {"text": "", "detected": ""}
            language_from_catalog = name_language
            try:
                project_ref = db.session.get(Project, project_key)
                if project_ref:
                    catalog_saved, language_from_catalog, opening_meta = _try_known_song_lyrics(
                        project_ref,
                        audio_path,
                        job_id,
                        name_language,
                        song_duration,
                        transcriber,
                    )
                    if catalog_saved:
                        logger.info(f"Catalog lyrics applied for project {project_id}; skipped Whisper")
                        return
            except Exception as catalog_err:
                logger.warning("Known-song lookup failed; falling back to Whisper: %s", catalog_err)
            finally:
                db.session.remove()

            # Unrecognized song: use the user's base language when set.
            # Otherwise prefer title/catalog hint; only switch with strong evidence.
            if user_selected_language:
                effective_language = user_selected_language
            else:
                effective_language = choose_transcription_language(
                    name_language=language_from_catalog or name_language,
                    opening_text=opening_meta.get("text") or "",
                    opening_detected=opening_meta.get("detected") or "",
                    force_language=False,
                )

            stage_lang = language_display_name(effective_language) if effective_language else "auto-detect"
            _update_job_stage(
                job_id,
                f"Song not in catalog. Transcribing ({stage_lang})…"[:64],
                10,
                {
                    "partial": True,
                    "preview": True,
                    "language": effective_language or "",
                    "language_name": stage_lang if effective_language else "",
                    "transcribed_until": 0,
                    "duration": song_duration,
                    "chunk_index": 0,
                    "chunk_count": 0,
                },
            )

            def on_snapshot(snapshot, is_final):
                _persist_transcription_snapshot(
                    project_id,
                    job_id,
                    snapshot,
                    is_final,
                    transcriber.model,
                )

            transcriber.transcribe_streaming(
                str(audio_path),
                language=effective_language,
                duration=song_duration,
                on_snapshot=on_snapshot,
            )
            logger.info(f"Transcription pipeline completed for project {project_id}")

        except Exception as e:
            logger.exception(f"Error during transcription pipeline for {project_id}: {e}")
            try:
                db.session.rollback()
            except Exception:
                pass
            try:
                db.session.remove()
                project = db.session.get(Project, project_id)
                job = db.session.get(RenderJob, job_id) if job_id else None
                if project:
                    project.status = "error"
                if job:
                    job.status = "failed"
                    job.error_code = "TRANSCRIPTION_ERROR"
                    job.error_message = str(e)
                    job.progress = 0
                db.session.commit()
            except Exception as db_err:
                logger.error(f"Failed to record transcription failure in DB: {db_err}")
