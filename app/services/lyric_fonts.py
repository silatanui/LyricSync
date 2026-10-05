"""
Resolve studio font names for ASS/libass burn-in and ensure TTF files exist
in a local fonts directory (downloaded from Fontsource on first use).
"""
from __future__ import annotations

import logging
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, Optional, Tuple

from config import Config

logger = logging.getLogger(__name__)

# UI picker name → (ASS Fontname, fontsource slug or None for system fonts)
_FONT_CATALOG: Dict[str, Tuple[str, Optional[str]]] = {
    "Caveat": ("Caveat", "caveat"),
    "Anton": ("Anton", "anton"),
    "Arial": ("Arial", None),
    "Avenir": ("Arial", None),
    "Baskerville": ("Libre Baskerville", "libre-baskerville"),
    "Bebas Neue": ("Bebas Neue", "bebas-neue"),
    "Bodoni": ("Bodoni Moda", "bodoni-moda"),
    "Cinzel": ("Cinzel", "cinzel"),
    "Cormorant Garamond": ("Cormorant Garamond", "cormorant-garamond"),
    "Courier New": ("Courier New", None),
    "DM Sans": ("DM Sans", "dm-sans"),
    "Estelle": ("Great Vibes", "great-vibes"),
    "Futura": ("Trebuchet MS", None),
    "Garamond": ("EB Garamond", "eb-garamond"),
    "Great Vibes": ("Great Vibes", "great-vibes"),
    "Georgia": ("Georgia", None),
    "Helvetica Neue": ("Arial", None),
    "Inter": ("Inter", "inter"),
    "ITC Century": ("Georgia", None),
    "Lato": ("Lato", "lato"),
    "League Spartan": ("League Spartan", "league-spartan"),
    "Libre Baskerville": ("Libre Baskerville", "libre-baskerville"),
    "Merriweather": ("Merriweather", "merriweather"),
    "Minion Pro": ("EB Garamond", "eb-garamond"),
    "Montserrat": ("Montserrat", "montserrat"),
    "Nunito": ("Nunito", "nunito"),
    "Open Sans": ("Open Sans", "open-sans"),
    "Oswald": ("Oswald", "oswald"),
    "Outfit": ("Outfit", "outfit"),
    "Playfair Display": ("Playfair Display", "playfair-display"),
    "Poppins": ("Poppins", "poppins"),
    "Proxima Nova": ("Montserrat", "montserrat"),
    "PT Sans": ("PT Sans", "pt-sans"),
    "Raleway": ("Raleway", "raleway"),
    "Roboto": ("Roboto", "roboto"),
    "Source Sans Pro": ("Source Sans 3", "source-sans-3"),
    "Times New Roman": ("Times New Roman", None),
    "Trebuchet MS": ("Trebuchet MS", None),
    "Ubuntu": ("Ubuntu", "ubuntu"),
    "Univers": ("Arial", None),
}

_WEIGHT_CANDIDATES = (400, 500, 600, 700, 800)


def get_fonts_dir() -> Path:
    fonts_dir = getattr(Config, "FONTS_ROOT", None)
    if fonts_dir is None:
        fonts_dir = Config.DATA_ROOT / "fonts"
    path = Path(fonts_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_ass_font_name(ui_name: str) -> str:
    key = (ui_name or "Caveat").strip()
    entry = _FONT_CATALOG.get(key)
    if entry:
        return entry[0]
    return key


def _nearest_weight(weight: int) -> int:
    try:
        w = int(weight)
    except (TypeError, ValueError):
        w = 600
    return min(_WEIGHT_CANDIDATES, key=lambda c: abs(c - w))


def _fontsource_url(slug: str, weight: int, italic: bool) -> str:
    style = "italic" if italic else "normal"
    return (
        f"https://cdn.jsdelivr.net/fontsource/fonts/{slug}@latest/"
        f"latin-{weight}-{style}.ttf"
    )


def _download_font(url: str, dest: Path) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "LyricSyncStudio/1.0"})
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = resp.read()
        if len(data) < 1000:
            return False
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".tmp")
        tmp.write_bytes(data)
        tmp.replace(dest)
        return True
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
        logger.warning("Font download failed (%s): %s", url, exc)
        return False


def ensure_font_files(ui_name: str, font_weight: int = 600, font_style: str = "normal") -> Path:
    """
    Ensure the selected family is available under fontsdir for libass.
    Returns the fonts directory (always), even when relying on system fonts.
    """
    fonts_dir = get_fonts_dir()
    key = (ui_name or "Caveat").strip()
    entry = _FONT_CATALOG.get(key)
    if not entry or not entry[1]:
        return fonts_dir

    slug = entry[1]
    weight = _nearest_weight(font_weight)
    italic = str(font_style or "").lower() == "italic"
    style_tag = "italic" if italic else "normal"
    dest = fonts_dir / f"{slug}-{weight}-{style_tag}.ttf"

    if dest.exists() and dest.stat().st_size > 1000:
        return fonts_dir

    # Try exact weight, then fall back across candidates.
    weights_to_try = [weight] + [w for w in _WEIGHT_CANDIDATES if w != weight]
    for w in weights_to_try:
        for use_italic in ((True, False) if italic else (False,)):
            candidate = fonts_dir / f"{slug}-{w}-{'italic' if use_italic else 'normal'}.ttf"
            if candidate.exists() and candidate.stat().st_size > 1000:
                return fonts_dir
            url = _fontsource_url(slug, w, use_italic)
            if _download_font(url, candidate):
                logger.info("Cached lyric font %s → %s", key, candidate.name)
                return fonts_dir

    logger.warning("Could not cache font files for %s; libass may fall back to a system face", key)
    return fonts_dir
