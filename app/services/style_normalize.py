"""Normalize studio style payloads (camelCase UI ↔ snake_case canonical)."""
from __future__ import annotations

from typing import Any, Dict

_CAMEL_TO_SNAKE = {
    "fontSize": "font_size",
    "lineHeight": "line_height",
    "letterSpacing": "letter_spacing",
    "fontWeight": "font_weight",
    "fontStyle": "font_style",
    "effectStrength": "effect_strength",
    "primaryColor": "primary_color",
    "highlightColor": "highlight_color",
    "textAlign": "text_align",
    "textCase": "text_case",
    "outlineEnabled": "outline_enabled",
    "outlineColor": "outline_color",
    "outlineSoftness": "outline_softness",
    "shadowEnabled": "shadow_enabled",
    "shadowColor": "shadow_color",
    "shadowOpacity": "shadow_opacity",
    "shadowDistance": "shadow",
    "shadowAngle": "shadow_angle",
    "shadowBlur": "shadow_blur",
    "bevelEnabled": "bevel_enabled",
    "bevelSize": "bevel_size",
    "bevelSoftness": "bevel_softness",
    "bevelAngle": "bevel_angle",
    "bevelHighlightColor": "bevel_highlight_color",
    "bevelHighlightOpacity": "bevel_highlight_opacity",
    "bevelShadowColor": "bevel_shadow_color",
    "bevelShadowOpacity": "bevel_shadow_opacity",
    "aspectRatio": "aspect_ratio",
}


def normalize_style_payload(style_data: Dict[str, Any] | None) -> Dict[str, Any]:
    """
    Convert camelCase preview keys to snake_case canonical keys.
    Snake_case values win when both forms are present.
    """
    if not style_data:
        return {}

    out: Dict[str, Any] = {}
    deferred: Dict[str, Any] = {}

    for key, value in style_data.items():
        if key in _CAMEL_TO_SNAKE:
            deferred[_CAMEL_TO_SNAKE[key]] = value
        else:
            out[key] = value

    for key, value in deferred.items():
        # Prefer an explicit snake_case value already in the payload.
        if key not in out:
            out[key] = value

    return out
