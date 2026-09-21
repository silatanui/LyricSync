import re
from difflib import SequenceMatcher
from typing import List, Dict, Any, Optional

class AlignmentEngine:
    @staticmethod
    def align_custom_lines(lines: List[Dict[str, Any]], transcript_words: List[Dict[str, Any]], total_duration: float) -> List[Dict[str, Any]]:
        """Map uploaded lyric lines onto audio word timings when transcript text is available."""
        if not lines or not transcript_words:
            return lines

        def clean(value: str) -> str:
            return re.sub(r"[^a-z0-9']", "", value.lower())

        audio_words = [w for w in transcript_words if clean(str(w.get("text", "")))]
        audio_tokens = [clean(str(w.get("text", ""))) for w in audio_words]
        cursor = 0
        aligned = []
        for line in lines:
            line["text"] = str(line.get("text", "")).strip().capitalize()
            lyric_tokens = [clean(token) for token in str(line.get("text", "")).split() if clean(token)]
            best_start, best_score = cursor, 0.0
            search_end = min(len(audio_tokens), cursor + 80)
            for start in range(cursor, search_end):
                window = audio_tokens[start:min(len(audio_tokens), start + max(1, len(lyric_tokens)) + 3)]
                score = SequenceMatcher(None, lyric_tokens, window[:len(lyric_tokens)]).ratio()
                if score > best_score:
                    best_start, best_score = start, score

            matched = best_score >= 0.45 and lyric_tokens
            if matched:
                end_index = min(len(audio_words), best_start + len(lyric_tokens))
                start_time = float(audio_words[best_start].get("start", line["start"]))
                end_time = float(audio_words[end_index - 1].get("end", line["end"]))
                word_timings = []
                for index, token in enumerate(lyric_tokens):
                    source = audio_words[min(best_start + index, end_index - 1)]
                    word_text = line["text"].split()[index]
                    if index == 0:
                        word_text = word_text.capitalize()
                    word_timings.append({"text": word_text, "start": source.get("start", start_time), "end": source.get("end", end_time)})
                line["start"], line["end"], line["words"] = round(start_time, 3), round(max(start_time + 0.1, end_time), 3), word_timings
                line["confidence"] = round(min(1.0, 0.55 + best_score * 0.45), 2)
                cursor = max(cursor + 1, end_index)
            else:
                line["confidence"] = 0.35
            aligned.append(line)

        return aligned

    @staticmethod
    def normalize_words(raw_words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Stage A: Normalize words from transcription provider.
        - Strips whitespace
        - Clamps negative timestamps
        - Ensures end >= start
        - Discards zero-information artifacts
        - Attaches stable word index
        """
        normalized = []
        idx = 0
        last_end = 0.0

        for w in raw_words:
            raw_text = str(w.get("text", "")).strip()
            if not raw_text:
                continue

            # Strip control characters
            cleaned_text = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", raw_text)
            if not cleaned_text:
                continue

            start = max(0.0, float(w.get("start", 0.0)))
            end = max(start, float(w.get("end", start)))

            # Monotonic time check
            if start < last_end - 0.05 and idx > 0:
                # Slight overlap correction
                start = max(start, last_end)
                end = max(start, end)

            last_end = end

            normalized.append({
                "word_index": idx,
                "text": cleaned_text,
                "start": round(start, 3),
                "end": round(end, 3),
            })
            idx += 1

        return normalized

    @staticmethod
    def segment_lines(
        words: List[Dict[str, Any]],
        max_words: int = 10,
        max_chars: int = 56,
        pause_threshold: float = 0.65
    ) -> List[Dict[str, Any]]:
        """
        Stage B: Deterministic line segmentation heuristics.
        Groups words into readable lyric lines based on:
        - Maximum words per line
        - Maximum visible characters
        - Pause gaps (> pause_threshold seconds)
        - Punctuation cues (. ! ? , ;)
        """
        if not words:
            return []

        lines = []
        current_line_words = []
        current_char_count = 0

        for i, word in enumerate(words):
            word_len = len(word["text"]) + (1 if current_line_words else 0)

            # Check pause gap before this word
            pause_detected = False
            if current_line_words:
                prev_word = current_line_words[-1]
                gap = word["start"] - prev_word["end"]
                if gap >= pause_threshold:
                    pause_detected = True

            # Check sentence punctuation in previous word
            punctuation_break = False
            if current_line_words:
                prev_text = current_line_words[-1]["text"]
                if re.search(r"[.!?]$", prev_text):
                    punctuation_break = True

            # Check threshold constraints
            word_count_exceeded = len(current_line_words) >= max_words
            char_count_exceeded = (current_char_count + word_len) > max_chars

            should_break = (
                current_line_words
                and (pause_detected or punctuation_break or word_count_exceeded or char_count_exceeded)
            )

            if should_break:
                lines.append(AlignmentEngine._create_line_object(len(lines) + 1, current_line_words))
                current_line_words = []
                current_char_count = 0

            current_line_words.append(word)
            current_char_count += len(word["text"]) + 1

        if current_line_words:
            lines.append(AlignmentEngine._create_line_object(len(lines) + 1, current_line_words))

        # Heuristic: Merge very short trailing or intermediate lines (< 2 words) if line length permits
        lines = AlignmentEngine._merge_short_lines(lines, max_words=max_words, max_chars=max_chars)

        return lines

    @staticmethod
    def _create_line_object(line_id: int, words: List[Dict[str, Any]]) -> Dict[str, Any]:
        line_text = " ".join(w["text"] for w in words)
        return {
            "id": line_id,
            "text": line_text,
            "start": words[0]["start"],
            "end": words[-1]["end"],
            "words": [
                {
                    "text": w["text"],
                    "start": w["start"],
                    "end": w["end"]
                }
                for w in words
            ]
        }

    @staticmethod
    def _merge_short_lines(
        lines: List[Dict[str, Any]],
        max_words: int = 8,
        max_chars: int = 42
    ) -> List[Dict[str, Any]]:
        if len(lines) <= 1:
            return lines

        merged = []
        i = 0
        while i < len(lines):
            cur = lines[i]
            # If current line has only 1 word and next exists, check if can merge
            if (
                len(cur["words"]) == 1
                and i + 1 < len(lines)
                and len(lines[i + 1]["words"]) + 1 <= max_words
                and len(cur["text"]) + len(lines[i + 1]["text"]) + 1 <= max_chars
                and lines[i + 1]["start"] - cur["end"] < 0.6
            ):
                nxt = lines[i + 1]
                combined_words = cur["words"] + nxt["words"]
                merged.append(AlignmentEngine._create_line_object(len(merged) + 1, combined_words))
                i += 2
            else:
                cur["id"] = len(merged) + 1
                merged.append(cur)
                i += 1

        return merged

    @staticmethod
    def split_line(line: Dict[str, Any], split_word_index: int) -> List[Dict[str, Any]]:
        """Split a line into two lines at split_word_index."""
        words = line.get("words", [])
        if split_word_index <= 0 or split_word_index >= len(words):
            return [line]

        line1 = AlignmentEngine._create_line_object(line["id"], words[:split_word_index])
        line2 = AlignmentEngine._create_line_object(line["id"] + 1, words[split_word_index:])
        return [line1, line2]

    @staticmethod
    def merge_lines(line1: Dict[str, Any], line2: Dict[str, Any]) -> Dict[str, Any]:
        """Merge two lines together."""
        combined_words = line1.get("words", []) + line2.get("words", [])
        return AlignmentEngine._create_line_object(line1["id"], combined_words)

    @staticmethod
    def nudge_line(line: Dict[str, Any], delta_seconds: float) -> Dict[str, Any]:
        """Nudge all timestamps of a line and its words by delta_seconds."""
        new_start = max(0.0, line["start"] + delta_seconds)
        new_end = max(new_start + 0.1, line["end"] + delta_seconds)
        
        new_words = []
        for w in line.get("words", []):
            w_start = max(0.0, w["start"] + delta_seconds)
            w_end = max(w_start + 0.05, w["end"] + delta_seconds)
            new_words.append({
                "text": w["text"],
                "start": round(w_start, 3),
                "end": round(w_end, 3),
            })
            
        return {
            "id": line["id"],
            "text": line["text"],
            "start": round(new_start, 3),
            "end": round(new_end, 3),
            "words": new_words,
        }

    @staticmethod
    def seek_to_word_index(all_words: List[Dict[str, Any]], target_time: float) -> int:
        """Binary search for the greatest word.start <= target_time."""
        if not all_words:
            return 0
        lo, hi = 0, len(all_words) - 1
        ans = 0
        while lo <= hi:
            mid = (lo + hi) // 2
            if all_words[mid]["start"] <= target_time:
                ans = mid
                lo = mid + 1
            else:
                hi = mid - 1
        return ans
