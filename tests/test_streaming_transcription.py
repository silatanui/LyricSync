from app.services.alignment import AlignmentEngine
from app.services.openai_transcription import (
    language_display_name,
    merge_chunk_words,
    normalize_language_code,
    plan_audio_chunks,
)


def test_language_detection_is_the_default_and_known_codes_pass_through():
    assert normalize_language_code(None) is None
    assert normalize_language_code("auto") is None
    assert normalize_language_code("EN") == "en"
    assert normalize_language_code("swahili") == "sw"
    assert normalize_language_code("not-a-language") is None
    assert language_display_name("yo") == "Yoruba"
    assert language_display_name("español") == "Español"


def test_opening_preview_starts_at_zero_and_later_slices_overlap():
    short = plan_audio_chunks(10)
    assert short == [(0.0, 10.0)]

    chunks = plan_audio_chunks(60)
    assert chunks[0][0] == 0.0
    assert chunks[0][1] == 12.0
    assert len(chunks) > 2
    assert chunks[-1][0] + chunks[-1][1] == 60 or abs((chunks[-1][0] + chunks[-1][1]) - 60) < 0.05
    # Each follow-up slice starts inside the previous slice.
    for previous, current in zip(chunks, chunks[1:]):
        previous_end = previous[0] + previous[1]
        assert current[0] < previous_end


def test_cjk_line_limits_are_tighter():
    limits = AlignmentEngine.line_limits_for_language("ja")
    assert limits["max_chars"] == 28
    assert AlignmentEngine.line_limits_for_language("en")["max_chars"] == 56


def test_overlap_keeps_words_from_the_slice_that_owns_them():
    existing = [
        {"text": "habari", "start": 10.2, "end": 10.8},
        {"text": "ya", "start": 11.4, "end": 11.7},
    ]
    incoming = [
        {"text": "ya", "start": 11.35, "end": 11.7},
        {"text": "asubuhi", "start": 11.9, "end": 12.6},
    ]
    merged = merge_chunk_words(existing, incoming, chunk_start=10.75, overlap_seconds=1.25)
    texts = [word["text"] for word in merged]
    assert texts == ["habari", "ya", "asubuhi"]
    assert merged[1]["start"] == 11.35


def test_polish_keeps_non_latin_lyrics_intact():
    assert AlignmentEngine.polish_lyric_text("habari za asubuhi") == "Habari za asubuhi"
    assert AlignmentEngine.polish_lyric_text("مرحبا") == "مرحبا"
    assert AlignmentEngine.polish_lyric_text("你好世界") == "你好世界"
    assert AlignmentEngine.polish_lyric_text("¿dónde estás?") == "¿Dónde estás?"


def test_bcp47_language_tags_normalize():
    assert normalize_language_code("en-US") == "en"
    assert normalize_language_code("zh-CN") == "zh"
    assert language_display_name("sw") == "Swahili"


def test_swahili_prompt_avoids_kwa_and_drops_loop_continuity():
    from app.services.openai_transcription import (
        collapse_repetitive_words,
        lyric_language_prompt,
        sanitize_continuity_prompt,
        words_look_repetition_locked,
    )

    # Swahili uses no seed prompt — Whisper echoes canned phrases into the transcript.
    assert lyric_language_prompt("sw") in (None, "")

    stuck = " ".join(["Kwa"] * 12)
    assert sanitize_continuity_prompt(stuck) == ""
    # Looping continuity is dropped; empty seed stays empty.
    assert lyric_language_prompt("sw", stuck) in (None, "")

    real = "Njooni mchote neema Bwana asifiwe"
    assert lyric_language_prompt("sw", real) == real

    words = [{"text": "Kwa", "start": i * 0.2, "end": i * 0.2 + 0.15} for i in range(10)]
    words = [{"text": "Fani", "start": 0.0, "end": 0.3}] + words
    assert words_look_repetition_locked(words)
    collapsed = collapse_repetitive_words(words, max_run=2)
    texts = [w["text"] for w in collapsed]
    assert texts.count("Kwa") == 2
    assert texts[0] == "Fani"
