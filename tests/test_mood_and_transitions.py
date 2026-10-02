"""
tests/test_mood_and_transitions.py - Comprehensive Unit & Governance Tests.

Tests:
1. config/mode_dna.py:
   - DNA metric bounds in [0.0, 1.0] and valid spatial roles.
   - Normalized lookup and fallback to DEFAULT_MODE_DNA.
2. core/GlobalMoodManager.py:
   - Curated master palettes and RGB boundaries [0, 255].
   - 2.0s smooth cosine crossfade mathematics.
   - AXIOM-01: Execution time <= 0.01 ms.
   - AXIOM-02: Zero dynamic heap allocations in hot-path update().
   - Facade properties and scene-based palette selection.
3. core/LocalTransitionManager.py:
   - Music Matchmaker: Evaluates live audio context to target DNA.
   - Weighted Lottery: Probabilistic selection according to DNA distance.
   - Flexible Cohort Allocation: DIVERSE, SYMMETRIC_PAIRS (ABAB, ABBA, ABA), and UNISON.
   - Downbeat Quantization: Beat-phase gating (< 0.05) and timeout fallback.
   - Clean Transition Techniques: Cosine crossfade, directional wipe, and transient blip.
   - Zero heap allocations in steady-state update().
4. modes/Mode.py:
   - mood_colors property delegation.
   - on_transition_exit and on_transition_enter lifecycle hooks.
"""

import math
import time
import tracemalloc
import unittest
from unittest.mock import MagicMock
import numpy as np

import config.mode_dna as mode_dna
from core.GlobalMoodManager import GlobalMoodManager, PALETTES
from core.LocalTransitionManager import (
    LocalTransitionManager,
    CohortPattern,
    TRANSITION_TECHNIQUES,
)
import modes.Mode as Mode


class TestModeDNA(unittest.TestCase):
    def test_all_mode_dna_bounds_and_roles(self):
        """All configured modes must define 4 metrics in [0.0, 1.0] and valid spatial_role."""
        valid_roles = {"vertical", "horizontal", "both"}
        self.assertGreater(len(mode_dna.MODE_DNA), 15)

        for name, dna in mode_dna.MODE_DNA.items():
            with self.subTest(mode=name):
                for metric in ("energy", "punch", "rhythm", "complexity"):
                    self.assertIn(metric, dna, f"Missing {metric} in DNA of {name}")
                    val = dna[metric]
                    self.assertIsInstance(val, (int, float))
                    self.assertTrue(0.0 <= val <= 1.0, f"{name}.{metric} out of bounds: {val}")

                self.assertIn("spatial_role", dna, f"Missing spatial_role in {name}")
                self.assertIn(dna["spatial_role"], valid_roles, f"Invalid role in {name}")

    def test_get_mode_dna_normalization(self):
        """get_mode_dna must handle exact, lower, underscore, and suffix variants."""
        # Exact
        dna_exact = mode_dna.get_mode_dna("Rainbow")
        self.assertEqual(dna_exact["energy"], mode_dna.MODE_DNA["Rainbow"]["energy"])

        # Lowercase and underscored
        dna_lower = mode_dna.get_mode_dna("rainbow")
        self.assertEqual(dna_lower, dna_exact)

        dna_under = mode_dna.get_mode_dna("beat_runner_mode")
        self.assertEqual(dna_under["punch"], mode_dna.MODE_DNA["Beat Runner"]["punch"])

        # Fallback for unknown mode
        fallback = mode_dna.get_mode_dna("NonExistentSuperMode")
        self.assertEqual(fallback, mode_dna.DEFAULT_MODE_DNA)


class TestGlobalMoodManager(unittest.TestCase):
    def setUp(self):
        GlobalMoodManager.reset_instance()
        self.manager = GlobalMoodManager.get_instance(initial_palette="Cyberpunk")

    def test_curated_palettes_validity(self):
        """Curated palettes must exist and have 4 valid RGB triplets [0, 255]."""
        required = ["Cyberpunk", "Solar Ember", "Deep Ocean", "Ethereal", "Neon Acid", "Monochrome Chrome"]
        for pal in required:
            self.assertIn(pal, PALETTES)
            colors = PALETTES[pal]
            self.assertEqual(len(colors), 4)
            for rgb in colors:
                self.assertEqual(len(rgb), 3)
                for c in rgb:
                    self.assertTrue(0 <= c <= 255)

    def test_smooth_cosine_crossfade_progression(self):
        """Palette crossfade must strictly follow cosine curve and complete in 2.0s."""
        self.assertEqual(self.manager.current_palette, "Cyberpunk")
        self.assertFalse(self.manager.is_transitioning)

        # Trigger transition to Solar Ember (duration = 2.0s)
        self.assertTrue(self.manager.set_palette("Solar Ember", duration=2.0))
        self.assertTrue(self.manager.is_transitioning)
        self.assertEqual(self.manager.target_palette, "Solar Ember")

        cyber_colors = np.array(PALETTES["Cyberpunk"], dtype=np.float32)
        solar_colors = np.array(PALETTES["Solar Ember"], dtype=np.float32)

        # Halfway at 1.0s (progress = 0.5):
        # w = 0.5 * (1 - cos(pi * 0.5)) = 0.5 * (1 - 0) = 0.5
        self.manager.update(1.0)
        self.assertTrue(self.manager.is_transitioning)
        self.assertAlmostEqual(self.manager.blend_progress, 0.5, places=2)

        expected_mid = 0.5 * cyber_colors + 0.5 * solar_colors
        np.testing.assert_allclose(self.manager.mood_colors, expected_mid, atol=2.0)

        # Finish transition at 2.0s total
        self.manager.update(1.0)
        self.assertFalse(self.manager.is_transitioning)
        self.assertEqual(self.manager.current_palette, "Solar Ember")
        self.assertEqual(self.manager.blend_progress, 1.0)
        np.testing.assert_array_equal(self.manager.mood_colors, PALETTES["Solar Ember"])

    def test_axiom_01_frame_budget(self):
        """GlobalMoodManager.update() must execute in <= 0.01 ms per frame."""
        self.manager.set_palette("Neon Acid", duration=2.0)
        iterations = 500
        t0 = time.perf_counter()
        for _ in range(iterations):
            self.manager.update(0.001)
        elapsed_per_frame_ms = ((time.perf_counter() - t0) / iterations) * 1000.0

        self.assertLess(
            elapsed_per_frame_ms, 0.01,
            f"AXIOM-01 violation: GlobalMoodManager update took {elapsed_per_frame_ms:.4f} ms > 0.01 ms"
        )

    def test_axiom_02_zero_allocation_in_update(self):
        """GlobalMoodManager.update() must allocate ZERO dynamic heap memory during crossfade."""
        self.manager.set_palette("Deep Ocean", duration=2.0)

        # Warm up
        self.manager.update(0.01)

        tracemalloc.start()
        snapshot_start = tracemalloc.take_snapshot()

        for _ in range(50):
            self.manager.update(0.033)

        snapshot_end = tracemalloc.take_snapshot()
        tracemalloc.stop()

        stats = snapshot_end.compare_to(snapshot_start, "lineno")
        # Filter for allocations inside GlobalMoodManager.py
        gmm_allocations = [
            stat for stat in stats
            if "GlobalMoodManager.py" in stat.traceback[0].filename
        ]
        total_gmm_bytes = sum(stat.size_diff for stat in gmm_allocations)
        self.assertEqual(
            total_gmm_bytes, 0,
            f"AXIOM-02 violation: {total_gmm_bytes} bytes allocated in GlobalMoodManager.update(): {gmm_allocations}"
        )

    def test_facade_properties_and_scene_switch(self):
        """Test primary, secondary, accent, background properties and scene mapping."""
        self.manager.set_palette("Cyberpunk", duration=0.01)
        self.manager.update(0.02)

        self.assertEqual(self.manager.mood_colors.shape, (4, 3))
        np.testing.assert_array_equal(self.manager.primary_color, PALETTES["Cyberpunk"][0])
        np.testing.assert_array_equal(self.manager.secondary_color, PALETTES["Cyberpunk"][1])
        np.testing.assert_array_equal(self.manager.accent_color, PALETTES["Cyberpunk"][2])
        np.testing.assert_array_equal(self.manager.background_color, PALETTES["Cyberpunk"][3])

        # Test scene mapping
        self.assertTrue(self.manager.set_palette_for_scene("CHILL"))
        self.assertEqual(self.manager.target_palette, "Deep Ocean")

        self.assertTrue(self.manager.set_palette_for_scene("DROP_IMPACT"))
        self.assertEqual(self.manager.target_palette, "Neon Acid")


class TestLocalTransitionManager(unittest.TestCase):
    def setUp(self):
        GlobalMoodManager.reset_instance()
        self.mock_listener = MagicMock()
        self.mock_listener.beat_phase = 0.50
        self.mock_listener.is_beat = False
        self.mock_listener.asserved_total_power = 0.60
        self.mock_listener.rhythm_salience = 0.70
        self.mock_listener.beat_trust = 0.80

        self.mock_mm = MagicMock()
        self.mock_mm.segments_list = []
        self.mock_mm.activ_configuration = {"modes": {}}

        self.ltm = LocalTransitionManager(self.mock_mm, self.mock_listener)

    def test_music_matchmaker_dna_evaluation(self):
        """Translates live audio context into normalized target DNA."""
        # Ambient mock
        mock_ctx = MagicMock()
        mock_ctx.energy = 0.25
        mock_ctx.salience = 0.15
        mock_ctx.beat_trust = 0.30
        mock_ctx.novelty = 0.10
        mock_ctx.tension = 0.10
        mock_ctx.is_drop_impact = False
        mock_ctx.is_syncopated = False

        dna_chill = self.ltm.evaluate_target_dna(mock_ctx)
        self.assertAlmostEqual(dna_chill["energy"], 0.25, places=2)
        self.assertLess(dna_chill["punch"], 0.30)
        self.assertLess(dna_chill["rhythm"], 0.40)

        # Drop impact mock
        mock_ctx.energy = 0.95
        mock_ctx.salience = 0.90
        mock_ctx.beat_trust = 0.85
        mock_ctx.is_drop_impact = True

        dna_drop = self.ltm.evaluate_target_dna(mock_ctx)
        self.assertAlmostEqual(dna_drop["energy"], 0.95, places=2)
        self.assertEqual(dna_drop["punch"], 1.0)
        self.assertGreater(dna_drop["rhythm"], 0.80)

    def test_weighted_lottery_probabilistic_selection(self):
        """Weighted lottery selects candidates probabilistically with non-zero chance for all."""
        pool = ["Rainbow", "Beat Runner", "Impact Shockwave", "Shining Stars"]
        target_high_energy = {"energy": 0.95, "punch": 0.95, "rhythm": 0.90, "complexity": 0.50}

        counts = {m: 0 for m in pool}
        draws = 1000
        for _ in range(draws):
            picked = self.ltm.select_mode_lottery(pool, target_high_energy)
            counts[picked] += 1

        # High energy modes (Beat Runner or Impact Shockwave) must dominate
        self.assertGreater(counts["Beat Runner"] + counts["Impact Shockwave"], counts["Rainbow"] + counts["Shining Stars"])
        # Non-rigid: Even ambient modes have a non-zero probability (preserving freshness and surprise)
        self.assertGreater(counts["Rainbow"], 0)
        self.assertGreater(counts["Shining Stars"], 0)

    def test_flexible_cohort_allocation_symmetries_and_unison(self):
        """Cohort allocation supports DIVERSE, SYMMETRIC_PAIRS (ABAB, ABBA, ABA), and UNISON."""
        pillars = ["Segment v1", "Segment v2", "Segment v3", "Segment v4"]

        # 1. Test UNISON
        alloc_unison = self.ltm.allocate_cohort_modes(pillars, pattern=CohortPattern.UNISON)
        self.assertEqual(len(alloc_unison), 4)
        # All 4 pillars have the exact same mode
        unique_modes = set(alloc_unison.values())
        self.assertEqual(len(unique_modes), 1)

        # 2. Test SYMMETRIC_PAIRS for 4 pillars (ABAB or ABBA)
        alloc_sym = self.ltm.allocate_cohort_modes(pillars, pattern=CohortPattern.SYMMETRIC_PAIRS)
        self.assertEqual(len(alloc_sym), 4)
        m1, m2, m3, m4 = alloc_sym["Segment v1"], alloc_sym["Segment v2"], alloc_sym["Segment v3"], alloc_sym["Segment v4"]
        is_abab = (m1 == m3 and m2 == m4)
        is_abba = (m1 == m4 and m2 == m3)
        self.assertTrue(is_abab or is_abba, f"Expected ABAB or ABBA symmetry, got: {alloc_sym}")

        # 3. Test SYMMETRIC_PAIRS for 3 segments (ABA sandwich)
        triad = ["Segment s1", "Segment s2", "Segment s3"]
        alloc_triad = self.ltm.allocate_cohort_modes(triad, pattern=CohortPattern.SYMMETRIC_PAIRS)
        self.assertEqual(alloc_triad["Segment s1"], alloc_triad["Segment s3"])

    def test_downbeat_quantization_lifecycle(self):
        """Transitions do not fire mid-beat; they wait for beat_phase < 0.05 or beat hit."""
        mock_seg = MagicMock()
        mock_seg.name = "Segment v1"
        mock_seg.isBlocked = False
        self.mock_mm._find_segment_by_name = MagicMock(return_value=mock_seg)

        # 1. Queue transition while beat_phase is mid-beat (0.45)
        self.mock_listener.beat_phase = 0.45
        self.mock_listener.is_beat = False

        self.ltm.schedule_transition(
            allocation={"Segment v1": "Impact Shockwave"},
            quantize_downbeat=True
        )
        self.assertIsNotNone(self.ltm._pending_transition)

        # Update mid-beat: should NOT trigger
        self.ltm.update(0.033)
        self.assertIsNotNone(self.ltm._pending_transition)
        mock_seg.change_mode.assert_not_called()

        # 2. Advance to downbeat hit (phase = 0.02)
        self.mock_listener.beat_phase = 0.02
        self.ltm.update(0.033)

        # Should execute and clear pending
        self.assertIsNone(self.ltm._pending_transition)
        mock_seg.change_mode.assert_called_once()
        self.assertEqual(mock_seg.change_mode.call_args[0][0], "Impact Shockwave")

    def test_clean_transition_techniques(self):
        """Technique selector routes based on audio kinetics."""
        ctx_drop = MagicMock(is_drop_impact=True, energy=0.9, salience=0.8, is_rhythmic=True)
        tech_drop = self.ltm.select_transition_technique(ctx_drop)
        self.assertEqual(tech_drop["type"], "explosion")  # transient blip

        ctx_groove = MagicMock(is_drop_impact=False, energy=0.6, salience=0.7, is_rhythmic=True)
        tech_groove = self.ltm.select_transition_technique(ctx_groove)
        self.assertEqual(tech_groove["type"], "vertical_wipe")  # directional wipe

        ctx_chill = MagicMock(is_drop_impact=False, energy=0.3, salience=0.2, is_rhythmic=False)
        tech_chill = self.ltm.select_transition_technique(ctx_chill)
        self.assertEqual(tech_chill["type"], "global_change")  # smooth cosine crossfade

    def test_axiom_02_zero_allocation_in_steady_state(self):
        """LocalTransitionManager.update() must allocate ZERO heap bytes in steady state."""
        # Warm up to populate free lists
        for _ in range(20):
            self.ltm.update(0.033)

        tracemalloc.start()
        snapshot_start = tracemalloc.take_snapshot()

        for _ in range(50):
            self.ltm.update(0.033)

        snapshot_end = tracemalloc.take_snapshot()
        tracemalloc.stop()

        stats = snapshot_end.compare_to(snapshot_start, "lineno")
        ltm_allocations = [
            stat for stat in stats
            if "LocalTransitionManager.py" in stat.traceback[0].filename
        ]
        total_bytes = sum(stat.size_diff for stat in ltm_allocations)
        self.assertEqual(
            total_bytes, 0,
            f"AXIOM-02 violation: {total_bytes} bytes allocated in LocalTransitionManager.update(): {ltm_allocations}"
        )


class TestModeDelegationAndHooks(unittest.TestCase):
    def test_mode_mood_colors_delegation(self):
        """Every mode must expose mood_colors property returning GlobalMoodManager palette."""
        mode_instance = Mode.Mode(
            "TestMode", "Segment v1", None, None, [0, 1, 2], np.zeros((3, 3), dtype=np.int32), {}
        )
        mood = mode_instance.mood_colors
        self.assertEqual(mood.shape, (4, 3))
        self.assertEqual(mood.dtype, np.int32)

    def test_mode_transition_hooks_exist_and_callable(self):
        """Default on_transition_exit and on_transition_enter hooks exist on Mode."""
        mode_instance = Mode.Mode(
            "TestMode", "Segment v1", None, None, [0, 1, 2], np.zeros((3, 3), dtype=np.int32), {}
        )
        # Should execute cleanly without error
        mode_instance.on_transition_exit(0.5)
        mode_instance.on_transition_enter(0.5)


class TestRobustnessAndEdgeCases(unittest.TestCase):
    def setUp(self):
        GlobalMoodManager.reset_instance()
        self.gmm = GlobalMoodManager.get_instance(initial_palette="Cyberpunk")

        self.mock_listener = MagicMock()
        self.mock_listener.beat_phase = 0.50
        self.mock_listener.is_beat = False
        self.mock_listener.asserved_total_power = 0.50
        self.mock_listener.rhythm_salience = 0.50
        self.mock_listener.beat_trust = 0.50

        self.mock_mm = MagicMock()
        self.mock_mm.segments_list = []
        self.mock_mm.activ_configuration = {"modes": {}}

        self.ltm = LocalTransitionManager(self.mock_mm, self.mock_listener)

    def test_palette_no_stall_on_repeated_requests(self):
        """Repeated set_palette calls for active target must not reset crossfade timer."""
        self.gmm.set_palette("Solar Ember", duration=2.0)
        self.gmm.update(0.5)  # 25% progress
        self.assertAlmostEqual(self.gmm.blend_progress, 0.25, places=2)

        # Repeated request while already transitioning to Solar Ember
        self.assertTrue(self.gmm.set_palette("Solar Ember", duration=2.0))
        # Timer should NOT be wiped back to 0
        self.assertAlmostEqual(self.gmm.blend_progress, 0.25, places=2)

        # Advance further
        self.gmm.update(0.5)  # 50% progress
        self.assertAlmostEqual(self.gmm.blend_progress, 0.50, places=2)

    def test_evaluate_target_dna_robust_to_none_attributes(self):
        """evaluate_target_dna must not raise TypeError when context metrics are None."""
        mock_ctx = MagicMock()
        mock_ctx.energy = None
        mock_ctx.salience = None
        mock_ctx.beat_trust = None
        mock_ctx.novelty = None
        mock_ctx.tension = None
        mock_ctx.is_drop_impact = False
        mock_ctx.is_syncopated = False

        dna = self.ltm.evaluate_target_dna(mock_ctx)
        for key in ("energy", "punch", "rhythm", "complexity"):
            self.assertIn(key, dna)
            self.assertIsInstance(dna[key], float)
            self.assertTrue(0.0 <= dna[key] <= 1.0)

    def test_select_transition_technique_robust_to_none(self):
        """select_transition_technique must not crash on None energy/salience."""
        mock_ctx = MagicMock()
        mock_ctx.energy = None
        mock_ctx.salience = None
        mock_ctx.is_drop_impact = False
        mock_ctx.is_rhythmic = False

        tech = self.ltm.select_transition_technique(mock_ctx)
        self.assertIn("type", tech)
        self.assertEqual(tech["type"], "global_change")

    def test_small_profile_verticals_discovered_as_vertical_cohorts(self):
        """Small profile vertical segments (Segment s1/s2/s3) must be vertical cohorts."""
        seg1 = MagicMock(name="Segment s1", orientation="vertical")
        seg1.name = "Segment s1"
        seg2 = MagicMock(name="Segment s2", orientation="vertical")
        seg2.name = "Segment s2"
        seg3 = MagicMock(name="Segment s3", orientation="vertical")
        seg3.name = "Segment s3"

        self.mock_mm.segments_list = [seg1, seg2, seg3]
        verts, rings = self.ltm._discover_segment_cohorts()

        self.assertEqual(len(verts), 3)
        self.assertIn("Segment s1", verts)
        self.assertIn("Segment s2", verts)
        self.assertIn("Segment s3", verts)
        self.assertEqual(len(rings), 0)

    def test_symmetric_pairs_produces_contrasting_modes(self):
        """SYMMETRIC_PAIRS must choose distinct modes A and B when candidate pool has > 1 mode."""
        pool = ["Rainbow", "Beat Runner"]
        self.mock_mm._find_segment_by_name = MagicMock(return_value=MagicMock(modes={m: MagicMock() for m in pool}))

        alloc = self.ltm.allocate_cohort_modes(["Segment v1", "Segment v2"], pattern=CohortPattern.SYMMETRIC_PAIRS)
        self.assertNotEqual(alloc["Segment v1"], alloc["Segment v2"])

    def test_queued_transition_waits_for_active_transition(self):
        """Queued downbeat transition must wait until TD is no longer in transition."""
        mock_td = MagicMock()
        mock_td.is_in_transition = True
        self.mock_mm.transition_director = mock_td

        mock_seg = MagicMock()
        mock_seg.isBlocked = False
        self.mock_mm._find_segment_by_name = MagicMock(return_value=mock_seg)

        self.mock_listener.beat_phase = 0.01  # downbeat ready
        self.ltm.schedule_transition(
            allocation={"Segment v1": "Impact Shockwave"},
            quantize_downbeat=True
        )

        # Update while TD is in transition: must wait
        self.ltm.update(0.033)
        self.assertIsNotNone(self.ltm._pending_transition)
        mock_seg.change_mode.assert_not_called()

        # Finish TD transition
        mock_td.is_in_transition = False
        self.ltm.update(0.033)
        self.assertIsNone(self.ltm._pending_transition)
        mock_seg.change_mode.assert_called_once()


if __name__ == "__main__":
    unittest.main()
