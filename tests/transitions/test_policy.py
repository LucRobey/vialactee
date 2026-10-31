"""
tests/transitions/test_policy.py - Contract and Invariant Tests for Policy Compiler.

Covers:
- Successful compilation of DEFAULT_POLICY, DEFAULT_POLICY_SMALL, and synthetic policies.
- PolicyError on non-disjoint zones, non-partition groupings, missing segments, non-positive weights.
- PolicyError on static satisfiability failure (|M_allowed| == 0).
- PolicyError on 200-cast Monte Carlo probe failure.
- PolicyWarning emission on rule weight: 1.0, unused tags, and disabled rules.
- LocalTransitionManager and TransitionService fail-fast PolicyError propagation.

Adheres strictly to <= 500 lines under AXIOM-07.
"""
import unittest
import warnings
from typing import Any, Dict, Tuple

from transitions.api import (
    InstallationSnapshot,
    ModeProfile,
    SegmentDescriptor,
)
from transitions.fakes import FAKE_MODE_PROFILES, make_fake_installation, make_fake_small_installation
import transitions.policy as policy
from transitions.policy import (
    DEFAULT_POLICY,
    DEFAULT_POLICY_SMALL,
    NeutralRuleWeightWarning,
    PolicyError,
    PolicyWarning,
    UnusedModeTagWarning,
    compile_policy,
)


def _make_13_modes() -> Tuple[ModeProfile, ...]:
    return FAKE_MODE_PROFILES


def _make_11_segments() -> Tuple[SegmentDescriptor, ...]:
    return make_fake_installation().segments


def _make_3_segments() -> Tuple[SegmentDescriptor, ...]:
    return make_fake_small_installation().segments


def _make_valid_synthetic_policy() -> Dict[str, Any]:
    return {
        "version": 1,
        "settings": {
            "maxDifferentModes": 3,
            "temperature": 1.0,
            "memoryDepth": 4,
            "repeatPenalty": 1.5,
        },
        "zones": {
            "all": {
                "segments": ["s1", "s2", "s3"],
                "groupings": [
                    {
                        "id": "unison",
                        "weight": 1.0,
                        "groups": [["s1", "s2", "s3"]],
                    },
                    {
                        "id": "split",
                        "weight": 2.0,
                        "groups": [["s1", "s3"], ["s2"]],
                    },
                ],
            },
        },
        "rules": [
            {
                "id": "forbid_strobe_on_s2",
                "when": [{"at": "s2", "mode": "Hyper Strobe"}],
                "effect": "forbid",
            },
            {
                "id": "reward_rainbow",
                "when": [{"mode": "Rainbow"}],
                "weight": 1.5,
            },
        ],
    }


class TestPolicyCompilerContract(unittest.TestCase):
    def setUp(self):
        self.modes = _make_13_modes()
        self.segments_11 = _make_11_segments()
        self.segments_3 = _make_3_segments()

    def test_compile_default_policy_full(self):
        compiled = compile_policy(DEFAULT_POLICY, self.segments_11, self.modes)
        self.assertIsNotNone(compiled)
        self.assertEqual(compiled.settings.max_different_modes, 3)
        self.assertAlmostEqual(compiled.settings.temperature, 1.0)
        self.assertEqual(compiled.settings.memory_depth, 8)
        self.assertAlmostEqual(compiled.settings.repeat_penalty, 3.0)

    def test_compile_default_policy_small(self):
        compiled = compile_policy(DEFAULT_POLICY_SMALL, self.segments_3, self.modes)
        self.assertIsNotNone(compiled)
        self.assertEqual(compiled.settings.max_different_modes, 2)
        self.assertIn("strips", compiled.zones)

    def test_compile_synthetic_policy(self):
        raw = _make_valid_synthetic_policy()
        compiled = compile_policy(raw, self.segments_3, self.modes)
        self.assertIsNotNone(compiled)
        self.assertEqual(len(compiled.rules), 2)

    def test_compiled_policy_immutability(self):
        compiled = compile_policy(_make_valid_synthetic_policy(), self.segments_3, self.modes)
        with self.assertRaises((TypeError, AttributeError)):
            compiled.settings.max_different_modes = 99  # type: ignore


class TestPolicyInvariantValidation(unittest.TestCase):
    def setUp(self):
        self.modes = _make_13_modes()
        self.segments_11 = _make_11_segments()
        self.segments_3 = _make_3_segments()

    def test_non_disjoint_zones_raises_policy_error(self):
        p = _make_valid_synthetic_policy()
        p["zones"] = {
            "z1": {
                "segments": ["s1", "s2"],
                "groupings": [{"id": "u", "weight": 1.0, "groups": [["s1", "s2"]]}],
            },
            "z2": {
                "segments": ["s2", "s3"],
                "groupings": [{"id": "u", "weight": 1.0, "groups": [["s2", "s3"]]}],
            },
        }
        with self.assertRaises(PolicyError):
            compile_policy(p, self.segments_3, self.modes)

    def test_grouping_missing_segment_raises_policy_error(self):
        p = _make_valid_synthetic_policy()
        p["zones"]["all"]["groupings"].append(
            {"id": "broken", "weight": 1.0, "groups": [["s1", "s2"]]}
        )
        with self.assertRaises(PolicyError):
            compile_policy(p, self.segments_3, self.modes)

    def test_grouping_extra_segment_raises_policy_error(self):
        p = _make_valid_synthetic_policy()
        p["zones"]["all"]["groupings"].append(
            {"id": "broken", "weight": 1.0, "groups": [["s1", "s2", "s3", "alien"]]}
        )
        with self.assertRaises(PolicyError):
            compile_policy(p, self.segments_3, self.modes)

    def test_grouping_overlapping_groups_raises_policy_error(self):
        p = _make_valid_synthetic_policy()
        p["zones"]["all"]["groupings"].append(
            {"id": "broken", "weight": 1.0, "groups": [["s1", "s2"], ["s2", "s3"]]}
        )
        with self.assertRaises(PolicyError):
            compile_policy(p, self.segments_3, self.modes)

    def test_non_positive_grouping_weight_raises_policy_error(self):
        p = _make_valid_synthetic_policy()
        p["zones"]["all"]["groupings"][0]["weight"] = 0.0
        with self.assertRaises(PolicyError):
            compile_policy(p, self.segments_3, self.modes)

    def test_boolean_grouping_weight_raises_policy_error(self):
        p = _make_valid_synthetic_policy()
        p["zones"]["all"]["groupings"][0]["weight"] = True
        with self.assertRaises(PolicyError):
            compile_policy(p, self.segments_3, self.modes)

    def test_non_positive_rule_weight_raises_policy_error(self):
        p = _make_valid_synthetic_policy()
        p["rules"] = [{"id": "r", "when": [{"mode": "Rainbow"}], "weight": -0.5}]
        with self.assertRaises(PolicyError):
            compile_policy(p, self.segments_3, self.modes)

    def test_boolean_rule_weight_raises_policy_error(self):
        p = _make_valid_synthetic_policy()
        p["rules"] = [{"id": "r", "when": [{"mode": "Rainbow"}], "weight": True}]
        with self.assertRaises(PolicyError):
            compile_policy(p, self.segments_3, self.modes)

    def test_rule_weight_and_forbid_conflict_raises_policy_error(self):
        p = _make_valid_synthetic_policy()
        p["rules"] = [{"id": "r", "when": [{"mode": "Rainbow"}], "weight": 2.0, "effect": "forbid"}]
        with self.assertRaises(PolicyError):
            compile_policy(p, self.segments_3, self.modes)

    def test_invalid_settings_raises_policy_error(self):
        for bad_set in (
            {"maxDifferentModes": 0, "temperature": 1.0, "memoryDepth": 1, "repeatPenalty": 1.0},
            {"maxDifferentModes": 2, "temperature": 0.0, "memoryDepth": 1, "repeatPenalty": 1.0},
            {"maxDifferentModes": 2, "temperature": float("nan"), "memoryDepth": 1, "repeatPenalty": 1.0},
            {"maxDifferentModes": 2, "temperature": float("inf"), "memoryDepth": 1, "repeatPenalty": 1.0},
            {"maxDifferentModes": 2, "temperature": 1.0, "memoryDepth": -1, "repeatPenalty": 1.0},
            {"maxDifferentModes": 2, "temperature": 1.0, "memoryDepth": 1, "repeatPenalty": -0.1},
            {"maxDifferentModes": 2, "temperature": 1.0, "memoryDepth": 1, "repeatPenalty": float("nan")},
            {"maxDifferentModes": 2, "temperature": 1.0, "memoryDepth": 1, "repeatPenalty": float("inf")},
        ):
            p = _make_valid_synthetic_policy()
            p["settings"] = bad_set
            with self.assertRaises(PolicyError):
                compile_policy(p, self.segments_3, self.modes)

    def test_non_dict_settings_raises_policy_error(self):
        with self.assertRaises(PolicyError):
            compile_policy({"settings": "not_a_dict"}, self.segments_3, self.modes)
        p = _make_valid_synthetic_policy()
        p["settings"] = "invalid_string"
        with self.assertRaises(PolicyError):
            compile_policy(p, self.segments_3, self.modes)

    def test_nan_and_inf_rule_weight_raises_policy_error(self):
        for bad_w in (float("nan"), float("inf"), -float("inf")):
            p = _make_valid_synthetic_policy()
            p["rules"] = [{"id": "r", "when": [{"mode": "Rainbow"}], "weight": bad_w}]
            with self.assertRaises(PolicyError):
                compile_policy(p, self.segments_3, self.modes)

    def test_nan_and_inf_grouping_weight_raises_policy_error(self):
        for bad_w in (float("nan"), float("inf")):
            p = _make_valid_synthetic_policy()
            p["zones"]["all"]["groupings"][0]["weight"] = bad_w
            with self.assertRaises(PolicyError):
                compile_policy(p, self.segments_3, self.modes)

    def test_universal_fallback_policy_on_vertical_only_fixture(self):
        v_segs = (SegmentDescriptor(name="v1", id="v1", orientation="vertical"),)
        c = compile_policy({"settings": {"maxDifferentModes": 1}}, v_segs, self.modes)
        self.assertIsNotNone(c)

    def test_unknown_mode_in_rule_raises_policy_error(self):
        p = _make_valid_synthetic_policy()
        p["rules"] = [{"id": "r", "when": [{"mode": "NonExistentMode"}], "effect": "forbid"}]
        with self.assertRaises(PolicyError):
            compile_policy(p, self.segments_3, self.modes)

    def test_unknown_segment_in_rule_raises_policy_error(self):
        p = _make_valid_synthetic_policy()
        p["rules"] = [{"id": "r", "when": [{"at": "ghost_seg", "mode": "Rainbow"}], "effect": "forbid"}]
        with self.assertRaises(PolicyError):
            compile_policy(p, self.segments_3, self.modes)

    def test_segment_tag_resolving_to_zero_segments_raises_policy_error(self):
        p = _make_valid_synthetic_policy()
        p["rules"] = [{"id": "r", "when": [{"at": "tier:non_existent", "mode": "Rainbow"}], "effect": "forbid"}]
        with self.assertRaises(PolicyError):
            compile_policy(p, self.segments_3, self.modes)


class TestStaticSatisfiability(unittest.TestCase):
    def setUp(self):
        self.modes = _make_13_modes()
        self.segments_3 = _make_3_segments()

    def test_all_modes_forbidden_on_group_raises_policy_error(self):
        p = _make_valid_synthetic_policy()
        p["rules"] = [
            {"id": f"forbid_{m.name}", "when": [{"at": "s2", "mode": m.name}], "effect": "forbid"}
            for m in self.modes
        ]
        with self.assertRaises(PolicyError) as ctx:
            compile_policy(p, self.segments_3, self.modes)
        self.assertIn("s2", str(ctx.exception).lower())

    def test_partial_forbid_retains_allowed_modes(self):
        p = _make_valid_synthetic_policy()
        p["rules"] = [
            {"id": f"forbid_{m.name}", "when": [{"at": "s2", "mode": m.name}], "effect": "forbid"}
            for m in self.modes if m.name != "Rainbow"
        ]
        compiled = compile_policy(p, self.segments_3, self.modes)
        self.assertIsNotNone(compiled)


class TestFeasibilityProbe(unittest.TestCase):
    def setUp(self):
        self.modes = _make_13_modes()
        self.segments_3 = _make_3_segments()

    def test_feasibility_probe_passes_on_valid_policy(self):
        p = _make_valid_synthetic_policy()
        compiled = compile_policy(p, self.segments_3, self.modes)
        self.assertTrue(policy.run_feasibility_probe(compiled, casts_per_grouping=200))

    def test_feasibility_probe_fails_on_budget_exhaustion(self):
        p = _make_valid_synthetic_policy()
        p["settings"]["maxDifferentModes"] = 1
        p["rules"] = [
            {"id": "forbid_metronome_s1", "when": [{"at": "s1", "mode": "Metronome"}], "effect": "forbid"},
            {"id": "forbid_rainbow_s2", "when": [{"at": "s2", "mode": "Rainbow"}], "effect": "forbid"},
        ]
        for m in self.modes:
            if m.name not in ("Rainbow", "Metronome"):
                p["rules"].append({"id": f"forbid_{m.name}", "when": [{"mode": m.name}], "effect": "forbid"})
        with self.assertRaises(PolicyError):
            compile_policy(p, self.segments_3, self.modes)


class TestPolicyWarnings(unittest.TestCase):
    def setUp(self):
        self.modes = _make_13_modes()
        self.segments_3 = _make_3_segments()

    def test_rule_weight_1_0_emits_policy_warning(self):
        p = _make_valid_synthetic_policy()
        p["rules"] = [{"id": "neutral_weight_rule", "when": [{"mode": "Rainbow"}], "weight": 1.0}]
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            compiled = compile_policy(p, self.segments_3, self.modes)
            self.assertIsNotNone(compiled)
            self.assertTrue(any(issubclass(item.category, PolicyWarning) for item in w))
            self.assertTrue(any("1.0" in str(item.message) for item in w))

    def test_grouping_weight_1_0_does_not_emit_neutral_warning(self):
        p = _make_valid_synthetic_policy()
        p["rules"] = []
        p["zones"]["all"]["groupings"][0]["weight"] = 1.0
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            compile_policy(p, self.segments_3, self.modes)
            neutral_warns = [item for item in w if issubclass(item.category, NeutralRuleWeightWarning)]
            self.assertEqual(len(neutral_warns), 0)

    def test_unused_mode_tag_emits_warning(self):
        # Create a subset of modes where layer:meter is not present
        subset_modes = tuple(m for m in self.modes if "layer:meter" not in m.tags)
        p = _make_valid_synthetic_policy()
        p["rules"] = [{"id": "tag_rule", "when": [{"tag": "layer:meter"}], "weight": 2.0}]
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            compiled = compile_policy(p, self.segments_3, subset_modes)
            self.assertIsNotNone(compiled)
            self.assertTrue(any(issubclass(item.category, UnusedModeTagWarning) for item in w))
            self.assertTrue(any("layer:meter" in str(item.message) for item in w))

    def test_disabled_rule_is_skipped_without_warning(self):
        p = _make_valid_synthetic_policy()
        p["rules"] = [{"id": "disabled_rule", "enabled": False, "when": [{"mode": "Rainbow"}], "weight": 2.0}]
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            compiled = compile_policy(p, self.segments_3, self.modes)
            self.assertIsNotNone(compiled)
            self.assertEqual(len(compiled.rules), 0)
            self.assertEqual(len([item for item in w if issubclass(item.category, PolicyWarning)]), 0)


class TestManagerServiceIntegration(unittest.TestCase):
    def setUp(self):
        self.modes = _make_13_modes()
        self.segments_3 = _make_3_segments()
        self.snap = InstallationSnapshot(segments=self.segments_3, modes=self.modes)

    def test_service_configure_propagates_policy_error(self):
        from transitions.service import DefaultTransitionService
        svc = DefaultTransitionService()
        svc.set_installation(self.snap)
        bad_policy = _make_valid_synthetic_policy()
        bad_policy["settings"]["maxDifferentModes"] = 0
        with self.assertRaises(PolicyError):
            svc.configure(bad_policy)

    def test_manager_lazy_compilation_on_set_installation(self):
        from transitions.manager import LocalTransitionManager
        mgr = LocalTransitionManager()
        bad_policy = _make_valid_synthetic_policy()
        bad_policy["settings"]["temperature"] = -1.0
        mgr.configure(bad_policy)
        with self.assertRaises(PolicyError):
            mgr.set_installation(self.segments_3, self.modes)


if __name__ == "__main__":
    unittest.main()
