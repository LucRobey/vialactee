"""
research/tests/test_audio_loader.py - Unit tests for the cache-aware audio loader in the benchmark engine.

Regression guard: `load_audio_file` used to return the cached `.npz` samples (stored at 44.1 kHz) labelled
with whatever sample rate the caller asked for. A 22.05 kHz caller then received audio at half speed, which
stretched the BeatNet reference beats of every cached track to twice the song length.
"""

import os
import tempfile
import unittest

import numpy as np

from research.benchmarks.engine.evaluator import load_audio_file


class TestCachedAudioLoader(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.audio_path = os.path.join(self.tmp.name, "tone.mp3")  # never decoded: the cache is found first
        self.cached_sr = 44100
        self.seconds = 2.0
        t = np.arange(int(self.cached_sr * self.seconds)) / self.cached_sr
        self.freq = 440.0
        y = (0.5 * np.sin(2 * np.pi * self.freq * t)).astype(np.float32)
        np.savez(self.audio_path + ".npz", y=y, sr=self.cached_sr)

    def tearDown(self):
        self.tmp.cleanup()

    def _dominant_hz(self, y, sr):
        spectrum = np.abs(np.fft.rfft(y))
        return float(np.fft.rfftfreq(len(y), 1.0 / sr)[int(np.argmax(spectrum))])

    def test_same_rate_returns_cache_unchanged(self):
        y, sr = load_audio_file(self.audio_path, target_sr=44100)
        self.assertEqual(sr, 44100)
        self.assertEqual(len(y), int(self.cached_sr * self.seconds))

    def test_lower_rate_keeps_duration_and_pitch(self):
        y, sr = load_audio_file(self.audio_path, target_sr=22050)
        self.assertEqual(sr, 22050)
        self.assertAlmostEqual(len(y) / sr, self.seconds, delta=0.01)  # was 4.0 s before the fix
        self.assertAlmostEqual(self._dominant_hz(y, sr), self.freq, delta=2.0)  # was 220 Hz before the fix


if __name__ == "__main__":
    unittest.main()
