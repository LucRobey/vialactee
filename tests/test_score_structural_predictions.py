"""
tests/test_score_structural_predictions.py - Unit tests for research/benchmarks/score_structural_predictions.py.
"""

from __future__ import annotations
import os
import sys
import unittest

# Ensure repository root is on sys.path
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from research.benchmarks.score_structural_predictions import (
    normalize_track_predictions,
    evaluate_boundaries,
    evaluate_drops,
    evaluate_steady_false_alarms,
    score_structural_predictions,
)


class TestScoreStructuralPredictions(unittest.TestCase):

    def test_normalize_track_predictions(self):
        # 1. List of floats
        res1 = normalize_track_predictions([10.5, 45.0, 95.2])
        self.assertEqual(res1["boundaries"], [10.5, 45.0, 95.2])
        self.assertEqual(res1["drops"], [])

        # 2. List of dicts with types
        raw2 = [
            {"time_sec": 45.0, "type": "BUILDUP_OR_RISER"},
            {"time_sec": 53.0, "type": "CLIMAX_OR_DROP", "announced_at_sec": 48.0},
            {"time_sec": 95.0, "type": "SECTION_CHANGE"},
        ]
        res2 = normalize_track_predictions(raw2)
        self.assertEqual(res2["boundaries"], [95.0])
        self.assertEqual(len(res2["drops"]), 1)
        self.assertEqual(res2["drops"][0]["time_sec"], 53.0)
        self.assertEqual(res2["drops"][0]["announced_at_sec"], 48.0)

        # 3. Dict with "events" key (Ground truth schema format)
        raw3 = {
            "duration_sec": 120.0,
            "events": [
                {"time_sec": 20.0, "type": "BREAKDOWN_OR_SOLO"},
                {"time_sec": 60.0, "type": "CLIMAX_OR_DROP", "lead_time_sec": 3.5},
            ]
        }
        res3 = normalize_track_predictions(raw3)
        self.assertEqual(res3["boundaries"], [20.0])
        self.assertEqual(len(res3["drops"]), 1)
        self.assertEqual(res3["drops"][0]["lead_time_sec"], 3.5)

    def test_evaluate_boundaries_perfect_match(self):
        gt = [10.0, 50.0, 90.0]
        pred = [10.0, 50.0, 90.0]
        res = evaluate_boundaries(gt, pred, tolerance=0.5)
        self.assertEqual(res["tp"], 3)
        self.assertEqual(res["fp"], 0)
        self.assertEqual(res["fn"], 0)
        self.assertEqual(res["precision"], 1.0)
        self.assertEqual(res["recall"], 1.0)
        self.assertEqual(res["f1"], 1.0)
        self.assertAlmostEqual(res["mean_timing_error_ms"], 0.0)

    def test_evaluate_boundaries_with_jitter_and_tolerances(self):
        gt = [10.0, 50.0]
        # pred[0] is 150ms late (inside 0.5s tolerance)
        # pred[1] is 600ms late (outside 0.5s tolerance)
        pred = [10.150, 50.600]
        res = evaluate_boundaries(gt, pred, tolerance=0.5)
        self.assertEqual(res["tp"], 1)  # only 10.150 matched
        self.assertEqual(res["fp"], 1)  # 50.600 is false alarm
        self.assertEqual(res["fn"], 1)  # 50.0 missed
        self.assertAlmostEqual(res["precision"], 0.5)
        self.assertAlmostEqual(res["recall"], 0.5)
        self.assertAlmostEqual(res["f1"], 0.5)
        self.assertAlmostEqual(res["mean_timing_error_ms"], 150.0, places=1)

    def test_evaluate_boundaries_empty(self):
        # Both empty -> perfect precision/recall (no errors)
        res = evaluate_boundaries([], [], tolerance=0.5)
        self.assertEqual(res["tp"], 0)
        self.assertEqual(res["fp"], 0)
        self.assertEqual(res["fn"], 0)
        self.assertEqual(res["f1"], 1.0)

        # Ground truth has events, prediction empty -> recall=0
        res2 = evaluate_boundaries([10.0], [], tolerance=0.5)
        self.assertEqual(res2["tp"], 0)
        self.assertEqual(res2["fn"], 1)
        self.assertEqual(res2["recall"], 0.0)
        self.assertEqual(res2["f1"], 0.0)

    def test_evaluate_drops_metrics(self):
        gt_events = [
            {"id": "evt_001", "type": "BUILDUP_OR_RISER", "time_sec": 45.0, "pair_id": "drop_1"},
            {"id": "evt_002", "type": "CLIMAX_OR_DROP", "time_sec": 53.0, "pair_id": "drop_1"},
        ]
        # Predicted drop at 53.020 (20ms jitter) announced at 49.0s (4.0s lead time)
        pred_drops = [
            {"time_sec": 53.020, "announced_at_sec": 49.0}
        ]
        res = evaluate_drops(gt_events, pred_drops, tolerance=1.0)
        self.assertEqual(res["tp"], 1)
        self.assertEqual(res["fp"], 0)
        self.assertEqual(res["fn"], 0)
        self.assertEqual(res["f1"], 1.0)
        self.assertAlmostEqual(res["mean_jitter_ms"], 20.0, places=1)
        self.assertAlmostEqual(res["mean_lead_time_sec"], 4.0, places=1)
        # Buildup duration is 53.0 - 45.0 = 8.0s; lead time 4.0s -> coverage = 4/8 = 50%
        self.assertAlmostEqual(res["mean_buildup_coverage"], 0.50, places=2)

    def test_evaluate_steady_false_alarms(self):
        dur = 100.0
        # Single GT event at 50.0s with tolerance 1.0s -> exclusion window [49.0, 51.0]
        # Steady duration = 100.0 - 2.0 = 98.0s
        gt_events = [{"time_sec": 50.0, "type": "SECTION_CHANGE"}]

        # Predictions:
        # 1. 50.2s -> inside exclusion window (not a steady false alarm)
        # 2. 20.0s -> in steady window [0, 49.0] (false alarm 1)
        # 3. 80.0s -> in steady window [51.0, 100.0] (false alarm 2)
        preds = [50.2, 20.0, 80.0]
        res = evaluate_steady_false_alarms(gt_events, preds, total_duration_sec=dur, tolerance=1.0)

        self.assertAlmostEqual(res["steady_duration_sec"], 98.0, places=1)
        self.assertEqual(res["false_alarm_count"], 2)
        # FAR = 2 alarms / 98.0s * 60 = 1.224 alarms/min
        self.assertAlmostEqual(res["false_alarm_rate_per_min"], 2.0 / 98.0 * 60.0, places=2)

    def test_score_structural_predictions_pipeline(self):
        gt = {
            "schema_version": "1.0",
            "annotator": "test",
            "tracks": {
                "TrackA": {
                    "duration_sec": 120.0,
                    "status": "reviewed",
                    "has_climaxes": True,
                    "events": [
                        {"id": "evt_001", "type": "BUILDUP_OR_RISER", "time_sec": 20.0, "pair_id": "p1"},
                        {"id": "evt_002", "type": "CLIMAX_OR_DROP", "time_sec": 25.0, "pair_id": "p1"},
                        {"id": "evt_003", "type": "SECTION_CHANGE", "time_sec": 60.0},
                    ]
                }
            }
        }
        pred = {
            "TrackA": {
                "boundaries": [60.1],  # boundary hit (100ms error)
                "drops": [{"time_sec": 25.05, "announced_at_sec": 21.0}],  # drop hit (50ms error, 4s lead)
            }
        }

        res = score_structural_predictions(gt, pred, tolerance=0.5, drop_tolerance=1.0)
        self.assertIn("TrackA", res["tracks"])
        tA = res["tracks"]["TrackA"]
        self.assertEqual(tA["boundaries"]["tp"], 1)
        self.assertEqual(tA["boundaries"]["f1"], 1.0)
        self.assertEqual(tA["drops"]["tp"], 1)
        self.assertEqual(tA["drops"]["f1"], 1.0)
        self.assertAlmostEqual(tA["drops"]["mean_jitter_ms"], 50.0, places=1)

        ov = res["overall"]
        self.assertEqual(ov["boundary_micro_f1"], 1.0)
        self.assertEqual(ov["drop_f1"], 1.0)
        self.assertAlmostEqual(ov["drop_mean_jitter_ms"], 50.0, places=1)

    def test_evaluate_boundaries_bipartite_closest_match(self):
        # GT at 10.0s. Pred 1 at 9.6s (400ms error). Pred 2 at 10.01s (10ms error).
        # Bipartite min-distance matching must match 10.01s with 10ms error, not 9.6s!
        gt = [10.0]
        pred = [9.6, 10.01]
        res = evaluate_boundaries(gt, pred, tolerance=0.5)
        self.assertEqual(res["tp"], 1)
        self.assertEqual(res["fp"], 1)
        self.assertAlmostEqual(res["mean_timing_error_ms"], 10.0, places=1)

    def test_score_with_false_alarm_drops_on_no_climax_track(self):
        gt = {
            "schema_version": "1.0",
            "tracks": {
                "TrackNoClimax": {
                    "duration_sec": 100.0,
                    "has_climaxes": False,
                    "status": "reviewed",
                    "events": []
                }
            }
        }
        pred = {
            "TrackNoClimax": {
                "boundaries": [],
                "drops": [{"time_sec": 50.0}]  # False positive drop!
            }
        }
        res = score_structural_predictions(gt, pred)
        ov = res["overall"]
        # FP on a no-climax track must be counted in total drop false positives!
        self.assertEqual(ov["drop_precision"], 0.0)
        self.assertEqual(ov["total_steady_false_alarms"], 1)

    def test_unreviewed_track_reporting(self):
        from research.benchmarks.score_structural_predictions import print_scorecard
        gt = {
            "schema_version": "1.0",
            "tracks": {
                "UnreviewedTrack": {
                    "duration_sec": 100.0,
                    "has_climaxes": True,
                    "status": "unreviewed",
                    "events": []
                }
            }
        }
        res = score_structural_predictions(gt, {"UnreviewedTrack": {}})
        self.assertEqual(res["tracks"]["UnreviewedTrack"]["status"], "unreviewed")
        self.assertEqual(res["tracks"]["UnreviewedTrack"]["num_gt_boundaries"], 0)
        self.assertEqual(res["tracks"]["UnreviewedTrack"]["num_gt_drops"], 0)
        # Verify print_scorecard does not raise
        print_scorecard(res)


if __name__ == "__main__":
    unittest.main()
