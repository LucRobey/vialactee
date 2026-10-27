"""
Tests for the shared Mode authoring helpers (modes/Mode.py) and related mode fixes.

Covers: drop_hit / drop_decay, dt / alpha, palette LUT + sampling, highlight_color luminance safety,
beat_pulse, segment_phase_offset, allocation-free blenders (numerical equivalence), the
Coloured_middle_wave transition-buffer fix, and a dead-settings ratchet.
"""
import ast
import inspect
import math
import sys
import unittest

import numpy as np

from music.MusicalContextEngine import MusicalContextEngine, MusicalScene
from mood.api import create_mood_service
from modes.Mode import Mode as BaseMode, PALETTE_LUT_SIZE
from modes.Coloured_middle_wave_mode import Coloured_middle_wave_mode
from tests.test_all_modes_musical_context import ALL_MODE_CLASSES, MockListener


def _luminance(rgb) -> float:
    return 0.2126 * float(rgb[0]) + 0.7152 * float(rgb[1]) + 0.0722 * float(rgb[2])


class _ModeTestCase(unittest.TestCase):
    PALETTE = "Cyberpunk"

    def setUp(self):
        self.mood = create_mood_service(initial_palette=self.PALETTE)
        BaseMode.bind_mood_colors(self.mood.colors())
        BaseMode.bind_mood_modifiers(self.mood.modifiers())
        self.addCleanup(BaseMode.reset_mood_colors)
        self.listener = MockListener()
        self.engine = MusicalContextEngine(self.listener)
        self.engine._is_silent = False
        self.listener.context = self.engine

    def make(self, cls=BaseMode, n=40, segment="test_segment"):
        rgb = np.zeros((n, 3), dtype=np.int32)
        return cls(cls.__name__, segment, self.listener, None, list(range(n)), rgb, {})


class TestDropHelpers(_ModeTestCase):
    def test_drop_hit_is_one_frame_trigger(self):
        mode = self.make()
        self.engine._current_scene = MusicalScene.DROP_IMPACT
        self.engine._is_drop_impact = True
        self.assertTrue(mode.drop_hit)
        self.engine._is_drop_impact = False  # dwell continues, trigger is gone
        self.assertFalse(mode.drop_hit)

    def test_drop_decay_follows_progress_only_inside_a_drop(self):
        mode = self.make()
        self.engine._current_scene = MusicalScene.DROP_IMPACT
        self.engine._drop_progress = 0.6
        self.assertAlmostEqual(mode.drop_decay, 0.6)
        self.engine._current_scene = MusicalScene.BUILDUP  # buildup also reports drop_progress
        self.assertEqual(mode.drop_decay, 0.0)

    def test_no_context_is_safe(self):
        mode = self.make()
        self.listener.context = None
        self.assertFalse(mode.drop_hit)
        self.assertEqual(mode.drop_decay, 0.0)
        self.assertGreaterEqual(mode.beat_pulse(), 0.0)


class TestTiming(_ModeTestCase):
    def test_dt_fallbacks(self):
        mode = self.make()
        self.listener.dt = 0.02
        self.assertAlmostEqual(mode.dt, 0.02)
        self.assertAlmostEqual(mode.fps_ratio, 1.2)
        self.listener.dt = 0.0
        self.assertAlmostEqual(mode.dt, 1.0 / 60.0)
        self.listener.dt = "bad"
        self.assertAlmostEqual(mode.dt, 1.0 / 60.0)

    def test_alpha_is_frame_rate_independent(self):
        mode = self.make()
        self.listener.dt = 1.0 / 30.0
        one_long_frame = mode.alpha(8.0)
        self.listener.dt = 1.0 / 60.0
        two_short_frames = 1.0 - (1.0 - mode.alpha(8.0)) ** 2
        self.assertAlmostEqual(one_long_frame, two_short_frames, places=9)
        self.assertEqual(mode.alpha(0.0), 0.0)
        self.assertLess(mode.alpha(1e6), 1.0 + 1e-12)

    def test_segment_phase_offset_is_stable_and_distinct(self):
        a1 = self.make(segment="segment_h00").segment_phase_offset
        a2 = self.make(segment="segment_h00").segment_phase_offset
        b = self.make(segment="segment_v3").segment_phase_offset
        self.assertEqual(a1, a2)
        self.assertNotEqual(a1, b)
        for value in (a1, b):
            self.assertTrue(0.0 <= value < 1.0)


class TestPalette(_ModeTestCase):
    def test_lut_endpoints_and_midpoint(self):
        mode = self.make()
        lut = mode.palette_lut
        mood = self.mood.colors()
        self.assertEqual(lut.shape, (PALETTE_LUT_SIZE, 3))
        np.testing.assert_array_equal(lut[0], mood[0])
        np.testing.assert_array_equal(lut[-1], mood[2])
        mid = PALETTE_LUT_SIZE // 2
        np.testing.assert_allclose(lut[mid], mood[1], atol=3)

    def test_lut_refreshes_when_mood_changes(self):
        mode = self.make()
        before = mode.palette_lut.copy()
        other = np.array([(255, 0, 0), (0, 255, 0), (0, 0, 255), (9, 9, 9)], dtype=np.int32)
        BaseMode.bind_mood_colors(other)
        after = mode.palette_lut
        self.assertFalse(np.array_equal(before, after))
        np.testing.assert_array_equal(after[0], other[0])
        np.testing.assert_array_equal(after[-1], other[2])

    def test_palette_sample_matches_lut(self):
        mode = self.make(n=33)
        t = np.linspace(0.0, 1.0, 33)
        out = np.zeros((33, 3), dtype=np.int32)
        mode.palette_sample(t, out)
        expected = mode.palette_lut[(t * (PALETTE_LUT_SIZE - 1)).astype(np.intp)]
        np.testing.assert_array_equal(out, expected)

    def test_palette_sample_clamps_out_of_range(self):
        mode = self.make(n=4)
        t = np.array([-1.0, 0.0, 1.0, 5.0])
        out = np.zeros((4, 3), dtype=np.int32)
        mode.palette_sample(t, out)
        np.testing.assert_array_equal(out[0], mode.palette_lut[0])
        np.testing.assert_array_equal(out[3], mode.palette_lut[-1])


class TestHighlight(_ModeTestCase):
    def test_highlight_is_never_dimmer_than_any_slot(self):
        from mood.palettes import PALETTES

        for name in PALETTES:
            mood = create_mood_service(initial_palette=name)
            BaseMode.bind_mood_colors(mood.colors())
            mode = self.make()
            highlight = mode.highlight_color
            colors = mood.colors()
            self.assertGreaterEqual(
                _luminance(highlight), max(_luminance(c) for c in colors) - 1e-6,
                f"highlight dimmer than a palette slot on {name}",
            )
            self.assertTrue(np.all(highlight >= 0) and np.all(highlight <= 255))


class TestBeatPulse(_ModeTestCase):
    def setUp(self):
        super().setUp()
        self.mode = self.make()
        self.engine._energy = 0.8
        self.engine._tension = 0.0
        self.engine._is_silent = False

    def test_locked_pulse_is_punchy_and_phase_locked(self):
        self.engine._beat_trust = 1.0
        self.listener.beat_phase = 0.0
        self.assertAlmostEqual(self.mode.beat_pulse(2.0), 1.0)
        self.listener.beat_phase = 0.5
        self.assertAlmostEqual(self.mode.beat_pulse(2.0), 0.25, places=6)

    def test_lost_tempo_falls_back_to_acoustic_energy(self):
        self.engine._beat_trust = 0.0
        self.listener.beat_phase = 0.9  # rhythmic term would be ~0
        value = self.mode.beat_pulse()
        self.assertGreater(value, 0.4)
        self.assertLessEqual(value, 0.8)

    def test_silence_returns_zero_without_confidence(self):
        self.engine._beat_trust = 0.0
        self.engine._is_silent = True
        self.assertEqual(self.mode.beat_pulse(), 0.0)

    def test_always_in_unit_interval(self):
        for trust in (0.0, 0.5, 1.0):
            for phase in (0.0, 0.25, 0.99):
                for tension in (0.0, 1.0):
                    self.engine._beat_trust = trust
                    self.engine._tension = tension
                    self.listener.beat_phase = phase
                    self.assertTrue(0.0 <= self.mode.beat_pulse() <= 1.0)

    def test_rhythm_lock_and_mood_modifiers(self):
        self.engine._beat_trust = 0.0
        self.engine._salience = 0.8
        self.assertEqual(self.mode.rhythm_lock, 0.0)
        self.engine._beat_trust = 1.0
        self.engine._salience = 1.0
        self.assertAlmostEqual(self.mode.rhythm_lock, 1.0)
        self.assertAlmostEqual(self.mode.mood_pace, 1.0)
        self.assertAlmostEqual(self.mode.mood_sharpness, 1.0)
        self.assertAlmostEqual(self.mode.mood_trail, 1.0)
        self.assertAlmostEqual(self.mode.mood_accent, 0.0)


class TestBlendEquivalence(_ModeTestCase):
    def _reference(self, base, target, ratio):
        """Exact legacy implementation (two truncating steps into an int buffer)."""
        out = base.copy()
        np.multiply(out, 1.0 - ratio, out=out, casting='unsafe')
        np.add(out, np.asarray(target) * ratio, out=out, casting='unsafe')
        return out

    def test_segment_blend_with_colour_tuple(self):
        mode = self.make(n=20)
        mode.rgb_list[:] = np.arange(60).reshape(20, 3)
        base = mode.rgb_list.copy()
        mode.smooth_segment_vectorized(0.3, 4, 14, (200, 100, 50))
        expected = base.copy()
        expected[4:15] = self._reference(base[4:15], (200, 100, 50), 0.3)
        np.testing.assert_array_equal(mode.rgb_list, expected)

    def test_segment_blend_with_matrix_and_colour_array(self):
        mode = self.make(n=20)
        mode.rgb_list[:] = 100
        base = mode.rgb_list.copy()
        target = (np.arange(33).reshape(11, 3) * 7).astype(np.float32)
        mode.smooth_segment_vectorized(0.5, 2, 12, target)
        expected = base.copy()
        expected[2:13] = self._reference(base[2:13], target, 0.5)
        np.testing.assert_array_equal(mode.rgb_list, expected)

        base = mode.rgb_list.copy()
        mode.smooth_segment_vectorized(0.25, 0, 19, np.array([10, 20, 30], dtype=np.int32))
        np.testing.assert_array_equal(mode.rgb_list, self._reference(base, (10, 20, 30), 0.25))

    def test_full_blend(self):
        mode = self.make(n=12)
        mode.rgb_list[:] = 50
        base = mode.rgb_list.copy()
        target = np.full((12, 3), 250, dtype=np.int32)
        mode.smooth_vectorized(0.4, target)
        np.testing.assert_array_equal(mode.rgb_list, self._reference(base, target, 0.4))


class TestColouredMiddleWaveBuffer(_ModeTestCase):
    def test_draws_into_redirected_transition_buffer(self):
        mode = self.make(Coloured_middle_wave_mode, n=41)
        self.engine._energy = 0.9
        self.listener.asserved_fft_band = np.ones(8) * 0.9
        self.listener._delayed_asserved_fft_band = np.ones(8) * 0.9
        own_before = mode.rgb_list.copy()
        other = np.zeros_like(mode.rgb_list)
        for _ in range(5):
            mode.render(buffer=other)
        self.assertTrue(other.any(), "mode did not draw into the redirected buffer")
        np.testing.assert_array_equal(mode.rgb_list, own_before)


class TestDeadSettingsRatchet(_ModeTestCase):
    """A schema setting must be read somewhere outside __init__/get_settings_schema.

    KNOWN_DEAD is a ratchet: it lists existing offenders so new dead sliders fail the test.
    When you fix one, remove it from the list (the test fails if the list contains a fixed one).
    """

    KNOWN_DEAD: set = set()

    @staticmethod
    def _self_loads_outside_setup(source: str) -> set:
        found = set()
        for fn in ast.walk(ast.parse(source)):
            if isinstance(fn, ast.FunctionDef) and fn.name not in ("__init__", "get_settings_schema"):
                for node in ast.walk(fn):
                    if (
                        isinstance(node, ast.Attribute)
                        and isinstance(node.ctx, ast.Load)
                        and isinstance(node.value, ast.Name)
                        and node.value.id == "self"
                    ):
                        found.add(node.attr)
        return found

    def test_no_new_dead_settings(self):
        dead = set()
        for cls in ALL_MODE_CLASSES:
            mode = self.make(cls, n=30)
            used = self._self_loads_outside_setup(inspect.getsource(sys.modules[cls.__module__]))
            for descriptor in mode.get_settings_schema():
                attr = descriptor.get("attr") or descriptor.get("key")
                if attr not in used:
                    dead.add((cls.__name__, attr))
        self.assertEqual(
            dead - self.KNOWN_DEAD, set(),
            "New dead settings (exposed in the UI but never read by the mode)",
        )
        self.assertEqual(
            self.KNOWN_DEAD - dead, set(),
            "Fixed settings are still in KNOWN_DEAD; remove them from the ratchet",
        )


if __name__ == "__main__":
    unittest.main()
