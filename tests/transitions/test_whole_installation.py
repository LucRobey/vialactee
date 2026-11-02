"""
tests/transitions/test_whole_installation.py

Optional `wholeInstallation` policy block: with probability w/(w+1) (recency-decayed) the whole
installation plays ONE group, ignoring the zone groupings.
"""
import copy
import random
import unittest

from transitions.api import PolicyError
from transitions.casting import WHOLE_KEY, ZONES_KEY, cast_transition
from transitions.fakes import make_fake_installation
from transitions.memory import TransitionMemory
from transitions.policy import DEFAULT_POLICY, compile_policy

TARGET = {"energy": 0.6, "punch": 0.5, "rhythm": 0.6, "complexity": 0.5}


def _policy(whole):
    raw = copy.deepcopy(DEFAULT_POLICY)
    if whole is not None:
        raw["wholeInstallation"] = whole
    return raw


class TestWholeInstallation(unittest.TestCase):
    def setUp(self):
        self.inst = make_fake_installation()

    def _compile(self, whole, **overrides):
        raw = _policy(whole)
        raw.update(overrides)
        return compile_policy(raw, self.inst.segments, self.inst.modes)

    def test_absent_block_keeps_previous_behaviour(self):
        compiled = self._compile(None)
        self.assertIsNone(compiled.whole)
        res = cast_transition(compiled, TARGET, self.inst.segments, TransitionMemory(8), rng=random.Random(1))
        self.assertNotIn(WHOLE_KEY, res.groupings_by_zone)

    def test_compiles_to_one_group_with_every_segment(self):
        compiled = self._compile({"id": "unison", "weight": 1})
        self.assertEqual(len(compiled.whole.groups), 1)
        self.assertEqual(set(compiled.whole.groups[0]), set(compiled.segment_ids))

    def test_disabled_block_is_ignored(self):
        self.assertIsNone(self._compile({"id": "unison", "weight": 1, "enabled": False}).whole)

    def test_whole_draw_yields_a_single_mode_for_all_segments(self):
        compiled = self._compile({"id": "unison", "weight": 1e9})
        mem = TransitionMemory(8)
        rng = random.Random(7)
        res = cast_transition(compiled, TARGET, self.inst.segments, mem, rng=rng)
        self.assertEqual(res.groupings_by_zone, {WHOLE_KEY: "unison"})
        self.assertEqual(len(res.groups), 1)
        self.assertEqual(len(set(res.full_cast_by_id.values())), 1)
        self.assertEqual(len(res.orders_by_segment_name), len(compiled.segment_ids))

    def test_frequency_follows_weight_and_zones_are_still_used(self):
        compiled = self._compile({"id": "unison", "weight": 1})  # ~50% before recency
        rng = random.Random(99)
        wholes = zones = 0
        for _ in range(400):
            res = cast_transition(compiled, TARGET, self.inst.segments, TransitionMemory(0), rng=rng)
            if res.groupings_by_zone.get(WHOLE_KEY) == "unison":
                wholes += 1
            else:
                zones += 1
                self.assertEqual(res.groupings_by_zone[WHOLE_KEY], ZONES_KEY)
                self.assertIn("pillars", res.groupings_by_zone)
        self.assertGreater(wholes, 140)
        self.assertGreater(zones, 140)

    def test_recency_penalty_reduces_repeated_whole(self):
        compiled = self._compile({"id": "unison", "weight": 1})
        mem = TransitionMemory(8)
        base = mem.grouping_weight(WHOLE_KEY, "unison", 1.0, 3.0)
        mem.record({"v1": "Rainbow"}, {WHOLE_KEY: "unison"})
        self.assertLess(mem.grouping_weight(WHOLE_KEY, "unison", 1.0, 3.0), base)
        self.assertIsNotNone(compiled.whole)

    def test_forbid_rules_hold_for_the_whole_group(self):
        rules = list(DEFAULT_POLICY["rules"]) + [
            {"id": "no-strobe-metronome", "when": [{"mode": "Hyper Strobe"}, {"mode": "Metronome"}], "effect": "forbid"},
        ]
        compiled = self._compile({"id": "unison", "weight": 1e9}, rules=rules)
        rng = random.Random(3)
        for _ in range(100):
            res = cast_transition(compiled, TARGET, self.inst.segments, TransitionMemory(0), rng=rng)
            self.assertEqual(res.forbid_violations, 0)

    def test_invalid_blocks_raise_policy_error(self):
        for bad in (
            {"id": "x", "weight": 0},
            {"id": "x", "weight": "a"},
            {"id": "", "weight": 1},
            {"id": "pillars-all", "weight": 1},  # duplicates a grouping id
            {"id": "x", "weight": 1, "extra": 1},
            [],
        ):
            with self.subTest(bad=bad), self.assertRaises(PolicyError):
                self._compile(bad)


if __name__ == "__main__":
    unittest.main()
