"""Local overrides for songs Whisper/LRCLIB routinely get wrong.

Used for language-specific gospel and other tracks where the title is known
but public catalogs are missing or ASR invents English gibberish.
"""

from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.song_catalog import clean_title_fragment, parse_artist_title

logger = logging.getLogger(__name__)

_PACK_PATH = Path(__file__).resolve().parent.parent / "data" / "known_lyrics.json"


def _normalize_key(value: str) -> str:
    text = clean_title_fragment(value).lower()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace("dr.", "dr").replace("dr ", "dr ")
    return text


@lru_cache(maxsize=1)
def _load_pack() -> List[Dict[str, Any]]:
    if not _PACK_PATH.exists():
        return []
    try:
        data = json.loads(_PACK_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Could not load known lyrics pack: %s", exc)
        return []
    if not isinstance(data, list):
        return []
    return [row for row in data if isinstance(row, dict) and row.get("lyrics")]


def lookup_local_lyrics(project_name: str, artist: str = "", title: str = "") -> Optional[Dict[str, Any]]:
    """Return a catalog-style match when the local pack knows this song."""
    parsed_artist, parsed_title = parse_artist_title(project_name)
    artist = clean_title_fragment(artist or parsed_artist)
    title = clean_title_fragment(title or parsed_title)
    name_key = _normalize_key(project_name)
    artist_key = _normalize_key(artist)
    title_key = _normalize_key(title)
    combo_key = _normalize_key(f"{artist} {title}".strip())

    for row in _load_pack():
        row_artist = clean_title_fragment(row.get("artist") or "")
        row_title = clean_title_fragment(row.get("title") or "")
        keys = {
            _normalize_key(row_title),
            _normalize_key(f"{row_artist} {row_title}"),
            _normalize_key(f"{row_artist} - {row_title}"),
        }
        for alias in row.get("aliases") or []:
            keys.add(_normalize_key(alias))

        matched = False
        if title_key and title_key == _normalize_key(row_title):
            if not artist_key or artist_key in _normalize_key(row_artist) or _normalize_key(row_artist) in artist_key:
                matched = True
        if not matched and (name_key in keys or combo_key in keys):
            matched = True
        if not matched and title_key and title_key in keys:
            matched = True
        if not matched:
            continue

        lyrics = str(row.get("lyrics") or "").strip()
        if len(lyrics.splitlines()) < 4:
            continue
        return {
            "artist": row_artist,
            "title": row_title,
            "album": clean_title_fragment(row.get("album") or ""),
            "lyrics_text": lyrics,
            "synced": False,
            "source": "local-pack",
            "external_id": row.get("id") or f"local:{_normalize_key(row_title)}",
            "confidence": 0.99,
            "duration": float(row.get("duration") or 0),
            "instrumental": False,
            "identified_by": "local-pack",
            "language": row.get("language") or "",
        }
    return None
