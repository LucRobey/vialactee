"""
Unit tests for core/Transition_Director.py.
Verifies segment geometry loading, transition initiation,
state transitions, countdown mechanics, and timer safeguards.
"""
import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from core.Transition_Director import Transition_Director


class TestTransitionDirector(unittest.TestCase):
    def setUp(self):
        self.mode_master = MagicMock()
        self.mode_master.change_configuration = AsyncMock()
        self.mode_master.transition_locked = False

        self.listener = MagicMock()
        self.listener.live_is_song_change = False
        self.listener.live_is_verse_chorus_change = False
        self.listener.analyzer.lookahead_seconds = 5.0

        self.infos = {
            "silence_threshold": 150,
            "silence_duration_trigger": 10.0,
            "auto_transition_time": 20.0,
        }
        self.director = Transition_Director(self.mode_master, self.listener, self.infos)

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

    def test_async_update_progress_and_completion(self):
        async def run_test():
            self.director.start_transition({"type": "global_change", "duration": 0.1})
            # Step size = (1/30) / 0.1 = ~0.333
            t0 = 100.0
            await self.director.update(t0)
            self.assertGreater(self.director.transition_progress, 0.0)
            self.assertEqual(self.director.state, "TRANSITION_DUAL")

            # Advance enough steps to complete transition
            for i in range(1, 5):
                await self.director.update(t0 + i * 0.033)

            self.assertEqual(self.director.transition_progress, 1.0)
            self.assertEqual(self.director.state, "PASSATION")

        asyncio.run(run_test())

    def test_live_event_lookahead_countdowns(self):
        async def run_test():
            t0 = 100.0
            await self.director.update(t0)
            self.assertEqual(self.director.upcoming_song_change_countdown, 0.0)
            self.assertEqual(self.director.upcoming_structural_change_countdown, 0.0)

            # Trigger live song change
            self.listener.live_is_song_change = True
            await self.director.update(t0 + 0.1)
            self.assertEqual(self.director.upcoming_song_change_countdown, 5.0)

            # Reset flag and advance time by 1 second
            self.listener.live_is_song_change = False
            await self.director.update(t0 + 1.1)
            self.assertAlmostEqual(self.director.upcoming_song_change_countdown, 4.0, places=2)

        asyncio.run(run_test())

    def test_transition_locked_guard(self):
        async def run_test():
            # Force expiration of next change time
            past_time = self.director.next_change_time + 1.0
            self.mode_master.transition_locked = True

            await self.director.update(past_time)
            # Should NOT trigger change_configuration when transition is locked
            self.mode_master.change_configuration.assert_not_called()
            self.assertGreater(self.director.next_change_time, past_time)

        asyncio.run(run_test())


if __name__ == '__main__':
    unittest.main()
