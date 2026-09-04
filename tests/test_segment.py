"""
Unit tests for core/Segment.py.
Verifies mode loading, mode name normalization (handling legacy formats),
propagation directions, blocking behavior, and dual-buffer transition rendering.
"""
import unittest
import numpy as np
from unittest.mock import MagicMock

from core.Segment import Segment


class TestSegment(unittest.TestCase):
    def setUp(self):
        self.mock_listener = MagicMock()
        self.mock_listener.luminosite = 1.0
        self.mock_listener.asserved_total_power = 0.5
        self.mock_listener.smoothed_fft_band_values = np.zeros(8)
        self.mock_listener.asserved_fft_band = np.zeros(8)
        self.mock_listener._delayed_asserved_fft_band = np.zeros(8)
        self.mock_listener.nb_of_fft_band = 8

        self.num_leds = 20
        self.indexes = list(range(self.num_leds))
        self.global_leds = np.zeros((100, 3), dtype=np.int32)
        self.infos = {}

        self.segment = Segment(
            name="Segment v4",
            listener=self.mock_listener,
            leds=self.global_leds,
            indexes=self.indexes,
            orientation="vertical",
            infos=self.infos,
        )

    def test_initialization(self):
        self.assertEqual(self.segment.name, "Segment v4")
        self.assertEqual(self.segment.nb_of_leds, self.num_leds)
        self.assertEqual(self.segment.rgb_list.shape, (self.num_leds, 3))
        self.assertEqual(self.segment.dual_rgb_list.shape, (self.num_leds, 3))
        self.assertFalse(self.segment.isBlocked)
        self.assertFalse(self.segment.is_in_transition)
        self.assertEqual(self.segment.way, "UP")
        self.assertGreater(len(self.segment.modes), 0)
        self.assertIn(self.segment.activ_mode, self.segment.modes)

    def test_normalize_mode_name(self):
        # Exact match
        self.assertEqual(self.segment._normalize_mode_name("Rainbow"), "Rainbow")

        # Whitespace trimmed
        self.assertEqual(self.segment._normalize_mode_name("  Rainbow  "), "Rainbow")

        # Case insensitive
        self.assertEqual(self.segment._normalize_mode_name("rainbow"), "Rainbow")

        # Legacy snake_case with _mode suffix
        self.assertEqual(self.segment._normalize_mode_name("Plasma_fire_mode"), "Plasma Fire")
        self.assertEqual(self.segment._normalize_mode_name("Metronome_mode"), "Metronome")
        self.assertEqual(self.segment._normalize_mode_name("Hyper_strobe_mode"), "Hyper Strobe")

        # Non-existent mode should return raw string without crashing
        self.assertEqual(self.segment._normalize_mode_name("Unknown Mode"), "Unknown Mode")

    def test_way_direction_toggles(self):
        self.assertEqual(self.segment.way, "UP")
        self.segment.switch_way()
        self.assertEqual(self.segment.way, "DOWN")
        self.segment.switch_way()
        self.assertEqual(self.segment.way, "UP")

        self.segment.change_way("DOWN")
        self.assertEqual(self.segment.way, "DOWN")

    def test_blocking_behavior(self):
        self.segment.block()
        self.assertTrue(self.segment.isBlocked)

        current_mode = self.segment.activ_mode
        other_mode = "Rainbow" if current_mode != "Rainbow" else "Plasma Fire"

        # Mode changes must be ignored when blocked
        self.segment.change_mode(other_mode)
        self.assertEqual(self.segment.activ_mode, current_mode)

        self.segment.unblock()
        self.assertFalse(self.segment.isBlocked)
        self.segment.execute_mode_swap(other_mode)
        self.assertEqual(self.segment.activ_mode, other_mode)

    def test_execute_mode_swap_instant(self):
        current_mode = self.segment.activ_mode
        other_mode = "Rainbow" if current_mode != "Rainbow" else "Plasma Fire"

        self.segment.execute_mode_swap(other_mode)
        self.assertEqual(self.segment.activ_mode, other_mode)
        self.assertTrue(self.segment.modes[other_mode].isActiv)

        # Swapping to same mode is a no-op
        self.segment.execute_mode_swap(other_mode)
        self.assertEqual(self.segment.activ_mode, other_mode)

    def test_transition_dual_buffer_lifecycle(self):
        start_mode = "Rainbow"
        target_mode = "Plasma Fire"
        self.segment.execute_mode_swap(start_mode)

        # Start transition
        self.segment.change_mode(target_mode, {"type": "fade_to_black", "duration": 2.0})
        self.assertTrue(self.segment.is_in_transition)
        self.assertEqual(self.segment.target_mode_name, target_mode)

        # Mock Transition Director in DUAL state
        mock_td = MagicMock()
        mock_td.state = "TRANSITION_DUAL"
        mock_td.transition_progress = 0.5
        mock_td.transition_type = "fade_to_black"

        self.segment.update(mock_td)
        self.assertTrue(self.segment.is_in_transition)
        self.assertEqual(self.segment.activ_mode, start_mode)

        # Mock Transition Director finishing with PASSATION
        mock_td.state = "PASSATION"
        mock_td.transition_progress = 1.0
        self.segment.update(mock_td)

        self.assertFalse(self.segment.is_in_transition)
        self.assertEqual(self.segment.activ_mode, target_mode)

    def test_update_leds_reversal(self):
        self.segment.rgb_list[:] = np.arange(self.num_leds)[:, None] * 10
        self.segment.way = "UP"
        self.segment.update_leds()
        np.testing.assert_array_equal(self.global_leds[self.indexes], self.segment.rgb_list)

        self.segment.way = "DOWN"
        self.segment.update_leds()
        np.testing.assert_array_equal(self.global_leds[self.indexes], self.segment.rgb_list[::-1])


if __name__ == '__main__':
    unittest.main()
