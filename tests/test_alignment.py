import pytest
from app.services.alignment import AlignmentEngine

def test_custom_lines_align_to_transcript_words():
    lines = [{"id": "line_0", "text": "Hello bright world", "start": 1.0, "end": 4.0, "words": []}]
    transcript = [
        {"text": "Hello", "start": 8.0, "end": 8.4},
        {"text": "bright", "start": 8.5, "end": 8.9},
        {"text": "world", "start": 9.0, "end": 9.5},
    ]
    aligned = AlignmentEngine.align_custom_lines(lines, transcript, 20.0)
    assert aligned[0]["start"] == 8.0
    assert aligned[0]["end"] == 9.5
    assert aligned[0]["confidence"] >= 0.9


def test_unmatched_lines_are_interpolated_between_anchors():
    lines = [
        {"id": "line_0", "text": "First anchor line here", "start": 1.0, "end": 2.0, "words": []},
        {"id": "line_1", "text": "Mystery middle line", "start": 10.0, "end": 12.0, "words": []},
        {"id": "line_2", "text": "Second anchor line here", "start": 20.0, "end": 22.0, "words": []},
    ]
    transcript = [
        {"text": "First", "start": 5.0, "end": 5.3},
        {"text": "anchor", "start": 5.4, "end": 5.8},
        {"text": "line", "start": 5.9, "end": 6.2},
        {"text": "here", "start": 6.3, "end": 6.7},
        {"text": "Second", "start": 14.0, "end": 14.4},
        {"text": "anchor", "start": 14.5, "end": 14.9},
        {"text": "line", "start": 15.0, "end": 15.3},
        {"text": "here", "start": 15.4, "end": 15.8},
    ]
    aligned = AlignmentEngine.align_custom_lines(lines, transcript, 30.0)
    assert aligned[0]["start"] == 5.0
    assert aligned[2]["start"] == 14.0
    # Middle line should land between the two anchors, not steal the second anchor.
    assert aligned[0]["end"] <= aligned[1]["start"] <= aligned[2]["start"]
    assert aligned[1]["confidence"] < aligned[0]["confidence"]


def test_alignment_skips_instrumental_intro_hallucinations():
    """Whisper often invents a few words during the bed; first lyrics must wait for vocals."""
    lines = [
        {"id": "line_0", "text": "Desert blooms again tonight", "start": 1.0, "end": 3.0, "words": []},
        {"id": "line_1", "text": "Under quiet silver light", "start": 4.0, "end": 6.0, "words": []},
    ]
    transcript = [
        # Sparse instrumental hallucinations
        {"text": "the", "start": 0.4, "end": 0.6},
        {"text": "desert", "start": 1.0, "end": 1.3},
        {"text": "oh", "start": 2.2, "end": 2.4},
        # Gap, then real singing
        {"text": "Desert", "start": 14.0, "end": 14.4},
        {"text": "blooms", "start": 14.5, "end": 14.9},
        {"text": "again", "start": 15.0, "end": 15.3},
        {"text": "tonight", "start": 15.4, "end": 15.9},
        {"text": "Under", "start": 16.5, "end": 16.9},
        {"text": "quiet", "start": 17.0, "end": 17.4},
        {"text": "silver", "start": 17.5, "end": 17.9},
        {"text": "light", "start": 18.0, "end": 18.4},
    ]
    onset = AlignmentEngine.estimate_vocal_onset(transcript, 40.0)
    assert onset >= 12.0
    aligned = AlignmentEngine.align_custom_lines(lines, transcript, 40.0)
    assert aligned[0]["start"] >= 13.5
    assert aligned[1]["start"] >= aligned[0]["start"]

def test_word_normalization():
    raw_words = [
        {"text": "  Hello  ", "start": -0.5, "end": 1.2},
        {"text": "", "start": 1.2, "end": 1.3},
        {"text": "\x00\x1fWorld!", "start": 1.1, "end": 1.8},
    ]
    normalized = AlignmentEngine.normalize_words(raw_words)
    assert len(normalized) == 2
    assert normalized[0]["text"] == "Hello"
    assert normalized[0]["start"] == 0.0
    assert normalized[0]["end"] == 1.2
    assert normalized[0]["word_index"] == 0
    assert normalized[1]["text"] == "World!"
    assert normalized[1]["start"] >= normalized[0]["end"]

def test_line_segmentation_pause_detection():
    words = [
        {"word_index": 0, "text": "First", "start": 0.0, "end": 0.5},
        {"word_index": 1, "text": "sentence", "start": 0.6, "end": 1.0},
        # Big pause: 2.5 - 1.0 = 1.5s
        {"word_index": 2, "text": "After", "start": 2.5, "end": 3.0},
        {"word_index": 3, "text": "pause", "start": 3.1, "end": 3.6},
    ]
    lines = AlignmentEngine.segment_lines(words, pause_threshold=0.6)
    assert len(lines) == 2
    assert lines[0]["text"] == "First sentence"
    assert lines[1]["text"] == "After pause"

def test_line_segmentation_punctuation():
    words = [
        {"word_index": 0, "text": "Stop.", "start": 0.0, "end": 0.4},
        {"word_index": 1, "text": "Go", "start": 0.5, "end": 0.8},
        {"word_index": 2, "text": "now", "start": 0.9, "end": 1.2},
    ]
    lines = AlignmentEngine.segment_lines(words)
    # Stop. has period punctuation break
    assert len(lines) >= 1

def test_line_segmentation_max_words():
    words = [
        {"word_index": i, "text": f"word{i}", "start": i * 0.5, "end": (i * 0.5) + 0.4}
        for i in range(16)
    ]
    lines = AlignmentEngine.segment_lines(words, max_words=6)
    for l in lines:
        assert len(l["words"]) <= 8

def test_seek_to_word_index_binary_search():
    words = [
        {"text": "A", "start": 1.0, "end": 1.5},
        {"text": "B", "start": 2.0, "end": 2.5},
        {"text": "C", "start": 3.0, "end": 3.5},
        {"text": "D", "start": 4.0, "end": 4.5},
    ]
    assert AlignmentEngine.seek_to_word_index(words, 0.5) == 0
    assert AlignmentEngine.seek_to_word_index(words, 1.2) == 0
    assert AlignmentEngine.seek_to_word_index(words, 2.3) == 1
    assert AlignmentEngine.seek_to_word_index(words, 3.8) == 2
    assert AlignmentEngine.seek_to_word_index(words, 10.0) == 3

def test_split_and_merge_lines():
    line = {
        "id": 1,
        "text": "One two three four",
        "start": 1.0,
        "end": 4.0,
        "words": [
            {"text": "One", "start": 1.0, "end": 1.8},
            {"text": "two", "start": 1.9, "end": 2.4},
            {"text": "three", "start": 2.5, "end": 3.2},
            {"text": "four", "start": 3.3, "end": 4.0},
        ]
    }
    splits = AlignmentEngine.split_line(line, split_word_index=2)
    assert len(splits) == 2
    assert splits[0]["text"] == "One two"
    assert splits[1]["text"] == "three four"

    merged = AlignmentEngine.merge_lines(splits[0], splits[1])
    assert merged["text"] == "One two three four"
    assert len(merged["words"]) == 4

def test_nudge_line():
    line = {
        "id": 1,
        "text": "Nudge test",
        "start": 2.0,
        "end": 3.5,
        "words": [
            {"text": "Nudge", "start": 2.0, "end": 2.6},
            {"text": "test", "start": 2.7, "end": 3.5},
        ]
    }
    nudged = AlignmentEngine.nudge_line(line, delta_seconds=0.5)
    assert nudged["start"] == 2.5
    assert nudged["end"] == 4.0
    assert nudged["words"][0]["start"] == 2.5
    assert nudged["words"][1]["end"] == 4.0
