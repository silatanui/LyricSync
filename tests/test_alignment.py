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
