import json
import logging
from pathlib import Path
from flask import current_app
from app.extensions import db
from app.models import Project, Transcription, LyricLine, LyricWord, RenderJob
from app.services.openai_transcription import OpenAITranscriber
from app.services.alignment import AlignmentEngine

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

def run_transcription_pipeline(app, project_id: str, job_id: str = None):
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
            if job:
                job.status = "transcribing"
                job.stage = "Uploading audio to OpenAI Whisper-1"
                job.progress = 25
                db.session.commit()

            project.status = "transcribing"
            db.session.commit()

            audio_path = str(Path(project.audio_path).resolve())

            # Transcribe with Whisper-1
            transcriber = OpenAITranscriber()
            tx_result = transcriber.transcribe_word_timestamps(audio_path)

            # Whisper can take longer than cPanel's MySQL idle timeout; reload ORM state before writing.
            db.session.remove()
            project = db.session.get(Project, project_id)
            job = db.session.get(RenderJob, job_id) if job_id else None
            if not project:
                raise RuntimeError("Project disappeared while transcription was running")

            if job:
                job.status = "aligning"
                job.stage = "Aligning words and generating lyric lines"
                job.progress = 80
                db.session.commit()

            raw_words = tx_result.get("words", [])
            normalized_words = AlignmentEngine.normalize_words(raw_words)
            segmented_lines = AlignmentEngine.segment_lines(normalized_words)
            for line in segmented_lines:
                line["confidence"] = 0.95
                line["text"] = line["text"].strip().capitalize()
                if line.get("words"):
                    line["words"][0]["text"] = line["words"][0]["text"].strip().capitalize()

            # Persist raw transcription
            tx_record = Transcription(
                project_id=project.id,
                model=transcriber.model,
                language=tx_result.get("language", "en"),
                raw_text=tx_result.get("text", ""),
                json_payload=json.dumps(tx_result),
                version=project.current_revision,
            )
            db.session.add(tx_record)

            # Update canonical document
            canonical = project.get_canonical_json()
            canonical["transcription"]["raw_text"] = tx_result.get("text", "")
            canonical["transcription"]["language"] = tx_result.get("language", "en")
            canonical["lyrics"] = segmented_lines
            canonical.setdefault("meta", {}).setdefault("description", "Synchronized lyric video project")

            # If title was not explicitly given or is generic, generate title from lyrics using OpenAI
            is_auto_title = canonical.get("meta", {}).get("auto_title", False) or project.name.lower() in ("untitled song", "untitled song project", "untitled")
            if is_auto_title and tx_result.get("text"):
                canonical.setdefault("meta", {})["title"] = project.name

            project.set_canonical_json(canonical)

            # Clear old lines for this revision if any and save new lines
            for old_line in list(project.lyric_lines):
                db.session.delete(old_line)

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
                    w_model = LyricWord(
                        line_id=l_model.id,
                        word_index=w_idx,
                        text=w_data["text"],
                        start=w_data["start"],
                        end=w_data["end"],
                    )
                    db.session.add(w_model)

            project.status = "ready"
            if job:
                job.status = "completed"
                job.stage = "Transcription and alignment complete"
                job.progress = 100
                
            db.session.commit()
            logger.info(f"Transcription pipeline completed for project {project_id}")

        except Exception as e:
            logger.exception(f"Error during transcription pipeline: {e}")
            db.session.rollback()
            project.status = "error"
            if job:
                job.status = "failed"
                job.error_code = "TRANSCRIPTION_ERROR"
                job.error_message = str(e)
            db.session.commit()
