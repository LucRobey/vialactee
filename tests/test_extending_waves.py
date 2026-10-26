"""
Behavioural tests for Extending_waves_mode: one wave per rhythmic tempo tick (flywheel `is_beat`),
whether or not the tick is backed by a real acoustic transient, and preservation of the loved traits.
"""
import unittest

import numpy as np

from music.MusicalContextEngine import MusicalScene
from modes.Extending_waves_mode import Extending_waves_mode
from tests.test_mode_helpers import _ModeTestCase


class TestExtendingWavesTempoTicks(_ModeTestCase):
    def setUp(self):
        super().setUp()
        self.engine._current_scene = MusicalScene.GROOVE
        self.engine._energy = 0.6
        self.engine._is_real_beat = False

    def mode(self, n=41):
        rgb = np.zeros((n, 3), dtype=np.int32)
        return Extending_waves_mode("Extending Waves", "seg", self.listener, None, list(range(n)), rgb, {})

    def _tick(self, mode, real=False):
        self.listener.is_beat = True
        self.engine._is_real_beat = real
        mode.time_since_wave = 1.0
        mode.run()
        self.listener.is_beat = False
        self.engine._is_real_beat = False

    def test_unverified_tempo_tick_spawns_an_outward_wave(self):
        mode = self.mode()
        self._tick(mode, real=False)  # flywheel tick, no acoustic transient
        self.assertEqual(mode.wave_count, 1)
        self.assertGreater(mode.wave_velocities[0], 0)
        self.assertGreater(mode.wave_amps[0], 0.8)

    def test_real_beat_still_spawns_a_wave(self):
        mode = self.mode()
        self.listener.is_beat = False
        self.engine._is_real_beat = True
        mode.time_since_wave = 1.0
        mode.run()
        self.assertEqual(mode.wave_count, 1)

    def test_no_tick_no_wave(self):
        mode = self.mode()
        for _ in range(120):
            mode.run()
        self.assertEqual(mode.wave_count, 0)

    def test_one_wave_per_tick_over_a_bar(self):
        mode = self.mode()
        bpm = self.listener.bpm
        frames_per_beat = int(round(60.0 * 60.0 / bpm))
        ticks = 8
        for beat in range(ticks):
            self.listener.is_beat = True
            mode.run()
            self.listener.is_beat = False
            for _ in range(frames_per_beat - 1):
                mode.run()
        self.assertEqual(mode.wave_count, ticks)

    def test_tick_during_buildup_propagates_outward_without_reversal(self):
        mode = self.mode()
        self.engine._current_scene = MusicalScene.BUILDUP
        self._tick(mode)
        self.assertGreater(mode.wave_velocities[0], 0)

    def test_jittery_double_tick_is_debounced(self):
        mode = self.mode()
        self.listener.is_beat = True
        mode.time_since_wave = 1.0
        mode.run()
        mode.run()  # second tick a frame later: inside the 0.35-beat minimum interval
        self.assertEqual(mode.wave_count, 1)

    def test_output_is_centre_symmetric(self):
        mode = self.mode(n=41)
        self._tick(mode)
        for _ in range(25):
            mode.run()
        np.testing.assert_array_equal(mode.rgb_list, mode.rgb_list[::-1])

    def test_drop_without_a_tick_spawns_nothing(self):
        """No drop-impact flood: during the 1.5 s drop, waves only come from tempo ticks."""
        mode = self.mode()
        self.engine._current_scene = MusicalScene.DROP_IMPACT
        self.engine._is_drop_impact = True
        self.engine._drop_progress = 1.0
        for _ in range(90):
            mode.run()
        self.assertEqual(mode.wave_count, 0)

    def test_drop_with_a_tick_spawns_one_ordinary_wave(self):
        mode = self.mode()
        self.engine._current_scene = MusicalScene.DROP_IMPACT
        self.engine._is_drop_impact = True
        self.engine._drop_progress = 1.0
        self._tick(mode)
        self.assertEqual(mode.wave_count, 1)
        self.assertEqual(float(mode.wave_velocities[0]), 1.0)
        self.assertLessEqual(float(mode.wave_amps[0]), 0.9 + 1e-6)

    def test_drop_wave_uses_the_normal_palette_not_the_drop_colour(self):
        mode = self.mode()
        self.engine._current_scene = MusicalScene.DROP_IMPACT
        self.engine._is_drop_impact = True
        self._tick(mode)
        mood = mode.mood_colors
        np.testing.assert_array_equal(mode.wave_colors[0], mood[mode.wave_count % 3])


if __name__ == "__main__":
    unittest.main()
