"""
Unit tests for the Oracle Anticipation Flywheel AudioAnalyzer,
StructuralNoveltyDetector, and RhythmConfig.
"""
import unittest
import numpy as np
import time

from core.RhythmConfig import RhythmConfig
from core.StructuralNoveltyDetector import StructuralNoveltyDetector
from core.AudioAnalyzer import (
    AudioAnalyzer,
    FastTemplateBank,
    bpm_to_class,
    class_to_bpm_candidates,
    tempo_class_distance,
    harmonic_alignment,
    class_based_phase_sweep,
    evaluate_specific_bpms,
)
from core.AudioIngestion import AudioIngestion
from core.Listener import Listener


class TestRhythmConfig(unittest.TestCase):
    def test_default_config_values(self):
        cfg = RhythmConfig()
        self.assertAlmostEqual(cfg.high_confidence_threshold, 0.30)
        self.assertAlmostEqual(cfg.moderate_confidence_threshold, 0.15)
        self.assertAlmostEqual(cfg.high_snap_ratio, 0.50)
        self.assertAlmostEqual(cfg.moderate_snap_ratio, 0.15)
        self.assertAlmostEqual(cfg.sweep_interval, 0.2)
        self.assertAlmostEqual(cfg.bpm_min, 40.0)
        self.assertAlmostEqual(cfg.bpm_max, 220.0)
        self.assertAlmostEqual(cfg.song_novelty_asserved_th, 0.8)
        self.assertAlmostEqual(cfg.structural_cooldown_seconds, 20.0)


class TestStructuralNoveltyDetector(unittest.TestCase):
    def setUp(self):
        self.cfg = RhythmConfig()
        self.detector = StructuralNoveltyDetector(nb_fft_bands=8, config=self.cfg)

    def test_initial_state(self):
        self.assertFalse(self.detector.is_song_change)
        self.assertFalse(self.detector.is_verse_chorus_change)
        self.assertEqual(len(self.detector.stm_timbre), 8)
        self.assertEqual(len(self.detector.ltm_timbre), 8)

    def test_constant_input_stability(self):
        timbre = np.ones(8) / 8.0
        power = 50.0
        # Warm up STM and LTM filters past the LTM convergence window
        for i in range(4000):
            self.detector.update(
                current_timbre=timbre,
                current_power=power,
                current_time=i * (1.0 / 60.0),
                dt=1.0 / 60.0,
                fps_ratio=1.0
            )
        self.assertFalse(self.detector.is_song_change)
        self.assertAlmostEqual(self.detector.combined_novelty, 0.0, places=2)

    def test_silence_detection(self):
        dt = 1.0 / 60.0
        timbre = np.zeros(8)
        power = 1.0  # below silence threshold 5.0
        
        song_change_fired = False
        # Feed enough silence frames to exceed threshold (1.5s * 60 = 90 frames)
        for i in range(120):
            current_time = i * dt
            self.detector.update(
                current_timbre=timbre,
                current_power=power,
                current_time=current_time,
                dt=dt,
                fps_ratio=1.0
            )
            if self.detector.is_song_change:
                song_change_fired = True
                
        self.assertTrue(song_change_fired)
        self.assertEqual(len(self.detector.song_changes_times), 1)


class TestHarmonicMath(unittest.TestCase):
    def test_bpm_to_class(self):
        self.assertAlmostEqual(bpm_to_class(60.0), 0.0, places=5)
        self.assertAlmostEqual(bpm_to_class(120.0), 0.0, places=5)
        self.assertAlmostEqual(bpm_to_class(240.0), 0.0, places=5)
        self.assertAlmostEqual(bpm_to_class(90.0), float(np.log2(1.5)), places=5)

    def test_class_to_bpm_candidates(self):
        candidates = class_to_bpm_candidates(0.0)
        expected = [30.0, 45.0, 60.0, 90.0, 120.0]
        for c, e in zip(candidates, expected):
            self.assertAlmostEqual(c, e, places=4)

    def test_tempo_class_distance(self):
        self.assertAlmostEqual(tempo_class_distance(0.1, 0.2), 0.1, places=5)
        self.assertAlmostEqual(tempo_class_distance(0.05, 0.95), 0.1, places=5)

    def test_harmonic_alignment(self):
        min_d, aligned = harmonic_alignment(0.0, 0.0)
        self.assertAlmostEqual(min_d, 0.0, places=5)
        self.assertAlmostEqual(aligned, 0.0, places=5)
        
        fifth_class = float(np.log2(1.5))
        min_d, aligned = harmonic_alignment(fifth_class, 0.0)
        self.assertAlmostEqual(min_d, 0.0, places=5)


class TestTemplateBank(unittest.TestCase):
    def test_template_bank_generation(self):
        bank = FastTemplateBank(btrack_fps=60.0, odf_size=300)
        t_120 = bank.get_template(120.0)
        self.assertEqual(t_120.shape, (30, 300))
        
        for row in t_120:
            self.assertAlmostEqual(float(np.mean(row)), 0.0, places=3)
            self.assertAlmostEqual(float(np.sum(row**2)), 1.0, places=3)


class TestAudioAnalyzerIntegration(unittest.TestCase):
    def setUp(self):
        self.infos = {
            "startServer": False,
            "useMicrophone": False,
            "HARDWARE_MODE": "simulation",
            "onRaspberry": False,
            "fakeDelay": 5.0,
            "latency": 0.0,
        }
        self.listener = Listener(self.infos)
        self.analyzer = self.listener.analyzer

    def test_initialization(self):
        self.assertEqual(self.analyzer.odf_buffer_size, 300)
        self.assertAlmostEqual(self.analyzer.bpm, 120.0)
        self.assertEqual(self.analyzer.beat_count, 0)
        self.assertAlmostEqual(self.analyzer.speaker_phase, 0.0)
        self.assertFalse(self.listener.is_beat)
        self.assertIsNotNone(self.analyzer.novelty_detector)
        self.assertIsNotNone(self.analyzer.config)

    def test_delegation_properties(self):
        self.assertFalse(self.analyzer.is_song_change)
        self.assertFalse(self.analyzer.is_verse_chorus_change)
        self.assertAlmostEqual(self.analyzer.asserved_novelty, 0.0)
        self.assertEqual(self.analyzer.silence_frames, 0)

    def test_synthetic_pulse_tracking(self):
        fps = 60.0
        dt = 1.0 / fps
        fps_ratio = 1.0
        
        for frame in range(400):
            current_time = frame * dt
            if frame % 30 == 0:
                self.listener.ingestion.fft_band_values = np.array([200.0, 150.0, 10.0, 5.0, 0.0, 0.0, 0.0, 0.0])
            else:
                self.listener.ingestion.fft_band_values = np.array([2.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
                
            self.analyzer.detect_band_peaks(current_time, dt, fps_ratio)
            
        self.assertGreater(self.analyzer.confidence_score, 0.20)
        self.assertAlmostEqual(self.analyzer.bpm, 120.0, delta=5.0)
        self.assertGreater(self.analyzer.beat_count, 5)

    def test_dropped_beat_detection(self):
        fps = 60.0
        dt = 1.0 / fps
        fps_ratio = 1.0
        
        for frame in range(300):
            current_time = frame * dt
            if frame % 30 == 0:
                self.listener.ingestion.fft_band_values = np.array([200.0, 150.0, 10.0, 5.0, 0.0, 0.0, 0.0, 0.0])
            else:
                self.listener.ingestion.fft_band_values = np.array([2.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
            self.analyzer.detect_band_peaks(current_time, dt, fps_ratio)

        initial_beats = self.analyzer.beat_count
        for frame in range(300, 420):
            current_time = frame * dt
            self.listener.ingestion.fft_band_values = np.zeros(8)
            self.analyzer.detect_band_peaks(current_time, dt, fps_ratio)
            
        self.assertGreater(self.analyzer.beat_count, initial_beats)


if __name__ == '__main__':
    unittest.main()
