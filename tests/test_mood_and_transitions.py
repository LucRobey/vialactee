"""
tests/test_mood_and_transitions.py - Comprehensive Unit & Governance Tests.

Tests:
1. config/mode_dna.py:
   - DNA metric bounds in [0.0, 1.0] and valid spatial roles.
   - Normalized lookup and fallback to DEFAULT_MODE_DNA.
2. mood/ (sealed sector): see tests/test_mood_sector.py for palettes, crossfade and AXIOM-01/02.
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

import transitions.mode_dna as mode_dna
from mood.api import create_mood_service
from mood.palettes import PALETTES
from transitions.api import MusicSnapshot, SegmentDescriptor
from transitions.director import Transition_Director
from transitions.manager import (
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


class TestLocalTransitionManager(unittest.TestCase):
    def setUp(self):
        self.director = Transition_Director()
        self.music = MusicSnapshot(
            beat_phase=0.50,
            is_beat=False,
            energy=0.60,
            salience=0.70,
            beat_trust=0.80,
        )
        self.ltm = LocalTransitionManager(director=self.director, music=self.music)

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
        self.ltm.set_installation([
            SegmentDescriptor(
                name="Segment v1",
                orientation="vertical",
                available_modes=("Rainbow", "Impact Shockwave"),
                active_mode="Rainbow",
                is_blocked=False,
            )
        ])

        # 1. Queue transition while beat_phase is mid-beat (0.45)
        self.ltm.music = MusicSnapshot(beat_phase=0.45, is_beat=False, beat_trust=0.80)

        self.ltm.schedule_transition(
            allocation={"Segment v1": "Impact Shockwave"},
            quantize_downbeat=True
        )
        self.assertIsNotNone(self.ltm._pending_transition)

        # Update mid-beat: should NOT trigger
        self.ltm.update(0.033)
        self.assertIsNotNone(self.ltm._pending_transition)
        self.assertEqual(self.ltm.pop_orders(), ())

        # 2. Advance to downbeat hit (phase = 0.02)
        self.ltm.update(0.033, MusicSnapshot(beat_phase=0.02, is_beat=False, beat_trust=0.80))

        # Should execute and clear pending
        self.assertIsNone(self.ltm._pending_transition)
        orders = self.ltm.pop_orders()
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0].segment, "Segment v1")
        self.assertEqual(orders[0].target_mode, "Impact Shockwave")

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
        self.assertEqual(tech_chill["type"], "fade_in_out")  # smooth cosine crossfade

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
            if "manager.py" in stat.traceback[0].filename
        ]
        total_bytes = sum(stat.size_diff for stat in ltm_allocations)
        self.assertEqual(
            total_bytes, 0,
            f"AXIOM-02 violation: {total_bytes} bytes allocated in LocalTransitionManager.update(): {ltm_allocations}"
        )


class TestModeDelegationAndHooks(unittest.TestCase):
    def tearDown(self):
        Mode.Mode.reset_mood_colors()

    def test_mode_mood_colors_delegation(self):
        """Every mode must expose mood_colors: static fallback by default, the live mood view once bound."""
        mode_instance = Mode.Mode(
            "TestMode", "Segment v1", None, None, [0, 1, 2], np.zeros((3, 3), dtype=np.int32), {}
        )
        mood = mode_instance.mood_colors
        self.assertEqual(mood.shape, (4, 3))
        self.assertEqual(mood.dtype, np.int32)

        service = create_mood_service(initial_palette="Neon Acid")
        Mode.Mode.bind_mood_colors(service.colors())
        self.assertIs(mode_instance.mood_colors, service.colors())
        np.testing.assert_array_equal(mode_instance.mood_colors, PALETTES["Neon Acid"])

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
        self.director = Transition_Director()
        self.music = MusicSnapshot(
            beat_phase=0.50,
            is_beat=False,
            energy=0.50,
            salience=0.50,
            beat_trust=0.50,
        )
        self.ltm = LocalTransitionManager(director=self.director, music=self.music)

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
        self.assertEqual(tech["type"], "fade_in_out")

    def test_small_profile_verticals_discovered_as_vertical_cohorts(self):
        """Small profile vertical segments (Segment s1/s2/s3) must be vertical cohorts."""
        self.ltm.set_installation([
            SegmentDescriptor(name="Segment s1", orientation="vertical"),
            SegmentDescriptor(name="Segment s2", orientation="vertical"),
            SegmentDescriptor(name="Segment s3", orientation="vertical"),
        ])
        verts, rings = self.ltm._discover_segment_cohorts()

        self.assertEqual(len(verts), 3)
        self.assertIn("Segment s1", verts)
        self.assertIn("Segment s2", verts)
        self.assertIn("Segment s3", verts)
        self.assertEqual(len(rings), 0)

    def test_symmetric_pairs_produces_contrasting_modes(self):
        """SYMMETRIC_PAIRS must choose distinct modes A and B when candidate pool has > 1 mode."""
        pool = ("Rainbow", "Beat Runner")
        self.ltm.set_installation([
            SegmentDescriptor(name="Segment v1", orientation="vertical", available_modes=pool),
            SegmentDescriptor(name="Segment v2", orientation="vertical", available_modes=pool),
        ])

        alloc = self.ltm.allocate_cohort_modes(["Segment v1", "Segment v2"], pattern=CohortPattern.SYMMETRIC_PAIRS)
        self.assertNotEqual(alloc["Segment v1"], alloc["Segment v2"])

    def test_queued_transition_waits_for_active_transition(self):
        """Queued downbeat transition must wait until TD is no longer in transition."""
        self.director.start_transition({"type": "fade_in_out", "duration": 2.0})
        self.assertTrue(self.director.is_in_transition)

        self.ltm.set_installation([
            SegmentDescriptor(name="Segment v1", orientation="vertical", is_blocked=False),
        ])
        self.ltm.music = MusicSnapshot(beat_phase=0.01, is_beat=True, beat_trust=0.80)

        self.ltm.schedule_transition(
            allocation={"Segment v1": "Impact Shockwave"},
            quantize_downbeat=True
        )

        # Update while TD is in transition: must wait
        self.ltm.update(0.033)
        self.assertIsNotNone(self.ltm._pending_transition)
        self.assertEqual(self.ltm.pop_orders(), ())

        # Finish TD transition
        self.director.cancel_transition()
        self.ltm.update(0.033)
        self.assertIsNone(self.ltm._pending_transition)
        orders = self.ltm.pop_orders()
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0].segment, "Segment v1")

    def test_generate_staggered_configs_cohort_complementary(self):
        """Verifies generate_staggered_configs partitions verticals and rings with complementary techniques."""
        self.ltm.set_installation([
            SegmentDescriptor(name="Segment v1", orientation="vertical"),
            SegmentDescriptor(name="Segment h10", orientation="horizontal"),
        ])

        alloc = {"Segment v1": "Impact Shockwave", "Segment h10": "Rainbow"}
        from transitions.stagger import StaggerPattern
        configs = self.ltm.generate_staggered_configs(alloc, pattern=StaggerPattern.COHORT_COMPLEMENTARY)

        self.assertEqual(configs["Segment v1"]["type"], "vertical_wipe")
        self.assertEqual(configs["Segment v1"]["direction"], "DOWN")
        self.assertEqual(configs["Segment v1"]["start_offset"], 0.0)

        self.assertEqual(configs["Segment h10"]["type"], "fade_in_out")
        self.assertGreater(configs["Segment h10"]["start_offset"], 0.0)

    def test_schedule_transition_staggered_execution(self):
        """Verifies schedule_transition with staggered=True emits per-segment orders and sets max duration on TD."""
        self.ltm.set_installation([
            SegmentDescriptor(name="Segment v1", orientation="vertical", is_blocked=False),
            SegmentDescriptor(name="Segment h10", orientation="horizontal", is_blocked=False),
        ])

        self.ltm.schedule_transition(
            allocation={"Segment v1": "Impact Shockwave", "Segment h10": "Rainbow"},
            quantize_downbeat=False,
            staggered=True,
        )

        orders = self.ltm.pop_orders()
        self.assertEqual(len(orders), 2)
        by_seg = {o.segment: o for o in orders}

        # TD must be in TRANSITION_DUAL with transition_duration = max(dur + offset)
        self.assertTrue(self.director.is_in_transition)
        expected_max = max(
            by_seg["Segment v1"].duration + by_seg["Segment v1"].start_offset,
            by_seg["Segment h10"].duration + by_seg["Segment h10"].start_offset,
        )
        self.assertAlmostEqual(self.director.transition_duration, expected_max, places=2)

    def test_all_blocked_segments_do_not_start_director_transition(self):
        """When all targeted segments are blocked, _execute_transition must not start Transition_Director."""
        self.ltm.set_installation([
            SegmentDescriptor(name="Segment v1", orientation="vertical", is_blocked=True),
            SegmentDescriptor(name="Segment v2", orientation="vertical", is_blocked=True),
        ])
        self.director.is_pending = True

        self.ltm.schedule_transition(
            allocation={"Segment v1": "Impact Shockwave", "Segment v2": "Rainbow"},
            quantize_downbeat=False,
        )

        self.assertEqual(self.ltm.pop_orders(), ())
        self.assertFalse(self.director.is_in_transition)
        self.assertEqual(self.director.state, "PASSATION")
        self.assertFalse(self.director.is_pending)

    def test_immediate_schedule_transition_clears_pending_and_replaces_undrained_orders(self):
        """schedule_transition(quantize_downbeat=False) clears _pending_transition and does not duplicate un-popped orders."""
        self.ltm.set_installation([
            SegmentDescriptor(name="Segment v1", orientation="vertical", is_blocked=False),
            SegmentDescriptor(name="Segment v2", orientation="vertical", is_blocked=False),
        ])

        # 1. Queue a beat-quantized transition
        self.ltm.schedule_transition(
            allocation={"Segment v1": "Rainbow", "Segment v2": "Rainbow"},
            quantize_downbeat=True,
        )
        self.assertIsNotNone(self.ltm._pending_transition)

        # 2. Fire two immediate transitions before pop_orders()
        self.ltm.schedule_transition(
            allocation={"Segment v1": "Beat Runner", "Segment v2": "Beat Runner"},
            quantize_downbeat=False,
        )
        self.ltm.schedule_transition(
            allocation={"Segment v1": "Impact Shockwave", "Segment v2": "Impact Shockwave"},
            quantize_downbeat=False,
        )

        self.assertIsNone(self.ltm._pending_transition)
        orders = self.ltm.pop_orders()
        self.assertEqual(len(orders), 2)
        self.assertEqual({o.target_mode for o in orders}, {"Impact Shockwave"})


if __name__ == "__main__":
    unittest.main()

