"""Tests for the mode profile (research/choreography/profile.py) and its pictures, on a made-up show."""
import os
import tempfile
import unittest
from pathlib import Path

import numpy as np

from research.choreography import pictures
from research.choreography.feeds import _held
from research.choreography.layout import load_layout
from research.choreography.profile import describe, profile, reaction

FPS = 30.0


def _made_up_show(layout, kick_times, seconds=20.0, break_from=8.0, break_to=12.0):
    """Frames where the low LEDs flash cyan on every kick and the top glows red with the treble; calm in the break."""
    n = int(seconds * FPS)
    t = np.arange(n) / FPS
    alt = 1.0 - layout.xy[:, 1] / 245.0
    low, top = alt < 1 / 3, alt > 2 / 3
    pulse = np.zeros(n)
    for k in kick_times:
        pulse += np.exp(-np.clip(t - k, 0, None) / 0.1) * (t >= k)
    treble = 0.5 + 0.4 * np.sin(2 * np.pi * t / 5.0)
    frames = np.zeros((n, layout.total, 3), dtype=np.uint8)
    frames[:, low, 1] = frames[:, low, 2] = (40 + 200 * np.clip(pulse, 0, 1))[:, None].astype(np.uint8)
    frames[:, top, 0] = (220 * treble)[:, None].astype(np.uint8)
    in_break = (t >= break_from) & (t < break_to)
    truth = {
        "events": {"kick": np.array(kick_times), "snare": np.array([]), "beat": np.array(kick_times),
                   "drop": np.array([break_to]), "section_change": np.array([])},
        "bars": np.array(kick_times[::4]),
        "masks": {"no_beat": np.zeros(n, dtype=bool), "breakdown": in_break, "silence": np.zeros(n, dtype=bool),
                  "kick_present": ~in_break, "buildup": np.zeros(n, dtype=bool)},
        "levels": {"loudness": 0.5 + 0.3 * np.clip(pulse, 0, 1), "band_bass": np.clip(pulse, 0, 1), "band_mid": np.full(n, 0.5), "band_high": treble},
    }
    return frames, truth


class TestReaction(unittest.TestCase):
    def test_a_flash_is_measured_with_its_size_delay_and_fade(self):
        t = np.arange(int(20 * FPS)) / FPS
        kicks = np.arange(1.0, 19.0, 0.5)
        bright = np.full(len(t), 0.1)
        for k in kicks:
            bright += 0.4 * np.exp(-np.clip(t - k - 0.033, 0, None) / 0.1) * (t >= k + 0.033)
        r = reaction(bright, FPS, kicks)
        self.assertGreater(r["jump"], 0.3)
        self.assertAlmostEqual(r["delay_ms"], 33.3, delta=34.0)
        self.assertIsNotNone(r["half_life_ms"])
        self.assertLess(r["half_life_ms"], 150.0)
        self.assertIsNone(reaction(bright, FPS, kicks[:2]))            # too few events to say
        flat = reaction(np.full(len(t), 0.3), FPS, kicks)
        self.assertAlmostEqual(flat["jump"], 0.0, places=6)


class TestProfile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layout = load_layout()
        kicks = [k for k in np.arange(1.0, 19.5, 0.5) if not 8.0 <= k < 12.0]
        cls.frames, cls.truth = _made_up_show(cls.layout, kicks)
        cls.p = profile(cls.frames, FPS, cls.layout, cls.truth)
        cls.words = " ".join(describe(cls.p))

    def test_reactions_and_contrast(self):
        self.assertGreater(self.p["reactions"]["kick"]["jump"], 0.08)
        self.assertLess(self.p["reactions"]["between_kicks"]["jump"], 0.02)
        self.assertGreater(self.p["kick_contrast"], 0.08)
        self.assertIsNone(self.p["reactions"]["snare"])
        self.assertIn("Punches on the kick", self.words)
        self.assertIn("Too few snares", self.words)

    def test_the_break_is_seen_as_calm(self):
        st = self.p["stretches"]["breakdown"]
        self.assertAlmostEqual(st["share_of_passage"], 0.2, delta=0.02)
        self.assertLess(st["movement_ratio"], 0.3)
        self.assertIn("In a break", self.words)
        self.assertIsNone(self.p["stretches"]["no_beat"])

    def test_space_and_colour(self):
        sp = self.p["space"]
        self.assertGreater(sp["low_follows_bass"], 0.9)
        self.assertGreater(sp["top_follows_treble"], 0.9)
        self.assertLess(abs(sp["low_follows_treble"]), 0.5)
        self.assertEqual(set(self.p["colour"]["dominant"]), {"cyan", "red"})
        self.assertLess(self.p["colour"]["white_share"], 0.05)
        self.assertIn("The bottom follows the bass, the top follows the treble.", self.words)

    def test_light_comfort_and_variety(self):
        self.assertGreater(self.p["light"]["high"], self.p["light"]["low"])
        self.assertLess(self.p["comfort"]["flicker"], 0.3)
        self.assertGreater(self.p["variety"]["bars"], 3)
        self.assertEqual(self.p["light"]["dark_share"], 0.0)

    def test_pictures_are_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            pictures.time_strip(self.frames, self.layout, self.truth, FPS, tmp / "strip.png", "test")
            instants = pictures.choose_instants(self.frames, self.truth, FPS)
            pictures.contact_sheet(self.frames, self.layout, instants, tmp / "sheet.png", "test")
            pictures.reaction_plot(self.p["reactions"], FPS, tmp / "reactions.png", "test")
            for name in ("strip.png", "sheet.png", "reactions.png"):
                self.assertGreater(os.path.getsize(tmp / name), 2000)
            labels = [label for label, _ in instants]
            self.assertTrue(any(l.startswith("on a kick") for l in labels))
            self.assertTrue(any(l.startswith("in the break") for l in labels))
            self.assertTrue(any(l.startswith("on the drop") for l in labels))


class TestHeldValues(unittest.TestCase):
    def test_the_frame_of_a_beat_carries_that_beats_value(self):
        times = np.array([0.5083, 1.0049, 1.4951])            # beats that do not fall on a frame edge
        col = _held(times, np.array([1.0, 2.0, 3.0]), 120)
        for t, v in zip(times, (1.0, 2.0, 3.0)):
            self.assertEqual(col[int(round(t * 60))], v)
        self.assertEqual(col[0], 0.0)                          # nothing before the first beat


if __name__ == "__main__":
    unittest.main()
