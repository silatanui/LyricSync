import os
import subprocess
import tempfile
import time
import random
import logging
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
from flask import has_app_context, current_app
from openai import OpenAI
import openai
from config import Config
from app.services.media_probe import get_ffmpeg_binary

logger = logging.getLogger(__name__)

def optimize_audio_for_whisper(input_path: str) -> Tuple[str, bool]:
    """
    Compresses audio into a lightweight 16kHz mono 48kbps MP3 for OpenAI Whisper.
    Whisper's neural network internally resamples audio to 16kHz mono.
    Compressing heavy WAV/FLAC/high-bitrate files (often 30MB-80MB) down to ~1MB:
      1. Prevents exceeding OpenAI's strict 25MB file upload ceiling.
      2. Shrinks upload transfer time from 30-60s to <1s.
      3. Accelerates Whisper speech recognition and decoding.
    Returns (path_to_audio, is_temp_file).
    """
    input_file = Path(input_path).resolve()
    ffmpeg_bin = get_ffmpeg_binary()

    if not ffmpeg_bin or not input_file.exists():
        return str(input_file), False

    # Check file size (in MB)
    file_size_mb = input_file.stat().st_size / (1024 * 1024)
    file_ext = input_file.suffix.lower()

    # If already a very small MP3 (< 3 MB), no need to re-encode
    if file_ext == ".mp3" and file_size_mb < 3.0:
        return str(input_file), False

    try:
        tmp = tempfile.NamedTemporaryFile(suffix="_whisper.mp3", delete=False)
        tmp.close()
        temp_path = tmp.name

        cmd = [
            ffmpeg_bin, "-y",
            "-i", str(input_file),
            "-vn",
            "-ac", "1",
            "-ar", "16000",
            "-b:a", "48k",
            "-f", "mp3",
            temp_path
        ]
        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
            timeout=30
        )
        if res.returncode == 0 and Path(temp_path).exists() and Path(temp_path).stat().st_size > 500:
            logger.info(
                f"Audio optimized for Whisper: {file_size_mb:.2f}MB -> {Path(temp_path).stat().st_size / (1024*1024):.2f}MB"
            )
            return temp_path, True
        else:
            logger.warning(f"FFmpeg audio optimization failed, falling back to original: {res.stderr[-200:]}")
            if Path(temp_path).exists():
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
    except Exception as exc:
        logger.warning(f"Audio pre-compression exception: {exc}")

    return str(input_file), False

class OpenAITranscriber:
    def __init__(self, api_key: str = None, model: str = None):
        if api_key is None and has_app_context():
            api_key = current_app.config.get("OPENAI_API_KEY")
        self.api_key = api_key if api_key is not None else Config.OPENAI_API_KEY

        if model is None and has_app_context():
            model = current_app.config.get("OPENAI_TRANSCRIPTION_MODEL")
        self.model = model or Config.OPENAI_TRANSCRIPTION_MODEL or "whisper-1"

        timeout = Config.OPENAI_TIMEOUT_SECONDS
        retries = Config.OPENAI_TRANSCRIPTION_RETRIES
        if has_app_context():
            timeout = current_app.config.get("OPENAI_TIMEOUT_SECONDS", timeout)
            retries = current_app.config.get("OPENAI_TRANSCRIPTION_RETRIES", retries)

        self.timeout = max(15.0, float(timeout))
        self.max_retries = max(1, int(retries))
        if self.api_key and self.api_key not in ("mock", "replace-this", ""):
            self.client = OpenAI(api_key=self.api_key, timeout=self.timeout)
        else:
            self.client = None

    def transcribe_word_timestamps(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribes an audio file and returns word-level timestamps.
        Includes audio compression, retry logic for transient errors, and fast failure for quota/auth errors.
        """
        audio_path_resolved = str(Path(audio_path).resolve())
        if not Path(audio_path_resolved).exists():
            raise FileNotFoundError(f"Audio file for transcription not found: {audio_path_resolved}")

        if not self.client or self.api_key in ("replace-this", "mock", ""):
            logger.info("Using mock transcription provider because OPENAI_API_KEY is not configured.")
            return self._mock_transcription(audio_path_resolved)

        # Optimize audio to 16kHz mono MP3 for sub-second uploads & fast Whisper processing
        upload_path, is_temp = optimize_audio_for_whisper(audio_path_resolved)

        max_retries = self.max_retries
        backoff = 2.0

        try:
            for attempt in range(1, max_retries + 1):
                try:
                    with open(upload_path, "rb") as audio_file:
                        result = self.client.audio.transcriptions.create(
                            model=self.model,
                            file=audio_file,
                            response_format="verbose_json",
                            timestamp_granularities=["word"],
                        )
                    
                    words = []
                    for w in (getattr(result, "words", None) or []):
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
                    err_msg = str(e)
                    err_lower = err_msg.lower()

                    # Fast-fail non-retryable errors
                    is_quota = "insufficient_quota" in err_lower or "quota" in err_lower and "exceeded" in err_lower
                    is_auth = "invalid_api_key" in err_lower or "incorrect api key" in err_lower or isinstance(e, getattr(openai, "AuthenticationError", ()))
                    is_too_large = "maximum content size limit is 25mb" in err_lower or "413" in err_lower

                    if is_quota:
                        logger.error(f"OpenAI quota exceeded: {e}")
                        raise RuntimeError("OpenAI account quota exceeded ($0 credit balance). Please add credits to your OpenAI platform account.")
                    if is_auth:
                        logger.error(f"OpenAI authentication failed: {e}")
                        raise RuntimeError("Invalid OpenAI API key. Please verify the OPENAI_API_KEY in server configuration.")
                    if is_too_large:
                        logger.error(f"Audio file exceeded OpenAI 25MB ceiling: {e}")
                        raise RuntimeError("Audio file exceeds OpenAI Whisper 25MB limit even after compression.")

                    logger.warning(f"Transcription attempt {attempt}/{max_retries} failed: {e}")
                    if attempt == max_retries:
                        raise RuntimeError(f"OpenAI transcription failed: {e}")
                    
                    sleep_time = (backoff ** attempt) + random.uniform(0.1, 0.5)
                    time.sleep(sleep_time)
        finally:
            if is_temp and Path(upload_path).exists():
                try:
                    os.unlink(upload_path)
                except OSError:
                    pass

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
