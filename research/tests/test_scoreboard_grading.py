"""Tests for the grading functions of the scoreboard (research/scoreboard/grade.py) on made-up signals."""
import unittest

import numpy as np

from research.scoreboard import grade

FPS = 60.0


class TestEvents(unittest.TestCase):
    def test_perfect_shifted_and_missing(self):
        ref = np.arange(1.0, 21.0, 0.5)
        self.assertEqual(grade.event_score(ref, ref, 0.05)["f1"], 1.0)
        late = grade.event_score(ref + 0.02, ref, 0.05)
        self.assertEqual(late["f1"], 1.0)
        self.assertAlmostEqual(late["offset_ms"], 20.0, places=3)
        self.assertEqual(grade.event_score(ref + 0.1, ref, 0.05)["f1"], 0.0)
        half = grade.event_score(ref[::2], ref, 0.05)
        self.assertAlmostEqual(half["found"], 0.5)
        self.assertAlmostEqual(half["right"], 1.0)

    def test_one_estimate_cannot_serve_two_truth_events(self):
        res = grade.event_score([1.00], [0.98, 1.02], 0.05)
        self.assertAlmostEqual(res["found"], 0.5)

    def test_ungradeable_truth_is_ignored_not_punished(self):
        ref = [1.0, 2.0, 3.0, 4.0]
        res = grade.event_score([1.0, 2.0, 3.0, 4.0, 9.0], ref, 0.05, gradeable=[True, True, False, False])
        self.assertEqual(res["n_truth"], 2)
        self.assertAlmostEqual(res["found"], 1.0)
        self.assertAlmostEqual(res["right"], 2 / 3)      # the hit at 9.0 is the only false alarm

    def test_rising_edges_merge_held_frames(self):
        v = np.zeros(120, dtype=np.float32)
        v[30:33] = 1.0
        v[90] = 0.4
        v[10] = np.nan
        np.testing.assert_allclose(grade.rising_edges(v, FPS), [0.5, 1.5])


class TestStates(unittest.TestCase):
    def setUp(self):
        self.ref = grade.regions_to_mask([(10.0, 20.0)], int(40 * FPS), FPS)

    def test_perfect_and_stuck_signals(self):
        self.assertEqual(grade.state_score(self.ref, self.ref, FPS)["balanced"], 1.0)
        stuck_on = grade.state_score(np.ones_like(self.ref), self.ref, FPS)
        stuck_off = grade.state_score(np.zeros_like(self.ref), self.ref, FPS)
        self.assertAlmostEqual(stuck_on["balanced"], 0.5)
        self.assertAlmostEqual(stuck_off["balanced"], 0.5)

    def test_late_signal_reports_its_delay(self):
        est = grade.regions_to_mask([(11.0, 21.0)], len(self.ref), FPS)
        res = grade.state_score(est, self.ref, FPS)
        self.assertAlmostEqual(res["edge_delay_s"], 1.0, places=2)
        self.assertAlmostEqual(res["when_on"], 0.9, places=2)

    def test_truth_without_any_stretch_gives_no_balanced_score(self):
        res = grade.state_score(np.zeros(600, dtype=bool), np.zeros(600, dtype=bool), FPS)
        self.assertTrue(np.isnan(res["balanced"]))
        self.assertEqual(res["when_off"], 1.0)


class TestLevelsAndTempo(unittest.TestCase):
    def test_follow_finds_shape_and_lag_whatever_the_units(self):
        t20 = np.arange(0, 60, 1 / 20.0)
        truth_db = -30.0 + 20.0 * np.sin(2 * np.pi * t20 / 7.0) * np.sin(2 * np.pi * t20 / 1.3)
        t60 = np.arange(0, 60, 1 / FPS)
        live = 0.5 + 0.4 * np.sin(2 * np.pi * (t60 - 0.2) / 7.0) * np.sin(2 * np.pi * (t60 - 0.2) / 1.3)
        res = grade.follow_score(live, FPS, truth_db, 20.0)
        self.assertGreater(res["corr"], 0.97)
        self.assertAlmostEqual(res["lag_ms"], 200.0, delta=51.0)
        rng = np.random.default_rng(0)
        self.assertLess(abs(grade.follow_score(rng.standard_normal(len(t60)), FPS, truth_db, 20.0)["corr"]), 0.2)

    def test_tempo_levels(self):
        beats = np.arange(1.0, 30.0, 0.5)
        ref = np.full(len(beats), 120.0)
        n = int(31 * FPS)
        self.assertEqual(grade.tempo_score(np.full(n, 121.0), FPS, beats, ref)["right"], 1.0)
        double = grade.tempo_score(np.full(n, 240.0), FPS, beats, ref)
        self.assertEqual((double["right"], double["double"]), (0.0, 1.0))
        self.assertEqual(grade.tempo_score(np.full(n, 60.0), FPS, beats, ref)["half"], 1.0)

    def test_equal_score_and_peaks(self):
        self.assertAlmostEqual(grade.equal_score(np.array([1, 2, 3, np.nan]), np.array([1, 2, 4, 4])), 2 / 3)
        v = np.zeros(600)
        v[30::30] = 1.0                                   # a hit every half second...
        v[150] = 0.1                                      # ...one of them far too weak to count
        expected = [k * 0.5 for k in range(1, 20) if k != 5]
        np.testing.assert_allclose(grade.peak_times(v, FPS, rel=0.3), expected)


if __name__ == "__main__":
    unittest.main()
