"""Generate a lyric-aware AI background image with OpenAI (chat prompt + gpt-image)."""

from __future__ import annotations

import base64
import io
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI
from PIL import Image

from config import Config

logger = logging.getLogger(__name__)

AI_THEME_ID = "ai_lyric_scene"

_PROMPT_SYSTEM = (
    "You design cinematic lyric-video backgrounds. Given a song title, artist, and lyrics, "
    "write ONE detailed image-generation prompt (120-220 words) for a still backdrop. "
    "Describe mood, lighting, color palette, setting, atmosphere, and composition that fit the song. "
    "Leave the center and lower-third relatively clean for overlaid lyrics (soft bokeh / negative space). "
    "No text, logos, watermarks, UI, or readable lettering in the image. "
    "No celebrities or real people faces unless the lyrics clearly require silhouettes. "
    "Return ONLY the prompt text."
)

_USER_DRAFT_SYSTEM = (
    "You expand a user's short scene brief into ONE detailed image-generation prompt "
    "(120-220 words) for a lyric-video backdrop. Preserve their subject, mood, palette, "
    "and setting — do not invent a different concept. "
    "Leave the center and lower-third relatively clean for overlaid lyrics "
    "(soft bokeh / negative space). "
    "No text, logos, watermarks, UI, or readable lettering in the image. "
    "No celebrities or real people faces unless the brief clearly asks for silhouettes. "
    "Return ONLY the prompt text."
)

_SAFETY_SUFFIX = (
    "Widescreen cinematic composition, high detail, mood-matched to the song, "
    "no text, no watermark, no UI, no captions."
)

USER_PROMPT_MIN_CHARS = 8
USER_PROMPT_MAX_CHARS = 1200


def sanitize_user_prompt(user_prompt: str | None) -> str:
    """Normalize a user-drafted scene brief for image generation."""
    draft = re.sub(r"\s+", " ", str(user_prompt or "")).strip()
    return draft[:USER_PROMPT_MAX_CHARS]


def _client() -> OpenAI:
    key = Config.OPENAI_API_KEY
    if not key or key in ("mock", "replace-this", ""):
        raise RuntimeError("OpenAI API key is not configured.")
    return OpenAI(api_key=key, timeout=180.0)


def _chat_model() -> str:
    return getattr(Config, "OPENAI_CHAT_MODEL", None) or "gpt-4o-mini"


def _image_model() -> str:
    return getattr(Config, "OPENAI_IMAGE_MODEL", None) or "gpt-image-1"


def _lyrics_excerpt(lyrics: List[Dict[str, Any]], limit: int = 1800) -> str:
    lines = []
    for row in lyrics or []:
        text = re.sub(r"\s+", " ", str(row.get("text") or "")).strip()
        if text:
            lines.append(text)
    blob = "\n".join(lines).strip()
    if len(blob) > limit:
        blob = blob[:limit].rsplit("\n", 1)[0] + "\n…"
    return blob


def build_scene_prompt(
    *,
    title: str,
    artist: str = "",
    lyrics: Optional[List[Dict[str, Any]]] = None,
    language: str = "",
    client: Optional[OpenAI] = None,
) -> str:
    """Ask a compatible chat model for a rich visual brief grounded in the lyrics."""
    api = client or _client()
    lyric_text = _lyrics_excerpt(lyrics or [])
    user_bits = [
        f"Song title: {title or 'Untitled'}",
        f"Artist: {artist or 'Unknown'}",
    ]
    if language:
        user_bits.append(f"Language: {language}")
    if lyric_text:
        user_bits.append(f"Lyrics:\n{lyric_text}")
    else:
        user_bits.append(
            "Lyrics are not available yet. Infer a tasteful cinematic mood from the title and artist only."
        )
    user_bits.append(
        "Style: photoreal or painterly cinematic still suitable as a full-bleed lyric video background."
    )

    response = api.chat.completions.create(
        model=_chat_model(),
        messages=[
            {"role": "system", "content": _PROMPT_SYSTEM},
            {"role": "user", "content": "\n".join(user_bits)},
        ],
        max_tokens=420,
        temperature=0.75,
    )
    prompt = (response.choices[0].message.content or "").strip().strip('"')
    if not prompt or len(prompt) < 40:
        prompt = (
            f"Cinematic lyric-video backdrop for the song '{title or 'Untitled'}' "
            f"by {artist or 'an unknown artist'}: atmospheric lighting, rich color grading, "
            "soft depth of field, clean center space for lyrics, no text or logos."
        )
    # Hard constraints appended so the image model stays lyric-safe.
    prompt = f"{prompt} {_SAFETY_SUFFIX}"
    return prompt[:2200]


def build_user_draft_prompt(
    *,
    user_prompt: str,
    title: str = "",
    artist: str = "",
    client: Optional[OpenAI] = None,
) -> str:
    """Expand a user-written scene brief into a safe image-generation prompt."""
    draft = sanitize_user_prompt(user_prompt)
    if len(draft) < USER_PROMPT_MIN_CHARS:
        raise ValueError(
            f"Describe the scene you want in at least {USER_PROMPT_MIN_CHARS} characters."
        )

    api = client or _client()
    user_bits = [
        f"Song title (optional context): {title or 'Untitled'}",
        f"Artist (optional context): {artist or 'Unknown'}",
        f"User scene brief:\n{draft}",
        "Style: photoreal or painterly cinematic still suitable as a full-bleed lyric video background.",
    ]
    try:
        response = api.chat.completions.create(
            model=_chat_model(),
            messages=[
                {"role": "system", "content": _USER_DRAFT_SYSTEM},
                {"role": "user", "content": "\n".join(user_bits)},
            ],
            max_tokens=420,
            temperature=0.7,
        )
        prompt = (response.choices[0].message.content or "").strip().strip('"')
    except Exception as exc:
        logger.warning("User-draft prompt polish failed (%s); using raw brief", exc)
        prompt = ""

    if not prompt or len(prompt) < 40:
        prompt = (
            f"{draft}. Cinematic lyric-video backdrop for '{title or 'Untitled'}' "
            f"by {artist or 'an unknown artist'}: atmospheric lighting, rich color grading, "
            "soft depth of field, clean center space for lyrics, no text or logos."
        )
    prompt = f"{prompt} {_SAFETY_SUFFIX}"
    return prompt[:2200]


def image_api_size(aspect_ratio: str) -> str:
    """Reasonable OpenAI image sizes mapped from studio aspect ratios."""
    ar = (aspect_ratio or "16:9").strip()
    if ar == "9:16":
        return "1024x1536"
    if ar in ("1:1", "4:5"):
        return "1024x1024" if ar == "1:1" else "1024x1536"
    return "1536x1024"


def _decode_image_bytes(result) -> bytes:
    data = result.data[0]
    b64 = getattr(data, "b64_json", None) or (data.get("b64_json") if isinstance(data, dict) else None)
    if b64:
        return base64.b64decode(b64)
    url = getattr(data, "url", None) or (data.get("url") if isinstance(data, dict) else None)
    if url:
        import urllib.request
        with urllib.request.urlopen(url, timeout=90) as resp:
            return resp.read()
    raise RuntimeError("Image API returned no image payload.")


def generate_image_bytes(prompt: str, aspect_ratio: str = "16:9", client: Optional[OpenAI] = None) -> Tuple[bytes, str, str]:
    """
    Generate image bytes via gpt-image (preferred) with dall-e-3 fallback.
    Returns (bytes, model_used, api_size).
    """
    api = client or _client()
    size = image_api_size(aspect_ratio)
    model = _image_model()

    try:
        kwargs = {
            "model": model,
            "prompt": prompt,
            "n": 1,
            "size": size,
        }
        # gpt-image family prefers quality; dall-e-3 uses different values.
        if str(model).startswith("gpt-image") or str(model).startswith("chatgpt-image"):
            kwargs["quality"] = getattr(Config, "OPENAI_IMAGE_QUALITY", None) or "medium"
        result = api.images.generate(**kwargs)
        return _decode_image_bytes(result), model, size
    except Exception as primary_err:
        logger.warning("Primary image model %s failed (%s); trying dall-e-3", model, primary_err)
        dalle_size = {
            "1536x1024": "1792x1024",
            "1024x1536": "1024x1792",
            "1024x1024": "1024x1024",
        }.get(size, "1792x1024")
        result = api.images.generate(
            model="dall-e-3",
            prompt=prompt[:3900],
            n=1,
            size=dalle_size,
            quality="standard",
            response_format="b64_json",
        )
        return _decode_image_bytes(result), "dall-e-3", dalle_size


def fit_to_canvas(image_bytes: bytes, width: int, height: int) -> Image.Image:
    """Cover-crop the generated image onto the project canvas size."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    src_w, src_h = img.size
    if src_w <= 0 or src_h <= 0:
        raise RuntimeError("Generated image has invalid dimensions.")
    scale = max(width / src_w, height / src_h)
    new_w = max(1, int(round(src_w * scale)))
    new_h = max(1, int(round(src_h * scale)))
    resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    left = max(0, (new_w - width) // 2)
    top = max(0, (new_h - height) // 2)
    return resized.crop((left, top, left + width, top + height))


def generate_ai_background(
    *,
    output_path: Path,
    title: str,
    artist: str = "",
    lyrics: Optional[List[Dict[str, Any]]] = None,
    language: str = "",
    aspect_ratio: str = "16:9",
    width: int = 1920,
    height: int = 1080,
    user_prompt: str | None = None,
) -> Dict[str, Any]:
    """
    Build a scene prompt (from lyrics or a user draft), generate an image,
    and save a WebP still sized for the project canvas.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    client = _client()
    draft = sanitize_user_prompt(user_prompt)
    if draft:
        scene_prompt = build_user_draft_prompt(
            user_prompt=draft,
            title=title,
            artist=artist,
            client=client,
        )
        prompt_source = "user_draft"
    else:
        scene_prompt = build_scene_prompt(
            title=title,
            artist=artist,
            lyrics=lyrics,
            language=language,
            client=client,
        )
        prompt_source = "lyrics"
    raw_bytes, model_used, api_size = generate_image_bytes(
        scene_prompt,
        aspect_ratio=aspect_ratio,
        client=client,
    )
    canvas = fit_to_canvas(raw_bytes, int(width), int(height))
    # Reasonable web-friendly still for studio + export (not a multi‑MB PNG).
    canvas.save(output_path, format="WEBP", quality=88, method=4)

    return {
        "path": str(output_path.resolve()),
        "prompt": scene_prompt,
        "user_prompt": draft or None,
        "prompt_source": prompt_source,
        "model": model_used,
        "chat_model": _chat_model(),
        "api_size": api_size,
        "width": int(width),
        "height": int(height),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "theme_id": AI_THEME_ID,
    }
