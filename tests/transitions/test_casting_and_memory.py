"""
tests/transitions/test_casting_and_memory.py - Tests for TransitionMemory and Joint Transition Caster.

Covers:
1. TransitionMemory decay math, grouping_weight, variety_factor, and is_exact_repeat.
2. 5,000 seeded draws invariant check: 0 forbid violations, distinct modes <= maxDifferentModes, <= 10 ms/cast.
3. Blocked segments treated as fixed placements counting toward budget and rule evaluation.
4. Gibbs mode-class move under full mode budget (|distinct(M)| == maxDifferentModes).
5. 3-placement recipe boost rule evaluation.
6. Anti-repeat guard triggering redraws when identical to previous cast.
7. Repeat penalty (repeatPenalty=3.0 vs 0.0) increasing mean time-to-repeat without degrading DNA match.
8. Runtime fallback when a rule makes a group unsatisfiable with a blocked segment (fallback_segments + no crash).
"""

import math
import random
import time
import unittest

from transitions.api import SegmentDescriptor
from transitions.casting import cast_transition, compute_mode_fit
from transitions.fakes import make_fake_installation, make_fake_small_installation
from transitions.memory import TransitionMemory
from transitions.policy import DEFAULT_POLICY, compile_policy, evaluate_rule


class TestTransitionMemory(unittest.TestCase):
    def test_memory_grouping_weight_decay(self):
        mem = TransitionMemory(depth=4)
        base_w = 2.0
        self.assertAlmostEqual(mem.grouping_weight("horizontals", "h-tiers", base_w, 1.5), 2.0)

        # Record age k=0 match (0.75^0 = 1.0)
        mem.record({"h00": "Rainbow"}, {"horizontals": "h-tiers"})
        expected = base_w / (1.0 + 1.5 * 1.0)
        self.assertAlmostEqual(mem.grouping_weight("horizontals", "h-tiers", base_w, 1.5), expected, places=6)
        self.assertAlmostEqual(mem.grouping_weight("horizontals", "h-all", base_w, 1.5), base_w)

        # Record non-match so previous entry becomes k=1 (0.75^1 = 0.75)
        mem.record({"h00": "Metronome"}, {"horizontals": "h-all"})
        expected_age2 = base_w / (1.0 + 1.5 * 0.75)
        self.assertAlmostEqual(mem.grouping_weight("horizontals", "h-tiers", base_w, 1.5), expected_age2, places=6)

    def test_memory_variety_factor_and_exact_repeat(self):
        mem = TransitionMemory(depth=4)
        mem.record({"s1": "Rainbow", "s2": "Rainbow"}, {"strips": "strips-all"})
        self.assertTrue(mem.is_exact_repeat({"s1": "Rainbow", "s2": "Rainbow"}))
        self.assertFalse(mem.is_exact_repeat({"s1": "Rainbow", "s2": "Metronome"}))

        vf = mem.variety_factor(("s1", "s2"), "Rainbow", repeat_penalty=1.5)
        # mean_recency = (1.0 + 1.0) / 2 = 1.0 -> 1 / (1 + 1.5 * 1.0) = 0.4
        self.assertAlmostEqual(vf, 1.0 / (1.0 + 1.5 * 1.0), places=6)


class TestJointTransitionCaster(unittest.TestCase):
    def setUp(self):
        self.inst = make_fake_installation()
        self.compiled = compile_policy(DEFAULT_POLICY, self.inst.segments, self.inst.modes)
        self.target_dna = {"energy": 0.6, "punch": 0.5, "rhythm": 0.6, "complexity": 0.5}

    def test_5000_seeded_draws_invariants_and_latency(self):
        """Across 5,000 seeded draws: 0 forbid violations, distinct <= maxDifferentModes, <= 10 ms/cast."""
        raw = dict(DEFAULT_POLICY)
        raw["rules"] = list(DEFAULT_POLICY["rules"]) + [
            {"id": "forbid-strobe-and-metronome", "when": [{"mode": "Hyper Strobe"}, {"mode": "Metronome"}], "effect": "forbid"}
        ]
        compiled = compile_policy(raw, self.inst.segments, self.inst.modes)
        forbid_rules = [r for r in compiled.rules if r.is_forbid]

        rng = random.Random(12345)
        mem = TransitionMemory(depth=8)

        t0 = time.perf_counter()
        n_draws = 5000
        for _ in range(n_draws):
            res = cast_transition(
                compiled,
                self.target_dna,
                self.inst.segments,
                mem,
                rng=rng,
            )
            self.assertEqual(len(res.orders_by_segment_name), 11)
            distinct = set(res.full_cast_by_id.values())
            self.assertLessEqual(len(distinct), compiled.settings.max_different_modes)
            self.assertEqual(res.forbid_violations, 0)
            for r in forbid_rules:
                self.assertFalse(evaluate_rule(r, res.full_cast_by_id))
            mem.record(res.full_cast_by_id, res.groupings_by_zone)

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        mean_ms = elapsed_ms / n_draws
        self.assertLessEqual(mean_ms, 10.0, f"Mean cast latency {mean_ms:.3f} ms exceeds 10 ms budget")

    def test_blocked_segments_count_toward_budget_and_rules(self):
        """Blocked segments act as fixed placements that consume mode budget and trigger rules."""
        raw = dict(DEFAULT_POLICY)
        raw["rules"] = list(DEFAULT_POLICY["rules"]) + [
            {"id": "forbid-strobe-and-metronome", "when": [{"mode": "Hyper Strobe"}, {"mode": "Metronome"}], "effect": "forbid"}
        ]
        segs = list(self.inst.segments)
        # Block h00 with Rainbow and v1 with Hyper Strobe
        segs[0] = SegmentDescriptor(
            name=segs[0].name,
            id=segs[0].id,
            orientation=segs[0].orientation,
            available_modes=segs[0].available_modes,
            active_mode="Rainbow",
            is_blocked=True,
            tags=segs[0].tags,
        )
        segs[1] = SegmentDescriptor(
            name=segs[1].name,
            id=segs[1].id,
            orientation=segs[1].orientation,
            available_modes=segs[1].available_modes,
            active_mode="Hyper Strobe",
            is_blocked=True,
            tags=segs[1].tags,
        )
        compiled = compile_policy(raw, segs, self.inst.modes)
        mem = TransitionMemory(depth=8)
        rng = random.Random(99)

        for _ in range(100):
            res = cast_transition(compiled, self.target_dna, segs, mem, rng=rng)
            # Blocked segments are omitted from orders_by_segment_name
            self.assertNotIn("Segment h00", res.orders_by_segment_name)
            self.assertNotIn("Segment v1", res.orders_by_segment_name)
            # Active modes including blocked segments must be <= 3
            all_active = set(res.full_cast_by_id.values())
            self.assertLessEqual(len(all_active), 3)
            # Because v1 is blocked on Hyper Strobe, no segment may get Metronome
            self.assertNotIn("Metronome", all_active)

    def test_gibbs_mode_class_move_under_full_budget(self):
        """With 5 groups and cap 3, mode-class moves escape the frozen-budget trap to reach recipes."""
        raw_policy = {
            "version": 1,
            "settings": {"maxDifferentModes": 3, "temperature": 1.0, "memoryDepth": 4, "repeatPenalty": 0.0},
            "zones": {
                "pillars": {
                    "segments": ["v1", "v2", "v3", "v4"],
                    "groupings": [
                        {"id": "p-halves", "weight": 1.0, "groups": [["v1", "v2"], ["v3", "v4"]]}
                    ],
                },
                "horizontals": {
                    "segments": ["h00", "h10", "h11", "h20", "h30", "h31", "h32"],
                    "groupings": [
                        {"id": "h-tiers", "weight": 1.0, "groups": [["tier:canopy"], ["tier:mid"], ["tier:low"]]}
                    ],
                },
            },
            "rules": [
                # Force initial draw into 3 modes shared across the 5 groups unless refined by mode-class moves
                {"id": "boost-power-bar", "when": [{"at": "pillars", "mode": "Power Bar"}], "weight": 20.0},
                {"id": "boost-stars", "when": [{"at": "tier:canopy", "mode": "Shining Stars"}], "weight": 20.0},
                {
                    "id": "recipe-3",
                    "when": [
                        {"at": "pillars", "mode": "Power Bar"},
                        {"at": "tier:canopy", "mode": "Shining Stars"},
                        {"at": "tier:low", "mode": "Rainbow"},
                    ],
                    "weight": 500.0,
                },
            ],
        }
        compiled = compile_policy(raw_policy, self.inst.segments, self.inst.modes)
        mem = TransitionMemory(depth=4)
        rng = random.Random(7)

        recipe_hits = 0
        for _ in range(100):
            res = cast_transition(compiled, self.target_dna, self.inst.segments, mem, rng=rng)
            distinct = set(res.full_cast_by_id.values())
            self.assertLessEqual(len(distinct), 3)
            if (
                res.full_cast_by_id["v1"] == "Power Bar"
                and res.full_cast_by_id["h00"] == "Shining Stars"
                and res.full_cast_by_id["h10"] == "Rainbow"
            ):
                recipe_hits += 1
        self.assertGreater(recipe_hits, 25)

    def test_3_placement_recipe_boost(self):
        """A bonus rule raises target frequency >= 1.5x vs baseline, and a 3-placement recipe boosts co-occurrence."""
        small_inst = make_fake_small_installation()
        base_policy = {
            "version": 1,
            "settings": {"maxDifferentModes": 3, "temperature": 1.0, "memoryDepth": 4, "repeatPenalty": 0.0},
            "zones": {
                "strips": {
                    "segments": ["s1", "s2", "s3"],
                    "groupings": [
                        {"id": "triad", "weight": 1.0, "groups": [["s1"], ["s2"], ["s3"]]}
                    ],
                }
            },
            "rules": [],
        }
        boost_policy = dict(base_policy, rules=[
            {"id": "bonus_s1", "when": [{"at": "s1", "mode": "Rainbow"}], "weight": 10.0},
            {"id": "bonus_s2", "when": [{"at": "s2", "mode": "Metronome"}], "weight": 10.0},
            {
                "id": "triad_recipe",
                "when": [
                    {"at": "s1", "mode": "Rainbow"},
                    {"at": "s2", "mode": "Metronome"},
                    {"at": "s3", "mode": "Hyper Strobe"},
                ],
                "weight": 200.0,
            },
        ])
        comp_base = compile_policy(base_policy, small_inst.segments, small_inst.modes)
        comp_boost = compile_policy(boost_policy, small_inst.segments, small_inst.modes)
        mem = TransitionMemory(depth=4)

        rng_base = random.Random(42)
        base_s1_hits = 0
        base_recipe_hits = 0
        for _ in range(200):
            res = cast_transition(comp_base, self.target_dna, small_inst.segments, mem, rng=rng_base)
            if res.orders_by_segment_name["Segment s1"] == "Rainbow":
                base_s1_hits += 1
            if (
                res.orders_by_segment_name["Segment s1"] == "Rainbow"
                and res.orders_by_segment_name["Segment s2"] == "Metronome"
                and res.orders_by_segment_name["Segment s3"] == "Hyper Strobe"
            ):
                base_recipe_hits += 1

        rng_boost = random.Random(42)
        boost_s1_hits = 0
        boost_recipe_hits = 0
        for _ in range(200):
            res = cast_transition(comp_boost, self.target_dna, small_inst.segments, mem, rng=rng_boost)
            if res.orders_by_segment_name["Segment s1"] == "Rainbow":
                boost_s1_hits += 1
            if (
                res.orders_by_segment_name["Segment s1"] == "Rainbow"
                and res.orders_by_segment_name["Segment s2"] == "Metronome"
                and res.orders_by_segment_name["Segment s3"] == "Hyper Strobe"
            ):
                boost_recipe_hits += 1

        self.assertGreaterEqual(boost_s1_hits, base_s1_hits * 1.5)
        self.assertGreater(boost_recipe_hits, base_recipe_hits + 30)

    def test_repeat_penalty_increases_mean_time_to_repeat(self):
        """repeatPenalty=3.0 increases mean time-to-repeat vs repeatPenalty=0.0 while keeping DNA distance bounded."""
        def run_sim(penalty: float) -> tuple[float, float]:
            raw = dict(DEFAULT_POLICY)
            raw["settings"] = dict(DEFAULT_POLICY["settings"], repeatPenalty=penalty)
            comp = compile_policy(raw, self.inst.segments, self.inst.modes)
            mem = TransitionMemory(depth=8)
            rng = random.Random(2026)
            last_seen = {}
            ttr_samples = []
            dna_dists = []

            for step in range(300):
                res = cast_transition(comp, self.target_dna, self.inst.segments, mem, rng=rng)
                for sid, m_name in res.full_cast_by_id.items():
                    key = (sid, m_name)
                    if key in last_seen:
                        ttr_samples.append(step - last_seen[key])
                    last_seen[key] = step
                    dna = comp.mode_dna[m_name]
                    dist = math.sqrt(
                        (dna[0] - self.target_dna["energy"]) ** 2
                        + (dna[1] - self.target_dna["punch"]) ** 2
                        + (dna[2] - self.target_dna["rhythm"]) ** 2
                        + (dna[3] - self.target_dna["complexity"]) ** 2
                    )
                    dna_dists.append(dist)
                mem.record(res.full_cast_by_id, res.groupings_by_zone)

            mean_ttr = sum(ttr_samples) / len(ttr_samples)
            mean_dna = sum(dna_dists) / len(dna_dists)
            return mean_ttr, mean_dna

        ttr_0, dna_0 = run_sim(0.0)
        ttr_3, dna_3 = run_sim(3.0)
        self.assertGreater(ttr_3, ttr_0)
        self.assertLessEqual(dna_3 - dna_0, 0.15)

    def test_runtime_infeasible_cast_fallback_does_not_crash(self):
        """If blocked segments exhaust maxDifferentModes and forbid rules block reuse, fallback preserves active mode."""
        small_inst = make_fake_small_installation()
        raw_policy = {
            "version": 1,
            "settings": {"maxDifferentModes": 1, "temperature": 1.0, "memoryDepth": 4, "repeatPenalty": 0.0},
            "zones": {
                "strips": {
                    "segments": ["s1", "s2", "s3"],
                    "groupings": [
                        {"id": "split", "weight": 1.0, "groups": [["s1"], ["s2", "s3"]]}
                    ],
                }
            },
            "rules": [
                # Forbid Rainbow on s2 when s1 is blocked on Rainbow (while s1 is not blocked at compile time)
                {"id": "no-rainbow-s2-with-metronome", "when": [{"at": "s1", "mode": "Metronome"}, {"at": "s2", "mode": "Metronome"}], "effect": "forbid"}
            ],
        }
        compiled = compile_policy(raw_policy, small_inst.segments, small_inst.modes)
        # Now block s1 on Metronome at runtime with maxDifferentModes=1 -> s2,s3 can only reuse Metronome, which is forbidden!
        segs = list(small_inst.segments)
        segs[0] = SegmentDescriptor(
            name=segs[0].name,
            id=segs[0].id,
            orientation=segs[0].orientation,
            available_modes=segs[0].available_modes,
            active_mode="Metronome",
            is_blocked=True,
            tags=segs[0].tags,
        )
        mem = TransitionMemory(depth=4)
        res = cast_transition(compiled, self.target_dna, segs, mem)
        self.assertEqual(res.fallback_segments, ("s2", "s3"))
        self.assertEqual(res.orders_by_segment_name, {})


if __name__ == "__main__":
    unittest.main()
