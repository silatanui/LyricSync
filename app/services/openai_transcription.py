import time
import random
import logging
import json
from pathlib import Path
from typing import Dict, Any, List
from flask import has_app_context, current_app
from openai import OpenAI
from config import Config

logger = logging.getLogger(__name__)

class OpenAITranscriber:
    def __init__(self, api_key: str = None, model: str = None):
        if api_key is None and has_app_context():
            api_key = current_app.config.get("OPENAI_API_KEY")
        self.api_key = api_key if api_key is not None else Config.OPENAI_API_KEY

        if model is None and has_app_context():
            model = current_app.config.get("OPENAI_TRANSCRIPTION_MODEL")
        self.model = model or Config.OPENAI_TRANSCRIPTION_MODEL or "whisper-1"

        if self.api_key and self.api_key not in ("mock", "replace-this", ""):
            self.client = OpenAI(api_key=self.api_key, timeout=60.0)
        else:
            self.client = None

    def transcribe_word_timestamps(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribes an audio file and returns word-level timestamps.
        Includes retry logic for transient errors and fallback mock when no API key is set.
        """
        audio_path_resolved = str(Path(audio_path).resolve())
        if not Path(audio_path_resolved).exists():
            raise FileNotFoundError(f"Audio file for transcription not found: {audio_path_resolved}")

        if not self.client or self.api_key in ("replace-this", "mock", ""):
            logger.info("Using mock transcription provider because OPENAI_API_KEY is not configured.")
            return self._mock_transcription(audio_path_resolved)

        max_retries = 2
        backoff = 2.0

        for attempt in range(1, max_retries + 1):
            try:
                with open(audio_path_resolved, "rb") as audio_file:
                    result = self.client.audio.transcriptions.create(
                        model=self.model,
                        file=audio_file,
                        response_format="verbose_json",
                        timestamp_granularities=["word"],
                    )
                
                words = []
                for w in (getattr(result, "words", None) or []):
                    # Handle both dictionary and object formats
                    word_text = getattr(w, "word", None) or (w.get("word") if isinstance(w, dict) else "")
                    w_start = getattr(w, "start", 0.0) or (w.get("start", 0.0) if isinstance(w, dict) else 0.0)
                    w_end = getattr(w, "end", 0.0) or (w.get("end", 0.0) if isinstance(w, dict) else 0.0)
                    words.append({
                        "text": str(word_text).strip(),
                        "start": float(w_start),
                        "end": float(w_end),
                    })

                return {
                    "text": getattr(result, "text", ""),
                    "language": getattr(result, "language", "en"),
                    "duration": getattr(result, "duration", None),
                    "words": words,
                }
            except Exception as e:
                logger.warning(f"Transcription attempt {attempt} failed: {e}")
                if attempt == max_retries:
                    raise RuntimeError(f"OpenAI transcription failed after {max_retries} attempts: {e}")
                # Exponential backoff with jitter
                sleep_time = (backoff ** attempt) + random.uniform(0.1, 1.0)
                time.sleep(sleep_time)

    def order_uploaded_lyrics(self, lyrics_text: str, transcript_text: str) -> str:
        """Use the language model to clean and order supplied lyrics against the audio transcript."""
        if not self.client or not lyrics_text.strip() or not transcript_text.strip():
            return lyrics_text
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You organize supplied song lyrics to match the order and line breaks heard in a transcript. Return only the lyrics, one line per lyric, with no commentary. Do not invent or remove words; preserve the supplied wording as much as possible."},
                    {"role": "user", "content": f"SUPPLIED LYRICS:\n{lyrics_text[:12000]}\n\nAUDIO TRANSCRIPT:\n{transcript_text[:12000]}"},
                ],
                max_tokens=4000,
                temperature=0.1,
            )
            ordered = (response.choices[0].message.content or "").strip()
            return ordered or lyrics_text
        except Exception as error:
            logger.warning("Could not order uploaded lyrics with AI: %s", error)
            return lyrics_text

    def _mock_transcription(self, audio_path: str) -> Dict[str, Any]:
        """
        Deterministic mock transcription for offline testing, demos, or CI runs.
        """
        sample_words = [
            ("Welcome", 0.5, 1.0),
            ("to", 1.05, 1.3),
            ("LyricSync", 1.35, 2.0),
            ("the", 2.4, 2.7),
            ("future", 2.75, 3.2),
            ("of", 3.25, 3.4),
            ("lyric", 3.45, 3.9),
            ("videos", 3.95, 4.5),
            ("Sing", 5.2, 5.7),
            ("your", 5.75, 6.0),
            ("heart", 6.05, 6.5),
            ("out", 6.55, 7.0),
            ("underneath", 7.6, 8.3),
            ("the", 8.35, 8.5),
            ("neon", 8.55, 9.1),
            ("lights", 9.15, 9.8),
            ("Every", 10.5, 10.9),
            ("beat", 10.95, 11.4),
            ("in", 11.45, 11.7),
            ("harmony", 11.75, 12.6),
            ("tonight", 12.8, 13.7),
        ]
        words = [{"text": text, "start": s, "end": e} for text, s, e in sample_words]
        full_text = " ".join([w["text"] for w in words])
        return {
            "text": full_text,
            "language": "en",
            "duration": 15.0,
            "words": words,
        }
