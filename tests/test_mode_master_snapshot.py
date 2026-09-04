"""
Unit tests for core/Mode_master.py.
Verifies configuration loading, state snapshot serialization,
segment reporting, transition normalization, and settings mapping.
"""
import unittest
import numpy as np
from unittest.mock import MagicMock

from core.Mode_master import Mode_master


class TestModeMasterSnapshot(unittest.TestCase):
    def setUp(self):
        self.mock_listener = MagicMock()
        self.mock_listener.luminosite = 0.8
        self.mock_listener.sensi = 0.5
        self.mock_listener.smoothed_fft_band_values = np.zeros(8)
        self.mock_listener.asserved_fft_band = np.zeros(8)
        self.mock_listener._delayed_asserved_fft_band = np.zeros(8)
        self.mock_listener.nb_of_fft_band = 8
        self.mock_listener.asserved_total_power = 0.0

        # Two numpy arrays matching segs_1 (785) and segs_2 (519) LED strip sizes
        self.leds1 = np.zeros((785, 3), dtype=np.int32)
        self.leds2 = np.zeros((519, 3), dtype=np.int32)

        self.infos = {
            "onRaspberry": False,
            "HARDWARE_MODE": "simulation",
            "printCpuFpsInfo": False,
            "auto_transition_time": 25.0,
        }

        self.mode_master = Mode_master(self.mock_listener, self.infos, self.leds1, self.leds2)

    def test_load_configurations(self):
        self.assertIsInstance(self.mode_master.configurations, dict)
        self.assertGreater(len(self.mode_master.playlists), 0)
        self.assertEqual(len(self.mode_master.blocked_playlists), len(self.mode_master.playlists))

    def test_get_state_snapshot_schema(self):
        snapshot = self.mode_master.get_state_snapshot()
        self.assertIsInstance(snapshot, dict)

        required_keys = [
            "activePlaylist",
            "enabledPlaylists",
            "activeConfiguration",
            "queuedConfiguration",
            "selectedTransition",
            "transitionLocked",
            "transitionState",
            "transitionProgress",
            "luminosity",
            "sensibility",
            "autoTransitionTime",
            "playlists",
            "availableModes",
            "segments",
            "modeSettingsCatalog",
            "modeSettings",
            "system",
        ]
        for key in required_keys:
            self.assertIn(key, snapshot, f"Snapshot missing required key: {key}")

        # Numerical bounds
        self.assertEqual(snapshot["luminosity"], 80)
        self.assertEqual(snapshot["sensibility"], 50)
        self.assertEqual(snapshot["autoTransitionTime"], 25)

    def test_segments_in_snapshot(self):
        snapshot = self.mode_master.get_state_snapshot()
        segments = snapshot["segments"]
        self.assertEqual(len(segments), 11)

        for seg in segments:
            self.assertIn("id", seg)
            self.assertIn("name", seg)
            self.assertIn("mode", seg)
            self.assertIn("direction", seg)
            self.assertIn("blocked", seg)
            self.assertIn("inTransition", seg)
            self.assertIn(seg["direction"], ["UP", "DOWN"])
            self.assertIsInstance(seg["blocked"], bool)

    def test_normalize_transition(self):
        self.assertEqual(
            self.mode_master._normalize_transition("CUT"),
            {"type": "explosion", "duration": 0.0}
        )
        self.assertEqual(
            self.mode_master._normalize_transition("CROSSFADE"),
            {"type": "global_change", "duration": 3.0}
        )
        self.assertEqual(
            self.mode_master._normalize_transition("FADE IN/OUT"),
            {"type": "fade_in_out", "duration": 2.0}
        )
        # Unknown fallback
        self.assertEqual(
            self.mode_master._normalize_transition("CUSTOM_RANDOM"),
            {"type": "fade_in_out", "duration": 2.0}
        )

    def test_segment_name_from_id(self):
        self.assertEqual(self.mode_master._segment_name_from_id("v4"), "Segment v4")
        self.assertEqual(self.mode_master._segment_name_from_id("h00"), "Segment h00")
        self.assertIsNone(self.mode_master._segment_name_from_id(""))
        self.assertIsNone(self.mode_master._segment_name_from_id(None))


if __name__ == '__main__':
    unittest.main()
