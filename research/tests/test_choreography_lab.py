"""Tests for the choreography lab (research/choreography/): layout, feeds, measures, and a rendered clip."""
import unittest

import numpy as np

from research.choreography import measures
from research.choreography.feeds import FPS, SLOTS, Feed
from research.choreography.layout import load_layout
from research.choreography.render import CLIP_FPS, brightness, render_clip


class _Record:
    """Stand-in for MusicSignals: any slot can be set."""


class TestLayout(unittest.TestCase):
    def test_the_installation_has_eleven_segments_and_1304_leds(self):
        layout = load_layout()
        self.assertEqual(len(layout.segments), 11)
        self.assertEqual(layout.total, 1304)
        self.assertEqual(layout.xy.shape, (1304, 2))
        self.assertEqual(sum(s.size for s in layout.segments), 1304)
        v1 = next(s for s in layout.segments if s.seg_id == "v1")
        np.testing.assert_allclose(layout.xy[v1.offset], [205, 188])
        np.testing.assert_allclose(layout.xy[v1.offset + 1], [205, 187])     # a pillar climbs


class TestFeed(unittest.TestCase):
    def test_apply_writes_typed_values_and_leaves_missing_slots_alone(self):
        n = 10
        kick = np.zeros(n, dtype=np.float32)
        kick[3] = 0.7
        present = np.ones(n, dtype=np.float32)
        bass = np.full(n, np.nan, dtype=np.float32)
        feed = Feed("test", {"kick": kick, "kick_present": present, "band_bass": bass, "bar_position": np.full(n, 2.0, dtype=np.float32)})
        rec = _Record()
        rec.band_bass = 0.33                         # what the Listener had set
        feed.apply(3, rec)
        self.assertAlmostEqual(rec.kick, 0.7, places=5)
        self.assertIs(rec.kick_present, True)
        self.assertEqual(rec.bar_position, 2)
        self.assertIsInstance(rec.bar_position, int)
        self.assertEqual(rec.band_bass, 0.33)        # NaN in the feed: untouched
        feed.apply(99, rec)                          # past the end: nothing happens
        self.assertEqual(feed.provides(), ["bar_position", "kick", "kick_present"])
        self.assertTrue(set(feed.columns) <= set(SLOTS))


class TestMeasures(unittest.TestCase):
    def test_kick_punch_tells_a_light_that_follows_the_kicks_from_one_that_does_not(self):
        fps, seconds = 30.0, 20.0
        t = np.arange(int(seconds * fps)) / fps
        kicks = np.arange(1.0, 19.0, 0.5)
        follows = np.zeros(len(t))
        for k in kicks:
            follows += 0.6 * np.exp(-np.clip(t - k, 0, None) / 0.12) * (t >= k)
        steady = np.full(len(t), 0.5)
        good = measures.kick_punch(follows, fps, kicks)
        flat = measures.kick_punch(steady, fps, kicks)
        self.assertGreater(good["contrast"], 0.3)
        self.assertAlmostEqual(flat["contrast"], 0.0, places=6)
        self.assertTrue(np.isnan(measures.kick_punch(follows, fps, kicks[:2])["contrast"]))    # too few kicks to say

    def test_alive(self):
        bright = np.array([0.0, 0.0, 0.3, 0.5, 0.3, 0.5])
        silent = np.array([True, True, False, False, False, False])
        res = measures.alive(bright, silent)
        self.assertEqual(res["lit"], 1.0)
        self.assertGreater(res["movement"], 0.05)


class TestRenderedClip(unittest.TestCase):
    """A made-up song with a thump every half second; the lab mode fed with those kicks must punch on them."""

    @classmethod
    def setUpClass(cls):
        from research.choreography.candidates.Kick_bands_mode import Kick_bands_mode

        sr = 44100
        rng = np.random.default_rng(0)
        mono = (0.05 * rng.standard_normal(13 * sr)).astype(np.float32)
        burst_t = np.arange(int(0.12 * sr)) / sr
        burst = (0.8 * np.sin(2 * np.pi * 60.0 * burst_t) * np.exp(-burst_t / 0.04)).astype(np.float32)
        cls.kicks = np.arange(1.0, 12.0, 0.5)
        for t in cls.kicks:
            i = int(t * sr)
            mono[i : i + len(burst)] += burst
        n = int(13 * FPS)
        kick = np.zeros(n, dtype=np.float32)
        kick[np.round(cls.kicks * FPS).astype(int)] = 0.9
        feed = Feed("made-up truth", {"kick": kick, "band_bass": np.full(n, 0.5, dtype=np.float32),
                                      "band_mid": np.full(n, 0.3, dtype=np.float32), "band_high": np.full(n, 0.3, dtype=np.float32),
                                      "snare": np.zeros(n, dtype=np.float32), "drop": np.zeros(n, dtype=np.float32)})
        cls.start, cls.duration = 6.0, 5.0
        cls.layout = load_layout()
        cls.frames = render_clip(Kick_bands_mode, mono, cls.layout, feed, cls.start, cls.duration)
        cls.frames_today = render_clip(Kick_bands_mode, mono, cls.layout, None, cls.start, cls.duration)

    def test_shape_and_light(self):
        self.assertEqual(self.frames.shape, (int(self.duration * CLIP_FPS), 1304, 3))
        self.assertEqual(self.frames.dtype, np.uint8)
        self.assertGreater(float(brightness(self.frames).mean()), 0.05)
        self.assertEqual(self.frames_today.shape, self.frames.shape)       # the fallbacks run without a feed

    def test_the_light_punches_on_the_kicks_it_is_fed(self):
        inside = [k - self.start for k in self.kicks if self.start <= k < self.start + self.duration]
        res = measures.kick_punch(brightness(self.frames), CLIP_FPS, inside)
        self.assertGreater(res["contrast"], 0.05)
        self.assertGreater(res["on_kick"], res["between"])

    def test_same_input_gives_the_same_frames(self):
        from research.choreography.candidates.Kick_bands_mode import Kick_bands_mode

        sr = 44100
        mono = np.zeros(8 * sr, dtype=np.float32)
        a = render_clip(Kick_bands_mode, mono, self.layout, None, 6.0, 1.0)
        b = render_clip(Kick_bands_mode, mono, self.layout, None, 6.0, 1.0)
        np.testing.assert_array_equal(a, b)


if __name__ == "__main__":
    unittest.main()
