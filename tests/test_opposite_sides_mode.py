"""
Unit tests for Opposite_sides_mode (Plan v2 redesign).
Verifies:
1. Fixed solid core pixels remain identical across frames when spectral_tilt, bands, and sparks vary.
2. Bass-only spectrum lights only the left wing; treble-only spectrum lights only the right wing.
3. Mode stays alive at rhythm_lock == 0 (non-black, evolving output).
4. Ghost beats (is_beat=True with is_real_beat=False) never spawn sparks; verified triggers do.
5. Output is deterministic for identical input sequences.
6. Fractional reach produces anti-aliased tips, and redirected transition buffers work cleanly.
"""
import unittest
import numpy as np

from music.MusicalContextEngine import MusicalContextEngine, MusicalScene
from mood.api import create_mood_service
from modes.Mode import Mode as BaseMode
from modes.Opposite_sides_mode import Opposite_sides_mode
from tests.test_all_modes_musical_context import MockListener


class TestOppositeSidesMode(unittest.TestCase):
    def setUp(self):
        self.mood = create_mood_service(initial_palette="Cyberpunk")
        BaseMode.bind_mood_colors(self.mood.colors())
        BaseMode.bind_mood_modifiers(self.mood.modifiers())
        self.addCleanup(BaseMode.reset_mood_colors)

        self.listener = MockListener()
        self.engine = MusicalContextEngine(self.listener)
        self.engine._is_silent = False
        self.listener.context = self.engine

    def _make_mode(self, num_leds: int = 50, segment: str = "test_segment") -> Opposite_sides_mode:
        rgb = np.zeros((num_leds, 3), dtype=np.int32)
        return Opposite_sides_mode(
            "Opposite_sides_mode",
            segment,
            self.listener,
            None,
            list(range(num_leds)),
            rgb,
            {},
        )

    def test_core_pixels_remain_identical_when_tilt_bands_and_sparks_vary(self):
        """The central core slice is fixed in position and solid in colour across varying tilt, bands, and sparks."""
        mode = self._make_mode(num_leds=50)
        self.assertEqual(mode.core_width, 4)  # round(0.08 * 50) = 4
        core_slice = slice(mode.mid_start, mode.mid_end + 1)

        core_snapshots = []
        configs = [
            (-0.85, np.array([0.9, 0.8, 0.7, 0.1, 0.0, 0.0, 0.0, 0.0]), False, False),
            (0.00, np.array([0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4]), True, False),
            (0.85, np.array([0.0, 0.0, 0.0, 0.1, 0.2, 0.8, 0.9, 1.0]), False, True),
            (-0.40, np.array([0.6, 0.5, 0.4, 0.3, 0.3, 0.5, 0.6, 0.7]), True, True),
        ]
        for tilt, bands, real_beat, drop_imp in configs:
            self.engine._spectral_tilt = tilt
            self.engine._is_real_beat = real_beat
            self.engine._is_drop_impact = drop_imp
            self.listener.asserved_fft_band = bands
            self.listener.band_flux = np.array([25.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 25.0])
            mode.run()
            core = mode.rgb_list[core_slice].copy()
            # Core is solid (every pixel inside the core matches the first core pixel)
            for row in core:
                np.testing.assert_array_equal(row, core[0])
            core_snapshots.append(core)

        for snap in core_snapshots[1:]:
            np.testing.assert_array_equal(snap, core_snapshots[0])

    def test_bass_only_lights_left_wing_and_treble_only_lights_right_wing(self):
        """A bass-only spectrum lights only the left wing; a treble-only spectrum lights only the right wing."""
        # 1. Bass-only
        mode_bass = self._make_mode(num_leds=50)
        self.engine._spectral_tilt = -0.9
        self.engine._is_real_beat = False
        self.engine._is_drop_impact = False
        self.listener.band_flux = np.zeros(8)
        self.listener.asserved_fft_band = np.array([0.9, 0.85, 0.8, 0.0, 0.0, 0.0, 0.0, 0.0])
        for _ in range(15):
            mode_bass.run()

        left_wing_bass = mode_bass.rgb_list[: mode_bass.mid_start]
        right_wing_bass = mode_bass.rgb_list[mode_bass.mid_end + 1 :]
        self.assertTrue(np.any(left_wing_bass > 0), "Left wing should be lit on bass-only spectrum")
        self.assertTrue(np.all(right_wing_bass == 0), "Right wing must remain dark on bass-only spectrum")

        # 2. Treble-only
        mode_treble = self._make_mode(num_leds=50)
        self.engine._spectral_tilt = 0.9
        self.listener.asserved_fft_band = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.8, 0.85, 0.9])
        for _ in range(15):
            mode_treble.run()

        left_wing_treble = mode_treble.rgb_list[: mode_treble.mid_start]
        right_wing_treble = mode_treble.rgb_list[mode_treble.mid_end + 1 :]
        self.assertTrue(np.all(left_wing_treble == 0), "Left wing must remain dark on treble-only spectrum")
        self.assertTrue(np.any(right_wing_treble > 0), "Right wing should be lit on treble-only spectrum")

    def test_stays_alive_at_zero_rhythm_lock(self):
        """At rhythm_lock == 0, both wings remain active and responsive to continuous spectrum changes."""
        mode = self._make_mode(num_leds=50)
        self.engine._beat_trust = 0.0
        self.engine._salience = 0.0
        self.engine._is_locked = False
        self.engine._is_real_beat = False
        self.listener.beat_trust = 0.0
        self.listener.beat_confidence = 0.0
        self.listener.is_beat = False
        self.listener.is_real_beat = False
        self.assertEqual(mode.rhythm_lock, 0.0)

        self.listener.asserved_fft_band = np.array([0.7, 0.6, 0.5, 0.3, 0.3, 0.5, 0.6, 0.7])
        for _ in range(10):
            mode.run()

        left_wing = mode.rgb_list[: mode.mid_start]
        right_wing = mode.rgb_list[mode.mid_end + 1 :]
        self.assertTrue(np.any(left_wing > 0))
        self.assertTrue(np.any(right_wing > 0))

    def test_no_sparks_on_ghost_beat_without_is_real_beat(self):
        """When unlocked, ghost beats and coasting phase wraps never spark; when locked, phase reaching 1 sparks."""
        mode = self._make_mode(num_leds=50)
        self.listener.asserved_fft_band = np.array([0.6, 0.6, 0.6, 0.3, 0.3, 0.6, 0.6, 0.6])
        self.listener.band_flux = np.zeros(8)
        self.engine._is_drop_impact = False
        self.engine._is_locked = False

        # Ghost beat while unlocked: is_beat=True, is_real_beat=False, plus coasting phase wrap
        self.listener.is_beat = True
        self.listener.is_real_beat = False
        self.engine._is_real_beat = False
        for ph in (0.2, 0.5, 0.85, 0.95, 0.05):
            self.listener.beat_phase = ph
            mode.run()
        self.assertEqual(float(np.max(mode._spark)), 0.0, "Ghost beats / coasting phase wraps must not spawn sparks")

        # Verified real beat while unlocked: is_real_beat=True
        self.engine._is_real_beat = True
        mode.run()
        self.assertGreater(float(np.max(mode._spark)), 0.0, "is_real_beat=True should spawn sparks when unlocked")
        self.assertTrue(np.all(mode._spark[mode.mid_start : mode.mid_end + 1] == 0.0), "Core must never have sparks")

        # When beat is locked (is_locked=True), sparks fire whenever beat_phase reaches 1 (wraps 0.92 -> 0.04)
        mode._spark.fill(0.0)
        mode._crackle_queue = 0
        self.engine._is_locked = True
        self.engine._is_real_beat = False
        self.listener.beat_phase = 0.92
        mode.run()
        self.assertEqual(float(np.max(mode._spark)), 0.0)
        self.listener.beat_phase = 0.04
        mode.run()
        self.assertGreater(float(np.max(mode._spark)), 0.0, "Locked phase wrap past 1.0 should spawn sparks")

    def test_deterministic_output_for_identical_input(self):
        """Two mode instances fed the exact same input sequence produce bit-identical RGB frames."""
        def run_sequence() -> np.ndarray:
            m = self._make_mode(num_leds=50, segment="det_seg")
            frames = []
            for f in range(40):
                self.engine._spectral_tilt = 0.6 * np.sin(f * 0.2)
                self.engine._is_real_beat = (f % 12 == 0)
                self.engine._is_drop_impact = (f == 25)
                self.listener.asserved_fft_band = np.array([
                    0.5 + 0.4 * np.sin(f * 0.15 + b * 0.3) for b in range(8)
                ])
                self.listener.band_flux = np.zeros(8)
                if f % 9 == 0:
                    self.listener.band_flux[f % 8] = 0.85
                m.run()
                frames.append(m.rgb_list.copy())
            return np.stack(frames)

        first = run_sequence()
        second = run_sequence()
        np.testing.assert_array_equal(first, second)

    def test_redirected_buffer_and_anti_aliased_tip(self):
        """Mode renders cleanly into a redirected buffer (Law 6) and produces intermediate tip values."""
        mode = self._make_mode(num_leds=60)
        self.listener.asserved_fft_band = np.array([0.45, 0.45, 0.45, 0.0, 0.0, 0.0, 0.0, 0.0])
        self.listener.band_flux = np.zeros(8)
        self.engine._is_real_beat = False
        self.engine._is_drop_impact = False

        own_before = mode.rgb_list.copy()
        alt_buffer = np.zeros_like(mode.rgb_list)
        mode.render(buffer=alt_buffer)

        np.testing.assert_array_equal(mode.rgb_list, own_before)
        self.assertTrue(np.any(alt_buffer > 0))
        # Verify fractional coverage exists in (0, 1) on the active wing tip
        fractional = mode._cov_l[(mode._cov_l > 0.0) & (mode._cov_l < 1.0)]
        self.assertEqual(len(fractional), 1, "Expected exactly 1 anti-aliased tip LED on the active wing")

    def test_spark_count_setting_and_spark_color_variable(self):
        """sparkCount setting scales firework crackle emission (0 disables sparks) and spark_color sets tint."""
        mode = self._make_mode(num_leds=50)
        np.testing.assert_array_equal(mode.spark_color, np.array([255.0, 255.0, 255.0]))
        self.assertEqual(mode.spark_count, 5)

        # Setting sparkCount=0 disables all sparks on beat, drop, and flux
        applied = mode.apply_settings({"sparkCount": 0})
        self.assertEqual(applied, {"sparkCount": 0})
        self.assertEqual(mode.spark_count, 0)
        self.engine._is_locked = False
        self.engine._is_real_beat = True
        self.engine._is_drop_impact = True
        self.listener.band_flux = np.full(8, 25.0)
        mode.run()
        self.assertEqual(float(np.max(mode._spark)), 0.0)

        # Raising sparkCount queues staggered 1-LED pinpoint pops ("pop de pop pop depop")
        mode.apply_settings({"sparkCount": 6})
        mode.spark_color[:] = (0.0, 255.0, 0.0)
        self.engine._is_drop_impact = False
        self.listener.band_flux = np.zeros(8)
        mode.run()
        # On the trigger frame, exactly 1 single-LED pinpoint pops immediately and the rest are queued
        self.assertEqual(int(np.sum(mode._spark > 0.1)), 1)
        self.assertGreater(mode._crackle_queue, 0)


if __name__ == "__main__":
    unittest.main()
