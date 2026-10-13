"""
Unit tests for core/Segment.py.
Verifies mode loading, mode name normalization (handling legacy formats),
propagation directions, blocking behavior, and dual-buffer transition rendering.
"""
import unittest
import numpy as np
from unittest.mock import MagicMock

from core.Segment import Segment
from transitions.api import TransitionStatus


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

        # Transition status in DUAL state
        blend = MagicMock()
        status = TransitionStatus(state="TRANSITION_DUAL", progress=0.5, is_in_transition=True, technique="fade_to_black")

        self.segment.update(status, blend)
        blend.assert_called_once()
        self.assertTrue(self.segment.is_in_transition)
        self.assertEqual(self.segment.activ_mode, start_mode)

        # Transition finishing with PASSATION
        status = TransitionStatus(state="PASSATION", progress=1.0, technique="fade_to_black")
        self.segment.update(status, blend)

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

    def test_local_timing_staggered_lifecycle(self):
        """Verifies start_offset delay, local progress calculation, and completion."""
        start_mode = "Rainbow"
        target_mode = "Plasma Fire"
        self.segment.execute_mode_swap(start_mode)

        # Transition with 0.5s offset, 1.0s duration, vertical_wipe technique
        self.segment.change_mode(target_mode, {
            "type": "vertical_wipe",
            "duration": 1.0,
            "start_offset": 0.5,
        })
        self.assertTrue(self.segment.is_in_transition)
        self.assertEqual(self.segment.transition_start_offset, 0.5)
        self.assertEqual(self.segment.transition_duration, 1.0)
        self.assertEqual(self.segment.transition_technique, "vertical_wipe")

        blend = MagicMock()
        status = TransitionStatus(state="TRANSITION_DUAL", progress=0.1, technique="fade_in_out")

        # 1. Before start_offset (elapsed = 0.3 < 0.5): remains in active mode, no blend
        self.segment.update(status, blend, dt=0.3)
        blend.assert_not_called()
        self.assertTrue(self.segment.is_in_transition)
        self.assertEqual(self.segment.activ_mode, start_mode)

        # 2. During transition (elapsed = 0.3 + 0.4 = 0.7s, offset=0.5, dur=1.0)
        # Local progress p = (0.7 - 0.5) / 1.0 = 0.20
        self.segment.update(status, blend, dt=0.4)
        blend.assert_called_once()
        call_args = blend.call_args[0]
        # args: (rgb_list, dual_rgb_list, progress, technique, coords)
        self.assertAlmostEqual(call_args[2], 0.20, places=2)
        self.assertEqual(call_args[3], "vertical_wipe")
        self.assertEqual(self.segment.activ_mode, start_mode)
        self.assertTrue(self.segment.is_in_transition)

        # 3. Midway (elapsed = 0.7 + 0.5 = 1.2s, p = (1.2 - 0.5)/1.0 = 0.70)
        blend.reset_mock()
        self.segment.update(status, blend, dt=0.5)
        blend.assert_called_once()
        self.assertAlmostEqual(blend.call_args[0][2], 0.70, places=2)

        # 4. Past completion (elapsed = 1.2 + 0.4 = 1.6s >= 1.5s total)
        blend.reset_mock()
        self.segment.update(status, blend, dt=0.4)
        blend.assert_not_called()
        self.assertFalse(self.segment.is_in_transition)
        self.assertEqual(self.segment.activ_mode, target_mode)

    def test_local_timing_not_aborted_by_idle_director_passation(self):
        """Transition must NOT abort on frame 1 when Director is in PASSATION (idle)."""
        start_mode = "Rainbow"
        target_mode = "Plasma Fire"
        self.segment.execute_mode_swap(start_mode)

        self.segment.change_mode(target_mode, {"type": "fade_in_out", "duration": 1.0, "start_offset": 0.0})
        self.assertTrue(self.segment.is_in_transition)

        idle_status = TransitionStatus(state="PASSATION", progress=0.0)
        blend = MagicMock()

        # Frame 1: dt=0.1. Must remain in transition!
        self.segment.update(idle_status, blend, dt=0.1)
        self.assertTrue(self.segment.is_in_transition)
        blend.assert_called_once()
        self.assertAlmostEqual(blend.call_args[0][2], 0.10, places=2)

        # Advance to completion: dt=0.95 -> total 1.05s >= 1.0s
        blend.reset_mock()
        self.segment.update(idle_status, blend, dt=0.95)
        self.assertFalse(self.segment.is_in_transition)
        self.assertEqual(self.segment.activ_mode, target_mode)

    def test_forced_interruption_and_mode_cancel(self):
        """Forced transition interrupts ongoing transition; requesting active mode cancels transition."""
        start_mode = "Rainbow"
        mid_mode = "Plasma Fire"
        self.segment.execute_mode_swap(start_mode)

        self.segment.change_mode(mid_mode, {"type": "fade_in_out", "duration": 2.0})
        self.assertTrue(self.segment.is_in_transition)
        self.assertEqual(self.segment.target_mode_name, mid_mode)

        # Non-forced request to a different mode while transitioning is ignored
        self.segment.change_mode("Hyper Strobe", {"type": "fade_in_out", "duration": 2.0})
        self.assertEqual(self.segment.target_mode_name, mid_mode)

        # Forced request overrides ongoing transition (e.g. drop explosion)
        self.segment.change_mode("Hyper Strobe", {"type": "explosion", "duration": 0.4, "force": True})
        self.assertTrue(self.segment.is_in_transition)
        self.assertEqual(self.segment.target_mode_name, "Hyper Strobe")
        self.assertEqual(self.segment.transition_technique, "explosion")
        self.assertFalse(self.segment.modes[mid_mode].isActiv)  # mid_mode terminated

        # Requesting active mode cancels transition and stays on active mode
        self.segment.change_mode(start_mode, {"type": "fade_in_out", "duration": 2.0})
        self.assertFalse(self.segment.is_in_transition)
        self.assertIsNone(self.segment.target_mode_name)
        self.assertEqual(self.segment.activ_mode, start_mode)
        self.assertTrue(self.segment.modes[start_mode].isActiv)

    def test_target_mode_rendered_on_completion_frame(self):
        """On the exact frame of passation completion, target mode is rendered into rgb_list."""
        start_mode = "Rainbow"
        target_mode = "Plasma Fire"
        self.segment.execute_mode_swap(start_mode)

        self.segment.change_mode(target_mode, {"type": "fade_in_out", "duration": 0.2, "start_offset": 0.0})
        status = TransitionStatus(state="TRANSITION_DUAL", progress=0.5)
        blend = MagicMock()

        # Step to completion in 1 step: dt=0.25 >= 0.20
        self.segment.update(status, blend, dt=0.25)
        self.assertFalse(self.segment.is_in_transition)
        self.assertEqual(self.segment.activ_mode, target_mode)
        # Verify the target mode is active and running
        self.assertTrue(self.segment.modes[target_mode].isActiv)


if __name__ == '__main__':
    unittest.main()
