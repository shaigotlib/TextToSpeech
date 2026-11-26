import unittest
from src.text_model import TextDocument, WordSpan

class TestTextModel(unittest.TestCase):
    def test_english_tokenization_and_spans(self):
        text = "The quick brown fox."
        doc = TextDocument(text)
        self.assertEqual(doc.total_words, 4)
        words = [span.text for span in doc.spans]
        self.assertEqual(words, ["The", "quick", "brown", "fox"])

        # Verify span offsets
        self.assertEqual(doc.spans[0].char_start, 0)
        self.assertEqual(doc.spans[0].char_end, 3)
        self.assertEqual(doc.spans[1].char_start, 4)
        self.assertEqual(doc.spans[1].char_end, 9)

    def test_hebrew_tokenization(self):
        text = "שלום עולם! זהו מבחן."
        doc = TextDocument(text)
        self.assertEqual(doc.total_words, 4)
        words = [span.text for span in doc.spans]
        self.assertEqual(words, ["שלום", "עולם", "זהו", "מבחן"])

    def test_char_offset_to_word_index(self):
        text = "First second third fourth"
        doc = TextDocument(text)
        # char offsets:
        # "First" [0..5]
        # "second" [6..12]
        # "third" [13..18]
        # "fourth" [19..25]
        self.assertEqual(doc.get_word_index_by_char_offset(0), 0)
        self.assertEqual(doc.get_word_index_by_char_offset(3), 0)
        self.assertEqual(doc.get_word_index_by_char_offset(6), 1)
        self.assertEqual(doc.get_word_index_by_char_offset(10), 1)
        self.assertEqual(doc.get_word_index_by_char_offset(13), 2)
        self.assertEqual(doc.get_word_index_by_char_offset(19), 3)
        self.assertEqual(doc.get_word_index_by_char_offset(100), 3)  # Past end clamps to last

    def test_word_index_to_char_offset(self):
        text = "First second third fourth"
        doc = TextDocument(text)
        self.assertEqual(doc.get_char_offset_for_word_index(0), 0)
        self.assertEqual(doc.get_char_offset_for_word_index(1), 6)
        self.assertEqual(doc.get_char_offset_for_word_index(2), 13)
        self.assertEqual(doc.get_char_offset_for_word_index(3), 19)
        self.assertEqual(doc.get_char_offset_for_word_index(10), 19)

    def test_clamp_word_index(self):
        text = "One two three"
        doc = TextDocument(text)
        self.assertEqual(doc.clamp_word_index(-5), 0)
        self.assertEqual(doc.clamp_word_index(1), 1)
        self.assertEqual(doc.clamp_word_index(5), 2)

    def test_empty_or_whitespace_text(self):
        doc = TextDocument("   \n\t  ")
        self.assertEqual(doc.total_words, 0)
        self.assertEqual(doc.clamp_word_index(0), 0)
        self.assertEqual(doc.get_word_index_by_char_offset(0), 0)
        self.assertEqual(doc.get_char_offset_for_word_index(0), 0)

    def test_word_timestamps_calculation(self):
        text = "One two three four"
        doc = TextDocument(text)
        total_duration_ms = 4000
        timestamps = doc.get_word_timestamps(total_duration_ms)
        self.assertEqual(len(timestamps), 4)
        self.assertEqual(timestamps[0], 0)
        self.assertTrue(0 < timestamps[1] < timestamps[2] < timestamps[3] < total_duration_ms)


if __name__ == "__main__":
    unittest.main()
