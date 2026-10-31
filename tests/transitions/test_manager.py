"""
tests/transitions/test_manager.py - Unit & Governance Tests for LocalTransitionManager and Mode Delegation.

Tests:
1. transitions/manager.py:
   - Music Matchmaker: Evaluates live audio context to target DNA.
   - Coherence Allocation: allocate_all_segments and allocate_initial via cast_transition.
   - Memory Recording Lifecycle: History recorded ONLY when _execute_transition emits orders
     (not when a queued transition is overwritten before firing).
   - Downbeat Quantization: Beat-phase gating (< 0.05) and timeout fallback.
   - Clean Transition Techniques: Cosine crossfade, directional wipe, and transient blip.
   - Zero heap allocations in steady-state update() (AXIOM-02).
2. modes/Mode.py:
   - mood_colors property delegation.
"""

import tracemalloc
import unittest
from unittest.mock import MagicMock
import numpy as np

from mood.api import create_mood_service
from mood.palettes import PALETTES
from transitions.api import MusicSnapshot, SegmentDescriptor
from transitions.director import Transition_Director
from transitions.fakes import FAKE_MODE_PROFILES, make_fake_installation
from transitions.manager import LocalTransitionManager
import modes.Mode as Mode


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

        mock_ctx.energy = 0.95
        mock_ctx.salience = 0.90
        mock_ctx.beat_trust = 0.85
        mock_ctx.is_drop_impact = True

        dna_drop = self.ltm.evaluate_target_dna(mock_ctx)
        self.assertAlmostEqual(dna_drop["energy"], 0.95, places=2)
        self.assertEqual(dna_drop["punch"], 1.0)
        self.assertGreater(dna_drop["rhythm"], 0.80)

    def test_allocate_all_segments_respects_policy_budget_and_forbids(self):
        """allocate_all_segments delegates to cast_transition and enforces policy constraints."""
        from transitions.policy import DEFAULT_POLICY

        inst = make_fake_installation()
        raw = dict(DEFAULT_POLICY)
        raw["rules"] = [
            {"id": "forbid-vertical-axis-on-horizontals", "when": [{"at": "orientation:horizontal", "tag": "axis:vertical"}], "effect": "forbid"},
            {"id": "no-horizontal-axis-on-verticals", "when": [{"at": "orientation:vertical", "tag": "axis:horizontal"}], "weight": 0.15},
        ]
        self.ltm.set_installation(inst.segments, inst.modes)
        self.ltm.configure(raw)
        target_dna = self.ltm.evaluate_target_dna(self.music)
        alloc = self.ltm.allocate_all_segments(target_dna)
        self.assertEqual(len(alloc), 11)
        self.assertLessEqual(len(set(alloc.values())), 3)
        for seg in inst.segments:
            if seg.orientation == "horizontal":
                self.assertNotEqual(alloc[seg.name], "Power Bar")

    def test_allocate_initial_records_first_history_entry(self):
        """allocate_initial returns a coherent allocation keyed by segment name and records history."""
        inst = make_fake_installation()
        self.ltm.set_installation(inst.segments, inst.modes)
        self.assertEqual(len(self.ltm.memory), 0)
        alloc = self.ltm.allocate_initial(self.music)
        self.assertEqual(len(alloc), 11)
        self.assertEqual(set(alloc.keys()), {s.name for s in inst.segments})
        self.assertEqual(len(self.ltm.memory), 1)

    def test_memory_recorded_only_when_transition_actually_fires(self):
        """Queued transitions that are overwritten before firing must NOT pollute TransitionMemory."""
        inst = make_fake_installation()
        self.ltm.set_installation(inst.segments, inst.modes)
        self.assertEqual(len(self.ltm.memory), 0)

        # Schedule a quantized transition while mid-beat (does not fire yet)
        self.ltm.music = MusicSnapshot(beat_phase=0.45, is_beat=False, beat_trust=0.80)
        self.ltm.schedule_transition(quantize_downbeat=True)
        self.assertIsNotNone(self.ltm._pending_transition)
        self.assertEqual(len(self.ltm.memory), 0)

        # Overwrite with an immediate transition before the queued one fires
        self.ltm.schedule_transition(quantize_downbeat=False)
        self.assertIsNone(self.ltm._pending_transition)
        self.assertEqual(len(self.ltm.memory), 1)

    def test_downbeat_quantization_lifecycle(self):
        """Transitions do not fire mid-beat; they wait for beat_phase < 0.05 or beat hit."""
        self.ltm.set_installation([
            SegmentDescriptor(
                name="Segment v1",
                id="v1",
                orientation="vertical",
                available_modes=("Rainbow", "Impact Shockwave"),
                active_mode="Rainbow",
                is_blocked=False,
            )
        ], FAKE_MODE_PROFILES)

        self.ltm.music = MusicSnapshot(beat_phase=0.45, is_beat=False, beat_trust=0.80)

        self.ltm.schedule_transition(
            allocation={"Segment v1": "Impact Shockwave"},
            quantize_downbeat=True
        )
        self.assertIsNotNone(self.ltm._pending_transition)

        self.ltm.update(0.033)
        self.assertIsNotNone(self.ltm._pending_transition)
        self.assertEqual(self.ltm.pop_orders(), ())

        self.ltm.update(0.033, MusicSnapshot(beat_phase=0.02, is_beat=False, beat_trust=0.80))

        self.assertIsNone(self.ltm._pending_transition)
        orders = self.ltm.pop_orders()
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0].segment, "Segment v1")
        self.assertEqual(orders[0].target_mode, "Impact Shockwave")

    def test_clean_transition_techniques(self):
        """Technique selector routes based on audio kinetics."""
        ctx_drop = MagicMock(is_drop_impact=True, energy=0.9, salience=0.8, is_rhythmic=True)
        tech_drop = self.ltm.select_transition_technique(ctx_drop)
        self.assertEqual(tech_drop["type"], "explosion")

        ctx_groove = MagicMock(is_drop_impact=False, energy=0.6, salience=0.7, is_rhythmic=True)
        tech_groove = self.ltm.select_transition_technique(ctx_groove)
        self.assertEqual(tech_groove["type"], "vertical_wipe")

        ctx_chill = MagicMock(is_drop_impact=False, energy=0.3, salience=0.2, is_rhythmic=False)
        tech_chill = self.ltm.select_transition_technique(ctx_chill)
        self.assertEqual(tech_chill["type"], "fade_in_out")

    def test_axiom_02_zero_allocation_in_steady_state(self):
        """LocalTransitionManager.update() must allocate ZERO heap bytes in steady state."""
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

    def test_queued_transition_waits_for_active_transition(self):
        """Queued downbeat transition must wait until TD is no longer in transition."""
        self.director.start_transition({"type": "fade_in_out", "duration": 2.0})
        self.assertTrue(self.director.is_in_transition)

        self.ltm.set_installation([
            SegmentDescriptor(name="Segment v1", id="v1", orientation="vertical", is_blocked=False),
        ], FAKE_MODE_PROFILES)
        self.ltm.music = MusicSnapshot(beat_phase=0.01, is_beat=True, beat_trust=0.80)

        self.ltm.schedule_transition(
            allocation={"Segment v1": "Impact Shockwave"},
            quantize_downbeat=True
        )

        self.ltm.update(0.033)
        self.assertIsNotNone(self.ltm._pending_transition)
        self.assertEqual(self.ltm.pop_orders(), ())

        self.director.cancel_transition()
        self.ltm.update(0.033)
        self.assertIsNone(self.ltm._pending_transition)
        orders = self.ltm.pop_orders()
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0].segment, "Segment v1")

    def test_schedule_transition_staggered_execution(self):
        """Verifies schedule_transition with staggered=True emits per-segment orders and sets max duration on TD."""
        self.ltm.set_installation([
            SegmentDescriptor(name="Segment v1", id="v1", orientation="vertical", is_blocked=False),
            SegmentDescriptor(name="Segment h10", id="h10", orientation="horizontal", is_blocked=False),
        ], FAKE_MODE_PROFILES)

        self.ltm.schedule_transition(
            allocation={"Segment v1": "Impact Shockwave", "Segment h10": "Rainbow"},
            quantize_downbeat=False,
            staggered=True,
        )

        orders = self.ltm.pop_orders()
        self.assertEqual(len(orders), 2)
        by_seg = {o.segment: o for o in orders}

        self.assertTrue(self.director.is_in_transition)
        expected_max = max(
            by_seg["Segment v1"].duration + by_seg["Segment v1"].start_offset,
            by_seg["Segment h10"].duration + by_seg["Segment h10"].start_offset,
        )
        self.assertAlmostEqual(self.director.transition_duration, expected_max, places=2)

    def test_all_blocked_segments_do_not_start_director_transition(self):
        """When all targeted segments are blocked, _execute_transition must not start Transition_Director."""
        self.ltm.set_installation([
            SegmentDescriptor(name="Segment v1", id="v1", orientation="vertical", is_blocked=True),
            SegmentDescriptor(name="Segment v2", id="v2", orientation="vertical", is_blocked=True),
        ], FAKE_MODE_PROFILES)
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
            SegmentDescriptor(name="Segment v1", id="v1", orientation="vertical", is_blocked=False),
            SegmentDescriptor(name="Segment v2", id="v2", orientation="vertical", is_blocked=False),
        ], FAKE_MODE_PROFILES)

        self.ltm.schedule_transition(
            allocation={"Segment v1": "Rainbow", "Segment v2": "Rainbow"},
            quantize_downbeat=True,
        )
        self.assertIsNotNone(self.ltm._pending_transition)

        self.ltm.schedule_transition(
            allocation={"Segment v1": "Chromatic Chaser", "Segment v2": "Chromatic Chaser"},
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
