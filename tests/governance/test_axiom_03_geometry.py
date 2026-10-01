"""
tests/governance/test_axiom_03_geometry.py
Enforces AXIOM-03: Physical Chandelier Geometry & The Vertical Invariant
- Exact LED pixel counts (1,304 full, 249 small)
- Vertical strips wired bottom-up (step.y = -1 or vertical_up)
- Dynamic path resolution via Configuration_manager
"""
import json
import os
import unittest

from config.Configuration_manager import (
    resolve_segments_file_path,
    resolve_configurations_file_path,
)


class TestAxiom03Geometry(unittest.TestCase):
    def setUp(self):
        self.repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    def test_full_profile_geometry_and_counts(self):
        """Verify full profile has 1,304 LEDs across 11 segments on 2 channels."""
        path = resolve_segments_file_path({"hardware_profile": "full"})
        self.assertTrue(os.path.isfile(path))
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        segs_1 = data.get("segs_1", [])
        segs_2 = data.get("segs_2", [])
        count_1 = sum(s["size"] for s in segs_1)
        count_2 = sum(s["size"] for s in segs_2)

        self.assertEqual(count_1, 785, f"Channel 1 must have 785 LEDs, got {count_1}")
        self.assertEqual(count_2, 519, f"Channel 2 must have 519 LEDs, got {count_2}")
        self.assertEqual(count_1 + count_2, 1304, "Total LEDs must equal 1,304")
        self.assertEqual(len(segs_1) + len(segs_2), 11, "Total segments must equal 11")

    def test_small_profile_geometry_and_counts(self):
        """Verify small profile has 249 LEDs across 3 segments on 1 channel."""
        path = resolve_segments_file_path({"hardware_profile": "small"})
        self.assertTrue(os.path.isfile(path))
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        segs_1 = data.get("segs_1", [])
        count_1 = sum(s["size"] for s in segs_1)

        self.assertEqual(count_1, 249, f"Channel 1 must have 249 LEDs, got {count_1}")
        self.assertEqual(len(segs_1), 3, "Total segments must equal 3")

    def test_vertical_invariant_bottom_up(self):
        """Verify vertical strips are wired bottom-to-top (vertical_up / step.y = -1)."""
        for profile in ["full", "small"]:
            path = resolve_segments_file_path({"hardware_profile": profile})
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for key, val in data.items():
                if key.startswith("segs_") and isinstance(val, list):
                    for seg in val:
                        orientation = seg.get("orientation", "")
                        step = seg.get("step", {})
                        if "vertical" in orientation:
                            self.assertIn(
                                orientation, ["vertical", "vertical_up"],
                                f"Segment {seg.get('name')} orientation invalid: {orientation}"
                            )
                            # step.y must be -1 for physical ascending wiring
                            self.assertEqual(
                                step.get("y"), -1,
                                f"AXIOM-03 violation in {profile}: Segment {seg.get('name')} step.y must be -1"
                            )


if __name__ == "__main__":
    unittest.main()
