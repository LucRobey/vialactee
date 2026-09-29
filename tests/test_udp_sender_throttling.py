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
        self.sender.sock = MagicMock()

    def test_analyzer_state_throttled_to_10hz(self):
        analyzer = MagicMock()
        analyzer.bpm = 120.0
        analyzer.speaker_phase = 0.5
        analyzer.flywheel_status = "locked"
        analyzer.confidence_score = 0.95
        analyzer.current_beat_tag = "Kick"
        analyzer.is_beat = True
        analyzer.is_real_beat = True
        analyzer.is_dropped_beat = False
        analyzer.rolling_flux_baseline = 10.0
        analyzer.asserved_novelty = 0.1
        analyzer.combined_novelty = 0.2
        analyzer.is_song_change = False
        analyzer.is_verse_chorus_change = False
        analyzer.silence_frames = 0

        self.sender.set_analyzer(analyzer)

        # Call show() 50 times in rapid succession (simulating 50 frames in 10ms)
        start_time = 1000.0
        with patch("time.monotonic", return_value=start_time):
            for _ in range(50):
                self.sender.show()

        # Port 9003 should only receive 1 packet because monotonic time did not advance by >= 0.1s
        metadata_calls = [
            call for call in self.sender.sock.sendto.call_args_list
            if call[0][1] == ("127.0.0.1", SEGMENT_METADATA_PORT)
        ]
        self.assertEqual(len(metadata_calls), 1)
        data = json.loads(metadata_calls[0][0][0].decode("utf-8"))
        self.assertEqual(data["type"], "analyzer_state")
        self.assertEqual(data["bpm"], 120.0)

        # Advance time by 0.11s and show() again -> exactly 1 more packet
        with patch("time.monotonic", return_value=start_time + 0.11):
            self.sender.show()

        metadata_calls = [
            call for call in self.sender.sock.sendto.call_args_list
            if call[0][1] == ("127.0.0.1", SEGMENT_METADATA_PORT)
        ]
        self.assertEqual(len(metadata_calls), 2)

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
        from core.BaseAudioAnalyzer import BaseAudioAnalyzer

        class CustomBaseAnalyzer(BaseAudioAnalyzer):
            def update(self, audio_chunk, current_time): pass
            def reset(self): pass
            @property
            def beat_phase(self): return 0.725

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


if __name__ == "__main__":
    unittest.main()
