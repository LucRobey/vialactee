"""
Unit tests verifying documentation parity, bug fixes, and single-source-of-truth invariants.
"""
import unittest
import numpy as np
import time

from core.Listener import Listener
import core.Transition_Engine as TE
from hardware.Fake_leds import Fake_leds, FakeLedsVisualizer
from modes.Magnetic_ball_mode import Magnetic_ball_mode


class TestDocsParityAndBugs(unittest.TestCase):
    def setUp(self):
        self.infos_full = {
            "useMicrophone": False,
            "fakeDelay": 0.5,
            "latency": 0.0,
            "onRaspberry": False,
            "HARDWARE_MODE": "simulation",
            "hardware_profile": "full",
        }
        self.infos_small = {
            "useMicrophone": False,
            "fakeDelay": 0.5,
            "latency": 0.0,
            "onRaspberry": False,
            "HARDWARE_MODE": "simulation",
            "hardware_profile": "small",
        }

    def test_listener_delayed_flags_reset(self):
        """Verify delayed novelty flags reset to False when no queued event matches."""
        listener = Listener(self.infos_full)
        # Manually force sticky flags
        listener._delayed_is_song_change = True
        listener._delayed_is_verse_chorus_change = True

        # Run update with empty delay queue
        listener.update()

        self.assertFalse(listener.is_song_change)
        self.assertFalse(listener.is_verse_chorus_change)

    def test_listener_standalone_phase(self):
        """Verify listener exposes standalone_phase alias matching beat_phase."""
        listener = Listener(self.infos_full)
        self.assertEqual(listener.standalone_phase, listener.beat_phase)

    def test_fake_leds_dynamic_reconstruction_full(self):
        """Verify Fake_leds dynamically reconstructs 1,304 LEDs for full profile."""
        defs = Fake_leds._load_visualizer_segments_def(self.infos_full)
        total_leds = sum(seg[0] for channel in defs for seg in channel)
        total_segs = sum(len(channel) for channel in defs)
        self.assertEqual(total_leds, 1304)
        self.assertEqual(total_segs, 11)

        # Verify vertical segments are wired bottom-to-top ("vertical_up")
        verticals = [seg for channel in defs for seg in channel if "vertical" in seg[1]]
        self.assertTrue(len(verticals) > 0)
        for seg in verticals:
            self.assertEqual(seg[1], "vertical_up")

    def test_fake_leds_dynamic_reconstruction_small(self):
        """Verify Fake_leds dynamically reconstructs 249 LEDs for small profile."""
        defs = Fake_leds._load_visualizer_segments_def(self.infos_small)
        total_leds = sum(seg[0] for channel in defs for seg in channel)
        total_segs = sum(len(channel) for channel in defs)
        self.assertEqual(total_leds, 249)
        self.assertEqual(total_segs, 3)

        # All small segments s1, s2, s3 are vertical_up
        for channel in defs:
            for seg in channel:
                self.assertEqual(seg[1], "vertical_up")

    def test_transition_engine_fade_in_out(self):
        """Verify Transition_Engine handles fade_in_out explicitly."""
        nb_leds = 10
        rgb_curr = np.full((nb_leds, 3), 255, dtype=np.int32)
        rgb_prev = np.zeros((nb_leds, 3), dtype=np.int32)

        # At progress 0.5 (middle of fade_in_out), should apply dual fade cleanly
        TE.apply_transition(rgb_curr, rgb_prev, progress=0.5, transition_name="fade_in_out", coords=None)
        self.assertEqual(rgb_curr.shape, (nb_leds, 3))
        # Both channels should be mixed ~127
        self.assertTrue(np.all(rgb_curr >= 120) and np.all(rgb_curr <= 135))

    def test_magnetic_ball_mode_wall_bounce(self):
        """Verify Magnetic_ball_mode wall bounce sets self.ball_pos without typo."""
        listener = Listener(self.infos_full)
        nb_leds = 50
        rgb_list = np.zeros((nb_leds, 3), dtype=np.uint8)
        indexes = list(range(nb_leds))
        mode = Magnetic_ball_mode("Magnetic Ball", "v1", listener, None, indexes, rgb_list, self.infos_full)

        # Force ball_pos to trigger negative wall bounce
        mode.ball_pos = -2.0
        mode.ball_speed = -5.0
        mode.run()

        # ball_pos should bounce to positive position and not crash on ball_pos_pos
        self.assertGreaterEqual(mode.ball_pos, 0.0)
        self.assertTrue(hasattr(mode, "ball_pos"))


if __name__ == "__main__":
    unittest.main()
