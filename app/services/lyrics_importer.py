import re
from typing import List, Dict, Any, Optional

class LyricsImporter:
    """
    Parses custom lyrics in plain text or LRC (timed lyrics) format
    and converts them into canonical LyricSync line and word structures.
    """

    LRC_TIMESTAMP_REGEX = re.compile(r'\[(\d{1,3}):(\d{1,2}(?:\.\d{1,3})?)\]')

    @classmethod
    def is_lrc(cls, text: str) -> bool:
        """Returns True if the text contains multiple LRC timestamp markers."""
        matches = cls.LRC_TIMESTAMP_REGEX.findall(text)
        return len(matches) >= 2

    @classmethod
    def parse_lrc(cls, text: str, total_duration: float = 180.0) -> List[Dict[str, Any]]:
        """
        Parses LRC formatted timed lyrics.
        Handles lines like: [00:15.20] In the quiet of the night
        """
        raw_lines = text.splitlines()
        parsed_entries = []

        for raw_line in raw_lines:
            line_str = raw_line.strip()
            if not line_str:
                continue

            # Check if this is a metadata tag like [ar:Artist] or [ti:Title]
            if re.match(r'^\[[a-zA-Z]{2,4}:.*\]$', line_str):
                continue

            # Find all timestamps in this line
            matches = list(cls.LRC_TIMESTAMP_REGEX.finditer(line_str))
            if not matches:
                continue

            # Text after the last timestamp
            last_match = matches[-1]
            lyric_text = line_str[last_match.end():].strip()
            if not lyric_text:
                continue

            for m in matches:
                mins = int(m.group(1))
                secs = float(m.group(2))
                start_time = round(mins * 60.0 + secs, 3)
                parsed_entries.append({
                    "start": start_time,
                    "text": lyric_text
                })

        if not parsed_entries:
            # Fall back to plain text parsing if no valid timestamped lines were extracted
            return cls.parse_plain_text(text, total_duration)

        # Sort chronologically by start timestamp
        parsed_entries.sort(key=lambda x: x["start"])

        result_lines = []
        for i, entry in enumerate(parsed_entries):
            start = entry["start"]
            text_str = entry["text"]

            # Compute line end timestamp
            if i + 1 < len(parsed_entries):
                next_start = parsed_entries[i + 1]["start"]
                # Leave a tiny 0.15s gap before the next line, clamped between 1.0s and 8.0s
                line_duration = max(1.0, min(8.0, next_start - start))
                end = round(start + max(0.8, line_duration - 0.15), 3)
            else:
                end = round(min(total_duration, start + 4.0), 3)
                if end <= start:
                    end = round(start + 3.0, 3)

            # Generate word-level timings
            words = text_str.split()
            word_list = []
            if words:
                w_duration = (end - start) / len(words)
                for w_idx, w_text in enumerate(words):
                    w_start = round(start + (w_idx * w_duration), 3)
                    w_end = round(start + ((w_idx + 1) * w_duration), 3)
                    word_list.append({
                        "text": w_text,
                        "start": w_start,
                        "end": w_end
                    })

            result_lines.append({
                "id": f"line_{i}",
                "start": start,
                "end": end,
                "text": text_str,
                "words": word_list
            })

        return result_lines

    @classmethod
    def parse_plain_text(cls, text: str, total_duration: float = 180.0) -> List[Dict[str, Any]]:
        """
        Parses untimed plain text lyrics and spaces them evenly across the audio duration.
        """
        raw_lines = [l.strip() for l in text.splitlines() if l.strip()]
        if not raw_lines:
            raise ValueError("No lyric lines found in provided text.")

        num_lines = len(raw_lines)
        total_duration = max(10.0, total_duration)
        lead_in = 1.5
        end_margin = 2.0
        usable_time = max(5.0, total_duration - lead_in - end_margin)

        # Target 2.5 to 5.0 seconds per line
        pace = usable_time / num_lines
        if pace > 5.5:
            pace = 5.0
        elif pace < 1.2:
            pace = 1.2

        result_lines = []
        for i, line_text in enumerate(raw_lines):
            line_start = round(lead_in + (i * pace), 3)
            line_duration = max(1.0, pace * 0.9)
            line_end = round(line_start + line_duration, 3)

            # Ensure within total duration if possible
            if line_start >= total_duration:
                line_start = round(total_duration - 1.5, 3)
                line_end = round(total_duration - 0.2, 3)

            words = line_text.split()
            word_list = []
            if words:
                w_duration = (line_end - line_start) / len(words)
                for w_idx, w_text in enumerate(words):
                    w_start = round(line_start + (w_idx * w_duration), 3)
                    w_end = round(line_start + ((w_idx + 1) * w_duration), 3)
                    word_list.append({
                        "text": w_text,
                        "start": w_start,
                        "end": w_end
                    })

            result_lines.append({
                "id": f"line_{i}",
                "start": line_start,
                "end": line_end,
                "text": line_text,
                "words": word_list
            })

        return result_lines

    @classmethod
    def import_lyrics(cls, text_or_content: str, total_duration: float = 180.0) -> List[Dict[str, Any]]:
        """
        Auto-detects format (LRC vs Plain text) and parses into canonical lyrics.
        """
        cleaned = text_or_content.strip()
        if not cleaned:
            raise ValueError("Lyric content cannot be empty.")

        if cls.is_lrc(cleaned):
            return cls.parse_lrc(cleaned, total_duration)
        return cls.parse_plain_text(cleaned, total_duration)
