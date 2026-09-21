# Regression tests for the stages that can change your words between the
# microphone and the cursor. Each case here corresponds to a real failure found
# in the 2026-09-19 dictation quality audit:
#
#   - _strip_fillers deleted the ordinary English words "like" and "you know",
#     turning "I would like to see" into "I would to see".
#   - The LLM polish stage replaced the transcript with whatever the model
#     returned, including a 44-character sentence delivered as "Jax".
#   - _trim_long_pauses gated silence against a fixed RMS, so a quiet microphone
#     read as one long silence and had its speech spliced away.

import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


class StripFillersTests(unittest.TestCase):
    """"like" and "you know" are only fillers when fenced by commas."""

    def setUp(self):
        from whisper_key.text_postprocess import _strip_fillers
        self.strip = _strip_fillers

    def test_content_words_survive(self):
        for text in (
            "a tool like Power BI",
            "I would like to see the measure",
            "much like you can see here",
            "you know the answer already",
        ):
            self.assertEqual(self.strip(text), text)

    def test_hedges_are_removed(self):
        self.assertEqual(self.strip("So, like, we shipped it."), "So, we shipped it.")
        self.assertEqual(self.strip("It was, you know, fine."), "It was, fine.")

    def test_um_and_uh_always_go(self):
        self.assertEqual(self.strip("Um, the report is slow."), "the report is slow.")
        self.assertEqual(self.strip("The uh model is large."), "The model is large.")
        self.assertEqual(self.strip("Umm, maybe."), "maybe.")

    def test_never_returns_empty(self):
        self.assertEqual(self.strip("um"), "um")


class PolishGuardTests(unittest.TestCase):
    """The LLM may punctuate. It may not rewrite."""

    def setUp(self):
        from whisper_key.text_postprocess import _polish_is_safe
        self.safe = _polish_is_safe

    def test_truncation_rejected(self):
        self.assertFalse(self.safe("x" * 44, "Jax", {}))
        self.assertFalse(self.safe("y" * 83, "I love it. The report is awesome.", {}))

    def test_paraphrase_rejected(self):
        self.assertFalse(self.safe(
            "the report is slow we should fix it",
            "The dashboard performs poorly and needs attention.", {}))

    def test_punctuation_accepted(self):
        self.assertTrue(self.safe(
            "the report is slow we should fix it",
            "The report is slow. We should fix it.", {}))
        self.assertTrue(self.safe("Hello world.", "Hello world.", {}))

    def test_thresholds_are_configurable(self):
        self.assertTrue(self.safe(
            "x" * 100, "x" * 50, {'max_length_shrink': 0.9, 'min_similarity': 0.1}))


class TrimLongPausesTests(unittest.TestCase):
    """Splicing must find real pauses without eating quiet speech."""

    @classmethod
    def setUpClass(cls):
        from whisper_key.audio_recorder import AudioRecorder
        cls.AudioRecorder = AudioRecorder
        cls.sr = AudioRecorder.WHISPER_SAMPLE_RATE
        cls.rng = np.random.default_rng(0)

    # Called unbound so no audio device is opened.
    def trim(self, audio):
        return self.AudioRecorder._trim_long_pauses(self.AudioRecorder, audio)

    def speech(self, seconds, level=1.0):
        return (self.rng.standard_normal(int(self.sr * seconds)) * 0.2 * level).astype(np.float32)

    def silence(self, seconds):
        return np.zeros(int(self.sr * seconds), dtype=np.float32)

    def test_counts_interior_cuts(self):
        clip = np.concatenate([self.speech(2), self.silence(4), self.speech(2)])
        out, cuts = self.trim(clip)
        self.assertEqual(cuts, 1)
        self.assertLess(len(out), len(clip))

        clip = np.concatenate([
            self.speech(2), self.silence(4), self.speech(2), self.silence(5), self.speech(2)])
        self.assertEqual(self.trim(clip)[1], 2)

    def test_short_pause_left_alone(self):
        clip = np.concatenate([self.speech(3), self.silence(0.5), self.speech(3)])
        out, cuts = self.trim(clip)
        self.assertEqual(cuts, 0)
        self.assertEqual(len(out), len(clip))

    def test_continuous_speech_untouched(self):
        self.assertEqual(self.trim(self.speech(8))[1], 0)

    def test_quiet_microphone_speech_is_not_spliced_away(self):
        # Every window sits far below the old absolute 0.005 gate.
        quiet = np.concatenate([
            self.speech(2, level=0.075), self.silence(4), self.speech(2, level=0.075)])
        out, cuts = self.trim(quiet)
        self.assertEqual(cuts, 1)
        self.assertGreater(len(out), self.sr * 3, "quiet speech was mistaken for silence")

        quiet = np.concatenate([
            self.speech(3, level=0.075), self.silence(0.5), self.speech(3, level=0.075)])
        out, cuts = self.trim(quiet)
        self.assertEqual(cuts, 0)
        self.assertEqual(len(out), len(quiet))


class TranscriptLogTests(unittest.TestCase):
    """The journal must be able to tell a decode error from a rewrite."""

    def test_record_transcript_accepts_raw(self):
        import inspect
        from whisper_key.transcript_log import record_transcript
        self.assertIn('raw', inspect.signature(record_transcript).parameters)


if __name__ == "__main__":
    unittest.main()
