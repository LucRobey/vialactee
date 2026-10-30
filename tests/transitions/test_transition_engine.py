"""
Unit tests for transitions/engine.py.
Verifies all mathematical transitions, geometric spatial masks,
progress clamping, and dispatcher routing.
"""
import unittest
import numpy as np

import transitions.engine as TE


class TestTransitionEngine(unittest.TestCase):
    def setUp(self):
        self.num_leds = 64
        self.old_rgb = np.full((self.num_leds, 3), 200, dtype=np.int32)
        self.new_rgb = np.full((self.num_leds, 3), 50, dtype=np.int32)
        # Synthetic coordinates spanning the room dimensions (430 x 246)
        xs = np.linspace(0, TE.ROOM_MAX_X, self.num_leds)
        ys = np.linspace(0, TE.ROOM_MAX_Y, self.num_leds)
        self.coords = np.column_stack([xs, ys])

    def test_apply_dual_fade(self):
        old = self.old_rgb.copy()
        TE.apply_dual_fade(old, self.new_rgb, progress=0.0)
        np.testing.assert_array_equal(old, self.old_rgb)

        old = self.old_rgb.copy()
        TE.apply_dual_fade(old, self.new_rgb, progress=1.0)
        np.testing.assert_array_equal(old, self.new_rgb)

        old = self.old_rgb.copy()
        TE.apply_dual_fade(old, self.new_rgb, progress=0.5)
        expected = ((self.old_rgb * 0.5) + (self.new_rgb * 0.5)).astype(np.int32)
        np.testing.assert_array_almost_equal(old, expected, decimal=0)

    def test_apply_colorful_glitch(self):
        old = self.old_rgb.copy()
        TE.apply_colorful_glitch(old, self.new_rgb, progress=0.0)
        np.testing.assert_array_equal(old, self.old_rgb)

        old = self.old_rgb.copy()
        TE.apply_colorful_glitch(old, self.new_rgb, progress=1.0)
        np.testing.assert_array_equal(old, self.new_rgb)

        old = self.old_rgb.copy()
        TE.apply_colorful_glitch(old, self.new_rgb, progress=0.4)
        self.assertEqual(old.shape, (self.num_leds, 3))
        self.assertTrue(np.all(old >= 0) and np.all(old <= 255))

    def test_apply_gravity_drop(self):
        old = self.old_rgb.copy()
        TE.apply_gravity_drop(old, self.new_rgb, self.coords, progress=0.0)
        np.testing.assert_array_equal(old, self.old_rgb)

        old = self.old_rgb.copy()
        TE.apply_gravity_drop(old, self.new_rgb, self.coords, progress=1.0)
        np.testing.assert_array_equal(old, self.new_rgb)

        old = self.old_rgb.copy()
        TE.apply_gravity_drop(old, self.new_rgb, self.coords, progress=0.5)
        self.assertEqual(old.shape, (self.num_leds, 3))

    def test_apply_weird_glitch(self):
        old = self.old_rgb.copy()
        TE.apply_weird_glitch(old, self.new_rgb, self.coords, progress=0.0)
        np.testing.assert_array_equal(old, self.old_rgb)

        old = self.old_rgb.copy()
        TE.apply_weird_glitch(old, self.new_rgb, self.coords, progress=1.0)
        np.testing.assert_array_equal(old, self.new_rgb)

        old = self.old_rgb.copy()
        TE.apply_weird_glitch(old, self.new_rgb, self.coords, progress=0.5)
        self.assertEqual(old.shape, (self.num_leds, 3))

    def test_apply_explosion(self):
        old = self.old_rgb.copy()
        TE.apply_explosion(old, self.new_rgb, self.coords, progress=0.0)
        np.testing.assert_array_equal(old, self.old_rgb)

        old = self.old_rgb.copy()
        TE.apply_explosion(old, self.new_rgb, self.coords, progress=1.0)
        np.testing.assert_array_equal(old, self.new_rgb)

        # Implosion phase (progress < 0.52)
        old = self.old_rgb.copy()
        TE.apply_explosion(old, self.new_rgb, self.coords, progress=0.3)
        self.assertEqual(old.shape, (self.num_leds, 3))

        # Blackout phase (0.52 <= progress < 0.60)
        old = self.old_rgb.copy()
        TE.apply_explosion(old, self.new_rgb, self.coords, progress=0.56)
        np.testing.assert_array_equal(old, np.zeros_like(old))

        # Explosion phase (progress >= 0.60)
        old = self.old_rgb.copy()
        TE.apply_explosion(old, self.new_rgb, self.coords, progress=0.8)
        self.assertEqual(old.shape, (self.num_leds, 3))

    def test_apply_horizontal_wipe(self):
        old = self.old_rgb.copy()
        TE.apply_horizontal_wipe(old, self.new_rgb, self.coords, progress=0.0)
        np.testing.assert_array_equal(old, self.old_rgb)

        old = self.old_rgb.copy()
        TE.apply_horizontal_wipe(old, self.new_rgb, self.coords, progress=1.0)
        np.testing.assert_array_equal(old, self.new_rgb)

        # Midway wipe (left-to-right)
        old = self.old_rgb.copy()
        TE.apply_horizontal_wipe(old, self.new_rgb, self.coords, progress=0.5, beam_thickness=0.05, reverse=False)
        # Leftmost LED (x=0) must be swapped to new_rgb
        np.testing.assert_array_equal(old[0], self.new_rgb[0])
        # Rightmost LED (x=430) must remain old_rgb
        np.testing.assert_array_equal(old[-1], self.old_rgb[-1])

        # Reverse wipe (right-to-left)
        old = self.old_rgb.copy()
        TE.apply_horizontal_wipe(old, self.new_rgb, self.coords, progress=0.5, beam_thickness=0.05, reverse=True)
        # Rightmost LED (x=430, normalized reversed=0.0) should be swapped to new_rgb
        np.testing.assert_array_equal(old[-1], self.new_rgb[-1])
        # Leftmost LED should remain old_rgb
        np.testing.assert_array_equal(old[0], self.old_rgb[0])

    def test_apply_vertical_wipe(self):
        old = self.old_rgb.copy()
        TE.apply_vertical_wipe(old, self.new_rgb, self.coords, progress=0.0)
        np.testing.assert_array_equal(old, self.old_rgb)

        old = self.old_rgb.copy()
        TE.apply_vertical_wipe(old, self.new_rgb, self.coords, progress=1.0)
        np.testing.assert_array_equal(old, self.new_rgb)

        old = self.old_rgb.copy()
        TE.apply_vertical_wipe(old, self.new_rgb, self.coords, progress=0.5, beam_thickness=0.05)
        np.testing.assert_array_equal(old[0], self.new_rgb[0])
        np.testing.assert_array_equal(old[-1], self.old_rgb[-1])

    def test_apply_box_wipe(self):
        old = self.old_rgb.copy()
        TE.apply_box_wipe(old, self.new_rgb, self.coords, progress=0.0)
        np.testing.assert_array_equal(old, self.old_rgb)

        old = self.old_rgb.copy()
        TE.apply_box_wipe(old, self.new_rgb, self.coords, progress=1.0)
        np.testing.assert_array_equal(old, self.new_rgb)

        old = self.old_rgb.copy()
        TE.apply_box_wipe(old, self.new_rgb, self.coords, progress=0.5)
        self.assertEqual(old.shape, (self.num_leds, 3))

    def test_apply_spiral_transition(self):
        old = self.old_rgb.copy()
        TE.apply_spiral_transition(old, self.new_rgb, self.coords, progress=0.0)
        np.testing.assert_array_equal(old, self.old_rgb)

        old = self.old_rgb.copy()
        TE.apply_spiral_transition(old, self.new_rgb, self.coords, progress=1.0)
        np.testing.assert_array_equal(old, self.new_rgb)

        old = self.old_rgb.copy()
        TE.apply_spiral_transition(old, self.new_rgb, self.coords, progress=0.5)
        self.assertEqual(old.shape, (self.num_leds, 3))

    def test_apply_transition_forwards_beam_thickness_to_spiral(self):
        """The dispatcher must pass beam_thickness to the spiral wipe like it does for the other wipes."""
        via_dispatcher = self.old_rgb.copy()
        TE.apply_transition(via_dispatcher, self.new_rgb, 0.5, "spiral", self.coords, beam_thickness=0.5)

        direct = self.old_rgb.copy()
        TE.apply_spiral_transition(direct, self.new_rgb, self.coords, 0.5, 0.5)
        np.testing.assert_array_equal(via_dispatcher, direct)

        default_width = self.old_rgb.copy()
        TE.apply_transition(default_width, self.new_rgb, 0.5, "spiral", self.coords)
        self.assertFalse(np.array_equal(via_dispatcher, default_width))

    def test_apply_transition_dispatcher_all_names(self):
        """Verify that every transition known to the system executes safely without raising exceptions."""
        all_transitions = [
            "fade_to_black",
            "fade_in_out",
            "global_change",
            "wipe_left_to_right",
            "wipe_right_to_left",
            "vertical_wipe",
            "box_wipe",
            "spiral",
            "gravity_drop",
            "weird_glitch",
            "explosion",
            "ember_dissolve",
            "luma_melt",
            "breath_dip",
            "silk_wipe",
            "silk_wipe_reverse",
            "iris_open",
            "iris_close",
            "zipper_merge",
            "collider",
            "prism_sweep",
            "flash_cut",
            "staccato_shutter",
            "transformer_cut",
            "non_existent_transition",  # Graceful fallback test
        ]
        for trans in all_transitions:
            with self.subTest(transition=trans):
                old = self.old_rgb.copy()
                TE.apply_transition(old, self.new_rgb, progress=0.5, transition_name=trans, coords=self.coords)
                self.assertEqual(old.shape, (self.num_leds, 3))
                self.assertTrue(np.all(old >= 0) and np.all(old <= 255))
                probe = old.copy()
                if np.array_equal(probe, self.old_rgb):
                    TE.apply_transition(probe, self.new_rgb, progress=0.7, transition_name=trans, coords=self.coords)
                self.assertFalse(np.array_equal(probe, self.old_rgb), f"{trans} did not mutate buffer during transition")

    def test_new_strip_intrinsic_transitions_endpoints_and_midpoint(self):
        """Every new transition must preserve old_rgb at progress=0.0, reach new_rgb at progress=1.0, and mutate in-place."""
        new_transitions = [
            "ember_dissolve",
            "luma_melt",
            "breath_dip",
            "silk_wipe",
            "silk_wipe_reverse",
            "iris_open",
            "iris_close",
            "zipper_merge",
            "collider",
            "prism_sweep",
            "flash_cut",
            "staccato_shutter",
            "transformer_cut",
        ]
        for trans in new_transitions:
            with self.subTest(transition=trans):
                buf0 = self.old_rgb.copy()
                TE.apply_transition(buf0, self.new_rgb, progress=0.0, transition_name=trans, coords=None)
                np.testing.assert_array_equal(buf0, self.old_rgb)

                buf1 = self.old_rgb.copy()
                TE.apply_transition(buf1, self.new_rgb, progress=1.0, transition_name=trans, coords=None)
                np.testing.assert_array_equal(buf1, self.new_rgb)

                buf_mid = self.old_rgb.copy()
                buf_id = id(buf_mid)
                TE.apply_transition(buf_mid, self.new_rgb, progress=0.5, transition_name=trans, coords=None)
                self.assertEqual(id(buf_mid), buf_id)
                self.assertEqual(buf_mid.shape, (self.num_leds, 3))
                self.assertTrue(np.all(buf_mid >= 0) and np.all(buf_mid <= 255))
                if np.array_equal(buf_mid, self.old_rgb):
                    TE.apply_transition(buf_mid, self.new_rgb, progress=0.7, transition_name=trans, coords=None)
                self.assertFalse(np.array_equal(buf_mid, self.old_rgb), f"{trans} did not mutate buffer during transition")

    def test_apply_transition_missing_coords_fallback(self):
        """When coords=None, spatial transitions must safely fall back to dual fade."""
        old = self.old_rgb.copy()
        TE.apply_transition(old, self.new_rgb, progress=0.5, transition_name="wipe_left_to_right", coords=None)
        expected = ((self.old_rgb * 0.5) + (self.new_rgb * 0.5)).astype(np.int32)
        np.testing.assert_array_almost_equal(old, expected, decimal=0)

    def test_apply_transition_clamped_progress(self):
        """Out-of-bound progress values should clamp gracefully."""
        old = self.old_rgb.copy()
        TE.apply_transition(old, self.new_rgb, progress=-0.5, transition_name="explosion", coords=self.coords)
        np.testing.assert_array_equal(old, self.old_rgb)

        old = self.old_rgb.copy()
        TE.apply_transition(old, self.new_rgb, progress=1.5, transition_name="explosion", coords=self.coords)
        np.testing.assert_array_equal(old, self.new_rgb)


if __name__ == '__main__':
    unittest.main()
