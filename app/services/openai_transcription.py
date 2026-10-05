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
    Compresses audio to 16kHz mono 64kbps MP3 before Whisper.
    Whisper internally resamples all audio to 16kHz mono; we pre-compress to:
      1. Guarantee files are under OpenAI's strict 25MB upload ceiling.
      2. Keep uploads small enough to stream in short chunks.
      3. Retain consonants that 32kbps drops, which matters for non-English vocals.
    NOTE: Always re-encode regardless of input format because the source file
    may be at 44.1kHz or 48kHz stereo which significantly slows Whisper decoding.
    Returns (path_to_audio, is_temp_file).
    """
    input_file = Path(input_path).resolve()
    ffmpeg_bin = get_ffmpeg_binary()

    if not ffmpeg_bin or not input_file.exists():
        return str(input_file), False

    file_size_mb = input_file.stat().st_size / (1024 * 1024)

    try:
        tmp = tempfile.NamedTemporaryFile(suffix="_whisper.mp3", delete=False)
        tmp.close()
        temp_path = tmp.name

        cmd = [
            ffmpeg_bin, "-y",
            "-i", str(input_file),
            "-vn",                  # strip video/cover-art streams
            "-ac", "1",             # mono (Whisper requirement)
            "-ar", "16000",         # 16kHz (Whisper native sample rate)
            "-b:a", "64k",          # 64kbps mono — still small, clearer for other languages
            "-f", "mp3",
            temp_path
        ]
        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
            timeout=60
        )
        if res.returncode == 0 and Path(temp_path).exists() and Path(temp_path).stat().st_size > 500:
            compressed_mb = Path(temp_path).stat().st_size / (1024 * 1024)
            logger.info(
                f"Audio pre-compressed for Whisper: {file_size_mb:.2f}MB -> {compressed_mb:.2f}MB"
            )
            return temp_path, True
        else:
            logger.warning(f"FFmpeg audio optimization failed, falling back to original: {res.stderr[-300:]}")
            if Path(temp_path).exists():
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
    except subprocess.TimeoutExpired:
        logger.warning("FFmpeg audio compression timed out — proceeding with original file")
    except Exception as exc:
        logger.warning(f"Audio pre-compression exception: {exc}")

    return str(input_file), False


WHISPER_LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "pt": "Portuguese",
    "de": "German",
    "it": "Italian",
    "sw": "Swahili",
    "yo": "Yoruba",
    "ha": "Hausa",
    "ig": "Igbo",
    "ar": "Arabic",
    "hi": "Hindi",
    "bn": "Bengali",
    "ur": "Urdu",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "ru": "Russian",
    "tr": "Turkish",
    "nl": "Dutch",
    "pl": "Polish",
    "id": "Indonesian",
    "ms": "Malay",
    "vi": "Vietnamese",
    "th": "Thai",
    "uk": "Ukrainian",
    "am": "Amharic",
    "zu": "Zulu",
    "af": "Afrikaans",
    "sv": "Swedish",
    "da": "Danish",
    "fi": "Finnish",
    "no": "Norwegian",
    "cs": "Czech",
    "ro": "Romanian",
    "el": "Greek",
    "he": "Hebrew",
    "fa": "Persian",
    "tl": "Tagalog",
}
_LANGUAGE_NAME_TO_CODE = {name.lower(): code for code, name in WHISPER_LANGUAGES.items()}
_LANGUAGE_NAME_TO_CODE.update({
    "mandarin": "zh",
    "cantonese": "zh",
    "portuguese": "pt",
    "flemish": "nl",
    "farsi": "fa",
    "persian": "fa",
    "filipino": "tl",
    "tagalog": "tl",
    "bahasa": "id",
    "norsk": "no",
})

# Continuity prompts steer Whisper toward sung lyrics in the chosen language.
_LANGUAGE_PROMPTS = {
    "en": "Song lyrics with clear word timing.",
    "es": "Letras de canción con timing claro de palabras.",
    "fr": "Paroles de chanson avec un timing clair des mots.",
    "pt": "Letra de música com timing claro das palavras.",
    "de": "Songtext mit klarer Wortzeitgebung.",
    "it": "Testo della canzone con timing chiaro delle parole.",
    "sw": "Maneno ya wimbo yaliyopangwa kwa muda sahihi.",
    "yo": "Ọrọ orin pẹlu àkókò ọ̀rọ̀ tó yé.",
    "ha": "Kalmomin waƙa tare da lokaci mai kyau.",
    "ar": "كلمات أغنية بتوقيت واضح للكلمات.",
    "hi": "गाने के बोल स्पष्ट शब्द समय के साथ।",
    "zh": "歌词，词语时间清晰。",
    "ja": "歌詞。単語のタイミングを正確に。",
    "ko": "노래 가사. 단어 타이밍을 명확하게.",
    "ru": "Текст песни с чёткими таймингами слов.",
    "tr": "Şarkı sözleri, kelime zamanlaması net.",
    "nl": "Songtekst met duidelijke woordtiming.",
    "pl": "Tekst piosenki z wyraźnym timingiem słów.",
    "id": "Lirik lagu dengan timing kata yang jelas.",
    "vi": "Lời bài hát với thời gian từ rõ ràng.",
    "th": "เนื้อเพลง จังหวะคำชัดเจน",
    "uk": "Текст пісні з чітким таймінгом слів.",
    "am": "የዘፈን ቃላት በግልጽ የቃል ጊዜ።",
    "zu": "Amagama engoma anesikhathi esicacile.",
    "af": "Liedjielirieke met duidelike woordtydsberekening.",
}


def normalize_language_code(value) -> str | None:
    """Return a Whisper language code, or None when detection should stay automatic."""
    if value is None:
        return None
    code = str(value).strip().lower().replace("_", "-")
    if code in ("", "auto", "detect", "und"):
        return None
    # Accept BCP-47 tags like en-US / zh-CN.
    if "-" in code:
        code = code.split("-", 1)[0]
    if code in WHISPER_LANGUAGES:
        return code
    return _LANGUAGE_NAME_TO_CODE.get(code)


def language_display_name(value) -> str:
    code = normalize_language_code(value)
    if code:
        return WHISPER_LANGUAGES[code]
    text = str(value or "").strip()
    return text[:1].upper() + text[1:] if text else ""


def lyric_language_prompt(language: str | None, continuity: str = "") -> str | None:
    """Build a Whisper prompt that keeps later slices in the song's language."""
    code = normalize_language_code(language)
    base = _LANGUAGE_PROMPTS.get(code) if code else "Song lyrics transcribed accurately in the sung language."
    continuity = (continuity or "").strip()
    if continuity:
        return f"{base} {continuity}"[:220]
    return base


def plan_audio_chunks(duration: float, first_seconds: float = 12.0, chunk_seconds: float = 20.0, overlap_seconds: float = 1.5) -> List[Tuple[float, float | None]]:
    """Split a song into a short opening preview plus overlapping follow-up slices.

    The first slice always starts at t=0 so early vocals are never skipped.
    Overlap lets the next slice replace words Whisper clipped at the cut.
    A None length means the whole file.
    """
    duration = float(duration or 0)
    if duration <= 0:
        return [(0.0, None)]
    if duration <= first_seconds + 0.75:
        return [(0.0, round(duration, 3))]

    chunks: List[Tuple[float, float | None]] = [(0.0, round(min(first_seconds, duration), 3))]
    start = chunks[0][1] - overlap_seconds
    for _ in range(500):
        if start >= duration - 0.45:
            break
        length = min(chunk_seconds, duration - start)
        if length < 0.6:
            break
        chunks.append((round(start, 3), round(length, 3)))
        end = start + length
        if end >= duration - 0.2:
            break
        next_start = end - overlap_seconds
        if next_start <= start:
            break
        start = next_start
    return chunks


def merge_chunk_words(existing: List[Dict[str, Any]], incoming: List[Dict[str, Any]], chunk_start: float, overlap_seconds: float) -> List[Dict[str, Any]]:
    """Keep words before the overlap midpoint and append the new slice after it."""
    if not existing or chunk_start <= 0:
        return list(incoming)
    boundary = float(chunk_start) + (float(overlap_seconds) * 0.5)
    merged = [
        word for word in existing
        if float(word.get("end", word.get("start", 0))) <= boundary + 0.04
    ]
    merged.extend(
        word for word in incoming
        if float(word.get("start", 0)) >= boundary - 0.08
    )
    merged.sort(key=lambda word: float(word.get("start", 0)))
    return merged


def extract_audio_chunk(source_path: str, start: float, length: float, dest_path: str) -> None:
    ffmpeg_bin = get_ffmpeg_binary()
    cmd = [
        ffmpeg_bin, "-y",
        "-i", source_path,
        "-ss", f"{start:.3f}",
        "-t", f"{length:.3f}",
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-b:a", "64k",
        "-f", "mp3",
        dest_path,
    ]
    res = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
        timeout=45,
    )
    if res.returncode != 0 or not Path(dest_path).exists() or Path(dest_path).stat().st_size < 200:
        tail = (res.stderr or "")[-300:]
        raise RuntimeError(f"Could not slice audio for streaming transcription: {tail}")


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

        # Minimum 360s — Whisper can take 4-6 min for a full-length song
        self.timeout = max(360.0, float(timeout))
        self.max_retries = max(1, int(retries))
        if self.api_key and self.api_key not in ("mock", "replace-this", ""):
            self.client = OpenAI(api_key=self.api_key, timeout=self.timeout)
        else:
            self.client = None

    def transcribe_word_timestamps(self, audio_path: str, language: str = None, prompt: str = None) -> Dict[str, Any]:
        """Transcribe a whole file. Language is detected unless a Whisper code is passed."""
        audio_path_resolved = str(Path(audio_path).resolve())
        if not Path(audio_path_resolved).exists():
            raise FileNotFoundError(f"Audio file for transcription not found: {audio_path_resolved}")

        if not self.client or self.api_key in ("replace-this", "mock", ""):
            logger.info("Using mock transcription provider because OPENAI_API_KEY is not configured.")
            return self._mock_transcription(audio_path_resolved)

        upload_path, is_temp = optimize_audio_for_whisper(audio_path_resolved)
        try:
            return self._request_transcript(upload_path, language=normalize_language_code(language), prompt=prompt)
        finally:
            if is_temp and Path(upload_path).exists():
                try:
                    os.unlink(upload_path)
                except OSError:
                    pass

    def transcribe_streaming(self, audio_path: str, language: str = None, duration: float = None, on_snapshot=None) -> Dict[str, Any]:
        """Transcribe in short slices and publish each slice as soon as it is ready.

        The first slice always starts at t=0 (about 12s) so early vocals are kept.
        Later slices overlap slightly and replace the words at the cut. Language is
        taken from the caller (name-based / user choice); auto-detect is only used
        when no language was provided.
        """
        audio_path_resolved = str(Path(audio_path).resolve())
        if not Path(audio_path_resolved).exists():
            raise FileNotFoundError(f"Audio file for transcription not found: {audio_path_resolved}")

        if not self.client or self.api_key in ("replace-this", "mock", ""):
            logger.info("Using mock transcription provider because OPENAI_API_KEY is not configured.")
            snapshot = self._mock_transcription(audio_path_resolved)
            snapshot["partial"] = False
            snapshot["transcribed_until"] = float(snapshot.get("duration") or 0)
            if on_snapshot:
                on_snapshot(snapshot, True)
            return snapshot

        requested = normalize_language_code(language)
        upload_path, is_temp = optimize_audio_for_whisper(audio_path_resolved)
        temp_files = [upload_path] if is_temp else []
        try:
            song_duration = float(duration or 0)
            if song_duration <= 0:
                from app.services.media_probe import MediaProbe
                song_duration = float(MediaProbe.probe(Path(upload_path)).get("duration") or 0)

            chunks = plan_audio_chunks(song_duration)
            accumulated: List[Dict[str, Any]] = []
            locked_language = requested
            detected_label = language_display_name(requested) if requested else ""
            continuity = ""
            latest = {
                "text": "",
                "language": requested or "",
                "language_name": detected_label,
                "duration": song_duration or None,
                "words": [],
                "partial": True,
                "transcribed_until": 0.0,
            }

            for index, (start, length) in enumerate(chunks):
                is_last = index == len(chunks) - 1
                if length is None:
                    piece_path = upload_path
                    piece_start = 0.0
                    piece_end = song_duration
                else:
                    tmp = tempfile.NamedTemporaryFile(suffix="_chunk.mp3", delete=False)
                    tmp.close()
                    piece_path = tmp.name
                    temp_files.append(piece_path)
                    extract_audio_chunk(upload_path, start, length, piece_path)
                    piece_start = start
                    piece_end = start + length

                piece = self._request_transcript(
                    piece_path,
                    language=locked_language,
                    prompt=lyric_language_prompt(locked_language, continuity),
                )
                if not locked_language:
                    locked_language = normalize_language_code(piece.get("language"))
                if piece.get("language"):
                    detected_label = language_display_name(piece.get("language")) or detected_label

                shifted = []
                for word in piece.get("words", []):
                    shifted.append({
                        "text": word["text"],
                        "start": round(float(word["start"]) + piece_start, 3),
                        "end": round(float(word["end"]) + piece_start, 3),
                    })
                accumulated = merge_chunk_words(accumulated, shifted, piece_start, 1.5)
                continuity = " ".join(word["text"] for word in accumulated)[-160:].strip()
                frontier = piece_end if piece_end else song_duration
                if not is_last and frontier:
                    frontier = float(frontier)
                latest = {
                    "text": " ".join(word["text"] for word in accumulated).strip(),
                    "language": locked_language or piece.get("language") or "",
                    "language_name": detected_label,
                    "duration": song_duration or piece.get("duration"),
                    "words": accumulated,
                    "partial": not is_last,
                    "transcribed_until": round(float(frontier or 0), 3),
                    "chunk_index": index + 1,
                    "chunk_count": len(chunks),
                }
                if on_snapshot:
                    on_snapshot(latest, is_last)
            return latest
        finally:
            for path in temp_files:
                try:
                    if path and Path(path).exists():
                        os.unlink(path)
                except OSError:
                    pass

    def _request_transcript(self, upload_path: str, language: str = None, prompt: str = None) -> Dict[str, Any]:
        """Call Whisper once for a file that is already small enough to upload."""
        max_retries = self.max_retries
        backoff = 2.0
        for attempt in range(1, max_retries + 1):
            try:
                with open(upload_path, "rb") as audio_file:
                    kwargs = {
                        "model": self.model,
                        "file": audio_file,
                        "response_format": "verbose_json",
                        "timestamp_granularities": ["word", "segment"],
                        "temperature": 0,
                    }
                    if language:
                        kwargs["language"] = language
                    if prompt:
                        kwargs["prompt"] = prompt[:220]
                    result = self.client.audio.transcriptions.create(**kwargs)
                return _transcript_from_response(result, fallback_language=language or "")
            except Exception as e:
                err_lower = str(e).lower()
                is_quota = "insufficient_quota" in err_lower or ("quota" in err_lower and "exceeded" in err_lower)
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
                time.sleep((backoff ** attempt) + random.uniform(0.1, 0.5))

    def order_uploaded_lyrics(self, lyrics_text: str, transcript_text: str) -> str:
        """Use the language model to clean and order supplied lyrics against the audio transcript."""
        if not self.client or not lyrics_text.strip() or not transcript_text.strip():
            return lyrics_text
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You organize supplied song lyrics to match the order and line breaks heard in a transcript. Return only the lyrics, one line per lyric, with no commentary. Do not invent or remove words. Keep the original language and spelling."},
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
        """Deterministic mock transcription for offline testing, demos, or CI runs."""
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


def _field(item, name, default=None):
    if item is None:
        return default
    if isinstance(item, dict):
        return item.get(name, default)
    return getattr(item, name, default)


def _transcript_from_response(result, fallback_language: str = "") -> Dict[str, Any]:
    """Read word timestamps from Whisper.

    Keep every timed word Whisper returns — including early vocals. Filtering by
    no_speech_prob previously dropped real lyric words near the start when Whisper
    mis-labeled soft singing / sparse openings as silence.
    """
    words = []
    for word in (_field(result, "words", None) or []):
        text = str(_field(word, "word", "") or "").strip()
        if not text:
            continue
        start = max(0.0, float(_field(word, "start", 0) or 0))
        end = float(_field(word, "end", start) or start)
        words.append({"text": text, "start": start, "end": max(start, end)})

    # Preserve chronological order; never drop leading words.
    words.sort(key=lambda item: (float(item["start"]), float(item["end"])))

    detected = _field(result, "language", None) or fallback_language or ""
    return {
        "text": _field(result, "text", "") or "",
        "language": detected,
        "duration": _field(result, "duration", None),
        "words": words,
    }
