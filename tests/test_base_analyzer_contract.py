"""
tests/test_base_analyzer_contract.py - Verifies the BaseAudioAnalyzer contract.
"""

import unittest
import numpy as np
from core.BaseAudioAnalyzer import BaseAudioAnalyzer
from core.AudioAnalyzer import AudioAnalyzer
from core.AudioIngestion import AudioIngestion
from core.RhythmConfig import RhythmConfig


class DummyMinimalAnalyzer(BaseAudioAnalyzer):
    """A minimal model that only implements the required abstract methods."""

    def __init__(self, ingestion, infos, config=None):
        super().__init__(ingestion, infos, config)
        self._phase = 0.0

    def update(self, current_time: float, dt: float, fps_ratio: float) -> None:
        self._phase = (self._phase + (self.bpm / 60.0) * dt) % 1.0

    def reset(self) -> None:
        self._phase = 0.0

    @property
    def beat_phase(self) -> float:
        return self._phase


class TestBaseAudioAnalyzerContract(unittest.TestCase):

    def setUp(self):
        self.infos = {
            "startServer": False,
            "useMicrophone": False,
            "HARDWARE_MODE": "simulation",
            "onRaspberry": False,
            "fakeDelay": 5.0,
            "latency": 0.0,
        }
        self.ingestion = AudioIngestion(self.infos)

    def test_production_analyzer_inherits_and_conforms(self):
        analyzer = AudioAnalyzer(self.ingestion, self.infos)
        self.assertIsInstance(analyzer, BaseAudioAnalyzer)

        # Core execution
        self.assertEqual(analyzer.lookahead_seconds, 5.0)
        self.assertEqual(analyzer.hardware_latency, 0.0)

        # Core rhythm
        self.assertEqual(analyzer.bpm, 120.0)
        self.assertEqual(analyzer.beat_phase, 0.0)
        self.assertFalse(analyzer.is_beat)
        self.assertFalse(analyzer.is_real_beat)
        self.assertEqual(analyzer.beat_count, 0)
        self.assertIsInstance(analyzer.flywheel_status, str)

        # Telemetry & Metadata
        telemetry = analyzer.capture_frame_telemetry()
        self.assertIn("bpm", telemetry)
        self.assertIn("beat_phase", telemetry)
        self.assertIn("confidence", telemetry)
        self.assertIn("status", telemetry)

        meta = analyzer.get_model_metadata()
        self.assertEqual(meta["model_class"], "AudioAnalyzer")
        self.assertIn("config", meta)

    def test_minimal_subclass_defaults(self):
        """Ensures an experimental model only needs 3 methods to be fully compliant."""
        minimal = DummyMinimalAnalyzer(self.ingestion, self.infos)
        self.assertIsInstance(minimal, BaseAudioAnalyzer)

        # Defaults for non-implemented domains
        self.assertEqual(minimal.bpm, 120.0)
        self.assertFalse(minimal.is_beat)
        self.assertFalse(minimal.is_real_beat)
        self.assertFalse(minimal.is_dropped_beat)
        self.assertFalse(minimal.is_downbeat)
        self.assertEqual(minimal.time_signature, (4, 4))
        self.assertEqual(minimal.current_beat_tag, "Bass/Kick")
        self.assertFalse(minimal.vocals_present)
        self.assertFalse(minimal.is_song_change)
        self.assertFalse(minimal.is_verse_chorus_change)
        self.assertEqual(minimal.asserved_novelty, 0.0)
        self.assertEqual(minimal.combined_novelty, 0.0)

        # Run update and reset
        minimal.update(current_time=1.0, dt=1.0 / 60.0, fps_ratio=1.0)
        self.assertGreater(minimal.beat_phase, 0.0)
        minimal.reset()
        self.assertEqual(minimal.beat_phase, 0.0)

        # Telemetry works out of the box
        telem = minimal.capture_frame_telemetry()
        self.assertIn("bpm", telem)
        self.assertIn("beat_phase", telem)


if __name__ == "__main__":
    unittest.main()
