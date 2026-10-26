import re
from difflib import SequenceMatcher
from typing import List, Dict, Any, Optional

# Terminal punctuation across Latin, CJK, Arabic, and Indic scripts.
_LINE_BREAK_PUNCT = re.compile(r"[.!?…。！？؟؛;،,]$")


class AlignmentEngine:
    @staticmethod
    def estimate_vocal_onset(
        transcript_words: List[Dict[str, Any]],
        total_duration: float = 0.0,
    ) -> float:
        """Estimate when singing starts, skipping instrumental / Whisper intro ghosts.

        Whisper often invents a few words during the bed before real vocals. We look
        for a clear gap followed by a denser word cluster, or the first sustained
        singing cluster.
        """
        words = [
            w for w in (transcript_words or [])
            if str(w.get("text", "")).strip()
        ]
        if not words:
            return 0.0

        def _start(w: Dict[str, Any]) -> float:
            return float(w.get("start") or 0.0)

        def _end(w: Dict[str, Any]) -> float:
            return float(w.get("end") or _start(w))

        cluster_onset = AlignmentEngine._first_dense_cluster_start(words)
        horizon = min(48.0, max(12.0, float(total_duration or 0) * 0.35 or 36.0))

        best_onset = cluster_onset
        best_score = -1.0
        for idx in range(1, len(words)):
            t = _start(words[idx])
            if t > horizon:
                break
            gap = t - _end(words[idx - 1])
            if gap < 1.6:
                continue
            before = words[:idx]
            after = words[idx:min(len(words), idx + 14)]
            if len(after) < 4:
                continue
            before_span = max(0.15, _end(before[-1]) - _start(before[0])) if before else 0.15
            after_span = max(0.15, _end(after[-1]) - _start(after[0]))
            before_density = (len(before) / before_span) if before else 0.0
            after_density = len(after) / after_span
            if after_density < 0.75:
                continue
            score = gap * after_density - (before_density * 0.6)
            if len(before) <= 7:
                score += 2.2
            if score > best_score:
                best_score = score
                best_onset = t

        if best_score > 0:
            return round(best_onset, 3)
        return round(cluster_onset, 3)

    @staticmethod
    def _first_dense_cluster_start(
        words: List[Dict[str, Any]],
        min_words: int = 5,
        max_internal_gap: float = 1.05,
    ) -> float:
        if not words:
            return 0.0
        i = 0
        n = len(words)
        while i < n:
            cluster = [words[i]]
            j = i + 1
            while j < n:
                gap = float(words[j].get("start") or 0) - float(cluster[-1].get("end") or 0)
                if gap > max_internal_gap:
                    break
                cluster.append(words[j])
                j += 1
            span = float(cluster[-1].get("end") or 0) - float(cluster[0].get("start") or 0)
            if len(cluster) >= min_words and span >= 1.8:
                return float(cluster[0].get("start") or 0)
            i = j if j > i else i + 1
        return float(words[0].get("start") or 0)

    @staticmethod
    def align_custom_lines(lines: List[Dict[str, Any]], transcript_words: List[Dict[str, Any]], total_duration: float) -> List[Dict[str, Any]]:
        """Map uploaded lyric lines onto audio word timings when transcript text is available."""
        if not lines or not transcript_words:
            return lines

        def clean(value: str) -> str:
            # Keep letters/numbers from any script; strip marks and punctuation.
            return re.sub(r"[^\w']", "", value.lower(), flags=re.UNICODE)

        audio_words = [w for w in transcript_words if clean(str(w.get("text", "")))]
        audio_tokens = [clean(str(w.get("text", ""))) for w in audio_words]
        if not audio_words:
            return lines

        vocal_onset = AlignmentEngine.estimate_vocal_onset(audio_words, total_duration)
        # Skip sparse intro hallucinations when searching for the first lyric lock.
        cursor = 0
        if vocal_onset > 1.0:
            for idx, word in enumerate(audio_words):
                if float(word.get("start") or 0) >= vocal_onset - 0.05:
                    cursor = idx
                    break

        aligned = []
        match_flags: List[bool] = []
        for line_index, line in enumerate(lines):
            line["text"] = AlignmentEngine.polish_lyric_text(str(line.get("text", "")).strip())
            lyric_tokens = [clean(token) for token in str(line.get("text", "")).split() if clean(token)]
            best_start, best_score = cursor, 0.0
            # Wider search window helps choir tracks where verses repeat and Whisper drifts.
            # First line also scans further so a strong verse match beats an intro ghost.
            window_span = max(120, len(lyric_tokens) * 12)
            if line_index == 0:
                window_span = max(window_span, 220)
            search_end = min(len(audio_tokens), cursor + window_span)
            for start in range(cursor, max(cursor + 1, search_end)):
                window = audio_tokens[start:min(len(audio_tokens), start + max(1, len(lyric_tokens)) + 4)]
                if not window or not lyric_tokens:
                    continue
                compare = window[:len(lyric_tokens)]
                score = SequenceMatcher(None, lyric_tokens, compare).ratio()
                # Bonus only for a true first-word anchor (important for Swahili verses).
                if lyric_tokens[0] == window[0]:
                    score = min(1.0, score + 0.12)
                elif lyric_tokens[0] not in window[:2]:
                    # Reject loose overlaps on common words like "line" / "you".
                    score *= 0.55
                start_time = float(audio_words[start].get("start") or 0.0)
                # Penalize locking lyrics onto instrumental / hallucinated intro words.
                if vocal_onset > 1.5 and start_time < vocal_onset - 0.35:
                    score *= 0.28
                elif line_index == 0 and start_time < 5.0 and vocal_onset > 8.0:
                    score *= 0.65
                if score > best_score:
                    best_start, best_score = start, score

            # Short lines need a first-word lock or a very strong overall score.
            if len(lyric_tokens) <= 3:
                first_locked = bool(lyric_tokens) and best_start < len(audio_tokens) and lyric_tokens[0] == audio_tokens[best_start]
                matched = bool(lyric_tokens) and ((first_locked and best_score >= 0.5) or best_score >= 0.78)
            else:
                matched = best_score >= 0.45 and bool(lyric_tokens)
            # Refuse a weak first-line lock that still sits in the intro bed.
            if matched and line_index == 0 and vocal_onset > 2.0:
                candidate_start = float(audio_words[best_start].get("start") or 0.0)
                if candidate_start < vocal_onset - 0.5 and best_score < 0.82:
                    matched = False
            if matched:
                end_index = min(len(audio_words), best_start + max(1, len(lyric_tokens)))
                start_time = float(audio_words[best_start].get("start", line["start"]))
                end_time = float(audio_words[end_index - 1].get("end", line["end"]))
                original_tokens = str(line.get("text", "")).split()
                word_timings = []
                for index, token in enumerate(lyric_tokens):
                    source = audio_words[min(best_start + index, end_index - 1)]
                    word_text = original_tokens[index] if index < len(original_tokens) else token
                    if index == 0:
                        word_text = AlignmentEngine.polish_lyric_text(word_text)
                    word_timings.append({
                        "text": word_text,
                        "start": source.get("start", start_time),
                        "end": source.get("end", end_time),
                    })
                line["start"] = round(start_time, 3)
                line["end"] = round(max(start_time + 0.1, end_time), 3)
                line["words"] = word_timings
                line["confidence"] = round(min(1.0, 0.55 + best_score * 0.45), 2)
                cursor = max(cursor + 1, end_index)
                match_flags.append(True)
            else:
                line["confidence"] = 0.35
                match_flags.append(False)
            aligned.append(line)

        # Interpolate unmatched lines between matched anchors so verses don't stay evenly-spaced.
        AlignmentEngine._interpolate_unmatched_lines(
            aligned,
            match_flags,
            total_duration,
            vocal_onset=vocal_onset,
        )
        AlignmentEngine._snap_early_lines_to_vocals(aligned, match_flags, vocal_onset)
        return aligned

    @staticmethod
    def _shift_line_times(line: Dict[str, Any], delta: float) -> None:
        if abs(delta) < 0.001:
            return
        line["start"] = round(max(0.0, float(line.get("start") or 0) + delta), 3)
        line["end"] = round(max(line["start"] + 0.1, float(line.get("end") or 0) + delta), 3)
        words = []
        for word in line.get("words") or []:
            w_start = round(max(0.0, float(word.get("start") or 0) + delta), 3)
            w_end = round(max(w_start + 0.05, float(word.get("end") or 0) + delta), 3)
            words.append({**word, "start": w_start, "end": w_end})
        if words:
            line["words"] = words

    @staticmethod
    def _snap_early_lines_to_vocals(
        lines: List[Dict[str, Any]],
        matched: List[bool],
        vocal_onset: float,
    ) -> None:
        """If the first lines still sit in the intro, slide the early block to vocal onset."""
        if not lines or vocal_onset <= 1.25:
            return
        first_start = float(lines[0].get("start") or 0)
        if first_start >= vocal_onset - 0.35:
            return
        # Only repair when the opening block is clearly early (not a one-line timing quirk).
        early_prefix = 0
        for line in lines[: min(4, len(lines))]:
            if float(line.get("start") or 0) < vocal_onset - 0.2:
                early_prefix += 1
        if early_prefix < 1:
            return
        delta = vocal_onset - first_start
        if delta < 0.4:
            return
        # Shift the early unmatched / early-matched prefix only; stop once a later
        # line is already past onset (those timings are usually trustworthy).
        for idx, line in enumerate(lines):
            start = float(line.get("start") or 0)
            if start >= vocal_onset + 0.15 and (idx == 0 or matched[idx]):
                break
            if start < vocal_onset + 0.15:
                AlignmentEngine._shift_line_times(line, delta)

    @staticmethod
    def _interpolate_unmatched_lines(
        lines: List[Dict[str, Any]],
        matched: List[bool],
        total_duration: float,
        vocal_onset: float = 0.0,
    ) -> None:
        if not lines or not matched or not any(matched):
            return
        n = len(lines)
        i = 0
        while i < n:
            if matched[i]:
                i += 1
                continue
            start_i = i
            while i < n and not matched[i]:
                i += 1
            end_i = i  # exclusive
            # Leading unmatched lines must not fill the instrumental intro from t=0.
            if start_i == 0:
                next_start = float(lines[end_i]["start"]) if end_i < n else float(total_duration or 0)
                prev_end = max(float(vocal_onset or 0), next_start - max(1.2, (end_i - start_i) * 2.2))
                prev_end = min(prev_end, max(0.0, next_start - 0.35))
            else:
                prev_end = float(lines[start_i - 1]["end"])
            next_start = float(lines[end_i]["start"]) if end_i < n else max(prev_end + 1.0, float(total_duration or prev_end + 1.0))
            span = max(0.4, next_start - prev_end)
            gap_count = end_i - start_i
            slot = span / (gap_count + 1)
            for offset in range(gap_count):
                idx = start_i + offset
                line_start = round(prev_end + slot * (offset + 0.15), 3)
                line_end = round(min(next_start - 0.05, line_start + max(0.45, slot * 0.85)), 3)
                if line_end <= line_start:
                    line_end = round(line_start + 0.4, 3)
                text = str(lines[idx].get("text", "")).strip()
                tokens = text.split()
                words = []
                if tokens:
                    step = max(0.05, (line_end - line_start) / len(tokens))
                    for w_i, token in enumerate(tokens):
                        w_start = round(line_start + w_i * step, 3)
                        w_end = round(line_start + (w_i + 1) * step, 3)
                        words.append({"text": token, "start": w_start, "end": w_end})
                lines[idx]["start"] = line_start
                lines[idx]["end"] = line_end
                lines[idx]["words"] = words
                lines[idx]["confidence"] = max(float(lines[idx].get("confidence") or 0), 0.45)

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
    def line_limits_for_language(language: str | None = None) -> Dict[str, float | int]:
        """Tune on-screen line length for scripts that pack more meaning per glyph."""
        code = (language or "").strip().lower()
        if code in {"zh", "ja", "ko"}:
            return {"max_words": 8, "max_chars": 28, "pause_threshold": 0.45}
        if code in {"th", "lo", "km", "my"}:
            return {"max_words": 9, "max_chars": 36, "pause_threshold": 0.5}
        if code in {"ar", "fa", "ur", "he"}:
            return {"max_words": 9, "max_chars": 48, "pause_threshold": 0.55}
        return {"max_words": 10, "max_chars": 56, "pause_threshold": 0.65}

    @staticmethod
    def trim_intro_hallucination_words(
        words: List[Dict[str, Any]],
        total_duration: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Drop sparse Whisper ghosts before the estimated vocal onset."""
        if not words:
            return []
        onset = AlignmentEngine.estimate_vocal_onset(words, total_duration)
        if onset <= 1.25:
            return words
        trimmed = [w for w in words if float(w.get("start") or 0) >= onset - 0.2]
        # Keep the original stream if trimming would throw away most of the song.
        if len(trimmed) < max(4, int(len(words) * 0.45)):
            return words
        return trimmed

    @staticmethod
    def segment_lines(
        words: List[Dict[str, Any]],
        max_words: int = 10,
        max_chars: int = 56,
        pause_threshold: float = 0.65,
        language: str | None = None,
        total_duration: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        Stage B: Deterministic line segmentation heuristics.
        Groups words into readable lyric lines based on:
        - Maximum words per line
        - Maximum visible characters
        - Pause gaps (> pause_threshold seconds)
        - Punctuation cues across Latin, CJK, and Arabic scripts
        """
        if not words:
            return []

        words = AlignmentEngine.trim_intro_hallucination_words(words, total_duration)

        if language:
            limits = AlignmentEngine.line_limits_for_language(language)
            max_words = int(limits["max_words"])
            max_chars = int(limits["max_chars"])
            pause_threshold = float(limits["pause_threshold"])

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
                if _LINE_BREAK_PUNCT.search(prev_text):
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

    @staticmethod
    def polish_lyric_text(text: str) -> str:
        """Uppercase the first Latin letter without lowercasing the rest of the line.

        Full ``str.capitalize()`` rewrites the remainder of the string and damages
        non-English lyrics. Scripts that are not Latin are left unchanged.
        """
        cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
        if not cleaned:
            return cleaned
        chars = list(cleaned)
        for index, char in enumerate(chars):
            if not char.isalpha():
                continue
            if char.isascii():
                chars[index] = char.upper()
            break
        return "".join(chars)
