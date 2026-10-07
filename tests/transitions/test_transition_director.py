"""
Unit tests for transitions/director.py.
Verifies segment geometry loading, transition initiation,
state transitions, countdown mechanics, and timer safeguards.
"""
import unittest

from config.Configuration_manager import resolve_segments_file_path
from transitions.api import MusicSnapshot
from transitions.director import Transition_Director


class TestTransitionDirector(unittest.TestCase):
    def setUp(self):
        self.infos = {
            "silence_threshold": 150,
            "silence_duration_trigger": 10.0,
            "auto_transition_time": 20.0,
        }
        self.director = Transition_Director(
            self.infos,
            segments_path=resolve_segments_file_path(self.infos),
        )

    def test_initialization_and_geometry(self):
        self.assertEqual(self.director.state, "PASSATION")
        self.assertEqual(self.director.transition_progress, 0.0)
        self.assertIsNone(self.director.transition_type)
        self.assertEqual(self.director.configuration_duration, 20.0)

        # Verify segment geometry loaded from active segments config
        self.assertGreater(len(self.director.all_segments), 0)
        self.assertGreater(len(self.director.verticals), 0)
        self.assertGreater(len(self.director.horizontals), 0)
        self.assertEqual(
            len(self.director.all_segments),
            len(self.director.verticals) + len(self.director.horizontals)
        )

    def test_no_segments_path_leaves_geometry_empty(self):
        director = Transition_Director(self.infos)
        self.assertEqual(director.all_segments, [])

    def test_start_transition(self):
        # None should be a no-op
        self.director.start_transition(None)
        self.assertEqual(self.director.state, "PASSATION")

        # Standard transition with duration
        self.director.start_transition({"type": "explosion", "duration": 2.0})
        self.assertEqual(self.director.state, "TRANSITION_DUAL")
        self.assertEqual(self.director.transition_type, "explosion")
        self.assertAlmostEqual(self.director.transition_step, (1.0 / 30.0) / 2.0)
        self.assertEqual(self.director.transition_progress, 0.0)

        # Zero duration transition (instant cut)
        self.director.start_transition({"type": "cut", "duration": 0.0})
        self.assertEqual(self.director.transition_step, 1.0)

    def test_cancel_transition_returns_to_idle(self):
        self.director.start_transition({"type": "explosion", "duration": 2.0})
        self.director.cancel_transition()
        self.assertEqual(self.director.state, "PASSATION")
        self.assertFalse(self.director.is_in_transition)

    def test_update_progress_and_completion(self):
        self.director.start_transition({"type": "global_change", "duration": 0.1})
        # Step size = (1/30) / 0.1 = ~0.333
        t0 = 100.0
        self.director.update(t0)
        self.assertGreater(self.director.transition_progress, 0.0)
        self.assertEqual(self.director.state, "TRANSITION_DUAL")

        # Advance enough steps to complete transition
        for i in range(1, 5):
            self.director.update(t0 + i * 0.033)

        self.assertEqual(self.director.transition_progress, 1.0)
        self.assertEqual(self.director.state, "PASSATION")

    def test_live_event_lookahead_countdowns(self):
        t0 = 100.0
        self.director.update(t0, MusicSnapshot())
        self.assertEqual(self.director.upcoming_song_change_countdown, 0.0)
        self.assertEqual(self.director.upcoming_structural_change_countdown, 0.0)

        # Trigger live song change
        self.director.update(t0 + 0.1, MusicSnapshot(live_is_song_change=True, lookahead_seconds=5.0))
        self.assertEqual(self.director.upcoming_song_change_countdown, 5.0)

        # Reset flag and advance time by 1 second
        self.director.update(t0 + 1.1, MusicSnapshot())
        self.assertAlmostEqual(self.director.upcoming_song_change_countdown, 4.0, places=2)

    def test_timer_expiry_reports_true_once_per_interval(self):
        self.director.update(0.0)  # arms the timer at 20 s
        self.assertFalse(self.director.update(19.0))
        self.assertTrue(self.director.update(20.5))
        self.assertFalse(self.director.update(21.0))
        self.assertGreater(self.director.next_change_time, 21.0)

    def test_transition_locked_guard(self):
        self.director.update(0.0)
        self.director.locked = True
        past_time = self.director.next_change_time + 1.0

        # Locked: no expiry reported, but the timer is pushed forward
        self.assertFalse(self.director.update(past_time))
        self.assertGreater(self.director.next_change_time, past_time)


if __name__ == '__main__':
    unittest.main()
