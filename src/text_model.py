from dataclasses import dataclass
from typing import List
import re

@dataclass
class WordSpan:
    index: int
    text: str
    char_start: int
    char_end: int
    char_length: int


class TextDocument:
    """Tokenizes text into words and tracks word positions for forward/backward navigation."""

    def __init__(self, raw_text: str):
        self.raw_text = raw_text or ""
        self.spans: List[WordSpan] = []
        self._tokenize()

    def _tokenize(self) -> None:
        if not self.raw_text:
            return

        # Matches Unicode word characters, including Hebrew ֐-׿ and intra-word hyphens/apostrophes
        pattern = re.compile(r"[\w֐-׿]+(?:[-'֫-ֿ][\w֐-׿]+)*", re.UNICODE)
        spans = []
        for idx, match in enumerate(pattern.finditer(self.raw_text)):
            start, end = match.span()
            word_text = match.group(0)
            spans.append(
                WordSpan(
                    index=idx,
                    text=word_text,
                    char_start=start,
                    char_end=end,
                    char_length=end - start,
                )
            )
        self.spans = spans

    @property
    def total_words(self) -> int:
        return len(self.spans)

    def clamp_word_index(self, index: int) -> int:
        if not self.spans:
            return 0
        return max(0, min(index, len(self.spans) - 1))

    def get_word_index_by_char_offset(self, char_offset: int) -> int:
        """Find the word index corresponding to a character offset."""
        if not self.spans:
            return 0
        if char_offset >= self.spans[-1].char_end:
            return len(self.spans) - 1

        for idx, span in enumerate(self.spans):
            if span.char_start <= char_offset < span.char_end:
                return idx
            if char_offset < span.char_start:
                return max(0, idx - 1)
        return len(self.spans) - 1

    def get_char_offset_for_word_index(self, word_index: int) -> int:
        """Get the starting character offset for a given word index."""
        if not self.spans:
            return 0
        clamped = self.clamp_word_index(word_index)
        return self.spans[clamped].char_start

    def get_word_timestamps(self, total_duration_ms: int) -> List[int]:
        """Estimate millisecond timestamp for each word based on character length and punctuation."""
        if not self.spans or total_duration_ms <= 0:
            return [0] * len(self.spans)

        weights = []
        for span in self.spans:
            weight = span.char_length
            # If followed by punctuation like comma or period, add slight pause weight
            trailing_slice = self.raw_text[span.char_end : span.char_end + 2]
            if any(p in trailing_slice for p in ".,!?;:"):
                weight += 2
            weights.append(weight)

        total_weight = sum(weights) or 1
        timestamps = []
        cumulative_weight = 0
        for w in weights:
            timestamps.append(int((cumulative_weight / total_weight) * total_duration_ms))
            cumulative_weight += w

        return timestamps
