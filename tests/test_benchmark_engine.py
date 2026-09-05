"""
tests/test_benchmark_engine.py - Verifies the immutable benchmark evaluation engine.
"""

import os
import unittest
import numpy as np

from core.AudioAnalyzer import AudioAnalyzer
from benchmarks.ground_truth.synthetic.generator import generate_click_120bpm
from benchmarks.engine.evaluator import run_benchmark_on_track, compute_scorecard
from benchmarks.engine.episode_slicer import extract_failure_episodes


class TestBenchmarkEngine(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "tmp_benchmark_test"))
        os.makedirs(cls.test_dir, exist_ok=True)
        cls.wav_path, cls.beats_path = generate_click_120bpm(cls.test_dir, duration=10.0)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_dir):
            import shutil
            shutil.rmtree(cls.test_dir, ignore_errors=True)

    def test_run_benchmark_on_click_track(self):
        result = run_benchmark_on_track(
            analyzer_class=AudioAnalyzer,
            audio_path=self.wav_path,
            beats_path=self.beats_path,
            fps=60.0
        )
        self.assertIn("scorecard", result)
        self.assertIn("true_beats", result)
        self.assertIn("est_beats", result)
        self.assertIn("telemetry", result)

        sc = result["scorecard"]
        self.assertIn("f1_50ms", sc)
        self.assertIn("f1_70ms", sc)
        self.assertIn("cmlt", sc)
        self.assertIn("amlt", sc)
        self.assertIn("phase_jitter_ms", sc)
        self.assertIn("avg_frame_time_ms", sc)

        # Ensure frame computation time is well under the 16.6ms real-time limit
        self.assertLess(sc["avg_frame_time_ms"], 5.0)

    def test_compute_scorecard_perfect_match(self):
        beats = np.arange(0.5, 10.0, 0.5)
        # Perfectly identical beats
        sc = compute_scorecard(beats, beats, [0.001] * len(beats))
        self.assertEqual(sc["f1_50ms"], 1.0)
        self.assertEqual(sc["f1_70ms"], 1.0)
        self.assertEqual(sc["cmlt"], 1.0)
        self.assertEqual(sc["amlt"], 1.0)
        self.assertEqual(sc["mean_phase_bias_ms"], 0.0)
        self.assertEqual(sc["phase_jitter_ms"], 0.0)

    def test_episode_slicer_detects_phase_inversion(self):
        true_beats = np.arange(0.5, 10.0, 0.5)
        # Shift estimated beats by half a period (upbeat: +0.25s)
        est_beats = true_beats + 0.25
        dummy_telemetry = [{"time": t, "bpm": 120.0, "confidence": 0.8, "custom_flux": 1.0, "beat_tag": "Bass/Kick"} for t in np.arange(0, 10, 0.1)]
        scorecard = {
            "upbeat_gap": 0.50,
            "phase_jitter_ms": 2.0,
            "mean_phase_bias_ms": 250.0,
        }

        episodes = extract_failure_episodes(
            song_name="Test_Inversion_Track",
            true_beats=true_beats,
            est_beats=est_beats,
            telemetry=dummy_telemetry,
            scorecard=scorecard
        )
        self.assertGreater(len(episodes), 0)
        self.assertEqual(episodes[0]["failure_type"], "PHASE_INVERSION_UPBEAT")

    def test_discover_neural_and_synthetic_tracks(self):
        from benchmarks.run_benchmark import discover_tracks
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        
        synth_tracks = discover_tracks("synthetic", repo_root)
        self.assertGreater(len(synth_tracks), 0)
        
        neural_tracks = discover_tracks("neural", repo_root)
        self.assertGreater(len(neural_tracks), 0)
        for name, audio_p, beats_p in neural_tracks:
            self.assertTrue(os.path.exists(audio_p))
            self.assertTrue(os.path.exists(beats_p))

    def test_academic_loader_ballroom_annotations(self):
        from benchmarks.ground_truth.academic.loader import load_academic_tracks
        tracks = load_academic_tracks("ballroom", limit=5, require_audio=False)
        self.assertEqual(len(tracks), 5)
        for track_id, audio_path, beats in tracks:
            self.assertGreater(len(beats), 0)
            # Beats should be monotonically increasing
            self.assertTrue(np.all(np.diff(beats) > 0))


if __name__ == "__main__":
    unittest.main()
