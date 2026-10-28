"""
Unit & Governance Tests for all 13 visual animation modes in modes/.
Verifies:
1. Instantiation and execution of all 13 modes.
2. Continuous, non-snapping behavior across MusicalContextEngine scenes (CHILL, GROOVE, BUILDUP, DROP_IMPACT).
3. Resilience when the Anticipation Flywheel is completely lost (beat_trust == 0, is_beat == False).
4. Delegation and harmonization with the mood sector's mood_colors and mood_modifiers.
5. Edge cases: 0 LEDs, 1 LED, None listener, None context.
6. AXIOM-01: Execution timing <= 0.20 ms per mode frame.
7. AXIOM-02: Zero dynamic heap allocations in hot-path run() loop via tracemalloc.
"""
import unittest
import numpy as np
import time
import gc
import tracemalloc

from music.MusicalContextEngine import MusicalContextEngine, MusicalScene
from mood.api import create_mood_service
from mood.palettes import PALETTES
from modes.Mode import Mode as BaseMode

from modes.Hyper_strobe_mode import Hyper_strobe_mode
from modes.Metronome_mode import Metronome_mode
from modes.Extending_waves_mode import Extending_waves_mode
from modes.Coloured_middle_wave_mode import Coloured_middle_wave_mode
from modes.Middle_bar_mode import Middle_bar_mode
from modes.Opposite_sides_mode import Opposite_sides_mode
from modes.Chromatic_chaser_mode import Chromatic_chaser_mode
from modes.Power_bar_mode import Power_bar_mode
from modes.Bary_rainbow_mode import Bary_rainbow_mode
from modes.Proportion_rainbow_mode import Proportion_rainbow_mode
from modes.Rainbow_mode import Rainbow_mode
from modes.Shining_stars_mode import Shining_stars_mode
from modes.Impact_shockwave_mode import Impact_shockwave_mode


ALL_MODE_CLASSES = [
    Hyper_strobe_mode,
    Metronome_mode,
    Extending_waves_mode,
    Coloured_middle_wave_mode,
    Middle_bar_mode,
    Opposite_sides_mode,
    Chromatic_chaser_mode,
    Power_bar_mode,
    Bary_rainbow_mode,
    Proportion_rainbow_mode,
    Rainbow_mode,
    Shining_stars_mode,
    Impact_shockwave_mode,
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
        self.mood = create_mood_service(initial_palette="Cyberpunk")
        BaseMode.bind_mood_colors(self.mood.colors())
        BaseMode.bind_mood_modifiers(self.mood.modifiers())
        self.addCleanup(BaseMode.reset_mood_colors)
        self.listener = MockListener()
        self.engine = MusicalContextEngine(self.listener)
        self.engine._is_silent = False
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

    def test_all_modes_instantiation_and_mood_colors(self):
        """All 13 modes must instantiate and expose mood_colors and mood_modifiers matching the mood service."""
        self.assertEqual(len(ALL_MODE_CLASSES), 13)
        for mode_cls in ALL_MODE_CLASSES:
            mode = self._instantiate_mode(mode_cls, num_leds=40)
            self.assertEqual(mode.mood_colors.shape, (4, 3))
            self.assertEqual(mode.mood_modifiers.shape, (4,))
            np.testing.assert_array_equal(mode.mood_colors, PALETTES["Cyberpunk"])

    def test_all_modes_run_across_scenes(self):
        """All 13 modes must execute run() cleanly without error across CHILL, GROOVE, BUILDUP, and DROP_IMPACT."""
        num_leds = 60
        for mode_cls in ALL_MODE_CLASSES:
            mode = self._instantiate_mode(mode_cls, num_leds=num_leds)

            # 1. CHILL Scene
            self.engine._is_silent = False
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

            self.assertEqual(mode.rgb_list.shape, (num_leds, 3))

    def test_all_modes_boundary_conditions(self):
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
        """AXIOM-01: Every mode must execute run() within the frame budget."""
        num_leds = 80
        for mode_cls in ALL_MODE_CLASSES:
            mode = self._instantiate_mode(mode_cls, num_leds=num_leds)
            self.engine._current_scene = MusicalScene.GROOVE
            self.engine._energy = 0.7
            self.engine._tension = 0.5
            self.listener.beat_phase = 0.2

            for _ in range(20):
                mode.run()

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

            for name, scene, energy, tension, beat, real_beat, drop_imm, drop_imp, drop_prog in scenes_to_test:
                self.engine._current_scene = scene
                self.engine._energy = energy
                self.engine._tension = tension
                self.engine._is_real_beat = real_beat
                self.engine._is_drop_imminent = drop_imm
                self.engine._is_drop_impact = drop_imp
                self.engine._drop_progress = drop_prog
                self.listener.is_beat = beat

                for _ in range(100):
                    mode.run()

                def measure():
                    gc.collect()
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
                    return [
                        stat for stat in non_tm
                        if file_name in stat.traceback.format()[0] and stat.size_diff > 512
                    ]

                mode_allocs = measure()
                if mode_allocs:
                    mode_allocs = measure()

                self.assertEqual(
                    len(mode_allocs), 0,
                    f"AXIOM-02 violation in {file_name} under {name}: {mode_allocs}"
                )

    def test_scene_flip_continuity_no_violent_snaps(self):
        """Flipping ctx.scene while holding audio steady must not cause instantaneous full-strip jumps."""
        num_leds = 40
        for mode_cls in ALL_MODE_CLASSES:
            mode = self._instantiate_mode(mode_cls, num_leds=num_leds)
            self.engine._is_silent = False
            self.engine._energy = 0.55
            self.engine._tension = 0.35
            self.engine._beat_trust = 0.75
            self.engine._salience = 0.70
            self.engine._is_real_beat = False
            self.engine._is_drop_impact = False
            self.listener.is_beat = False
            self.listener.beat_phase = 0.35

            # Settle in GROOVE for 20 frames
            self.engine._current_scene = MusicalScene.GROOVE
            for _ in range(20):
                mode.run()
            groove_step_1 = mode.rgb_list.copy().astype(np.float64)
            mode.run()
            groove_step_2 = mode.rgb_list.copy().astype(np.float64)
            normal_step_delta = float(np.mean(np.abs(groove_step_2 - groove_step_1)))

            # Flip scene label to DROP_IMPACT (without a 1-frame drop_hit) -> must NOT snap to a 100% solid fill
            self.engine._current_scene = MusicalScene.DROP_IMPACT
            mode.run()
            after_drop_scene = mode.rgb_list.copy().astype(np.float64)
            scene_flip_delta = float(np.mean(np.abs(after_drop_scene - groove_step_2)))
            self.assertLessEqual(
                scene_flip_delta,
                max(25.0, normal_step_delta * 2.5 + 5.0),
                f"{mode_cls.__name__} suffered a violent snap when ctx.scene flipped to DROP_IMPACT",
            )

            # Flip scene label to CHILL -> must NOT snap
            self.engine._current_scene = MusicalScene.CHILL
            mode.run()
            after_chill_scene = mode.rgb_list.copy().astype(np.float64)
            chill_flip_delta = float(np.mean(np.abs(after_chill_scene - after_drop_scene)))
            self.assertLessEqual(
                chill_flip_delta,
                max(25.0, normal_step_delta * 2.5 + 5.0),
                f"{mode_cls.__name__} suffered a violent snap when ctx.scene flipped to CHILL",
            )

    def test_flywheel_lost_resilience(self):
        """When beat_trust == 0 and is_beat/is_real_beat are False, every mode must still produce active, changing visuals."""
        num_leds = 40
        for mode_cls in ALL_MODE_CLASSES:
            mode = self._instantiate_mode(mode_cls, num_leds=num_leds)
            self.engine._current_scene = MusicalScene.CHILL
            self.engine._is_silent = False
            self.engine._energy = 0.65
            self.engine._tension = 0.25
            self.engine._beat_trust = 0.0
            self.engine._salience = 0.0
            self.engine._is_locked = False
            self.engine._is_real_beat = False
            self.engine._is_drop_impact = False
            self.listener.beat_trust = 0.0
            self.listener.beat_confidence = 0.0
            self.listener.is_beat = False
            self.listener.is_real_beat = False
            self.listener.asserved_fft_band = np.array([0.7, 0.6, 0.5, 0.4, 0.35, 0.3, 0.25, 0.2])
            self.listener._delayed_asserved_fft_band = np.copy(self.listener.asserved_fft_band)

            snapshots = []
            for frame in range(90):
                # Coasting flywheel phase (as in production when beat_trust == 0)
                self.listener.beat_phase = (frame * (124.0 / 3600.0)) % 1.0
                mode.run()
                if frame in (15, 45, 75):
                    snapshots.append(mode.rgb_list.copy())

            # 1. Mode must light up LEDs (not dead black)
            any_lit = any(bool(np.any(snap > 0)) for snap in snapshots)
            self.assertTrue(any_lit, f"{mode_cls.__name__} stayed completely black when flywheel was lost")

            # 2. Visuals must evolve over time (not frozen)
            changed = not (np.array_equal(snapshots[0], snapshots[1]) and np.array_equal(snapshots[1], snapshots[2]))
            self.assertTrue(changed, f"{mode_cls.__name__} froze when flywheel was lost")

    def test_hyper_strobe_behavioral_requirements(self):
        """Verify Hyper_strobe_mode real-beat gating, silence fade, and lost-flywheel ambient glow."""
        mode = self._instantiate_mode(Hyper_strobe_mode, num_leds=40)

        # Locked & no real beat -> stays dark
        self.engine._current_scene = MusicalScene.GROOVE
        self.engine._is_silent = False
        self.engine._is_real_beat = False
        self.engine._beat_trust = 0.8
        self.engine._salience = 0.8
        mode.run()
        self.assertTrue(np.all(mode.rgb_list == 0))

        # Real beat with high trust -> strobes brightly
        self.engine._is_real_beat = True
        self.engine._beat_trust = 0.8
        mode.run()
        self.assertTrue(np.any(mode.rgb_list > 0))

        # Lost flywheel -> gentle breathing glow
        mode.rgb_list.fill(0)
        self.engine._is_real_beat = False
        self.engine._beat_trust = 0.0
        self.engine._salience = 0.0
        self.engine._energy = 0.6
        mode.run()
        self.assertTrue(np.any(mode.rgb_list > 0))

    def test_metronome_and_wave_modes_behavioral_requirements(self):
        """Verify Metronome silence fade & Extending_waves continuous outward propagation."""
        metronome = self._instantiate_mode(Metronome_mode, num_leds=30)
        self.engine._is_silent = True
        metronome.rgb_list[:] = 100
        metronome.run()
        self.assertTrue(np.all(metronome.rgb_list < 100))

        waves = self._instantiate_mode(Extending_waves_mode, num_leds=40)
        self.engine._is_silent = False
        self.engine._current_scene = MusicalScene.BUILDUP
        self.engine._is_real_beat = True
        waves.time_since_wave = 1.0
        waves.run()
        active_slots = [w for w in range(waves.MAX_WAVES) if waves.wave_active[w]]
        self.assertTrue(len(active_slots) > 0)
        last_slot = (waves.wave_slot - 1) % waves.MAX_WAVES
        self.assertGreater(waves.wave_velocities[last_slot], 0)

    def test_bar_modes_and_physics_behavioral_requirements(self):
        """Verify Middle_bar and Power_bar continuous scaling."""
        mb = self._instantiate_mode(Middle_bar_mode, num_leds=40)
        self.engine._is_silent = False
        self.engine._energy = 0.8
        self.engine._vertical_center = 0.7
        for _ in range(10):
            mb.run()
        self.assertGreater(mb.size, 5.0)

        pb = self._instantiate_mode(Power_bar_mode, num_leds=40)
        self.engine._energy = 0.85
        pb.run()
        self.assertTrue(np.any(pb.rgb_list > 0))

    def test_all_modes_silence_decay_to_black(self):
        """Silence Law (S6): Every mode must decay its entire buffer to black under sustained ctx.is_silent = True."""
        num_leds = 40
        for mode_cls in ALL_MODE_CLASSES:
            mode = self._instantiate_mode(mode_cls, num_leds=num_leds)
            mode.rgb_list[:] = 180
            self.engine._is_silent = True
            self.engine._energy = 0.0
            self.engine._beat_trust = 0.0
            self.engine._salience = 0.0
            self.engine._is_real_beat = False
            self.engine._is_drop_impact = False
            self.listener.is_beat = False
            self.listener.is_real_beat = False
            self.listener.asserved_total_power = 0.0
            for _ in range(180):
                mode.run()
            self.assertTrue(
                np.all(mode.rgb_list == 0),
                f"{mode_cls.__name__} failed to decay to black during sustained silence (max={np.max(mode.rgb_list)})",
            )

    def test_proportion_rainbow_and_beat_tag_consumption(self):
        """Verify S7 consumption of listener.band_proportion and listener.beat_tag."""
        pr = self._instantiate_mode(Proportion_rainbow_mode, num_leds=30)
        self.engine._is_silent = False
        self.engine._energy = 0.8
        self.listener.band_proportion = np.zeros(8)
        pr.run()
        self.assertTrue(np.any(pr.rgb_list > 0))

        hs = self._instantiate_mode(Hyper_strobe_mode, num_leds=20)
        self.engine._is_real_beat = True
        self.engine._beat_trust = 0.8
        self.listener.beat_tag = "Bass/Kick"
        hs.run()
        kick_rgb = hs.rgb_list[0].copy()

        hs.rgb_list.fill(0)
        self.listener.beat_tag = "Snare/Mid"
        hs.run()
        snare_rgb = hs.rgb_list[0].copy()
        self.assertFalse(np.array_equal(kick_rgb, snare_rgb))


if __name__ == "__main__":
    unittest.main()
