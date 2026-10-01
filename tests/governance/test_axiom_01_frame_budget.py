"""
tests/governance/test_axiom_01_frame_budget.py
Enforces AXIOM-01: Real-Time Frame Budget & Execution Pacing
- 30.0 FPS visual target
- <= 20.0 ms compute threshold
- app_config.json configuration parity
"""
import json
import os
import unittest


class TestAxiom01FrameBudget(unittest.TestCase):
    def setUp(self):
        self.repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.config_path = os.path.join(self.repo_root, "config", "app_config.json")

    def test_app_config_frame_budget_constants(self):
        """Verify app_config.json explicitly sets target_fps=30 and alert_threshold_ms=20.0."""
        self.assertTrue(os.path.isfile(self.config_path), f"Missing config: {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        profiler_cfg = cfg.get("profiler", {})
        target_fps = profiler_cfg.get("target_fps")
        alert_ms = profiler_cfg.get("alert_threshold_ms")

        self.assertEqual(
            target_fps, 30,
            f"AXIOM-01 violation: profiler.target_fps must be 30, found {target_fps}"
        )
        self.assertAlmostEqual(
            alert_ms, 20.0, places=1,
            msg=f"AXIOM-01 violation: alert_threshold_ms must be 20.0, found {alert_ms}"
        )

        # Mathematical check: Frame budget is 33.33ms, margin must be >= 13.33ms (40%)
        frame_period_ms = 1000.0 / target_fps
        margin_ms = frame_period_ms - alert_ms
        margin_ratio = margin_ms / frame_period_ms

        self.assertAlmostEqual(frame_period_ms, 33.333, places=2)
        self.assertGreaterEqual(
            margin_ratio, 0.40,
            f"AXIOM-01 violation: Headroom margin {margin_ratio*100:.1f}% is below required 40%"
        )


if __name__ == "__main__":
    unittest.main()
