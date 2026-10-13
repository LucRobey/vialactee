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

    def test_song_change_countdown_triggers_transition(self):
        t0 = 100.0
        self.director.update(t0, MusicSnapshot())
        # Arm live song change with 2.0s lookahead
        self.director.update(t0 + 0.1, MusicSnapshot(live_is_song_change=True, lookahead_seconds=2.0))
        self.assertEqual(self.director.upcoming_song_change_countdown, 2.0)

        # Advance 1.0s: still armed, not triggered
        fired = self.director.update(t0 + 1.1, MusicSnapshot())
        self.assertFalse(fired)
        self.assertAlmostEqual(self.director.upcoming_song_change_countdown, 1.0, places=2)

        # Advance past 2.0s: arrives at speakers (countdown hits 0.0) -> triggers transition!
        fired = self.director.update(t0 + 2.11, MusicSnapshot())
        self.assertTrue(fired)
        self.assertEqual(self.director.last_trigger_reason, "song_change")

        # Following frame should not trigger again
        fired_next = self.director.update(t0 + 2.14, MusicSnapshot())
        self.assertFalse(fired_next)

    def test_structural_change_countdown_triggers_transition(self):
        t0 = 200.0
        self.director.update(t0, MusicSnapshot())
        # Arm live verse-chorus change with 1.5s lookahead
        self.director.update(t0 + 0.1, MusicSnapshot(live_is_verse_chorus_change=True, lookahead_seconds=1.5))
        self.assertEqual(self.director.upcoming_structural_change_countdown, 1.5)

        # Advance 1.6s -> arrives at speakers -> triggers transition!
        fired = self.director.update(t0 + 1.7, MusicSnapshot())
        self.assertTrue(fired)
        self.assertEqual(self.director.last_trigger_reason, "structural_change")

    def test_pre_drop_lookahead_alignment(self):
        t0 = 300.0
        self.director.update(t0, MusicSnapshot())

        # Buildup detected with 5.0s drop countdown
        music_buildup = MusicSnapshot(scene="BUILDUP", drop_countdown=5.0, lookahead_seconds=5.0)
        fired = self.director.update(t0 + 0.1, music_buildup)
        self.assertTrue(fired)
        self.assertEqual(self.director.last_trigger_reason, "pre_drop_buildup")
        self.assertIsNotNone(self.director.pending_transition_config)
        self.assertEqual(self.director.pending_transition_config["type"], "explosion")
        # 5.0 / 0.80 = 6.25s duration
        self.assertAlmostEqual(self.director.pending_transition_config["duration"], 6.25, places=2)

    def test_real_time_drop_impact_immediate(self):
        t0 = 400.0
        self.director.update(t0, MusicSnapshot())

        # Drop impact with no prior transition in progress
        music_impact = MusicSnapshot(is_drop_impact=True)
        fired = self.director.update(t0 + 0.1, music_impact)
        self.assertTrue(fired)
        self.assertEqual(self.director.last_trigger_reason, "drop_impact")
        self.assertEqual(self.director.pending_transition_config, {"type": "explosion", "duration": 0.4})
        self.assertFalse(self.director.pending_quantize_downbeat)

    def test_real_time_drop_impact_snaps_explosion_progress(self):
        t0 = 500.0
        # Transition running with explosion technique at progress 0.50
        self.director.start_transition({"type": "explosion", "duration": 6.25})
        self.director.transition_progress = 0.50

        # Drop lands at speakers
        fired = self.director.update(t0, MusicSnapshot(is_drop_impact=True))
        self.assertFalse(fired)  # Already transitioning, doesn't trigger new order
        # Snaps progress to >= 0.80 so explosion erupts on the transient hit
        self.assertGreaterEqual(self.director.transition_progress, 0.80)


    def test_pre_drop_buildup_unquantized_immediate(self):
        t0 = 600.0
        self.director.update(t0, MusicSnapshot())
        fired = self.director.update(t0 + 0.1, MusicSnapshot(scene="BUILDUP", drop_countdown=5.0))
        self.assertTrue(fired)
        self.assertFalse(self.director.pending_quantize_downbeat)

    def test_song_change_deferred_when_transition_in_progress(self):
        t0 = 700.0
        self.director.update(t0, MusicSnapshot())
        # Arm song change with 1.0s lookahead
        self.director.update(t0 + 0.1, MusicSnapshot(live_is_song_change=True, lookahead_seconds=1.0))

        # Start an active transition (duration 2.0s)
        self.director.start_transition({"type": "fade_in_out", "duration": 2.0})
        self.assertTrue(self.director.is_in_transition)

        # Advance past 1.0s: countdown reaches 0.0, but director is in transition
        fired = self.director.update(t0 + 1.2, MusicSnapshot())
        self.assertFalse(fired)  # Must not fire while in transition
        self.assertTrue(self.director._song_change_armed)  # Must remain armed!

        # Complete active transition: transition progress reaches 1.0 -> enters PASSATION and arms 5s cooldown
        fired = self.director.update(t0 + 2.5, MusicSnapshot())  # pushes progress to 1.0 -> PASSATION
        self.assertFalse(fired, "Must not fire immediately upon completion; 5s security cooldown is active")
        self.assertTrue(self.director._song_change_armed, "Must remain armed during cooldown")
        self.assertTrue(self.director.is_cooling_down, "Director must be cooling down")
        self.assertAlmostEqual(self.director.cooldown_remaining, 5.0, places=1)

        # Mid-cooldown at +2.5s into cooldown: still blocked
        fired_mid = self.director.update(t0 + 5.0, MusicSnapshot())
        self.assertFalse(fired_mid, "Still within 5s cooldown window")
        self.assertTrue(self.director._song_change_armed)

        # Advance past 5.0s cooldown (t0 + 2.5 + 5.1s = t0 + 7.6s): deferred song change fires!
        fired_end = self.director.update(t0 + 7.6, MusicSnapshot())
        self.assertTrue(fired_end, "Deferred song change fires after 5s security cooldown expires")
        self.assertEqual(self.director.last_trigger_reason, "song_change")
        self.assertFalse(self.director.is_cooling_down)
        self.assertEqual(self.director.cooldown_remaining, 0.0)

    def test_timer_deferred_when_song_change_armed(self):
        t0 = 800.0
        self.director.configuration_duration = 5.0
        self.director.update(t0, MusicSnapshot())
        # Timer armed at t0 + 5.0 = 805.0

        # At t=804.0, a song change is armed with lookahead 3.0s (arrives at 807.0)
        self.director.update(t0 + 4.0, MusicSnapshot(live_is_song_change=True, lookahead_seconds=3.0))

        # At t=805.5, timer would have expired, but song change is armed
        fired = self.director.update(t0 + 5.5, MusicSnapshot())
        self.assertFalse(fired)  # Timer is deferred
        self.assertNotEqual(self.director.last_trigger_reason, "timer")

    def test_drop_countdown_without_buildup_scene(self):
        t0 = 900.0
        self.director.update(t0, MusicSnapshot())
        # Scene is GROOVE, but drop_countdown is 3.0s
        fired = self.director.update(t0 + 0.1, MusicSnapshot(scene="GROOVE", drop_countdown=3.0))
        self.assertTrue(fired)
        self.assertEqual(self.director.last_trigger_reason, "pre_drop_buildup")
        self.assertAlmostEqual(self.director.pending_transition_config["duration"], 3.75, places=2)

    def test_drop_impact_interrupts_non_explosion_transition(self):
        t0 = 1000.0
        self.director.update(t0, MusicSnapshot())
        # A slow fade_in_out transition is running at progress 0.30
        self.director.start_transition({"type": "fade_in_out", "duration": 2.0})
        self.director.transition_progress = 0.30

        # Real-time drop impact arrives
        fired = self.director.update(t0 + 0.1, MusicSnapshot(is_drop_impact=True))
        self.assertTrue(fired)
        self.assertEqual(self.director.last_trigger_reason, "drop_impact")
        self.assertEqual(self.director.pending_transition_config["type"], "explosion")
        self.assertFalse(self.director.pending_quantize_downbeat)

    def test_lookahead_zero_in_live_mic_mode(self):
        t0 = 1100.0
        self.director.update(t0, MusicSnapshot())
        # Live song change with 0 lookahead
        fired = self.director.update(t0 + 0.1, MusicSnapshot(live_is_song_change=True, lookahead_seconds=0.0))
        self.assertTrue(fired)
        self.assertEqual(self.director.last_trigger_reason, "song_change")
        self.assertFalse(self.director.pending_quantize_downbeat)

    def test_cooldown_security_blocks_automatic_triggers_for_5_seconds(self):
        t0 = 2000.0
        self.director.set_min_time_between_transitions(5.0)
        self.director.update(t0, MusicSnapshot())

        # Start a 2.0s transition
        self.director.start_transition({"type": "fade_in_out", "duration": 2.0})
        self.assertTrue(self.director.is_in_transition)
        self.assertEqual(self.director.cooldown_remaining, 0.0)

        # Advance to completion (duration 2.0s)
        self.director.update(t0 + 2.1, MusicSnapshot())
        self.assertFalse(self.director.is_in_transition)
        self.assertEqual(self.director.state, "PASSATION")
        self.assertTrue(self.director.is_cooling_down)
        self.assertAlmostEqual(self.director.cooldown_remaining, 5.0, places=1)

        # 1. During cooldown (+2.0s into cooldown, 3.0s remaining): arm song change
        self.director.update(t0 + 4.1, MusicSnapshot(is_song_change=True))
        # Must NOT fire yet because cooldown is active
        self.assertTrue(self.director._song_change_armed)
        self.assertTrue(self.director.is_cooling_down)
        self.assertAlmostEqual(self.director.cooldown_remaining, 3.0, places=1)

        # 2. At +4.5s into cooldown (0.5s remaining): still blocked
        fired = self.director.update(t0 + 6.6, MusicSnapshot())
        self.assertFalse(fired)
        self.assertTrue(self.director._song_change_armed)

        # 3. Advance past 5.0s cooldown (t0 + 2.1 + 5.1s = t0 + 7.2s): armed song change fires!
        fired = self.director.update(t0 + 7.2, MusicSnapshot())
        self.assertTrue(fired)
        self.assertEqual(self.director.last_trigger_reason, "song_change")
        self.assertFalse(self.director.is_cooling_down)
        self.assertEqual(self.director.cooldown_remaining, 0.0)

    def test_urgent_drop_impact_bypasses_cooldown(self):
        t0 = 3000.0
        self.director.set_min_time_between_transitions(5.0)
        self.director.update(t0, MusicSnapshot())

        # Complete a transition -> enters 5.0s cooldown
        self.director.start_transition({"type": "fade_in_out", "duration": 1.0})
        self.director.update(t0 + 1.1, MusicSnapshot())
        self.assertTrue(self.director.is_cooling_down)
        self.assertAlmostEqual(self.director.cooldown_remaining, 5.0, places=1)

        # Urgent drop impact arrives at +1.0s into cooldown (4.0s remaining)
        fired = self.director.update(t0 + 2.1, MusicSnapshot(is_drop_impact=True))
        self.assertTrue(fired)
        self.assertEqual(self.director.last_trigger_reason, "drop_impact")
        self.assertEqual(self.director.pending_transition_config, {"type": "explosion", "duration": 0.4})
        self.assertEqual(self.director.cooldown_remaining, 0.0)

    def test_manual_reset_cooldown(self):
        t0 = 4000.0
        self.director.set_min_time_between_transitions(5.0)
        self.director.update(t0, MusicSnapshot())

        # Complete transition
        self.director.start_transition({"type": "fade_in_out", "duration": 1.0})
        self.director.update(t0 + 1.1, MusicSnapshot())
        self.assertTrue(self.director.is_cooling_down)

        # Manual reset
        self.director.reset_cooldown()
        self.assertFalse(self.director.is_cooling_down)
        self.assertEqual(self.director.cooldown_remaining, 0.0)


if __name__ == '__main__':
    unittest.main()

