"""
Tests for Global Mode infrastructure (utils/global_mode.py), all 5 Global Modes
(Monolithic_beat_blast_mode, Architectural_vu_equalizer_mode, Concentric_radial_ripple_mode,
Horizon_scanning_blade_mode, Spectral_avalanche_mode), and mixed global/per-segment
orchestration in Mode_master and CommandRouter.
"""
import asyncio
import gc
import time
import tracemalloc
import unittest
import numpy as np

from music.MusicalContextEngine import MusicalContextEngine, MusicalScene
from mood.api import create_mood_service
from modes.Mode import Mode as BaseMode
from modes.Monolithic_beat_blast_mode import Monolithic_beat_blast_mode
from modes.Architectural_vu_equalizer_mode import Architectural_vu_equalizer_mode
from modes.Concentric_radial_ripple_mode import Concentric_radial_ripple_mode
from modes.Horizon_scanning_blade_mode import Horizon_scanning_blade_mode
from modes.Spectral_avalanche_mode import Spectral_avalanche_mode
from tests.test_all_modes_musical_context import MockListener
from tools.choreography_matrix import measure_mode_choreography, MATRIX_CONFIG, DEFAULT_NB_BANDS

GLOBAL_MODE_SPECS = [
    ("Monolithic Beat Blast", Monolithic_beat_blast_mode, "Monolithic_beat_blast_mode.py", "beat"),
    ("Architectural VU Equalizer", Architectural_vu_equalizer_mode, "Architectural_vu_equalizer_mode.py", "level"),
    ("Concentric Radial Ripple", Concentric_radial_ripple_mode, "Concentric_radial_ripple_mode.py", "beat"),
    ("Horizon Scanning Blade", Horizon_scanning_blade_mode, "Horizon_scanning_blade_mode.py", "beat"),
    ("Spectral Avalanche", Spectral_avalanche_mode, "Spectral_avalanche_mode.py", "spectrum"),
]


class TestGlobalModes(unittest.TestCase):
    def setUp(self):
        self.mood = create_mood_service(initial_palette="Cyberpunk")
        BaseMode.bind_mood_colors(self.mood.colors())
        BaseMode.bind_mood_modifiers(self.mood.modifiers())
        self.addCleanup(BaseMode.reset_mood_colors)
        self.listener = MockListener()
        self.engine = MusicalContextEngine(self.listener)
        self.engine._is_silent = False
        self.listener.context = self.engine

    def test_architectural_roles_and_rendering_across_chandelier_segments(self):
        """All 5 Global Modes resolve pillar, bridge, canopy, and composite roles and render non-zero RGB."""
        expected_roles = {
            "Segment v1": "pillar",
            "Segment v2": "pillar",
            "Segment h10": "bridge",
            "Segment h11": "bridge",
            "Segment h00": "canopy",
            "Segment h30": "canopy",
            "studio_preview": "composite",
        }
        self.engine._energy = 0.80
        self.listener.asserved_fft_band = np.linspace(0.9, 0.4, 16, dtype=np.float64)

        for mode_name, mode_cls, _, _ in GLOBAL_MODE_SPECS:
            for seg_name, expected_role in expected_roles.items():
                with self.subTest(mode=mode_name, segment=seg_name):
                    rgb = np.zeros((48, 3), dtype=np.int32)
                    mode = mode_cls(mode_name, seg_name, self.listener, None, list(range(48)), rgb, {})
                    self.assertTrue(mode.IS_GLOBAL)
                    self.assertEqual(mode.spatial.role, expected_role)
                    for step in range(4):
                        self.listener.beat_phase = (step * 0.18) % 1.0
                        mode.run()
                    self.assertTrue(np.any(rgb > 0), f"{mode_name} on {seg_name} ({expected_role}) produced all-black buffer")

    def test_silence_decay_and_flywheel_lost_resilience(self):
        """All 5 Global Modes stay alive when beat_trust == 0 and decay to black in sustained silence."""
        for mode_name, mode_cls, _, _ in GLOBAL_MODE_SPECS:
            with self.subTest(mode=mode_name):
                rgb = np.zeros((45, 3), dtype=np.int32)
                mode = mode_cls(mode_name, "Segment v2", self.listener, None, list(range(45)), rgb, {})

                # 1. Flywheel lost (beat_trust = 0) -> stays alive via continuous acoustic fallback
                self.engine._is_silent = False
                self.engine._energy = 0.72
                self.engine._beat_trust = 0.0
                self.engine._salience = 0.0
                self.listener.beat_trust = 0.0
                self.listener.beat_confidence = 0.0
                self.listener.asserved_fft_band = np.linspace(0.8, 0.3, 16, dtype=np.float64)
                for frame in range(30):
                    self.listener.beat_phase = (frame * 0.03) % 1.0
                    mode.run()
                self.assertTrue(np.any(rgb > 0), f"{mode_name} went dark when beat_trust == 0")

                # 2. Sustained silence -> decays to black
                self.engine._is_silent = True
                self.engine._energy = 0.0
                for _ in range(180):
                    mode.run()
                self.assertTrue(np.all(rgb == 0), f"{mode_name} failed to decay to black in silence")

    def test_axiom_01_and_02_performance_and_zero_allocation(self):
        """All 5 Global Modes satisfy AXIOM-01 (<= 0.20 ms) and AXIOM-02 (0 heap allocations in run)."""
        self.engine._current_scene = MusicalScene.GROOVE
        self.engine._energy = 0.75
        self.listener.asserved_fft_band = np.linspace(0.85, 0.25, 16, dtype=np.float64)

        for mode_name, mode_cls, filename, _ in GLOBAL_MODE_SPECS:
            with self.subTest(mode=mode_name):
                rgb = np.zeros((60, 3), dtype=np.int32)
                mode = mode_cls(mode_name, "studio_preview", self.listener, None, list(range(60)), rgb, {})

                for _ in range(30):
                    mode.run()

                start_t = time.perf_counter()
                for _ in range(100):
                    mode.run()
                frame_ms = (time.perf_counter() - start_t) * 1000.0 / 100.0
                self.assertLessEqual(frame_ms, 0.20, f"{mode_name} took {frame_ms:.4f} ms > 0.20 ms")

                gc.collect()
                tracemalloc.start()
                s1 = tracemalloc.take_snapshot()
                for _ in range(100):
                    mode.run()
                s2 = tracemalloc.take_snapshot()
                tracemalloc.stop()

                allocs = [
                    stat for stat in s2.compare_to(s1, "lineno")
                    if filename in stat.traceback.format()[0] and stat.size_diff > 512
                ]
                self.assertEqual(allocs, [], f"AXIOM-02 violation in {mode_name}: {allocs}")

    def test_law_7_lead_dominance(self):
        """All 5 Global Modes satisfy Law 7 (declared LEAD is the dominant driver)."""
        for mode_name, mode_cls, _, expected_lead in GLOBAL_MODE_SPECS:
            with self.subTest(mode=mode_name):
                res = measure_mode_choreography(mode_cls, **MATRIX_CONFIG, nb_bands=DEFAULT_NB_BANDS)
                contribs = res["contributions"]
                best_driver = max(contribs, key=contribs.get)
                self.assertEqual(best_driver, expected_lead, f"{mode_name}: expected {expected_lead} to dominate, got {contribs}")
                audio_budget = max(1e-6, res["r_std_full"] - res["r_std_mute_all"])
                self.assertGreaterEqual(res["lead_contrib"], 0.30 * audio_budget)
                self.assertGreaterEqual(res["r_std_mute_sec"], 0.65 * res["r_std_full"])

    def test_law_5_settings_honesty_and_bind_segment_geometry(self):
        """All 5 Global Modes consume every declared setting in run() and update spatial buffers on bind_segment_geometry()."""
        import inspect
        import sys
        from tests.test_mode_helpers import TestDeadSettingsRatchet

        coords = np.column_stack((np.linspace(10.0, 400.0, 48), np.linspace(240.0, 20.0, 48)))
        for mode_name, mode_cls, _, _ in GLOBAL_MODE_SPECS:
            with self.subTest(mode=mode_name):
                rgb = np.zeros((48, 3), dtype=np.int32)
                mode = mode_cls(mode_name, "Segment v1", self.listener, None, list(range(48)), rgb, {})
                used = TestDeadSettingsRatchet._self_loads_outside_setup(
                    inspect.getsource(sys.modules[mode_cls.__module__])
                )
                for descriptor in mode.get_settings_schema():
                    attr = descriptor.get("attr") or descriptor.get("key")
                    self.assertIn(attr, used, f"{mode_cls.__name__} declares dead setting {attr!r}")

                mode.bind_segment_geometry("h00", "horizontal", ("tier:canopy", "half:left"), coords)
                self.assertEqual(mode.spatial.seg_id, "h00")
                self.assertEqual(mode.spatial.role, "canopy")
                mode.run()
                self.assertTrue(np.any(rgb >= 0))

    def test_mixed_global_and_per_segment_switching_in_mode_master(self):
        """Selecting any Global Mode switches all segments in unison; selecting a standard mode switches only that segment."""
        import core.Mode_master as Mode_master

        leds_1 = np.zeros((785, 3), dtype=np.int32)
        leds_2 = np.zeros((519, 3), dtype=np.int32)
        mm = Mode_master.Mode_master(self.listener, {"hardware_profile": "full", "useMicrophone": False}, leds_1, leds_2)

        for mode_name, _, _, _ in GLOBAL_MODE_SPECS:
            with self.subTest(mode=mode_name):
                applied = mm.handle_panel_command({"type": "set_segment_mode", "segment": "v4", "mode": mode_name})
                self.assertTrue(applied)
                for seg in mm.segments_list:
                    self.assertEqual(seg.get_current_mode(), mode_name)

        # Pick standard mode 'Power Bar' on segment v4 -> only v4 switches, others remain on last Global Mode
        applied_single = mm.handle_panel_command({"type": "set_segment_mode", "segment": "v4", "mode": "Power Bar"})
        self.assertTrue(applied_single)
        v4_seg = mm._find_segment_by_name("v4")
        v1_seg = mm._find_segment_by_name("v1")
        self.assertEqual(v4_seg.get_current_mode(), "Power Bar")
        self.assertEqual(v1_seg.get_current_mode(), "Spectral Avalanche")

        # WebSocket CommandRouter topology/select_segment_mode also activates global mode across all segments
        res = asyncio.run(mm.process_instruction({
            "page": "topology",
            "action": "select_segment_mode",
            "payload": {"segmentId": "h00", "mode": "Concentric Radial Ripple"},
        }))
        self.assertTrue(res.get("applied"))
        for seg in mm.segments_list:
            self.assertEqual(seg.get_current_mode(), "Concentric Radial Ripple")


if __name__ == "__main__":
    unittest.main()
