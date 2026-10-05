from io import BytesIO

from PIL import Image

from app.services.ai_background import (
    AI_THEME_ID,
    _lyrics_excerpt,
    fit_to_canvas,
    image_api_size,
)
from app.services.theme_catalog import get_theme, public_theme_payload


def test_ai_theme_is_in_catalog():
    theme = get_theme(AI_THEME_ID)
    assert theme is not None
    payload = public_theme_payload(theme)
    assert payload["is_ai"] is True
    assert payload["media_type"] == "image"


def test_image_api_size_maps_aspect_ratios():
    assert image_api_size("16:9") == "1536x1024"
    assert image_api_size("9:16") == "1024x1536"
    assert image_api_size("1:1") == "1024x1024"
    assert image_api_size("4:5") == "1024x1536"


def test_lyrics_excerpt_keeps_readable_lines():
    lyrics = [{"text": f"Line {i} of the song"} for i in range(40)]
    excerpt = _lyrics_excerpt(lyrics, limit=120)
    assert "Line 0" in excerpt
    assert len(excerpt) <= 130


def test_fit_to_canvas_cover_crops():
    src = Image.new("RGB", (800, 400), (20, 40, 80))
    buf = BytesIO()
    src.save(buf, format="PNG")
    out = fit_to_canvas(buf.getvalue(), 640, 360)
    assert out.size == (640, 360)
