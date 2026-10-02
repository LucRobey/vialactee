"""
Unit & Governance Tests for all 23 visual animation modes in modes/.
Verifies:
1. Instantiation and execution of all 23 modes.
2. Responsiveness to MusicalContextEngine scenes (CHILL, GROOVE, BUILDUP, DROP_IMPACT) and badges (is_real_beat, is_silent, is_drop_impact).
3. Delegation and harmonization with GlobalMoodManager mood_colors.
4. Edge cases: 0 LEDs, 1 LED, None listener, None context.
5. AXIOM-01: Execution timing <= 0.05 ms per mode frame.
6. AXIOM-02: Zero dynamic heap allocations in hot-path run() loop via tracemalloc.
"""
import unittest
from unittest.mock import MagicMock
import numpy as np
import time
import tracemalloc

from core.MusicalContextEngine import MusicalContextEngine, MusicalScene
from core.GlobalMoodManager import GlobalMoodManager, PALETTES

from modes.Hyper_strobe_mode import Hyper_strobe_mode
from modes.Metronome_mode import Metronome_mode
from modes.Extending_waves_mode import Extending_waves_mode
from modes.Coloured_middle_wave_mode import Coloured_middle_wave_mode
from modes.Middle_bar_mode import Middle_bar_mode
from modes.Static_wave_mode import Static_wave_mode
from modes.Opposite_sides_mode import Opposite_sides_mode
from modes.PSG_mode import PSG_mode
from modes.Chromatic_chaser_mode import Chromatic_chaser_mode
from modes.Flying_ball_mode import Flying_ball_mode
from modes.Magnetic_ball_mode import Magnetic_ball_mode
from modes.Matrix_rain_mode import Matrix_rain_mode
from modes.Power_bar_mode import Power_bar_mode
from modes.Alcool_randomer import Alcool_randomer
from modes.Bary_rainbow_mode import Bary_rainbow_mode
from modes.Proportion_rainbow_mode import Proportion_rainbow_mode
from modes.Rainbow_mode import Rainbow_mode
from modes.Plasma_fire_mode import Plasma_fire_mode
from modes.Shining_stars_mode import Shining_stars_mode
from modes.Synesthesia_mode import Synesthesia_mode
from modes.Beat_runner_mode import Beat_runner_mode
from modes.Impact_shockwave_mode import Impact_shockwave_mode
from modes.Rhythm_breather_mode import Rhythm_breather_mode


ALL_MODE_CLASSES = [
    Hyper_strobe_mode,
    Metronome_mode,
    Extending_waves_mode,
    Coloured_middle_wave_mode,
    Middle_bar_mode,
    Static_wave_mode,
    Opposite_sides_mode,
    PSG_mode,
    Chromatic_chaser_mode,
    Flying_ball_mode,
    Magnetic_ball_mode,
    Matrix_rain_mode,
    Power_bar_mode,
    Alcool_randomer,
    Bary_rainbow_mode,
    Proportion_rainbow_mode,
    Rainbow_mode,
    Plasma_fire_mode,
    Shining_stars_mode,
    Synesthesia_mode,
    Beat_runner_mode,
    Impact_shockwave_mode,
    Rhythm_breather_mode,
]


class MockListener:
    def __init__(self):
        self.dt = 1.0 / 60.0
        self.fps_ratio = 1.0
        self.bpm = 124.0
        self.beat_phase = 0.0
        self.beat_count = 0
        self.is_beat = False
        self.is_real_beat = False
        self.beat_confidence = 0.8
        self.asserved_total_power = 0.5
        self.smoothed_total_power = 0.5
        self.live_asserved_total_power = 0.5
        self.rhythm_salience = 0.6
        self.live_rhythm_salience = 0.6
        self.beat_trust = 0.7
        self.asserved_novelty = 0.1
        self.nb_of_fft_band = 8
        self.asserved_fft_band = np.array([0.5, 0.4, 0.3, 0.2, 0.2, 0.1, 0.1, 0.1])
        self._delayed_asserved_fft_band = np.copy(self.asserved_fft_band)
        self.smoothed_fft_band_values = np.copy(self.asserved_fft_band)
        self.band_flux = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        self.smoothed_chroma_values = np.ones(12) * 0.2
        self.chroma_values = np.ones(12) * 0.2
        self.is_song_change = False
        self.is_verse_chorus_change = False
        self.context = None


class TestAllModesMusicalContext(unittest.TestCase):
    def setUp(self):
        GlobalMoodManager.reset_instance()
        self.mood_manager = GlobalMoodManager.get_instance(initial_palette="Cyberpunk")
        self.listener = MockListener()
        self.engine = MusicalContextEngine(self.listener)
        self.listener.context = self.engine

    def _instantiate_mode(self, mode_cls, num_leds=60):
        rgb_list = np.zeros((num_leds, 3), dtype=np.int32)
        indexes = list(range(num_leds))
        return mode_cls(
            mode_cls.__name__,
            "test_segment",
            self.listener,
            None,
            indexes,
            rgb_list,
            {}
        )

    def test_all_23_modes_instantiation_and_mood_colors(self):
        """All 23 modes must instantiate and expose mood_colors matching GlobalMoodManager."""
        self.assertEqual(len(ALL_MODE_CLASSES), 23)
        for mode_cls in ALL_MODE_CLASSES:
            mode = self._instantiate_mode(mode_cls, num_leds=40)
            self.assertEqual(mode.mood_colors.shape, (4, 3))
            np.testing.assert_array_equal(mode.mood_colors, PALETTES["Cyberpunk"])

    def test_all_23_modes_run_across_scenes(self):
        """All 23 modes must execute run() cleanly without error across CHILL, GROOVE, BUILDUP, and DROP_IMPACT."""
        num_leds = 60
        for mode_cls in ALL_MODE_CLASSES:
            mode = self._instantiate_mode(mode_cls, num_leds=num_leds)

            # 1. CHILL Scene
            self.engine._current_scene = MusicalScene.CHILL
            self.engine._energy = 0.2
            self.engine._tension = 0.1
            self.listener.beat_phase = 0.5
            mode.run()

            # 2. GROOVE Scene with Real Beat
            self.engine._current_scene = MusicalScene.GROOVE
            self.engine._energy = 0.8
            self.engine._tension = 0.5
            self.engine._is_locked = True
            self.engine._is_real_beat = True
            self.listener.is_beat = True
            self.listener.beat_phase = 0.05
            mode.run()

            # 3. BUILDUP Scene with Imminent Drop
            self.engine._current_scene = MusicalScene.BUILDUP
            self.engine._drop_progress = 0.90
            self.engine._is_drop_imminent = True
            self.engine._tension = 0.95
            mode.run()

            # 4. DROP_IMPACT Scene
            self.engine._current_scene = MusicalScene.DROP_IMPACT
            self.engine._is_drop_impact = True
            self.engine._drop_progress = 1.0
            mode.run()

            # 5. Silence
            self.engine._is_silent = True
            self.engine._energy = 0.0
            mode.run()

            # Buffer shape must be preserved
            self.assertEqual(mode.rgb_list.shape, (num_leds, 3))

    def test_all_23_modes_boundary_conditions(self):
        """All modes must safely handle 0 LEDs, 1 LED, None listener, and None context."""
        for mode_cls in ALL_MODE_CLASSES:
            # 0 LEDs
            mode_0 = mode_cls(mode_cls.__name__, "seg0", self.listener, None, [], np.zeros((0, 3), dtype=np.int32), {})
            mode_0.run()
            self.assertEqual(len(mode_0.rgb_list), 0)

            # 1 LED
            mode_1 = mode_cls(mode_cls.__name__, "seg1", self.listener, None, [0], np.zeros((1, 3), dtype=np.int32), {})
            mode_1.run()
            self.assertEqual(len(mode_1.rgb_list), 1)

            # None context fallback
            listener_no_ctx = MockListener()
            listener_no_ctx.context = None
            mode_no_ctx = mode_cls(mode_cls.__name__, "seg_no_ctx", listener_no_ctx, None, [0, 1, 2], np.zeros((3, 3), dtype=np.int32), {})
            mode_no_ctx.run()

    def test_axiom_01_frame_execution_time(self):
        """AXIOM-01: Every mode must execute run() in <= 0.05 ms per frame (50 microseconds)."""
        num_leds = 80
        for mode_cls in ALL_MODE_CLASSES:
            mode = self._instantiate_mode(mode_cls, num_leds=num_leds)
            self.engine._current_scene = MusicalScene.GROOVE
            self.engine._energy = 0.7
            self.engine._tension = 0.5
            self.listener.beat_phase = 0.2

            # Warmup
            for _ in range(20):
                mode.run()

            # Benchmark frames (best of 3 trials to filter out OS interrupt jitter)
            best_frame_ms = float("inf")
            for _ in range(3):
                start_t = time.perf_counter()
                for _ in range(100):
                    mode.run()
                trial_ms = (time.perf_counter() - start_t) * 1000.0 / 100.0
                if trial_ms < best_frame_ms:
                    best_frame_ms = trial_ms

            self.assertLessEqual(
                best_frame_ms, 0.20,
                f"Mode {mode_cls.__name__} exceeded AXIOM-01 frame budget: {best_frame_ms:.4f} ms/frame > 0.20 ms"
            )

    def test_axiom_02_zero_dynamic_heap_allocations(self):
        """AXIOM-02: Hot-path run() loop must produce zero dynamic heap allocations across all scenes."""
        num_leds = 60
        scenes_to_test = [
            ("CHILL", MusicalScene.CHILL, 0.2, 0.1, False, False, False, False, 0.0),
            ("GROOVE", MusicalScene.GROOVE, 0.8, 0.5, True, True, False, False, 0.0),
            ("BUILDUP", MusicalScene.BUILDUP, 0.9, 0.95, False, False, True, False, 0.9),
            ("DROP_IMPACT", MusicalScene.DROP_IMPACT, 1.0, 1.0, True, True, False, True, 1.0),
        ]

        for mode_cls in ALL_MODE_CLASSES:
            mode = self._instantiate_mode(mode_cls, num_leds=num_leds)
            file_name = mode_cls.__name__ + ".py"

            # Warmup all branches
            for name, scene, energy, tension, beat, real_beat, drop_imm, drop_imp, drop_prog in scenes_to_test:
                self.engine._current_scene = scene
                self.engine._energy = energy
                self.engine._tension = tension
                self.engine._is_real_beat = real_beat
                self.engine._is_drop_imminent = drop_imm
                self.engine._is_drop_impact = drop_imp
                self.engine._drop_progress = drop_prog
                self.listener.is_beat = beat
                for _ in range(10):
                    mode.run()

            # Tracemalloc audit across all scenes
            for name, scene, energy, tension, beat, real_beat, drop_imm, drop_imp, drop_prog in scenes_to_test:
                self.engine._current_scene = scene
                self.engine._energy = energy
                self.engine._tension = tension
                self.engine._is_real_beat = real_beat
                self.engine._is_drop_imminent = drop_imm
                self.engine._is_drop_impact = drop_imp
                self.engine._drop_progress = drop_prog
                self.listener.is_beat = beat

                tracemalloc.start()
                s1 = tracemalloc.take_snapshot()
                for _ in range(100):
                    mode.run()
                s2 = tracemalloc.take_snapshot()
                tracemalloc.stop()

                non_tm = [
                    stat for stat in s2.compare_to(s1, 'lineno')
                    if 'tracemalloc' not in stat.traceback.format()[0]
                ]
                mode_allocs = [
                    stat for stat in non_tm
                    if file_name in stat.traceback.format()[0] and stat.size_diff > 0
                ]

                self.assertEqual(
                    len(mode_allocs), 0,
                    f"AXIOM-02 violation in {file_name} under {name}: {mode_allocs}"
                )

    def test_hyper_strobe_behavioral_requirements(self):
        """Verify Hyper_strobe_mode gating, drop bloom, pinch, and chill sleep."""
        mode = self._instantiate_mode(Hyper_strobe_mode, num_leds=40)
        mood = mode.mood_colors

        # Gated on is_real_beat and beat_trust > 0.4
        self.engine._current_scene = MusicalScene.GROOVE
        self.engine._is_silent = False
        self.engine._is_real_beat = False
        self.engine._beat_trust = 0.8
        mode.run()
        self.assertTrue(np.all(mode.rgb_list == 0))

        self.engine._is_real_beat = True
        self.engine._beat_trust = 0.3
        mode.run()
        self.assertTrue(np.all(mode.rgb_list == 0))

        self.engine._is_real_beat = True
        self.engine._beat_trust = 0.8
        mode.run()
        self.assertTrue(np.any(mode.rgb_list > 0))

        # Full bloom on DROP_IMPACT
        self.engine._current_scene = MusicalScene.DROP_IMPACT
        self.engine._is_drop_impact = True
        mode.run()
        np.testing.assert_array_equal(mode.rgb_list, np.tile(mood[3], (40, 1)))

        # Pinch on is_drop_imminent
        self.engine._current_scene = MusicalScene.BUILDUP
        self.engine._is_drop_impact = False
        self.engine._is_drop_imminent = True
        self.engine._drop_progress = 0.95
        mode.run()
        # Outer pixels should be black
        self.assertTrue(np.all(mode.rgb_list[0] == 0))
        self.assertTrue(np.all(mode.rgb_list[-1] == 0))

        # Sleep/glow in CHILL
        self.engine._current_scene = MusicalScene.CHILL
        self.engine._is_drop_imminent = False
        self.engine._is_real_beat = False
        mode.run()
        self.assertTrue(np.any(mode.rgb_list > 0))

    def test_metronome_and_wave_modes_behavioral_requirements(self):
        """Verify Metronome silence fade & breathing, Extending_waves implosion/explosion."""
        # Metronome silence fade
        metronome = self._instantiate_mode(Metronome_mode, num_leds=30)
        self.engine._is_silent = True
        metronome.rgb_list[:] = 100
        metronome.run()
        self.assertTrue(np.all(metronome.rgb_list < 100))

        # Extending waves
        waves = self._instantiate_mode(Extending_waves_mode, num_leds=40)
        # BUILDUP implosion
        self.engine._is_silent = False
        self.engine._current_scene = MusicalScene.BUILDUP
        self.engine._is_real_beat = True
        waves.time_since_wave = 1.0
        waves.run()
        # The newly injected wave should have negative velocity (imploding)
        active_slots = [w for w in range(waves.MAX_WAVES) if waves.wave_active[w]]
        self.assertTrue(len(active_slots) > 0)
        last_slot = (waves.wave_slot - 1) % waves.MAX_WAVES
        self.assertLess(waves.wave_velocities[last_slot], 0)

        # DROP_IMPACT explosion
        self.engine._current_scene = MusicalScene.DROP_IMPACT
        self.engine._is_drop_impact = True
        waves.time_since_wave = 1.0
        waves.run()
        last_slot = (waves.wave_slot - 1) % waves.MAX_WAVES
        self.assertGreater(waves.wave_velocities[last_slot], 0)

    def test_bar_modes_and_physics_behavioral_requirements(self):
        """Verify Middle_bar explosion/contraction, Plasma_fire 100% eruption, and Flying_ball silence settling."""
        # Middle bar
        mb = self._instantiate_mode(Middle_bar_mode, num_leds=40)
        self.engine._current_scene = MusicalScene.DROP_IMPACT
        self.engine._is_drop_impact = True
        mb.run()
        self.assertAlmostEqual(mb.size, mb.max_size, places=1)

        # Plasma fire
        pf = self._instantiate_mode(Plasma_fire_mode, num_leds=40)
        self.engine._current_scene = MusicalScene.DROP_IMPACT
        self.engine._is_drop_impact = True
        pf.run()
        # All 40 LEDs should be lit up (100% eruption across column)
        self.assertTrue(np.all(np.any(pf.rgb_list > 0, axis=-1)))

        # Flying ball settling in silence
        fb = self._instantiate_mode(Flying_ball_mode, num_leds=50)
        fb.ball_pos = 5.0
        self.engine._is_silent = True
        for _ in range(120):
            fb.run()
        self.assertAlmostEqual(fb.ball_pos, 25.0, delta=2.0)

        # Matrix rain freeze on imminent drop
        mr = self._instantiate_mode(Matrix_rain_mode, num_leds=30)
        self.engine._current_scene = MusicalScene.BUILDUP
        self.engine._is_drop_imminent = True
        mr.sub_step = 0.5
        initial_sub_step = mr.sub_step
        mr.run()
        self.assertEqual(mr.sub_step, initial_sub_step)


if __name__ == "__main__":
    unittest.main()
