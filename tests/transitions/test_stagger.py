"""
tests/transitions/test_stagger.py - Unit tests for transitions/stagger.py.
Verifies spatial propagation patterns, cohort-specific techniques,
maximum duration computation, and musical context pattern selection.
"""

import unittest
from types import SimpleNamespace

from transitions.stagger import (
    StaggerPattern,
    discover_segment_cohorts,
    generate_staggered_configs,
    get_max_transition_duration,
    select_stagger_pattern,
)


class TestStagger(unittest.TestCase):
    def setUp(self):
        self.verticals = ["Segment v1", "Segment v2", "Segment v3", "Segment v4"]
        self.rings = [
            ["Segment h10", "Segment h11"],
            ["Segment h20", "Segment h21"],
            ["Segment h30", "Segment h31"],
        ]
        self.all_segs = self.verticals + [s for r in self.rings for s in r]
        self.allocation = {seg: "Plasma Fire" for seg in self.all_segs}

    def test_simultaneous_pattern(self):
        configs = generate_staggered_configs(
            allocation=self.allocation,
            verticals=self.verticals,
            rings=self.rings,
            base_technique="fade_in_out",
            base_duration=2.0,
            pattern=StaggerPattern.SIMULTANEOUS,
        )
        self.assertEqual(len(configs), len(self.all_segs))
        for seg, cfg in configs.items():
            self.assertEqual(cfg["start_offset"], 0.0)
            self.assertEqual(cfg["duration"], 2.0)
            self.assertEqual(cfg["type"], "fade_in_out")

    def test_cascade_down_with_rings(self):
        configs = generate_staggered_configs(
            allocation=self.allocation,
            verticals=self.verticals,
            rings=self.rings,
            base_technique="fade_in_out",
            base_duration=2.0,
            pattern=StaggerPattern.CASCADE_DOWN,
            step_delay=0.10,
        )
        # Verticals wipe down starting at 0.0
        for v in self.verticals:
            self.assertEqual(configs[v]["start_offset"], 0.0)
            self.assertEqual(configs[v]["type"], "vertical_wipe")
            self.assertEqual(configs[v]["direction"], "DOWN")

        # Ring 0: 0.0s, Ring 1: 0.10s, Ring 2: 0.20s
        for s in self.rings[0]:
            self.assertAlmostEqual(configs[s]["start_offset"], 0.0, places=2)
            self.assertEqual(configs[s]["type"], "fade_in_out")
        for s in self.rings[1]:
            self.assertAlmostEqual(configs[s]["start_offset"], 0.10, places=2)
        for s in self.rings[2]:
            self.assertAlmostEqual(configs[s]["start_offset"], 0.20, places=2)

    def test_cascade_down_small_profile_verticals_only(self):
        alloc = {"Segment s1": "A", "Segment s2": "B", "Segment s3": "C"}
        verts = ["Segment s1", "Segment s2", "Segment s3"]
        configs = generate_staggered_configs(
            allocation=alloc,
            verticals=verts,
            rings=[],
            base_duration=1.5,
            pattern=StaggerPattern.CASCADE_DOWN,
            step_delay=0.20,
        )
        self.assertAlmostEqual(configs["Segment s1"]["start_offset"], 0.0, places=2)
        self.assertAlmostEqual(configs["Segment s2"]["start_offset"], 0.20, places=2)
        self.assertAlmostEqual(configs["Segment s3"]["start_offset"], 0.40, places=2)
        self.assertEqual(configs["Segment s1"]["direction"], "DOWN")

    def test_cascade_up_pattern(self):
        configs = generate_staggered_configs(
            allocation=self.allocation,
            verticals=self.verticals,
            rings=self.rings,
            base_technique="fade_in_out",
            base_duration=2.0,
            pattern=StaggerPattern.CASCADE_UP,
            step_delay=0.15,
        )
        for v in self.verticals:
            self.assertEqual(configs[v]["direction"], "UP")

        # Bottom ring (index 2) triggers first at 0.0
        for s in self.rings[2]:
            self.assertAlmostEqual(configs[s]["start_offset"], 0.0, places=2)
        # Top ring (index 0) triggers last at 0.30
        for s in self.rings[0]:
            self.assertAlmostEqual(configs[s]["start_offset"], 0.30, places=2)

    def test_center_out_pattern(self):
        configs = generate_staggered_configs(
            allocation=self.allocation,
            verticals=self.verticals,
            rings=self.rings,  # 3 rings: index 0, 1, 2. Mid is 1.
            base_technique="fade_in_out",
            base_duration=2.0,
            pattern=StaggerPattern.CENTER_OUT,
            step_delay=0.25,
        )
        # Center ring (index 1) has dist 0 -> start_offset 0.0
        for s in self.rings[1]:
            self.assertAlmostEqual(configs[s]["start_offset"], 0.0, places=2)
        # Outer rings (index 0 and 2) have dist 1 -> start_offset 0.25
        for s in self.rings[0]:
            self.assertAlmostEqual(configs[s]["start_offset"], 0.25, places=2)
        for s in self.rings[2]:
            self.assertAlmostEqual(configs[s]["start_offset"], 0.25, places=2)

    def test_cohort_complementary_pattern(self):
        configs = generate_staggered_configs(
            allocation=self.allocation,
            verticals=self.verticals,
            rings=self.rings,
            base_technique="fade_in_out",
            base_duration=2.0,
            pattern=StaggerPattern.COHORT_COMPLEMENTARY,
            step_delay=0.10,
        )
        # Verticals wipe vertically with shorter duration
        for v in self.verticals:
            self.assertEqual(configs[v]["type"], "vertical_wipe")
            self.assertEqual(configs[v]["direction"], "DOWN")
            self.assertLessEqual(configs[v]["duration"], 1.2)
            self.assertEqual(configs[v]["start_offset"], 0.0)

        # Rings fade with staggered offset starting at 0.20
        for s in self.rings[0]:
            self.assertEqual(configs[s]["type"], "fade_in_out")
            self.assertAlmostEqual(configs[s]["start_offset"], 0.20, places=2)
        for s in self.rings[1]:
            self.assertAlmostEqual(configs[s]["start_offset"], 0.30, places=2)

    def test_get_max_transition_duration(self):
        configs = {
            "seg1": {"duration": 2.0, "start_offset": 0.0},
            "seg2": {"duration": 1.5, "start_offset": 1.0},  # end 2.5
            "seg3": {"duration": 1.0, "start_offset": 2.0},  # end 3.0
        }
        self.assertAlmostEqual(get_max_transition_duration(configs), 3.0)

    def test_select_stagger_pattern(self):
        # Drop impact -> SIMULTANEOUS
        ctx_drop = SimpleNamespace(is_drop_impact=True, energy=0.9, salience=0.9)
        self.assertEqual(select_stagger_pattern(ctx_drop), StaggerPattern.SIMULTANEOUS)

        # High energy -> SIMULTANEOUS
        ctx_high = SimpleNamespace(is_drop_impact=False, energy=0.92, salience=0.5)
        self.assertEqual(select_stagger_pattern(ctx_high), StaggerPattern.SIMULTANEOUS)

        # Rhythmic groove -> COHORT_COMPLEMENTARY
        ctx_rhythm = SimpleNamespace(is_drop_impact=False, energy=0.6, salience=0.7, is_rhythmic=True)
        self.assertEqual(select_stagger_pattern(ctx_rhythm), StaggerPattern.COHORT_COMPLEMENTARY)

        # Chill ambient -> CENTER_OUT
        ctx_chill = SimpleNamespace(is_drop_impact=False, energy=0.3, salience=0.2, is_rhythmic=False, scene="CHILL")
        self.assertEqual(select_stagger_pattern(ctx_chill), StaggerPattern.CENTER_OUT)

    def test_discover_segment_cohorts(self):
        segs = [
            SimpleNamespace(name="Segment v1", orientation="vertical"),
            SimpleNamespace(name="Segment v2", orientation="vertical"),
            SimpleNamespace(name="Segment h10", orientation="horizontal"),
            SimpleNamespace(name="Segment h11", orientation="horizontal"),
            SimpleNamespace(name="Segment h20", orientation="horizontal"),
        ]
        verts, rings = discover_segment_cohorts(segs)
        self.assertEqual(verts, ["Segment v1", "Segment v2"])
        self.assertEqual(len(rings), 2)
        self.assertEqual(rings[0], ["Segment h10", "Segment h11"])
        self.assertEqual(rings[1], ["Segment h20"])

    def test_discover_segment_cohorts_deterministic_shuffled_ordering(self):
        """Ring cohorts must be strictly ordered by ring level even if segments are shuffled."""
        segs = [
            SimpleNamespace(name="Segment h30", orientation="horizontal"),
            SimpleNamespace(name="Segment h11", orientation="horizontal"),
            SimpleNamespace(name="Segment h20", orientation="horizontal"),
            SimpleNamespace(name="Segment h10", orientation="horizontal"),
        ]
        _, rings = discover_segment_cohorts(segs)
        self.assertEqual(len(rings), 3)
        self.assertEqual(rings[0], ["Segment h10", "Segment h11"])  # h1
        self.assertEqual(rings[1], ["Segment h20"])                 # h2
        self.assertEqual(rings[2], ["Segment h30"])                 # h3

    def test_select_stagger_pattern_with_enum_scene(self):
        class MockSceneEnum:
            def __init__(self, val):
                self.value = val
                self.name = val

        ctx_enum = SimpleNamespace(
            is_drop_impact=False,
            energy=0.4,
            salience=0.3,
            is_rhythmic=False,
            scene=MockSceneEnum("DEEP_AMBIENT"),
        )
        self.assertEqual(select_stagger_pattern(ctx_enum), StaggerPattern.CENTER_OUT)


if __name__ == "__main__":
    unittest.main()
