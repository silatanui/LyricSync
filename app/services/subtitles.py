import math
from typing import Dict, Any, List
from pathlib import Path

from app.services.lyric_fonts import resolve_ass_font_name
from app.services.style_normalize import normalize_style_payload


def hex_to_ass_color(hex_str: str, alpha: str = "00") -> str:
    """
    Convert CSS hex color '#RRGGBB' to ASS color format '&HAABBGGRR'.
    """
    hex_clean = hex_str.lstrip("#")
    if len(hex_clean) == 3:
        hex_clean = "".join([c * 2 for c in hex_clean])
    if len(hex_clean) != 6:
        return f"&H{alpha}FFFFFF&"
    r = hex_clean[0:2]
    g = hex_clean[2:4]
    b = hex_clean[4:6]
    return f"&H{alpha}{b.upper()}{g.upper()}{r.upper()}&"

def format_ass_time(seconds: float) -> str:
    """Format seconds into ASS timestamp H:MM:SS.cs (centiseconds)."""
    seconds = max(0.0, seconds)
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 99
    return f"{hrs}:{mins:02d}:{secs:02d}.{cs:02d}"

def format_srt_time(seconds: float) -> str:
    """Format seconds into SRT timestamp HH:MM:SS,mmm."""
    seconds = max(0.0, seconds)
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    if ms >= 1000:
        ms = 999
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{ms:03d}"

def format_vtt_time(seconds: float) -> str:
    """Format seconds into WebVTT timestamp HH:MM:SS.mmm."""
    return format_srt_time(seconds).replace(",", ".")


def escape_ass_text(text: str) -> str:
    return (
        str(text or "")
        .replace("\\", "\\\\")
        .replace("{", "\\{")
        .replace("}", "\\}")
        .replace("\n", "\\N")
    )


def apply_text_case(text: str, text_case: str) -> str:
    """Apply studio capitalization mode to lyric / word text."""
    raw = str(text or "")
    mode = (text_case or "as_is").lower()
    if mode == "upper":
        return raw.upper()
    if mode == "lower":
        return raw.lower()
    if mode == "title":
        return raw.title()
    return raw


def preview_reference_width(aspect_ratio: str) -> float:
    """Approximate studio preview canvas width (CSS) for export scale matching."""
    return {
        "9:16": 420.0,
        "1:1": 560.0,
        "4:5": 480.0,
        "16:9": 900.0,
    }.get(aspect_ratio or "16:9", 900.0)


def export_size_scale(aspect_ratio: str, play_res_x: int) -> float:
    """Scale UI font sizes up to full PlayRes so export matches studio proportions."""
    ref = preview_reference_width(aspect_ratio)
    if ref <= 0:
        return 1.0
    # Preview canvas is much narrower than export PlayRes; scale so burned-in
    # lyrics read at a similar visual weight to the studio preview on a full display.
    return max(1.0, float(play_res_x) / ref) * 1.85


def split_song_credit(full_title: str) -> tuple[str, str]:
    raw = (full_title or "").strip()
    if not raw:
        return "", ""
    for sep in (" - ", " – ", " — "):
        if sep in raw:
            left, right = raw.split(sep, 1)
            left, right = left.strip(), right.strip()
            if left and right:
                return left, right
    return "", raw


class SubtitleGenerator:
    @staticmethod
    def _chunk_lyrics(lyrics: List[Dict[str, Any]], format_type: str) -> List[List[Dict[str, Any]]]:
        """Groups lyrics lines into chunks based on format (stanza=4 lines, sentence=2 lines, line=1 line)."""
        if not lyrics:
            return []
        if format_type == "stanza":
            chunk_size = 4
        elif format_type == "sentence":
            chunk_size = 2
        else:
            chunk_size = 1

        chunks = []
        current_chunk = []
        for line in lyrics:
            if current_chunk and len(current_chunk) >= chunk_size:
                chunks.append(current_chunk)
                current_chunk = []
            current_chunk.append(line)
        if current_chunk:
            chunks.append(current_chunk)
        return chunks

    @staticmethod
    def generate_ass(canonical_data: Dict[str, Any], output_path: Path) -> Path:
        """
        Generates an ASS subtitle file from canonical JSON project data.
        Supports Whole Stanza, Sentence Couplet, and Single Line formats.
        """
        style_cfg = normalize_style_payload(canonical_data.get("style", {}) or {})
        ui_font = style_cfg.get("font", "Caveat")
        font_name = resolve_ass_font_name(ui_font)
        ui_font_size = int(style_cfg.get("font_size", 36) or 36)
        font_weight = int(style_cfg.get("font_weight", 600) or 600)
        font_style = str(style_cfg.get("font_style", "normal") or "normal").lower()
        text_case = str(style_cfg.get("text_case", "as_is") or "as_is").lower()
        letter_spacing_em = float(style_cfg.get("letter_spacing", 0) or 0)
        bold_flag = -1 if font_weight >= 600 else 0
        italic_flag = -1 if font_style == "italic" else 0
        effect = str(style_cfg.get("effect", "none") or "none").lower()
        effect_strength = max(0.0, min(1.0, float(style_cfg.get("effect_strength", 0.7) or 0.7)))
        primary_hex = style_cfg.get("primary_color", "#FFFFFF")
        highlight_hex = style_cfg.get("highlight_color", "#10B981")
        outline_enabled = style_cfg.get("outline_enabled", True)
        ui_outline = int(style_cfg.get("outline", 2) or 0) if outline_enabled else 0
        outline_hex = style_cfg.get("outline_color", "#000000")
        shadow_enabled = style_cfg.get("shadow_enabled", True)
        ui_shadow_distance = float(style_cfg.get("shadow", 3) or 0)
        shadow_hex = style_cfg.get("shadow_color", "#000000")
        shadow_opacity = max(0, min(100, int(style_cfg.get("shadow_opacity", 70) or 0)))
        shadow_angle = float(style_cfg.get("shadow_angle", 45) or 45)
        bevel_enabled = bool(style_cfg.get("bevel_enabled", False))
        ui_bevel_size = float(style_cfg.get("bevel_size", 2) or 0)
        position = style_cfg.get("position", "center")
        text_align = style_cfg.get("text_align", "center")
        mode = str(style_cfg.get("mode", "karaoke") or "karaoke").lower()
        lyrics_format = style_cfg.get("format") or canonical_data.get("render", {}).get("lyrics_format", "stanza")

        # Alignment: Numpad notation
        # Top: 7 (left), 8 (center), 9 (right)
        # Center: 4 (left), 5 (center), 6 (right)
        # Bottom: 1 (left), 2 (center), 3 (right)
        align_map = {
            ("top", "left"): 7,
            ("top", "center"): 8,
            ("top", "right"): 9,
            ("center", "left"): 4,
            ("center", "center"): 5,
            ("center", "right"): 6,
            ("bottom", "left"): 1,
            ("bottom", "center"): 2,
            ("bottom", "right"): 3,
        }
        alignment = align_map.get((position, text_align), 5)

        primary_color = hex_to_ass_color(primary_hex, "00")
        secondary_color = hex_to_ass_color(highlight_hex, "00")
        outline_color = hex_to_ass_color(outline_hex, "00")
        # ASS alpha is inverted: 00 = opaque, FF = transparent
        shadow_alpha = f"{max(0, min(255, int(round((100 - shadow_opacity) * 2.55)))):02X}"
        back_color = hex_to_ass_color(shadow_hex, shadow_alpha)

        render_cfg = canonical_data.get("render", {})
        target_aspect = render_cfg.get("aspect_ratio") or canonical_data.get("style", {}).get("aspectRatio", "16:9")
        if target_aspect == "9:16":
            play_res_x, play_res_y = 1080, 1920
        elif target_aspect == "1:1":
            play_res_x, play_res_y = 1080, 1080
        elif target_aspect == "4:5":
            play_res_x, play_res_y = 1080, 1350
        else:
            media_cfg = canonical_data.get("media", {})
            play_res_x = int(media_cfg.get("width", 1920) or 1920)
            play_res_y = int(media_cfg.get("height", 1080) or 1080)
            target_aspect = "16:9"

        # Scale typography from studio preview CSS px → full-resolution ASS PlayRes.
        size_scale = export_size_scale(target_aspect, play_res_x)
        font_size = max(18, int(round(ui_font_size * size_scale)))
        outline = int(round(ui_outline * size_scale)) if ui_outline > 0 else 0
        if bevel_enabled and ui_bevel_size > 0:
            outline = max(outline, int(round(ui_bevel_size * size_scale)))
        shadow_distance = ui_shadow_distance * size_scale if shadow_enabled else 0.0
        shadow = int(round(shadow_distance)) if shadow_enabled and shadow_distance > 0 else 0
        # ASS Spacing is in pixels; studio preview uses em relative to font size.
        spacing = round(letter_spacing_em * font_size, 2)
        margin_v = int(round((18 if position == "center" else 70) * size_scale))
        margin_h = int(round(48 * size_scale))

        shadow_rad = math.radians(shadow_angle)
        xshad = round(math.cos(shadow_rad) * shadow_distance, 2) if shadow_enabled else 0
        yshad = round(math.sin(shadow_rad) * shadow_distance, 2) if shadow_enabled else 0
        shad_override = f"{{\\xshad{xshad}\\yshad{yshad}}}" if shadow_enabled and shadow_distance > 0 else ""

        title_font_size = max(42, int(font_size * 1.35))
        header = f"""[Script Info]
; Script generated by LyricSync Studio
Title: LyricSync Karaoke Video
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: {play_res_x}
PlayResY: {play_res_y}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},{primary_color},{secondary_color},{outline_color},{back_color},{bold_flag},{italic_flag},0,0,100,100,{spacing},0,1,{outline},{shadow},{alignment},{margin_h},{margin_h},{margin_v},1
Style: Highlight,{font_name},{font_size},{secondary_color},{primary_color},{outline_color},{back_color},{bold_flag},{italic_flag},0,0,100,100,{spacing},0,1,{outline},{shadow},{alignment},{margin_h},{margin_h},{margin_v},1
Style: Title,{font_name},{title_font_size},{primary_color},{secondary_color},{outline_color},{back_color},{bold_flag},{italic_flag},0,0,100,100,{spacing},0,1,{outline + 1},{shadow + 1},5,{margin_h},{margin_h},{max(20, int(round(24 * size_scale)))},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        events = []
        lyrics = canonical_data.get("lyrics", [])
        motion_prefix = SubtitleGenerator._motion_effect_prefix(
            effect, effect_strength, play_res_x, play_res_y, position, text_align
        )

        # Cinematic title card before the first lyric line.
        song_title = (
            canonical_data.get("project", {}).get("name")
            or canonical_data.get("meta", {}).get("title")
            or canonical_data.get("name")
            or ""
        ).strip()

        first_lyric_start = float(lyrics[0].get("start", 0.0)) if lyrics else 5.0
        if first_lyric_start >= 0.8 and song_title:
            intro_end = min(5.2, first_lyric_start - 0.15)
            if intro_end >= 0.8:
                artist, title_only = split_song_credit(song_title)
                display_title = escape_ass_text(title_only or song_title)
                artist_line = escape_ass_text(artist) if artist else ""
                fade_in_ms = min(700, int(intro_end * 180))
                fade_out_ms = min(550, int(intro_end * 120))
                s_intro = format_ass_time(0.05)
                e_intro = format_ass_time(intro_end)
                if artist_line:
                    dialogue = (
                        f"{{\\fad({fade_in_ms},{fade_out_ms})\\fscx104\\fscy104"
                        f"\\t(0,{fade_in_ms},\\fscx100\\fscy100)}}"
                        f"{{\\c{secondary_color}\\fs{max(18, title_font_size // 3)}}}NOW PLAYING"
                        f"\\N{{\\c{primary_color}\\fs{title_font_size}}}{display_title}"
                        f"\\N{{\\c{secondary_color}\\fs{max(20, title_font_size // 2)}}}{artist_line}"
                    )
                else:
                    dialogue = (
                        f"{{\\fad({fade_in_ms},{fade_out_ms})\\fscx104\\fscy104"
                        f"\\t(0,{fade_in_ms},\\fscx100\\fscy100)}}"
                        f"{{\\c{secondary_color}\\fs{max(18, title_font_size // 3)}}}NOW PLAYING"
                        f"\\N{{\\c{primary_color}\\fs{title_font_size}}}{display_title}"
                    )
                events.append(
                    f"Dialogue: 1,{s_intro},{e_intro},Title,,0,0,0,,{dialogue}"
                )

        chunks = SubtitleGenerator._chunk_lyrics(lyrics, lyrics_format)


        def _cased_word(word_obj) -> str:
            return escape_ass_text(apply_text_case(word_obj.get("text", ""), text_case))

        def _timed_words(line: Dict[str, Any]) -> List[Dict[str, Any]]:
            """Word list with timings; synthesize evenly if ASR words are missing."""
            raw = [w for w in (line.get("words") or []) if str(w.get("text", "")).strip()]
            if raw:
                return raw
            tokens = [t for t in str(line.get("text", "")).strip().split() if t]
            if not tokens:
                return []
            start = float(line.get("start", 0.0) or 0.0)
            end = float(line.get("end", start + 1.0) or (start + 1.0))
            if end <= start:
                end = start + max(0.35, len(tokens) * 0.28)
            step = (end - start) / len(tokens)
            return [
                {
                    "text": tok,
                    "start": start + i * step,
                    "end": start + (i + 1) * step,
                }
                for i, tok in enumerate(tokens)
            ]

        def _active_override(word_text: str) -> str:
            """Per-word tracking tags for classic-style timed modes."""
            if mode == "underline":
                return f"{{\\u1\\c{secondary_color}}}{word_text}{{\\u0\\c{primary_color}}}"
            if mode == "glow":
                glow_bord = max(outline + 2, int(round(4 * size_scale)))
                return (
                    f"{{\\c{secondary_color}\\bord{glow_bord}\\3c{secondary_color}}}"
                    f"{word_text}{{\\c{primary_color}\\bord{outline}\\3c{outline_color}}}"
                )
            if mode == "scale":
                return (
                    f"{{\\c{secondary_color}\\fscx118\\fscy118}}{word_text}"
                    f"{{\\fscx100\\fscy100\\c{primary_color}}}"
                )
            if mode == "box":
                box_bord = max(outline + 3, int(round(6 * size_scale)))
                return (
                    f"{{\\c{primary_color}\\3c{secondary_color}\\bord{box_bord}\\shad0}}"
                    f"{word_text}{{\\c{primary_color}\\3c{outline_color}\\bord{outline}}}"
                )
            # classic color flash (default for unknown timed modes)
            return f"{{\\c{secondary_color}}}{word_text}{{\\c{primary_color}}}"

        if effect == "typewriter":
            # Word-after-word reveal across the whole chunk (never clip all lines at once).
            for chunk in chunks:
                if not chunk:
                    continue
                raw_chunk_end = float(chunk[-1].get("end", 0.0) or 0.0)
                flat: List[tuple[int, Dict[str, Any]]] = []
                for line_idx, line in enumerate(chunk):
                    for w in _timed_words(line):
                        flat.append((line_idx, w))
                if not flat:
                    continue
                for i, (line_idx, active_word) in enumerate(flat):
                    w_start = float(active_word.get("start", 0.0) or 0.0)
                    if i + 1 < len(flat):
                        w_end = float(flat[i + 1][1].get("start", w_start + 0.25) or (w_start + 0.25))
                    else:
                        w_end = max(w_start + 0.2, raw_chunk_end)
                    if w_end <= w_start:
                        w_end = w_start + 0.2

                    # Build text with only words revealed so far, line breaks preserved.
                    revealed_by_line: List[List[str]] = [[] for _ in chunk]
                    for j in range(i + 1):
                        lj, wj = flat[j]
                        revealed_by_line[lj].append(_cased_word(wj))
                    line_parts = [" ".join(parts) for parts in revealed_by_line if parts]
                    dialogue_text = "\\N".join(line_parts)
                    events.append(
                        f"Dialogue: 0,{format_ass_time(w_start)},{format_ass_time(w_end)},"
                        f"Default,,0,0,0,,{shad_override}{dialogue_text}"
                    )
        elif mode == "karaoke":
            for chunk in chunks:
                if not chunk:
                    continue
                raw_chunk_start = float(chunk[0].get("start", 0.0))
                raw_chunk_end = float(chunk[-1].get("end", 0.0))
                event_start_cs = int(round(raw_chunk_start * 100))
                event_end_cs = int(round(raw_chunk_end * 100))
                if event_end_cs <= event_start_cs:
                    event_end_cs = event_start_cs + 100

                chunk_start = format_ass_time(raw_chunk_start)
                chunk_end = format_ass_time(float(event_end_cs) / 100.0)

                current_rel_cs = 0
                line_parts = []

                for line in chunk:
                    words = _timed_words(line)
                    karaoke_text_parts = []
                    for w in words:
                        w_start_raw = float(w.get("start", raw_chunk_start))
                        w_end_raw = float(w.get("end", w_start_raw + 0.3))
                        w_start_cs = int(round(w_start_raw * 100)) - event_start_cs
                        w_end_cs = int(round(w_end_raw * 100)) - event_start_cs

                        gap_cs = w_start_cs - current_rel_cs
                        if gap_cs > 0:
                            # Insert silence duration so karaoke highlight doesn't run ahead
                            karaoke_text_parts.append(f"{{\\k{gap_cs}}}")
                            current_rel_cs += gap_cs
                        elif gap_cs < 0:
                            w_start_cs = current_rel_cs

                        duration_cs = max(1, w_end_cs - w_start_cs)
                        word_str = _cased_word(w)
                        karaoke_text_parts.append(f"{{\\kf{duration_cs}}}{word_str} ")
                        current_rel_cs += duration_cs

                    line_parts.append("".join(karaoke_text_parts).rstrip())

                full_chunk_text = "\\N".join(line_parts)
                events.append(
                    f"Dialogue: 0,{chunk_start},{chunk_end},Default,,0,0,0,,{motion_prefix}{shad_override}{full_chunk_text}"
                )
        elif mode == "none":
            for chunk in chunks:
                if not chunk:
                    continue
                raw_chunk_start = float(chunk[0].get("start", 0.0))
                raw_chunk_end = float(chunk[-1].get("end", 0.0))
                if raw_chunk_end <= raw_chunk_start:
                    raw_chunk_end = raw_chunk_start + 1.0
                chunk_start = format_ass_time(raw_chunk_start)
                chunk_end = format_ass_time(raw_chunk_end)
                line_parts = []
                for line in chunk:
                    words = _timed_words(line)
                    if words:
                        line_parts.append(" ".join(_cased_word(w) for w in words))
                    else:
                        line_parts.append(escape_ass_text(apply_text_case(line.get("text", ""), text_case)))
                full_chunk_text = "\\N".join(line_parts)
                events.append(
                    f"Dialogue: 0,{chunk_start},{chunk_end},Default,,0,0,0,,{motion_prefix}{shad_override}{full_chunk_text}"
                )
        else:
            # Timed active-word modes: classic / underline / glow / scale / box
            for chunk in chunks:
                if not chunk:
                    continue
                # Entrance motion once per chunk (stanza/couplet), not on every word/line.
                chunk_motion_applied = False
                for line_idx, line in enumerate(chunk):
                    words = _timed_words(line)
                    for active_word_idx, active_word in enumerate(words):
                        w_start = format_ass_time(active_word["start"])
                        w_end = format_ass_time(active_word["end"])

                        chunk_lines_styled = []
                        for curr_l_idx, curr_line in enumerate(chunk):
                            curr_words = _timed_words(curr_line)
                            line_tokens = []
                            for curr_w_idx, w in enumerate(curr_words):
                                word_text = _cased_word(w)
                                if curr_l_idx == line_idx and curr_w_idx == active_word_idx:
                                    line_tokens.append(_active_override(word_text))
                                else:
                                    line_tokens.append(word_text)
                            chunk_lines_styled.append(" ".join(line_tokens))

                        dialogue_text = "\\N".join(chunk_lines_styled)
                        event_motion = "" if chunk_motion_applied else motion_prefix
                        chunk_motion_applied = True
                        events.append(
                            f"Dialogue: 0,{w_start},{w_end},Default,,0,0,0,,{event_motion}{shad_override}{dialogue_text}"
                        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(header + "\n".join(events) + "\n")

        return output_path

    @staticmethod
    def _motion_effect_prefix(
        effect: str,
        strength: float,
        play_res_x: int,
        play_res_y: int,
        position: str,
        text_align: str,
    ) -> str:
        """Map studio motion effects to ASS override tags burned into the export."""
        if not effect or effect == "none":
            return ""

        strength = max(0.15, min(1.0, float(strength or 0.7)))
        fade_ms = int(180 + 420 * strength)
        slide_px = int(28 + 52 * strength)
        bounce_px = int(18 + 36 * strength)
        pulse_scale = int(104 + 12 * strength)

        # Approximate anchor for \move based on alignment / position.
        if text_align == "left":
            x = int(play_res_x * 0.12)
        elif text_align == "right":
            x = int(play_res_x * 0.88)
        else:
            x = play_res_x // 2

        if position == "top":
            y = int(play_res_y * 0.18)
        elif position == "bottom":
            y = int(play_res_y * 0.82)
        else:
            y = play_res_y // 2

        if effect == "fade":
            return f"{{\\fad({fade_ms},0)}}"
        if effect == "slide":
            return f"{{\\fad({fade_ms // 2},0)\\move({x},{y + slide_px},{x},{y},0,{fade_ms})}}"
        if effect == "bounce":
            mid = max(80, fade_ms // 2)
            return (
                f"{{\\fad({mid},0)"
                f"\\move({x},{y + bounce_px},{x},{y - int(bounce_px * 0.25)},0,{mid})"
                f"\\t({mid},{fade_ms},\\frz0)}}"
            )
        if effect == "pulse":
            return (
                f"{{\\fad({fade_ms // 3},0)"
                f"\\fscx{pulse_scale}\\fscy{pulse_scale}"
                f"\\t(0,{fade_ms},\\fscx100\\fscy100)}}"
            )
        if effect == "typewriter":
            # Karaoke already reveals by word; classic mode gets a crisp fade-in.
            return f"{{\\fad({max(80, fade_ms // 3)},0)}}"
        return ""

    @staticmethod
    def generate_srt(canonical_data: Dict[str, Any], output_path: Path) -> Path:
        """Generates standard SRT subtitles."""
        lines = canonical_data.get("lyrics", [])
        content = []
        for idx, line in enumerate(lines, 1):
            s_time = format_srt_time(line.get("start", 0.0))
            e_time = format_srt_time(line.get("end", 0.0))
            content.append(f"{idx}\n{s_time} --> {e_time}\n{line.get('text', '')}\n")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(content))
        return output_path

    @staticmethod
    def generate_vtt(canonical_data: Dict[str, Any], output_path: Path) -> Path:
        """Generates standard WebVTT subtitles."""
        lines = canonical_data.get("lyrics", [])
        content = ["WEBVTT\n"]
        for idx, line in enumerate(lines, 1):
            s_time = format_vtt_time(line.get("start", 0.0))
            e_time = format_vtt_time(line.get("end", 0.0))
            content.append(f"{idx}\n{s_time} --> {e_time}\n{line.get('text', '')}\n")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(content))
        return output_path
