"""
Behavioural tests for Extending_waves_mode: waves spawned from the continuous level accumulator
(decoupled from discrete beat ticks), outward-only propagation across all scenes, and beat secondary tinting.
"""
import unittest

import numpy as np

from music.MusicalContextEngine import MusicalScene
from modes.Extending_waves_mode import Extending_waves_mode
from tests.test_mode_helpers import _ModeTestCase


class TestExtendingWavesLevelAccumulator(_ModeTestCase):
    def setUp(self):
        super().setUp()
        self.engine._current_scene = MusicalScene.GROOVE
        self.engine._energy = 0.6
        self.engine._beat_trust = 0.85
        self.engine._salience = 0.80
        self.engine._is_real_beat = False

    def mode(self, n=41):
        rgb = np.zeros((n, 3), dtype=np.int32)
        return Extending_waves_mode("Extending Waves", "seg", self.listener, None, list(range(n)), rgb, {})

    def _swell(self, mode, low_e=0.20, high_e=0.80):
        self.engine._energy = low_e
        mode.run()
        self.engine._energy = high_e
        mode.time_since_wave = 1.0
        mode.run()

    def test_level_swell_spawns_an_outward_wave(self):
        mode = self.mode()
        self._swell(mode, low_e=0.25, high_e=0.85)
        self.assertGreaterEqual(mode.wave_count, 1)
        self.assertGreater(mode.wave_velocities[0], 0)
        self.assertGreater(mode.wave_amps[0], 0.7)

    def test_beat_ticks_alone_do_not_spawn_waves_when_level_is_flat(self):
        mode = self.mode()
        mode.level_accum = 0.0
        self.engine._energy = 0.50
        # Prime previous energy so d_energy == 0 and swell == 0
        mode.run()
        initial_count = mode.wave_count
        for _ in range(60):
            self.listener.is_beat = True
            self.engine._is_real_beat = True
            mode.time_since_wave = 1.0
            mode.run()
        self.assertEqual(mode.wave_count, initial_count)

    def test_sustained_level_modulation_spawns_multiple_waves(self):
        mode = self.mode()
        for i in range(180):
            self.engine._energy = 0.50 + 0.35 * float(np.sin(i * 0.22))
            mode.run()
        self.assertGreaterEqual(mode.wave_count, 4)

    def test_swell_during_buildup_propagates_outward_without_reversal(self):
        mode = self.mode()
        self.engine._current_scene = MusicalScene.BUILDUP
        self._swell(mode)
        self.assertGreater(mode.wave_velocities[0], 0)

    def test_jittery_double_swell_is_debounced(self):
        mode = self.mode()
        mode.time_since_wave = 1.0
        mode.level_accum = 1.5
        mode.run()
        first_count = mode.wave_count
        mode.level_accum = 1.5
        mode.run()  # next frame: inside min_wave_interval
        self.assertEqual(mode.wave_count, first_count)

    def test_output_is_centre_symmetric(self):
        mode = self.mode(n=41)
        self._swell(mode)
        for _ in range(25):
            mode.run()
        np.testing.assert_array_equal(mode.rgb_list, mode.rgb_list[::-1])

    def test_drop_with_flat_level_does_not_flood_waves(self):
        mode = self.mode()
        mode.level_accum = 0.0
        self.engine._energy = 0.60
        mode.run()
        base_count = mode.wave_count
        self.engine._current_scene = MusicalScene.DROP_IMPACT
        self.engine._is_drop_impact = True
        self.engine._drop_progress = 1.0
        for _ in range(90):
            mode.run()
        self.assertEqual(mode.wave_count, base_count)

    def test_beat_pulse_tints_spawned_wave_toward_highlight(self):
        mode_low_beat = self.mode()
        self.listener.beat_phase = 0.95  # beat_pulse ~ 0
        mode_low_beat.time_since_wave = 1.0
        mode_low_beat.run()

        mode_high_beat = self.mode()
        self.listener.beat_phase = 0.0   # beat_pulse == 1.0
        mode_high_beat.time_since_wave = 1.0
        mode_high_beat.run()

        self.assertFalse(np.allclose(mode_low_beat.wave_colors[0], mode_high_beat.wave_colors[0]))


if __name__ == "__main__":
    unittest.main()
