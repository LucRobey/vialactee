"""
Behavioural tests for Extending_waves_mode:
- Continuous center-outward scrolling wavelength stream (Lead: spectrum, Secondary: transient).
- Balanced dominant wavelength selection across all FFT bands (deviation + attack + onset flux + anti-stagnation fatigue).
- Crisp Red drum peaks on Band 0 attacks that immediately yield to melodic/harmonic wavelengths between hits.
- Steady volume-independent outward extension speed across scenes and strict center symmetry.
"""
import unittest

import numpy as np

import modes.Mode as BaseModeMod
from music.MusicalContextEngine import MusicalScene
from modes.Extending_waves_mode import Extending_waves_mode
from tests.test_mode_helpers import _ModeTestCase


class TestExtendingWavesSpectrumStream(_ModeTestCase):
    def setUp(self):
        super().setUp()
        self.engine._current_scene = MusicalScene.GROOVE
        self.engine._energy = 0.60
        self.engine._beat_trust = 0.85
        self.engine._salience = 0.80
        self.engine._is_real_beat = False
        self.listener.nb_of_fft_band = 8
        self.listener.asserved_fft_band = np.full(8, 0.20, dtype=np.float64)
        self.listener.band_flux = np.zeros(8, dtype=np.float64)

    def tearDown(self):
        BaseModeMod.Mode.reset_mood_colors()
        BaseModeMod.Mode.reset_mood_modifiers()
        super().tearDown()

    def mode(self, n=41):
        rgb = np.zeros((n, 3), dtype=np.int32)
        return Extending_waves_mode("Extending Waves", "seg", self.listener, None, list(range(n)), rgb, {})

    def test_bass_drum_transient_produces_red_peak_and_outward_wave(self):
        mode = self.mode()
        # Prime baseline spectrum
        mode.run()

        # Trigger a kick/drum hit in Band 0
        self.listener.asserved_fft_band[0] = 0.92
        self.listener.band_flux[0] = 12.0
        self.engine._is_real_beat = True
        mode.time_since_wave = 1.0
        mode.run()

        self.assertEqual(mode.dominant_band, 0)
        self.assertAlmostEqual(mode._current_hue, 0.0, places=2)
        self.assertGreater(mode._center_rgb[0], 180.0)
        self.assertGreater(mode._center_rgb[0], 4.0 * mode._center_rgb[1] + 1.0)
        self.assertGreater(mode._center_rgb[0], 4.0 * mode._center_rgb[2] + 1.0)
        self.assertGreaterEqual(mode.wave_count, 1)
        self.assertGreater(mode.wave_velocities[0], 0.0)

    def test_dominant_wavelength_maps_across_full_spectrum(self):
        # 1. Low band (b=0) -> Red (hue ~ 0.0)
        mode_low = self.mode()
        mode_low.run()
        self.listener.asserved_fft_band[:] = 0.15
        self.listener.asserved_fft_band[0] = 0.90
        self.listener.band_flux[0] = 10.0
        for _ in range(4):
            mode_low.run()
        self.assertEqual(mode_low.dominant_band, 0)
        self.assertLess(mode_low._current_hue, 0.08)

        # 2. Mid band (b=4) -> Green / Cyan (hue ~ 0.40 - 0.55)
        mode_mid = self.mode()
        self.listener.asserved_fft_band[:] = 0.15
        self.listener.band_flux[:] = 0.0
        mode_mid.run()
        self.listener.asserved_fft_band[4] = 0.90
        self.listener.band_flux[4] = 10.0
        for _ in range(8):
            mode_mid.run()
        self.assertEqual(mode_mid.dominant_band, 4)
        self.assertGreater(mode_mid._current_hue, 0.32)
        self.assertLess(mode_mid._current_hue, 0.60)

        # 3. High band (b=7) -> Blue / Violet (hue > 0.68)
        mode_high = self.mode()
        self.listener.asserved_fft_band[:] = 0.15
        self.listener.band_flux[:] = 0.0
        mode_high.run()
        self.listener.asserved_fft_band[7] = 0.92
        self.listener.band_flux[7] = 10.0
        for _ in range(8):
            mode_high.run()
        self.assertEqual(mode_high.dominant_band, 7)
        self.assertGreater(mode_high._current_hue, 0.68)

    def test_anti_stagnation_fatigue_rotates_sustained_dominant_band(self):
        mode = self.mode()
        mode.run()

        visited_bands = set()
        for f in range(90):
            # Two bands oscillate gently while Band 2 starts slightly higher than Band 6
            wobble = 0.06 * float(np.sin(f * 0.35))
            self.listener.asserved_fft_band[:] = 0.15
            self.listener.asserved_fft_band[2] = 0.78 + wobble
            self.listener.asserved_fft_band[6] = 0.72 - wobble
            mode.run()
            visited_bands.add(mode.dominant_band)

        self.assertIn(2, visited_bands)
        self.assertIn(6, visited_bands)
        self.assertGreaterEqual(len(visited_bands), 2)

    def test_post_drum_peak_hands_off_to_melodic_band(self):
        mode = self.mode()
        mode.run()

        # Frame 1: Drum hit on Band 0 alongside melodic rise on Band 5
        self.listener.asserved_fft_band[0] = 0.90
        self.listener.asserved_fft_band[5] = 0.65
        self.listener.band_flux[0] = 14.0
        self.engine._is_real_beat = True
        mode.run()
        self.assertEqual(mode.dominant_band, 0)

        # Step through the 4-frame drum hold while Band 5 remains active
        self.engine._is_real_beat = False
        self.listener.band_flux[:] = 0.0
        for i in range(6):
            self.listener.asserved_fft_band[0] = 0.75 - 0.03 * i
            self.listener.asserved_fft_band[5] = 0.68 + 0.03 * i
            mode.run()

        self.assertEqual(mode.dominant_band, 5)
        self.assertGreater(mode._current_hue, 0.40)

    def test_outward_scroll_speed_is_steady_and_volume_independent(self):
        mode_quiet = self.mode()
        self.engine._energy = 0.12
        pos_q0 = mode_quiet.scroll_pos
        for i in range(10):
            self.listener.asserved_fft_band[2] = 0.30 + 0.02 * i
            mode_quiet.run()
        delta_quiet = mode_quiet.scroll_pos - pos_q0

        mode_loud = self.mode()
        self.engine._energy = 0.95
        pos_l0 = mode_loud.scroll_pos
        for i in range(10):
            self.listener.asserved_fft_band[2] = 0.30 + 0.02 * i
            mode_loud.run()
        delta_loud = mode_loud.scroll_pos - pos_l0

        self.assertGreater(delta_quiet, 0.0)
        self.assertAlmostEqual(delta_quiet, delta_loud, places=6)

    def test_red_drum_peak_propagates_outward_without_reversal_in_buildup(self):
        mode = self.mode(n=41)
        self.engine._current_scene = MusicalScene.BUILDUP
        mode.run()

        # Inject a strong Red drum hit at center
        self.listener.asserved_fft_band[0] = 0.95
        self.listener.band_flux[0] = 15.0
        self.engine._is_real_beat = True
        mode.run()

        # Switch to a blue high-frequency wave afterward and let the Red peak travel outward
        self.engine._is_real_beat = False
        self.listener.band_flux[:] = 0.0
        self.listener.asserved_fft_band[:] = 0.15
        for i in range(18):
            self.listener.asserved_fft_band[7] = 0.65 + 0.01 * (i % 3)
            mode.run()

        # Outer half-strip must now hold the propagated Red energy while center has shifted to Blue/Violet
        outer_red = float(np.max(mode.half_rgb[5:16, 0]))
        self.assertGreater(outer_red, 80.0)
        self.assertGreater(mode.wave_velocities[0], 0.0)

    def test_output_is_centre_symmetric(self):
        mode = self.mode(n=41)
        for i in range(25):
            b = i % 8
            self.listener.asserved_fft_band[:] = 0.18
            self.listener.asserved_fft_band[b] = 0.82
            self.listener.band_flux[b] = 6.0 if (i % 4 == 0) else 0.0
            mode.run()
        np.testing.assert_array_equal(mode.rgb_list, mode.rgb_list[::-1])

    def test_silence_fades_strip_and_clears_active_waves(self):
        mode = self.mode(n=41)
        self.listener.asserved_fft_band[0] = 0.90
        self.listener.band_flux[0] = 12.0
        self.engine._is_real_beat = True
        mode.time_since_wave = 1.0
        mode.run()
        self.assertTrue(bool(np.any(mode.wave_active)))
        peak_sum = int(np.sum(mode.rgb_list))
        self.assertGreater(peak_sum, 0)

        # Sustained silence (> 22 frames) clears active waves and decays strip toward black
        self.engine._is_silent = True
        for _ in range(30):
            mode.run()
        self.assertFalse(bool(np.any(mode.wave_active)))
        self.assertLess(int(np.sum(mode.rgb_list)), peak_sum)

    def test_brief_silence_pocket_between_beats_does_not_freeze_or_black_out(self):
        mode = self.mode(n=41)
        for i in range(15):
            self.listener.asserved_fft_band[i % 8] = 0.85
            mode.run()

        # Simulate a 15-frame rhythmic pocket right after a big beat where ctx.is_silent flickers True
        self.engine._is_silent = True
        for _ in range(15):
            prev_scroll = mode.scroll_pos
            mode.run()
            self.assertGreater(mode.scroll_pos, prev_scroll, "scroll_pos froze during brief inter-beat pocket")
            self.assertGreater(int(np.max(mode.rgb_list)), 120, "strip blacked out during brief inter-beat pocket")

    def test_saturated_bands_on_big_beat_do_not_reset_history_to_black(self):
        mode = self.mode(n=41)
        for i in range(20):
            self.listener.asserved_fft_band[:] = 0.25
            self.listener.asserved_fft_band[i % 8] = 0.88
            mode.run()

        # Simulate a loud big beat where all 8 bands of asserved_fft_band clip at 1.0 for 10 frames
        self.listener.asserved_fft_band[:] = 1.0
        for _ in range(10):
            mode.run()
            self.assertGreater(int(np.max(mode.rgb_list)), 150, "strip reset to black when bands saturated at 1.0")
            self.assertGreater(float(np.max(mode._center_rgb)), 100.0)

    def test_locked_beat_phase_and_sound_power_modulate_center_intensity(self):
        mode = self.mode(n=41)
        self.engine._is_locked = True
        self.engine._beat_trust = 0.90
        self.engine._salience = 0.85
        self.engine._energy = 0.85
        self.engine._power = 0.85
        self.listener.asserved_total_power = 0.85
        self.listener.asserved_fft_band[:] = 0.30
        self.listener.asserved_fft_band[2] = 0.85

        # 1. At beat_phase = 0.50 (mid-beat valley): intensity is low, but not too low (visible rhythm)
        self.listener.beat_phase = 0.50
        mode.run()
        self.listener.asserved_fft_band[2] = 0.88
        mode.run()
        mid_phase_intensity = float(np.max(mode._center_rgb))
        self.assertGreater(mid_phase_intensity, 25.0)
        self.assertLess(mid_phase_intensity, 95.0)

        # 2. Close to phase 1 (beat_phase = 0.98): very intense light coming out from the middle
        self.listener.beat_phase = 0.98
        self.listener.asserved_fft_band[2] = 0.90
        mode.run()
        peak_phase_intensity = float(np.max(mode._center_rgb))
        self.assertGreater(peak_phase_intensity, 180.0)
        self.assertGreater(peak_phase_intensity, 2.8 * mid_phase_intensity)

        # 3. Lower sound power produces lower peak intensity than high sound power
        mode_soft = self.mode(n=41)
        self.engine._energy = 0.12
        self.engine._power = 0.12
        self.listener.asserved_total_power = 0.12
        self.listener.asserved_fft_band[:] = 0.08
        self.listener.asserved_fft_band[2] = 0.20
        self.listener.beat_phase = 0.98
        mode_soft.run()
        self.listener.asserved_fft_band[2] = 0.22
        mode_soft.run()
        soft_peak_intensity = float(np.max(mode_soft._center_rgb))
        self.assertLess(soft_peak_intensity, peak_phase_intensity * 0.70)

    def test_16_band_spectrum_mapping(self):
        self.listener.nb_of_fft_band = 16
        self.listener.asserved_fft_band = np.full(16, 0.15, dtype=np.float64)
        self.listener.band_flux = np.zeros(16, dtype=np.float64)
        mode = self.mode(n=41)
        self.assertEqual(mode.nb_bands, 16)
        mode.run()
        self.listener.asserved_fft_band[15] = 0.92
        self.listener.band_flux[15] = 10.0
        for _ in range(8):
            mode.run()
        self.assertEqual(mode.dominant_band, 15)
        self.assertGreater(mode._current_hue, 0.70)


if __name__ == "__main__":
    unittest.main()
