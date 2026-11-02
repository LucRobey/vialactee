"""
tests/test_udp_sender_throttling.py - Verifies UDP Sender rate limiting & heartbeat.
"""
import unittest
from unittest.mock import MagicMock, patch
import json
import time

from hardware.Udp_Sender import Udp_Sender, SEGMENT_METADATA_PORT


class TestUdpSenderThrottling(unittest.TestCase):
    def setUp(self):
        self.sender = Udp_Sender("127.0.0.1", 9001, 100)
        self.sender.sock.close()
        self.sender.sock = MagicMock()

    def test_segment_mode_immediate_on_change_and_1hz_heartbeat(self):
        base_time = 2000.0

        with patch("time.monotonic", return_value=base_time):
            # First send for seg1: should send immediately
            self.sender.set_segment_mode("seg1", "Rainbow")
            # Same state without time advance: should NOT send
            self.sender.set_segment_mode("seg1", "Rainbow")
            # First send for seg2: should send immediately (no starvation from seg1)
            self.sender.set_segment_mode("seg2", "Rainbow")

        metadata_calls = [
            call for call in self.sender.sock.sendto.call_args_list
            if call[0][1] == ("127.0.0.1", SEGMENT_METADATA_PORT)
        ]
        self.assertEqual(len(metadata_calls), 2)

        # Mode change on seg1 should trigger immediately even before 1s
        with patch("time.monotonic", return_value=base_time + 0.2):
            self.sender.set_segment_mode("seg1", "Middle Bar")

        metadata_calls = [
            call for call in self.sender.sock.sendto.call_args_list
            if call[0][1] == ("127.0.0.1", SEGMENT_METADATA_PORT)
        ]
        self.assertEqual(len(metadata_calls), 3)

        # Advance 1.05s: heartbeat should fire for both seg1 and seg2
        with patch("time.monotonic", return_value=base_time + 1.25):
            self.sender.set_segment_mode("seg1", "Middle Bar")
            self.sender.set_segment_mode("seg2", "Rainbow")

        metadata_calls = [
            call for call in self.sender.sock.sendto.call_args_list
            if call[0][1] == ("127.0.0.1", SEGMENT_METADATA_PORT)
        ]
        self.assertEqual(len(metadata_calls), 5)

    def test_analyzer_state_handles_none_and_missing_attributes(self):
        class SparseAnalyzer:
            bpm = None
            speaker_phase = None
            flywheel_status = None
            confidence_score = None
            current_beat_tag = None
            is_beat = None
            is_real_beat = None
            is_dropped_beat = None
            rolling_flux_baseline = None
            asserved_novelty = None
            combined_novelty = None
            is_song_change = None
            is_verse_chorus_change = None
            silence_frames = None

        self.sender.set_analyzer(SparseAnalyzer())
        # Must not raise TypeError or AttributeError
        self.sender.show()

        metadata_calls = [
            call for call in self.sender.sock.sendto.call_args_list
            if call[0][1] == ("127.0.0.1", SEGMENT_METADATA_PORT)
        ]
        self.assertEqual(len(metadata_calls), 1)
        payload = json.loads(metadata_calls[0][0][0].decode("utf-8"))
        self.assertEqual(payload["bpm"], 0.0)
        self.assertEqual(payload["phase"], 0.0)
        self.assertEqual(payload["status"], "None")
        self.assertEqual(payload["confidence"], 0.0)
        self.assertEqual(payload["is_beat"], False)
        self.assertEqual(payload["flux_baseline"], 0.0)
        self.assertEqual(payload["silence_frames"], 0)

    def test_analyzer_state_base_audio_analyzer_compatibility(self):
        from music.BaseAudioAnalyzer import BaseAudioAnalyzer

        class CustomBaseAnalyzer(BaseAudioAnalyzer):
            def update(self, current_time: float, dt: float, fps_ratio: float) -> None: pass
            def reset(self) -> None: pass
            @property
            def beat_phase(self) -> float: return 0.725

        analyzer = CustomBaseAnalyzer(MagicMock(), {})
        analyzer.bpm = 128.0
        self.sender.set_analyzer(analyzer)

        self.sender.show()
        metadata_calls = [
            call for call in self.sender.sock.sendto.call_args_list
            if call[0][1] == ("127.0.0.1", SEGMENT_METADATA_PORT)
        ]
        self.assertEqual(len(metadata_calls), 1)
        payload = json.loads(metadata_calls[0][0][0].decode("utf-8"))
        self.assertEqual(payload["bpm"], 128.0)
        self.assertEqual(payload["phase"], 0.725)

    def test_esp32_sender_routes_metadata_to_localhost_and_pixels_to_esp32(self):
        """Verify Udp_Sender with a remote ESP32 IP sends pixels to ESP32 and metadata to 127.0.0.1."""
        esp_sender = Udp_Sender("192.168.0.29", 9001, 50)
        esp_sender.sock.close()
        esp_sender.sock = MagicMock()

        esp_sender.set_segment_mode("Segment v1", "Rainbow", "Aurora")
        esp_sender.show()

        pixel_targets = [c[0][1] for c in esp_sender.sock.sendto.call_args_list if c[0][1][1] == 9001]
        meta_targets = [c[0][1] for c in esp_sender.sock.sendto.call_args_list if c[0][1][1] == SEGMENT_METADATA_PORT]

        self.assertEqual(pixel_targets, [("192.168.0.29", 9001)])
        self.assertEqual(meta_targets, [("127.0.0.1", SEGMENT_METADATA_PORT)])


if __name__ == "__main__":
    unittest.main()
