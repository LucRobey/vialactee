"""
Unit tests for Multi-Family Transition Contracts (transitions/families.py)
and the 3-Layer Mode-Cooperative Handshake (Segment + Mode exit/enter physics).
"""

import unittest
from unittest.mock import MagicMock
import numpy as np

from core.Segment import Segment
from core.TransitionBridge import apply_orders
from modes.Power_bar_mode import Power_bar_mode
from modes.Middle_bar_mode import Middle_bar_mode
from transitions.api import (
    AVAILABLE_TRANSITIONS,
    InstallationSnapshot,
    MusicSnapshot,
    SegmentDescriptor,
    SegmentOrder,
    TransitionOrders,
    create_transition_service,
)
from transitions.effects import set_transition_params
import transitions.engine as TE
from transitions.families import (
    DEFAULT_PARAMS,
    TRANSITION_FAMILIES,
    TransitionFamily,
    get_allowed_stagger_patterns,
    get_families,
    is_mode_cooperative,
    is_staggerable,
    roll_transition_params,
)
from transitions.stagger import StaggerPattern


class _DummyContext:
    def __init__(self, energy: float = 0.85, tension: float = 0.4, v_center: float = 0.6):
        self.energy = energy
        self.tension = tension
        self.vertical_center = v_center
        self.spectral_tilt = 0.0
        self.scene = "GROOVE"
        self.drop_progress = 0.0
        self.is_drop_impact = False
        self.is_drop_imminent = False
        self.is_syncopated = True
        self.is_real_beat = True
        self.is_silent = False


class _DummyListener:
    def __init__(self):
        self.luminosite = 1.0
        self.dt = 1.0 / 60.0
        self.bpm = 128.0
        self.is_beat = True
        self.is_real_beat = True
        self.asserved_total_power = 0.85
        self.band_flux = [10.0] * 8
        self.nb_of_fft_band = 8
        self.context = _DummyContext()


class TestTransitionFamilies(unittest.TestCase):
    def tearDown(self):
        set_transition_params(DEFAULT_PARAMS)

    def test_all_available_transitions_have_family_contracts(self):
        for tech in AVAILABLE_TRANSITIONS:
            if tech == "AUTO":
                continue
            self.assertIn(tech, TRANSITION_FAMILIES, f"{tech} missing from TRANSITION_FAMILIES")
            fams = get_families(tech)
            self.assertGreater(len(fams), 0)

    def test_2d_room_transitions_are_never_staggerable(self):
        room_locked = ("explosion", "spiral", "box_wipe", "weird_glitch", "gravity_drop", "wipe_left_to_right")
        for tech in room_locked:
            self.assertFalse(is_staggerable(tech), f"{tech} should not be staggerable")
            self.assertEqual(get_allowed_stagger_patterns(tech), (StaggerPattern.SIMULTANEOUS,))

        # Verify that requesting staggered=True on a 2D room transition forces start_offset == 0.0
        svc = create_transition_service()
        segs = tuple(
            SegmentDescriptor(name=f"Segment v{i}", orientation="vertical", available_modes=("Rainbow", "Power Bar"))
            for i in range(1, 5)
        )
        svc.set_installation(InstallationSnapshot(segments=segs))
        svc.request_next(technique="explosion", staggered=True)
        orders = svc.update(0.01, MusicSnapshot(beat_phase=0.0, is_beat=True))
        self.assertIsNotNone(orders)
        self.assertTrue(all(o.start_offset == 0.0 for o in orders.orders))

    def test_1d_and_organic_transitions_are_staggerable(self):
        staggerable_techs = ("silk_wipe", "iris_open", "ember_dissolve", "luma_melt", "prism_sweep", "fade_in_out")
        for tech in staggerable_techs:
            self.assertTrue(is_staggerable(tech), f"{tech} should be staggerable")
            self.assertGreater(len(get_allowed_stagger_patterns(tech)), 1)

    def test_roll_transition_params_generates_varied_parameters(self):
        self.assertIn(TransitionFamily.ROOM_EPI_2D, get_families("explosion"))
        self.assertIn(TransitionFamily.RHYTHMIC_CHOP, get_families("explosion"))
        epicenters = set()
        for _ in range(15):
            p = roll_transition_params("explosion")
            self.assertTrue(0.10 <= p["epicenter_x"] <= 0.90)
            self.assertTrue(0.10 <= p["epicenter_y"] <= 0.90)
            self.assertIn(p["chop_count"], (3, 4, 5))
            epicenters.add((p["epicenter_x"], p["epicenter_y"]))
        self.assertGreater(len(epicenters), 1, "Repeated rolls of explosion must vary the 2D epicenter")

    def test_dynamic_epicenter_and_focal_u_affect_shaders(self):
        num_leds = 20
        old_rgb = np.zeros((num_leds, 3), dtype=np.int32)
        new_rgb = np.full((num_leds, 3), 240, dtype=np.int32)
        coords = np.column_stack((np.linspace(0, 430, num_leds), np.linspace(0, 290, num_leds)))

        # Roll 1: Top-Left epicenter vs Roll 2: Bottom-Right epicenter
        set_transition_params({"epicenter_x": 0.15, "epicenter_y": 0.15})
        buf_tl = old_rgb.copy()
        TE.apply_box_wipe(buf_tl, new_rgb, coords, progress=0.45)

        set_transition_params({"epicenter_x": 0.85, "epicenter_y": 0.85})
        buf_br = old_rgb.copy()
        TE.apply_box_wipe(buf_br, new_rgb, coords, progress=0.45)
        self.assertFalse(np.array_equal(buf_tl, buf_br))

        # 1D focal_u shift on iris_open
        set_transition_params({"focal_u": 0.20, "edge_width": 0.12})
        iris_low = old_rgb.copy()
        TE.apply_transition(iris_low, new_rgb, 0.45, "iris_open")

        set_transition_params({"focal_u": 0.80, "edge_width": 0.12})
        iris_high = old_rgb.copy()
        TE.apply_transition(iris_high, new_rgb, 0.45, "iris_open")
        self.assertFalse(np.array_equal(iris_low, iris_high))


class TestModeCooperativeHandshake(unittest.TestCase):
    def setUp(self):
        self.listener = _DummyListener()
        self.leds = np.zeros((40, 3), dtype=np.int32)
        self.indexes = list(range(20))
        self.seg = Segment("Segment v1", self.listener, self.leds, self.indexes, "vertical", {})
        # Replace modes with deterministic test instances of Power_bar_mode and Middle_bar_mode
        self.seg.modes = {
            "Power Bar": Power_bar_mode("Power Bar", "Segment v1", self.listener, self.leds, self.indexes, self.seg.rgb_list, {}),
            "Middle Bar": Middle_bar_mode("Middle Bar", "Segment v1", self.listener, self.leds, self.indexes, self.seg.rgb_list, {}),
        }
        self.seg.activ_mode = "Power Bar"
        self.seg.modes["Power Bar"].start()

    def test_cooperative_mode_wind_down_and_bloom_in(self):
        plasma = self.seg.modes["Power Bar"]
        mid_bar = self.seg.modes["Middle Bar"]

        # Steady state: transition_scale is 1.0
        self.assertAlmostEqual(plasma.transition_scale, 1.0)
        self.assertAlmostEqual(mid_bar.transition_scale, 1.0)

        # Pollute dual_rgb_list to verify change_mode zeroes it out
        self.seg.dual_rgb_list.fill(123)
        self.seg.change_mode("Middle Bar", {"type": "ember_dissolve", "duration": 1.0, "mode_handshake": True})
        self.assertTrue(np.all(self.seg.dual_rgb_list == 0))
        self.assertAlmostEqual(mid_bar._enter_progress, 0.0)
        self.assertLess(mid_bar.transition_scale, 0.25)

        # Advance to 50% transition progress
        status_mid = MagicMock(state="TRANSITION_DUAL", progress=0.5, technique="ember_dissolve")
        self.seg.update(status_mid, TE.apply_transition, dt=0.5)
        self.assertAlmostEqual(plasma._exit_progress, 0.5, places=2)
        self.assertAlmostEqual(mid_bar._enter_progress, 0.5, places=2)
        self.assertLess(plasma.transition_scale, 1.0)
        self.assertGreater(mid_bar.transition_scale, 0.5)

        # Complete transition: hooks reset to steady state (1.0) and dual_rgb_list is handed off
        self.seg.update(status_mid, TE.apply_transition, dt=0.6)
        self.assertFalse(self.seg.is_in_transition)
        self.assertEqual(self.seg.activ_mode, "Middle Bar")
        self.assertAlmostEqual(mid_bar._enter_progress, 1.0)
        self.assertAlmostEqual(mid_bar._exit_progress, 0.0)
        self.assertAlmostEqual(mid_bar.transition_scale, 1.0)
        self.assertAlmostEqual(plasma._exit_progress, 0.0)

    def test_non_cooperative_cut_keeps_full_mode_scale(self):
        self.assertFalse(is_mode_cooperative("flash_cut"))
        self.assertTrue(is_mode_cooperative("ember_dissolve"))

        mm = MagicMock()
        mm._find_segment_by_name.return_value = self.seg
        orders = TransitionOrders(
            orders=(
                SegmentOrder(
                    segment="Segment v1",
                    target_mode="Middle Bar",
                    technique="flash_cut",
                    duration=0.6,
                    mode_handshake=False,
                ),
            ),
            reason="request_next",
        )
        apply_orders(mm, orders)
        self.assertFalse(self.seg.transition_mode_handshake)

        status_mid = MagicMock(state="TRANSITION_DUAL", progress=0.5, technique="flash_cut")
        self.seg.update(status_mid, TE.apply_transition, dt=0.3)
        self.assertAlmostEqual(self.seg.modes["Power Bar"].transition_scale, 1.0)
        self.assertAlmostEqual(self.seg.modes["Middle Bar"].transition_scale, 1.0)


if __name__ == "__main__":
    unittest.main()
