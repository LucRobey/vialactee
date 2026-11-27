"""The live-sound road (Spotify, aux) against the audio-file road, on a made-up song with a steady kick at 122 BPM.

These tests keep the measurement honest:
- the old live road (analyzer ticked by the 30-per-second display loop, as the code was until 2026-11-27)
  loses the place of the beats; the real connector, fixed since, is tested in tests/test_local_microphone_clock.py;
- a one-frame beat flag raised at 60 ticks a second is seen only about half the time by a 30-per-second
  reader. This is still true of the installation and is expected to change when such flags are held.
"""
import unittest

import numpy as np

from research.scoreboard.live_path import HOP, SR, WINDOW, _window, replay


def _on_time(beats: np.ndarray, kicks: np.ndarray, after: float = 12.0, tol: float = 0.05) -> float:
    """Share of the kicks after the warm-up that have a reported beat within 50 ms."""
    late = kicks[kicks >= after]
    if not len(beats) or not len(late):
        return 0.0
    return float(np.mean([np.min(np.abs(beats - k)) <= tol for k in late]))


class TestLivePath(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng = np.random.default_rng(0)
        mono = (0.02 * rng.standard_normal(30 * SR)).astype(np.float32)
        burst_t = np.arange(int(0.12 * SR)) / SR
        burst = (0.8 * np.sin(2 * np.pi * 60.0 * burst_t) * np.exp(-burst_t / 0.04)).astype(np.float32)
        cls.kicks = np.arange(1.0, 29.0, 0.4917)      # 122 BPM: beats do not always fall on the same tick parity
        for t in cls.kicks:
            i = int(t * SR)
            mono[i : i + len(burst)] += burst
        cls.runs = {p: replay(mono, p) for p in ("file", "live", "audio_clock", "audio_clock_held")}

    def test_window_ends_where_asked(self):
        mono = np.arange(10000, dtype=np.float32)
        w = _window(mono, 5000)
        self.assertEqual(len(w), WINDOW)
        self.assertEqual(w[-1], 4999.0)
        self.assertEqual(w[0], 5000.0 - WINDOW)
        start = _window(mono, 100)
        self.assertEqual(start[-1], 99.0)
        self.assertEqual(start[0], 0.0)                      # nothing before the song
        self.assertEqual(HOP * 60, SR)

    def test_the_file_road_finds_the_beats(self):
        self.assertGreater(_on_time(self.runs["file"]["emitted"], self.kicks), 0.9)

    def test_the_old_live_road_ticked_at_30_loses_them(self):
        live = _on_time(self.runs["live"]["emitted"], self.kicks)
        self.assertLess(live, 0.5, "the old road should lose the beats: has the replay of it changed?")

    def test_ticking_by_the_audio_restores_them(self):
        self.assertGreater(_on_time(self.runs["audio_clock"]["emitted"], self.kicks), 0.9)

    def test_a_30_fps_reader_misses_one_frame_flags_unless_they_are_held(self):
        for path in ("file", "audio_clock"):
            run = self.runs[path]
            share = len(run["seen"]) / max(1, len(run["emitted"]))
            self.assertLess(share, 0.75, path)
        held = self.runs["audio_clock_held"]
        self.assertEqual(len(held["seen"]), len(held["emitted"]))


if __name__ == "__main__":
    unittest.main()
