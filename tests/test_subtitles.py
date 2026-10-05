from pathlib import Path
from app.services.subtitles import (
    hex_to_ass_color,
    format_ass_time,
    format_srt_time,
    format_vtt_time,
    export_size_scale,
    apply_text_case,
    SubtitleGenerator
)

def test_hex_to_ass_color():
    # #RRGGBB -> &H00BBGGRR&
    # #FFE66D: R=FF, G=E6, B=6D -> &H006DE6FF&
    assert hex_to_ass_color("#FFE66D") == "&H006DE6FF&"
    # #FFFFFF -> &H00FFFFFF&
    assert hex_to_ass_color("#FFFFFF") == "&H00FFFFFF&"
    # #000000 -> &H00000000&
    assert hex_to_ass_color("#000000") == "&H00000000&"

def test_time_formatting():
    # 75.25 seconds = 1 minute, 15 seconds, 25 centiseconds
    assert format_ass_time(75.25) == "0:01:15.25"
    assert format_srt_time(75.25) == "00:01:15,250"
    assert format_vtt_time(75.25) == "00:01:15.250"

def test_ass_generation(tmp_path):
    canonical = {
        "media": {"width": 1920, "height": 1080},
        "style": {
            "mode": "karaoke",
            "font": "Arial",
            "font_size": 52,
            "primary_color": "#FFFFFF",
            "highlight_color": "#FFE66D",
            "position": "bottom",
            "outline": 2,
            "shadow": 1
        },
        "lyrics": [
            {
                "id": 1,
                "text": "Hello world",
                "start": 1.0,
                "end": 2.5,
                "words": [
                    {"text": "Hello", "start": 1.0, "end": 1.8},
                    {"text": "world", "start": 1.85, "end": 2.5}
                ]
            }
        ]
    }
    ass_path = tmp_path / "test.ass"
    out = SubtitleGenerator.generate_ass(canonical, ass_path)
    assert out.exists()

    content = out.read_text(encoding="utf-8")
    assert "[Script Info]" in content
    assert "[V4+ Styles]" in content
    assert "PlayResX: 1920" in content
    expected_size = max(18, int(round(52 * export_size_scale("16:9", 1920))))
    assert f"Style: Default,Arial,{expected_size}" in content
    assert "Dialogue: 0,0:00:01.00,0:00:02.50" in content
    assert "{\\kf80}Hello" in content or "Hello" in content

def test_srt_and_vtt_generation(tmp_path):
    canonical = {
        "lyrics": [
            {"id": 1, "text": "Test line", "start": 0.5, "end": 2.0}
        ]
    }
    srt_file = tmp_path / "test.srt"
    vtt_file = tmp_path / "test.vtt"

    SubtitleGenerator.generate_srt(canonical, srt_file)
    SubtitleGenerator.generate_vtt(canonical, vtt_file)

    assert "00:00:00,500 --> 00:00:02,000" in srt_file.read_text(encoding="utf-8")
    assert "WEBVTT" in vtt_file.read_text(encoding="utf-8")
    assert "00:00:00.500 --> 00:00:02.000" in vtt_file.read_text(encoding="utf-8")

def test_ass_generation_stanza_and_sentence(tmp_path):
    canonical = {
        "style": {"format": "stanza", "mode": "karaoke"},
        "lyrics": [
            {"id": 1, "text": "Line 1", "start": 1.0, "end": 2.0, "words": [{"text": "Line", "start": 1.0, "end": 1.5}, {"text": "1", "start": 1.5, "end": 2.0}]},
            {"id": 2, "text": "Line 2", "start": 2.0, "end": 3.0, "words": [{"text": "Line", "start": 2.0, "end": 2.5}, {"text": "2", "start": 2.5, "end": 3.0}]},
            {"id": 3, "text": "Line 3", "start": 3.0, "end": 4.0, "words": [{"text": "Line", "start": 3.0, "end": 3.5}, {"text": "3", "start": 3.5, "end": 4.0}]},
            {"id": 4, "text": "Line 4", "start": 4.0, "end": 5.0, "words": [{"text": "Line", "start": 4.0, "end": 4.5}, {"text": "4", "start": 4.5, "end": 5.0}]},
            {"id": 5, "text": "Line 5", "start": 5.0, "end": 6.0, "words": [{"text": "Line", "start": 5.0, "end": 5.5}, {"text": "5", "start": 5.5, "end": 6.0}]},
        ]
    }
    stanza_ass = tmp_path / "stanza.ass"
    SubtitleGenerator.generate_ass(canonical, stanza_ass)
    content = stanza_ass.read_text(encoding="utf-8")
    # First chunk spans line 1 to line 4 (1.00 to 5.00) joined by \N
    assert "Dialogue: 0,0:00:01.00,0:00:05.00" in content
    assert "\\N" in content

    # Test sentence format (pairs of 2)
    canonical["style"]["format"] = "sentence"
    sentence_ass = tmp_path / "sentence.ass"
    SubtitleGenerator.generate_ass(canonical, sentence_ass)
    s_content = sentence_ass.read_text(encoding="utf-8")
    assert "Dialogue: 0,0:00:01.00,0:00:03.00" in s_content

def test_ass_generation_with_typewriter_title(tmp_path):
    canonical = {
        "project": {"name": "Amazing Grace"},
        "style": {"format": "line", "mode": "karaoke", "font": "Caveat", "font_size": 34},
        "lyrics": [
            {
                "id": 1,
                "text": "Amazing grace how sweet the sound",
                "start": 4.0,
                "end": 8.0,
                "words": [
                    {"text": "Amazing", "start": 4.0, "end": 5.0},
                    {"text": "grace", "start": 5.0, "end": 6.0}
                ]
            }
        ]
    }
    ass_path = tmp_path / "typewriter_title.ass"
    SubtitleGenerator.generate_ass(canonical, ass_path)
    content = ass_path.read_text(encoding="utf-8")
    assert "Style: Title,Caveat" in content
    assert "NOW PLAYING" in content
    assert "Amazing Grace" in content
    assert "Dialogue: 1," in content


def test_ass_typography_and_motion_effects(tmp_path):
    canonical = {
        "media": {"width": 1920, "height": 1080},
        "style": {
            "mode": "karaoke",
            "font": "Garamond",
            "fontSize": 48,  # camelCase legacy key should normalize
            "font_weight": 400,
            "font_style": "italic",
            "letter_spacing": 0.1,
            "effect": "fade",
            "effect_strength": 0.8,
            "primary_color": "#FFFFFF",
            "highlight_color": "#10B981",
            "position": "center",
            "text_align": "center",
        },
        "lyrics": [
            {
                "id": 1,
                "text": "Hello world",
                "start": 1.0,
                "end": 2.5,
                "words": [
                    {"text": "Hello", "start": 1.0, "end": 1.8},
                    {"text": "world", "start": 1.85, "end": 2.5},
                ],
            }
        ],
    }
    ass_path = tmp_path / "typography.ass"
    SubtitleGenerator.generate_ass(canonical, ass_path)
    content = ass_path.read_text(encoding="utf-8")
    # Garamond maps to EB Garamond; weight 400 → Bold=0; italic → Italic=-1
    expected_size = max(18, int(round(48 * export_size_scale("16:9", 1920))))
    expected_spacing = round(0.1 * expected_size, 2)
    assert f"Style: Default,EB Garamond,{expected_size}," in content
    assert f",0,-1,0,0,100,100,{expected_spacing},0,1," in content
    assert "{\\fad(" in content


def test_ass_text_case_and_tracking_none(tmp_path):
    assert apply_text_case("Hello World", "upper") == "HELLO WORLD"
    canonical = {
        "media": {"width": 1920, "height": 1080},
        "style": {
            "mode": "none",
            "font": "Arial",
            "font_size": 36,
            "text_case": "upper",
            "primary_color": "#FFFFFF",
        },
        "lyrics": [
            {
                "id": 1,
                "text": "Hello world",
                "start": 1.0,
                "end": 2.0,
                "words": [
                    {"text": "Hello", "start": 1.0, "end": 1.5},
                    {"text": "world", "start": 1.5, "end": 2.0},
                ],
            }
        ],
    }
    ass_path = tmp_path / "case_none.ass"
    SubtitleGenerator.generate_ass(canonical, ass_path)
    content = ass_path.read_text(encoding="utf-8")
    assert "HELLO WORLD" in content
    assert "\\kf" not in content


def test_ass_estelle_font_maps_to_great_vibes(tmp_path):
    canonical = {
        "media": {"width": 1920, "height": 1080},
        "style": {"mode": "karaoke", "font": "Estelle", "font_size": 40},
        "lyrics": [
            {
                "id": 1,
                "text": "Test",
                "start": 1.0,
                "end": 2.0,
                "words": [{"text": "Test", "start": 1.0, "end": 2.0}],
            }
        ],
    }
    ass_path = tmp_path / "estelle.ass"
    SubtitleGenerator.generate_ass(canonical, ass_path)
    content = ass_path.read_text(encoding="utf-8")
    assert "Style: Default,Great Vibes," in content


def test_normalize_style_payload_prefers_snake_case():
    from app.services.style_normalize import normalize_style_payload

    out = normalize_style_payload({
        "fontSize": 40,
        "font_size": 52,
        "primaryColor": "#ABC",
        "textCase": "upper",
        "font": "Montserrat",
    })
    assert out["font_size"] == 52
    assert out["primary_color"] == "#ABC"
    assert out["text_case"] == "upper"
    assert out["font"] == "Montserrat"
    assert "fontSize" not in out


