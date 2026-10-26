"""
tests/test_mood_sector.py - Unit & axiom tests for the sealed mood sector (mood/).

- Curated palettes and RGB boundaries [0, 255].
- 2.0 s cosine crossfade mathematics, no-stall on repeated requests.
- AXIOM-01: update() <= 0.01 ms.  AXIOM-02: zero allocation in update().
- colors(): same read-only live view every call.
- Scene policy: debounce, DROP_IMPACT immediacy, auto-mode off by default.
"""
import gc
import time
import tracemalloc
import unittest

import numpy as np

from mood.api import MoodStatus, create_mood_service
from mood.palettes import PALETTES
from mood.scene_policy import (
    DEFAULT_DWELL,
    MODIFIER_DWELL,
    MODIFIER_FADE_DURATION,
    SCENE_TO_MODIFIERS,
    ModifierGovernor,
    SceneGovernor,
    modifiers_for_scene,
    palette_for_scene,
)


class TestMoodService(unittest.TestCase):
    def setUp(self):
        self.mood = create_mood_service(initial_palette="Cyberpunk")

    def test_curated_palettes_validity(self):
        """Curated palettes must exist and have 4 valid RGB triplets [0, 255]."""
        required = ["Cyberpunk", "Solar Ember", "Deep Ocean", "Ethereal", "Neon Acid", "Monochrome Chrome"]
        for pal in required:
            self.assertIn(pal, PALETTES)
            self.assertEqual(len(PALETTES[pal]), 4)
            for rgb in PALETTES[pal]:
                self.assertEqual(len(rgb), 3)
                for c in rgb:
                    self.assertTrue(0 <= c <= 255)

    def test_smooth_cosine_crossfade_progression(self):
        """Palette crossfade must follow the cosine curve and complete in 2.0 s."""
        status = self.mood.get_status()
        self.assertEqual(status.palette, "Cyberpunk")
        self.assertFalse(status.is_transitioning)

        self.assertTrue(self.mood.request_palette("Solar Ember", duration=2.0))
        status = self.mood.get_status()
        self.assertTrue(status.is_transitioning)
        self.assertEqual(status.target_palette, "Solar Ember")

        cyber = np.array(PALETTES["Cyberpunk"], dtype=np.float32)
        solar = np.array(PALETTES["Solar Ember"], dtype=np.float32)

        self.mood.update(1.0)  # progress 0.5 -> w = 0.5
        status = self.mood.get_status()
        self.assertTrue(status.is_transitioning)
        self.assertAlmostEqual(status.progress, 0.5, places=2)
        np.testing.assert_allclose(self.mood.colors(), 0.5 * cyber + 0.5 * solar, atol=2.0)

        self.mood.update(1.0)
        status = self.mood.get_status()
        self.assertFalse(status.is_transitioning)
        self.assertEqual(status.palette, "Solar Ember")
        self.assertEqual(status.progress, 1.0)
        np.testing.assert_array_equal(self.mood.colors(), PALETTES["Solar Ember"])

    def test_axiom_01_frame_budget(self):
        """update() must execute in <= 0.01 ms per frame."""
        self.mood.request_palette("Neon Acid", duration=2.0)
        for _ in range(50):
            self.mood.update(0.001)

        iterations = 500
        best_ms = float("inf")
        gc.collect()
        gc.disable()
        try:
            for _ in range(5):
                t0 = time.perf_counter()
                for _ in range(iterations):
                    self.mood.update(0.001)
                best_ms = min(best_ms, ((time.perf_counter() - t0) / iterations) * 1000.0)
        finally:
            gc.enable()
        self.assertLess(best_ms, 0.01, f"AXIOM-01 violation: mood update took {best_ms:.4f} ms > 0.01 ms")

    def test_axiom_02_zero_allocation_in_update(self):
        """update() must allocate ZERO dynamic heap memory during a crossfade (auto-mode on too)."""
        self.mood.set_auto_scene(True)
        self.mood.request_palette("Deep Ocean", duration=2.0)
        self.mood.update(MODIFIER_DWELL + 0.01, "CHILL")  # start modifier crossfade
        self.mood.update(0.01, "GROOVE")  # warm up palette + modifier fade + governors

        tracemalloc.start()
        start = tracemalloc.take_snapshot()
        for _ in range(50):
            self.mood.update(0.005, "GROOVE")
        end = tracemalloc.take_snapshot()
        tracemalloc.stop()

        in_sector = [s for s in end.compare_to(start, "lineno") if "mood" in s.traceback[0].filename
                     and "test_mood_sector" not in s.traceback[0].filename]
        total = sum(s.size_diff for s in in_sector)
        self.assertEqual(total, 0, f"AXIOM-02 violation: {total} bytes allocated in mood update: {in_sector}")

    def test_colors_is_one_live_read_only_view(self):
        """colors() is the same read-only (4, 3) int32 object and follows the crossfade live."""
        colors = self.mood.colors()
        self.assertIs(self.mood.colors(), colors)
        self.assertEqual(colors.shape, (4, 3))
        self.assertEqual(colors.dtype, np.int32)
        self.assertFalse(colors.flags.writeable)
        with self.assertRaises(ValueError):
            colors[0, 0] = 1

        before = colors.copy()
        self.mood.request_palette("Neon Acid", duration=2.0)
        self.mood.update(1.0)
        self.assertFalse(np.array_equal(colors, before))  # the old reference saw the change

    def test_unknown_palette_rejected(self):
        self.assertFalse(self.mood.request_palette("Nope"))
        self.assertEqual(self.mood.get_status().target_palette, "Cyberpunk")

    def test_unknown_initial_palette_falls_back(self):
        self.assertEqual(create_mood_service(initial_palette="Nope").get_status().palette, "Cyberpunk")

    def test_palette_no_stall_on_repeated_requests(self):
        """Repeated requests for the active target must not reset the crossfade timer."""
        self.mood.request_palette("Solar Ember", duration=2.0)
        self.mood.update(0.5)
        self.assertAlmostEqual(self.mood.get_status().progress, 0.25, places=2)

        self.assertTrue(self.mood.request_palette("Solar Ember", duration=2.0))
        self.assertAlmostEqual(self.mood.get_status().progress, 0.25, places=2)

        self.mood.update(0.5)
        self.assertAlmostEqual(self.mood.get_status().progress, 0.50, places=2)

    def test_next_palette_cycles(self):
        names = self.mood.get_status().available_palettes
        self.assertEqual(self.mood.next_palette(), names[1])
        self.assertEqual(self.mood.get_status().target_palette, names[1])

    def test_status_shape(self):
        status = self.mood.get_status()
        self.assertIsInstance(status, MoodStatus)
        self.assertEqual(status.available_palettes, tuple(PALETTES.keys()))
        self.assertFalse(status.auto_scene)

    def test_modifiers_is_one_live_read_only_view(self):
        """modifiers() is the same read-only (4,) float32 object and follows scene fades live."""
        mods = self.mood.modifiers()
        self.assertIs(self.mood.modifiers(), mods)
        self.assertEqual(mods.shape, (4,))
        self.assertEqual(mods.dtype, np.float32)
        self.assertFalse(mods.flags.writeable)
        with self.assertRaises(ValueError):
            mods[0] = 2.0

        before = mods.copy()
        self.mood.update(MODIFIER_DWELL + 0.05, "CHILL")
        self.mood.update(MODIFIER_FADE_DURATION * 0.5, "CHILL")
        self.assertFalse(np.array_equal(mods, before))

    def test_modifiers_decoupled_from_auto_scene_and_cosine_smoothed(self):
        """Even with auto_scene=False, modifiers() debounces (0.30s) and cosine-fades over 2.5s."""
        self.assertFalse(self.mood.get_status().auto_scene)
        # Short blip (< MODIFIER_DWELL) must not start a modifier transition
        self.mood.update(0.10, "DROP_IMPACT")
        np.testing.assert_allclose(self.mood.modifiers(), [1.0, 1.0, 1.0, 0.0], atol=1e-6)

        # Persist past debounce -> starts 2.5s cosine fade toward CHILL
        self.mood.update(MODIFIER_DWELL + 0.01, "CHILL")
        start_mods = np.array([1.0, 1.0, 1.0, 0.0], dtype=np.float32)
        chill_mods = np.array(SCENE_TO_MODIFIERS["CHILL"], dtype=np.float32)

        # Midpoint of 2.5s cosine crossfade -> 50% blend
        self.mood.update(MODIFIER_FADE_DURATION * 0.5)
        np.testing.assert_allclose(self.mood.modifiers(), 0.5 * (start_mods + chill_mods), atol=1e-3)

        # Complete crossfade -> exact CHILL target, while palette stayed Cyberpunk
        self.mood.update(MODIFIER_FADE_DURATION * 0.6)
        np.testing.assert_allclose(self.mood.modifiers(), chill_mods, atol=1e-5)
        self.assertEqual(self.mood.get_status().palette, "Cyberpunk")

    def test_modifiers_bounded_ranges(self):
        """All scene modifier targets stay within bounded subtle ranges."""
        for scene, (pace, sharpness, trail, accent) in SCENE_TO_MODIFIERS.items():
            self.assertEqual(modifiers_for_scene(scene.lower()), (pace, sharpness, trail, accent))
            self.assertTrue(0.75 <= pace <= 1.25, f"{scene} pace out of bounds")
            self.assertTrue(0.75 <= sharpness <= 1.25, f"{scene} sharpness out of bounds")
            self.assertTrue(0.80 <= trail <= 1.25, f"{scene} trail out of bounds")
            self.assertTrue(0.0 <= accent <= 0.30, f"{scene} accent out of bounds")


class TestSceneDriven(unittest.TestCase):
    def test_scene_mapping(self):
        self.assertEqual(palette_for_scene("CHILL"), "Deep Ocean")
        self.assertEqual(palette_for_scene("chill"), "Deep Ocean")
        self.assertEqual(palette_for_scene("BUILDUP"), "Solar Ember")
        self.assertEqual(palette_for_scene("DROP_IMPACT"), "Neon Acid")
        self.assertIsNone(palette_for_scene("STRUCTURAL_CHANGE"))

    def test_governor_debounces_scene(self):
        gov = SceneGovernor()
        self.assertIsNone(gov.update(1.0, "BUILDUP"))
        self.assertIsNone(gov.update(1.0, "BUILDUP"))
        self.assertEqual(gov.update(DEFAULT_DWELL, "BUILDUP"), "Solar Ember")
        self.assertIsNone(gov.update(5.0, "BUILDUP"))  # already applied: no repeat

    def test_governor_flicker_resets_timer(self):
        gov = SceneGovernor()
        gov.update(2.0, "BUILDUP")
        gov.update(0.1, "CHILL")   # scene changed: timer restarts
        self.assertIsNone(gov.update(2.0, "CHILL"))
        self.assertEqual(gov.update(DEFAULT_DWELL, "CHILL"), "Deep Ocean")

    def test_drop_impact_is_debounced_not_instant(self):
        """A 1.5s drop must not hijack the palette; all scenes require DEFAULT_DWELL (4.0s)."""
        gov = SceneGovernor()
        self.assertIsNone(gov.update(0.016, "DROP_IMPACT"))
        self.assertIsNone(gov.update(1.5, "DROP_IMPACT"))
        self.assertEqual(gov.update(DEFAULT_DWELL, "DROP_IMPACT"), "Neon Acid")
        self.assertIsNone(ModifierGovernor().update(0.1, "DROP_IMPACT"))
        self.assertEqual(ModifierGovernor().update(MODIFIER_DWELL, "DROP_IMPACT"), "DROP_IMPACT")

    def test_auto_mode_off_by_default_does_nothing(self):
        mood = create_mood_service()
        mood.update(10.0, "DROP_IMPACT")
        self.assertEqual(mood.get_status().target_palette, "Cyberpunk")

    def test_auto_mode_drives_palette(self):
        mood = create_mood_service(auto_scene=True)
        mood.update(DEFAULT_DWELL + 0.1, "BUILDUP")
        self.assertEqual(mood.get_status().target_palette, "Solar Ember")
        self.assertTrue(mood.get_status().is_transitioning)

    def test_manual_pick_is_not_held(self):
        """No manual hold: a manual pick works and the next debounced scene change takes over again."""
        mood = create_mood_service(auto_scene=True)
        mood.update(DEFAULT_DWELL + 0.1, "BUILDUP")    # auto -> Solar Ember
        self.assertTrue(mood.request_palette("Ethereal"))
        self.assertEqual(mood.get_status().target_palette, "Ethereal")
        mood.update(DEFAULT_DWELL + 0.1, "CHILL")      # scene change -> auto resumes
        self.assertEqual(mood.get_status().target_palette, "Deep Ocean")


if __name__ == "__main__":
    unittest.main()
