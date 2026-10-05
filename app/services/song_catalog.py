"""Look up known commercial tracks and pull published lyrics before Whisper.

Uses the project title (and optional AI identification from a short opening)
plus the free LRCLIB catalog. Synced LRC lyrics are preferred so the studio
can skip a full-song transcription for songs it already knows.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

import requests

logger = logging.getLogger(__name__)

LRCLIB_BASE = "https://lrclib.net/api"
USER_AGENT = "LyricSyncStudio/1.0 (https://github.com/silatanui/LyricSync)"

_SPLIT_PATTERNS = (
    re.compile(r"\s+[-–—]\s+"),
    re.compile(r"\s+[|]\s+"),
)
_NOISE_SUFFIX = re.compile(
    r"\b(official(\s+video)?|lyrics?(\s+video)?|audio|hd|hq|remaster(ed)?|"
    r"visuali[sz]er|topic|explicit|radio\s+edit|live|performance|"
    r"gospel(\s+song)?|thanksgiving(\s+anthem)?|anthem|worship|praise(\s+song)?)\b",
    re.IGNORECASE,
)
_TRACK_PREFIX = re.compile(r"^\s*\d{1,3}[\s._-]+")
_GENRE_CLAUSE = re.compile(
    r"[,|]\s*(?:gospel|thanksgiving|anthem|worship|praise|lyric|official|live|skiza)\b.*$",
    re.IGNORECASE,
)
_SWAHILI_TITLE_CUES = re.compile(
    r"\b(kama|mkono|wako|yesu|bwana|mungu|asante|ipyana|niseme|milele|"
    r"ushindi|neema|furaha|tumaini|baraka|wewe|mimi|hallelujah|aleuya|"
    r"swahili|kiswahili|nzuri|pendo|roho|mwokozi)\b",
    re.IGNORECASE,
)
_COMMON_ENGLISH = {
    "the", "and", "you", "are", "for", "that", "with", "this", "from", "your",
    "have", "was", "were", "been", "not", "but", "all", "can", "will", "just",
    "like", "come", "again", "free", "presence", "god", "world", "many", "way",
    "down", "lonely", "mountain", "welcome", "hear", "let", "me", "in", "of",
    "to", "a", "i", "my", "is", "it", "on", "be", "we", "one", "two",
}


def clean_title_fragment(value: str) -> str:
    text = _TRACK_PREFIX.sub("", str(value or "")).strip()
    text = _GENRE_CLAUSE.sub("", text)
    text = _NOISE_SUFFIX.sub(" ", text)
    text = re.sub(r"[_\.]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" -_|,")
    return text


_EXPLICIT_LANGUAGE_TAGS = (
    (re.compile(r"\b(kiswahili|swahili)\b", re.I), "sw"),
    (re.compile(r"\b(japanese|nihongo|日本語)\b", re.I), "ja"),
    (re.compile(r"\b(korean|hangul|한국어|조선말)\b", re.I), "ko"),
    (re.compile(r"\b(chinese|mandarin|cantonese|中文|汉语|漢語)\b", re.I), "zh"),
    (re.compile(r"\b(spanish|español|espanol)\b", re.I), "es"),
    (re.compile(r"\b(french|français|francais)\b", re.I), "fr"),
    (re.compile(r"\b(portuguese|português|portugues)\b", re.I), "pt"),
    (re.compile(r"\b(german|deutsch)\b", re.I), "de"),
    (re.compile(r"\b(arabic|العربية)\b", re.I), "ar"),
    (re.compile(r"\b(hindi|हिन्दी|हिंदी)\b", re.I), "hi"),
    (re.compile(r"\b(english)\b", re.I), "en"),
)


def script_language_evidence(text: str) -> str | None:
    """Return a language code when the writing system itself is a strong cue."""
    sample = str(text or "")
    if not sample.strip():
        return None
    counts = {
        "ja_kana": len(re.findall(r"[\u3040-\u30ff]", sample)),
        "ja_kanji": len(re.findall(r"[\u4e00-\u9fff]", sample)),
        "ko": len(re.findall(r"[\uac00-\ud7af]", sample)),
        "ar": len(re.findall(r"[\u0600-\u06ff]", sample)),
        "ru": len(re.findall(r"[\u0400-\u04ff]", sample)),
        "hi": len(re.findall(r"[\u0900-\u097f]", sample)),
        "th": len(re.findall(r"[\u0e00-\u0e7f]", sample)),
        "he": len(re.findall(r"[\u0590-\u05ff]", sample)),
        "latin": len(re.findall(r"[A-Za-z]", sample)),
    }
    total_letters = sum(counts.values()) or 1
    if counts["ja_kana"] >= 4 or (counts["ja_kana"] >= 2 and counts["ja_kanji"] >= 2):
        return "ja"
    if counts["ko"] >= 4:
        return "ko"
    if counts["ja_kanji"] >= 6 and counts["ja_kana"] == 0 and counts["ko"] == 0:
        return "zh"
    if counts["ar"] >= 4:
        return "ar"
    if counts["ru"] >= 4:
        return "ru"
    if counts["hi"] >= 4:
        return "hi"
    if counts["th"] >= 4:
        return "th"
    if counts["he"] >= 4:
        return "he"
    # Dominant non-Latin script even with smaller counts.
    for key, code in (
        ("ja_kana", "ja"),
        ("ko", "ko"),
        ("ar", "ar"),
        ("ru", "ru"),
        ("hi", "hi"),
        ("th", "th"),
        ("he", "he"),
    ):
        if counts[key] >= 2 and counts[key] / total_letters >= 0.35:
            return code
    return None


def infer_language_hint(*parts: str) -> str | None:
    """Guess a Whisper language code from titles / artist names when Auto is selected."""
    blob = " ".join(str(p or "") for p in parts)
    if not blob.strip():
        return None
    lower = blob.lower()

    for pattern, code in _EXPLICIT_LANGUAGE_TAGS:
        if pattern.search(blob):
            return code

    script = script_language_evidence(blob)
    if script:
        return script

    hits = _SWAHILI_TITLE_CUES.findall(blob)
    if len({h.lower() for h in hits}) >= 2 or "ipyana" in lower:
        return "sw"

    # Latin-letter titles default to English so Auto does not drift to a wrong CJK guess.
    latin = re.findall(r"[A-Za-z]", blob)
    if len(latin) >= 3:
        return "en"
    return None


def looks_like_wrong_language_lyrics(text: str, expected_language: str | None) -> bool:
    """Detect when ASR text clearly does not match the language we expected from the title."""
    expected = (expected_language or "").lower()
    if not expected:
        return False

    evidence = script_language_evidence(text)
    if evidence and evidence != expected:
        return True

    if expected == "en":
        # Forced/expected English but the transcript is dominated by another script.
        return evidence in {"ja", "zh", "ko", "ar", "ru", "hi", "th", "he"}

    if expected not in {"sw", "yo", "ha", "ig", "am", "zu"}:
        return False
    tokens = re.findall(r"[A-Za-z']+", text or "")
    if len(tokens) < 12:
        return False
    english_hits = sum(1 for token in tokens if token.lower() in _COMMON_ENGLISH)
    ratio = english_hits / len(tokens)
    swahili_hits = len(_SWAHILI_TITLE_CUES.findall(text or ""))
    return ratio >= 0.28 and swahili_hits < 3


def choose_transcription_language(
    name_language: str | None,
    opening_text: str = "",
    opening_detected: str | None = None,
) -> str | None:
    """
    Prefer the language implied by the audio/project name.
    Only switch when the opening transcript is pretty clearly another language.
    """
    from app.services.openai_transcription import normalize_language_code

    name_lang = normalize_language_code(name_language)
    audio_lang = normalize_language_code(opening_detected)
    evidence = script_language_evidence(opening_text or "")

    if name_lang:
        # Strong written-script evidence in the opening beats a Latin title.
        if evidence and evidence != name_lang:
            return evidence
        if (
            audio_lang
            and audio_lang != name_lang
            and evidence == audio_lang
            and looks_like_wrong_language_lyrics(opening_text, name_lang)
        ):
            return audio_lang
        return name_lang

    return evidence or audio_lang or None


def parse_artist_title(project_name: str) -> Tuple[str, str]:
    """Split names like 'Justin Timberlake - Mirrors' into artist + title."""
    name = clean_title_fragment(project_name)
    if not name:
        return "", ""

    by_match = re.split(r"\s+by\s+", name, maxsplit=1, flags=re.IGNORECASE)
    if len(by_match) == 2 and all(part.strip() for part in by_match):
        title, artist = clean_title_fragment(by_match[0]), clean_title_fragment(by_match[1])
        return artist, title

    for pattern in (re.compile(r"\s+[-–—]\s+"), re.compile(r"\s+[|]\s+")):
        parts = pattern.split(name, maxsplit=1)
        if len(parts) == 2 and all(parts):
            left, right = clean_title_fragment(parts[0]), clean_title_fragment(parts[1])
            # "Artist - Title" is the usual order when the left side looks like a person/band.
            if len(left.split()) <= 5:
                return left, right
            return right, left
    return "", name


def _duration_score(candidate_duration: float, song_duration: float) -> float:
    try:
        candidate_duration = float(candidate_duration or 0)
    except (TypeError, ValueError):
        candidate_duration = 0.0
    if song_duration <= 0 or candidate_duration <= 0:
        return 0.25
    delta = abs(candidate_duration - float(song_duration))
    if delta <= 3:
        return 1.0
    if delta <= 10:
        return 0.9
    if delta <= 25:
        return 0.72
    if delta <= 45:
        return 0.4
    if delta <= 90:
        return 0.15
    return 0.02


def _name_score(candidate: Dict[str, Any], artist: str, title: str, query: str) -> float:
    c_title = clean_title_fragment(candidate.get("trackName") or "").lower()
    c_artist = clean_title_fragment(candidate.get("artistName") or "").lower()
    title_l = title.lower()
    artist_l = artist.lower()
    query_l = clean_title_fragment(query).lower()
    # Strip duplicated artist prefixes like "Justin Timberlake - Mirrors"
    if " - " in c_title:
        maybe_artist, maybe_title = c_title.split(" - ", 1)
        if maybe_title:
            c_title = maybe_title.strip()
            if not c_artist:
                c_artist = maybe_artist.strip()
    score = 0.0
    if title_l and c_title == title_l:
        score += 0.55
    elif title_l and (title_l in c_title or c_title in title_l):
        score += 0.4
    elif query_l and query_l in c_title:
        score += 0.3
    if artist_l and c_artist == artist_l:
        score += 0.4
    elif artist_l and (artist_l in c_artist or c_artist in artist_l):
        score += 0.28
    elif not artist_l and query_l and query_l in f"{c_artist} {c_title}":
        score += 0.12
    if candidate.get("syncedLyrics"):
        score += 0.08
    elif candidate.get("plainLyrics"):
        score += 0.03
    return min(1.0, score)


def _http_get(url: str, timeout: float = 12.0) -> Any:
    response = requests.get(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=timeout,
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()
    if not response.content:
        return None
    return response.json()


def search_lrclib(
    query: str = "",
    track_name: str = "",
    artist_name: str = "",
) -> List[Dict[str, Any]]:
    params = []
    if track_name:
        params.append(f"track_name={quote(track_name)}")
    if artist_name:
        params.append(f"artist_name={quote(artist_name)}")
    if query and not (track_name or artist_name):
        params.append(f"q={quote(query)}")
    if not params and query:
        params.append(f"q={quote(query)}")
    if not params:
        return []
    url = f"{LRCLIB_BASE}/search?{'&'.join(params)}"
    try:
        data = _http_get(url)
    except Exception as exc:
        logger.warning("LRCLIB search failed: %s", exc)
        return []
    if not isinstance(data, list):
        return []
    return [row for row in data if isinstance(row, dict)]


def rank_candidates(
    candidates: List[Dict[str, Any]],
    *,
    artist: str,
    title: str,
    query: str,
    duration: float,
) -> List[Tuple[float, Dict[str, Any]]]:
    ranked = []
    for candidate in candidates:
        if not (candidate.get("syncedLyrics") or candidate.get("plainLyrics")):
            continue
        name = _name_score(candidate, artist, title, query)
        dur = _duration_score(candidate.get("duration"), duration)
        # Exact title + close duration can win even without an artist in the project name.
        if name >= 0.55 and dur >= 0.72:
            score = 0.35 * name + 0.65 * dur
        elif artist:
            score = 0.55 * name + 0.45 * dur
        else:
            score = 0.4 * name + 0.6 * dur
        ranked.append((score, candidate))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked


def identify_song_with_ai(
    openai_client,
    *,
    project_name: str,
    opening_lyrics: str = "",
    duration: float = 0,
    candidates: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Dict[str, str]]:
    """Ask the language model which commercial track this audio is."""
    if not openai_client:
        return None
    candidate_lines = []
    for row in (candidates or [])[:8]:
        candidate_lines.append(
            f"- {row.get('artistName', '')} — {row.get('trackName', '')} "
            f"(~{int(float(row.get('duration') or 0))}s)"
        )
    prompt = (
        "Identify the song from the project title and optional opening lyric snippet. "
        "Return ONLY compact JSON with keys artist, title, confidence (0-1). "
        "If unknown, return {\"artist\":\"\",\"title\":\"\",\"confidence\":0}."
    )
    user = (
        f"Project title: {project_name}\n"
        f"Audio duration seconds: {int(duration or 0)}\n"
        f"Opening lyrics hint:\n{(opening_lyrics or '')[:500]}\n"
    )
    if candidate_lines:
        user += "Catalog candidates:\n" + "\n".join(candidate_lines)
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user},
            ],
            max_tokens=120,
            temperature=0,
            response_format={"type": "json_object"},
        )
        raw = (response.choices[0].message.content or "").strip()
        data = json.loads(raw)
        artist = clean_title_fragment(data.get("artist", ""))
        title = clean_title_fragment(data.get("title", ""))
        confidence = float(data.get("confidence") or 0)
        if confidence < 0.55 or not title:
            return None
        return {"artist": artist, "title": title, "confidence": confidence}
    except Exception as exc:
        logger.warning("AI song identification failed: %s", exc)
        return None


def fetch_known_lyrics_with_ai(
    openai_client,
    *,
    artist: str,
    title: str,
    language_hint: str | None = None,
    opening_lyrics: str = "",
) -> Optional[Dict[str, Any]]:
    """Ask the model for published lyrics only when it truly knows the song."""
    if not openai_client or not title:
        return None
    system = (
        "You recall published song lyrics when you are sure they are correct. "
        "Return JSON with keys: known (boolean), language (ISO 639-1 when possible), "
        "lyrics (plain text, one line per lyric line), confidence (0-1). "
        "If you are not sure of the exact lyrics, set known=false and lyrics=\"\". "
        "Never invent, translate, or paraphrase. Keep the original language."
    )
    user = (
        f"Artist: {artist or 'Unknown'}\n"
        f"Title: {title}\n"
        f"Language hint: {language_hint or 'auto'}\n"
        f"Opening lyric snippet from audio (may be noisy):\n{(opening_lyrics or '')[:400]}"
    )
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=2500,
            temperature=0,
            response_format={"type": "json_object"},
        )
        data = json.loads((response.choices[0].message.content or "").strip())
        if not data.get("known"):
            return None
        lyrics = str(data.get("lyrics") or "").strip()
        confidence = float(data.get("confidence") or 0)
        if confidence < 0.7 or len(lyrics.splitlines()) < 4:
            return None
        if opening_lyrics and not _opening_agrees_with_lyrics(opening_lyrics, lyrics):
            return None
        return {
            "artist": artist,
            "title": title,
            "album": "",
            "lyrics_text": lyrics,
            "synced": False,
            "source": "openai-catalog",
            "external_id": None,
            "confidence": round(confidence, 3),
            "duration": 0,
            "instrumental": False,
            "identified_by": "openai-lyrics",
            "language": data.get("language") or language_hint or "",
        }
    except Exception as exc:
        logger.warning("AI known-lyrics fetch failed: %s", exc)
        return None


def _opening_agrees_with_lyrics(opening: str, lyrics: str) -> bool:
    """Require a little lexical overlap so we don't keep a wrong song's lyrics."""
    open_tokens = {t.lower() for t in re.findall(r"\w+", opening or "", flags=re.UNICODE) if len(t) > 2}
    lyric_tokens = {t.lower() for t in re.findall(r"\w+", lyrics or "", flags=re.UNICODE) if len(t) > 2}
    if not open_tokens or not lyric_tokens:
        return True
    overlap = len(open_tokens & lyric_tokens)
    if overlap >= 3:
        return True
    english_open = sum(1 for t in open_tokens if t in _COMMON_ENGLISH) / max(1, len(open_tokens))
    # If opening is mostly English garbage, don't use it to reject good lyrics.
    if english_open >= 0.35:
        return True
    return overlap >= 2


def _result_from_candidate(candidate: Dict[str, Any], confidence: float) -> Dict[str, Any]:
    synced = (candidate.get("syncedLyrics") or "").strip()
    plain = (candidate.get("plainLyrics") or "").strip()
    lyrics_text = synced or plain
    try:
        duration = float(candidate.get("duration") or 0)
    except (TypeError, ValueError):
        duration = 0.0
    return {
        "artist": clean_title_fragment(candidate.get("artistName") or ""),
        "title": clean_title_fragment(candidate.get("trackName") or ""),
        "album": clean_title_fragment(candidate.get("albumName") or ""),
        "lyrics_text": lyrics_text,
        "synced": bool(synced),
        "source": "lrclib",
        "external_id": candidate.get("id"),
        "confidence": round(float(confidence), 3),
        "duration": duration,
        "instrumental": bool(candidate.get("instrumental")),
    }


def lookup_known_song(
    project_name: str,
    duration: float = 0,
    *,
    openai_client=None,
    opening_lyrics: str = "",
    min_confidence: float = 0.62,
    language_hint: str | None = None,
) -> Optional[Dict[str, Any]]:
    """Return known lyrics when the catalog match is strong enough."""
    from app.services.known_lyrics_pack import lookup_local_lyrics

    artist, title = parse_artist_title(project_name)
    query = clean_title_fragment(project_name)
    language_hint = language_hint or infer_language_hint(project_name, artist, title)
    if not query and not title:
        return None

    # Local pack wins for songs ASR routinely destroys (e.g. Swahili gospel).
    local = lookup_local_lyrics(project_name, artist=artist, title=title)
    if local:
        return local

    candidates: List[Dict[str, Any]] = []
    if artist and title:
        candidates.extend(search_lrclib(track_name=title, artist_name=artist))
        candidates.extend(search_lrclib(query=f"{artist} {title}"))
    if title:
        candidates.extend(search_lrclib(track_name=title))
        candidates.extend(search_lrclib(query=title))
    if artist:
        candidates.extend(search_lrclib(query=artist))
    if query and query.lower() not in {(title or "").lower(), f"{artist} {title}".strip().lower()}:
        candidates.extend(search_lrclib(query=query))

    seen = set()
    unique = []
    for row in candidates:
        key = row.get("id") or f"{row.get('artistName')}|{row.get('trackName')}|{row.get('duration')}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)

    ranked = rank_candidates(unique, artist=artist, title=title or query, query=query, duration=duration)
    if ranked and ranked[0][0] >= min_confidence:
        result = _result_from_candidate(ranked[0][1], ranked[0][0])
        if opening_lyrics and not _opening_agrees_with_lyrics(opening_lyrics, result["lyrics_text"]):
            logger.info("Rejected catalog hit that did not match opening lyrics: %s", result.get("title"))
        else:
            return result

    identified = identify_song_with_ai(
        openai_client,
        project_name=project_name,
        opening_lyrics=opening_lyrics,
        duration=duration,
        candidates=[row for _, row in ranked[:8]] or unique[:8],
    )
    if identified:
        artist = identified.get("artist") or artist
        title = identified.get("title") or title
        local = lookup_local_lyrics(project_name, artist=artist, title=title)
        if local:
            local["identified_by"] = "openai+local-pack"
            return local
        retry = search_lrclib(track_name=title, artist_name=artist) if artist else search_lrclib(query=title)
        if not retry and title:
            retry = search_lrclib(query=f"{artist} {title}".strip())
        ranked_retry = rank_candidates(
            retry,
            artist=artist or "",
            title=title or "",
            query=f"{artist} {title}".strip(),
            duration=duration,
        )
        if ranked_retry and ranked_retry[0][0] >= max(0.55, min_confidence - 0.05):
            result = _result_from_candidate(ranked_retry[0][1], ranked_retry[0][0])
            if not opening_lyrics or _opening_agrees_with_lyrics(opening_lyrics, result["lyrics_text"]):
                result["identified_by"] = "openai"
                return result

    if artist and title and openai_client:
        ai_lyrics = fetch_known_lyrics_with_ai(
            openai_client,
            artist=artist,
            title=title,
            language_hint=language_hint,
            opening_lyrics=opening_lyrics,
        )
        if ai_lyrics:
            return ai_lyrics

    return None
