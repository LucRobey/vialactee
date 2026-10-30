"""
tests/test_fake_esp32_and_fake_leds.py - Verifies Fake_ESP32 UDP draining, timer resolution,
and Fake_leds font/label allocation caching.
"""
import unittest
from unittest.mock import MagicMock, patch
import numpy as np
import struct
import json
import sys
import os

from hardware.Fake_leds import Fake_leds, FakeLedsVisualizer
import hardware.Fake_ESP32 as Fake_ESP32


class TestFakeLedsAndFakeESP32(unittest.TestCase):
    def setUp(self):
        self.visualizer = FakeLedsVisualizer()

    def test_fake_leds_caches_segment_labels(self):
        """Verify that segment name labels are cached and not re-rendered on every show()."""
        self.visualizer._segment_label_cache.clear()
        self.visualizer._mode_label_cache.clear()

        with patch.object(self.visualizer, "handle_events"):
            if not self.visualizer.strips:
                self.visualizer.register_strip(100)

            # First show will populate the cache
            self.visualizer.show()
            cache_size = len(self.visualizer._segment_label_cache)
            self.assertGreater(cache_size, 0, "Segment label cache must be populated on first show()")

            # Wrap font with mock to track subsequent render calls
            mock_font = MagicMock(wraps=self.visualizer.font)
            real_font = self.visualizer.font
            self.visualizer.font = mock_font
            try:
                self.visualizer.show()
                mock_font.render.assert_not_called()
            finally:
                self.visualizer.font = real_font

    def test_fake_leds_caches_mode_labels(self):
        """Verify that segment active mode labels are cached."""
        self.visualizer._mode_label_cache.clear()
        self.visualizer.set_segment_mode("segment_v4", "Rainbow", "Fire")

        with patch.object(self.visualizer, "handle_events"):
            self.visualizer.show()
            self.assertTrue(
                any("Rainbow" in str(k) for k in self.visualizer._mode_label_cache.keys()),
                "Mode label cache must contain the active mode"
            )

            mock_mode_font = MagicMock(wraps=self.visualizer.mode_font)
            real_mode_font = self.visualizer.mode_font
            self.visualizer.mode_font = mock_mode_font
            try:
                self.visualizer.show()
                mock_mode_font.render.assert_not_called()
            finally:
                self.visualizer.mode_font = real_mode_font

    def test_fake_leds_caches_hud_labels_and_values(self):
        """Verify that static HUD section, label, value surfaces and background are cached."""
        self.visualizer._hud_section_cache.clear()
        self.visualizer._hud_label_cache.clear()
        self.visualizer._hud_value_cache.clear()
        self.visualizer.update_analyzer_data({
            "type": "analyzer_state",
            "bpm": 128.0,
            "phase": 0.5,
            "status": "locked",
            "confidence": 0.9,
            "beat_tag": "Kick",
            "is_beat": True,
            "is_real_beat": True,
            "is_dropped_beat": False,
            "flux_baseline": 15.0,
            "asserved_novelty": 0.3,
            "combined_novelty": 0.4,
            "is_song_change": False,
            "is_verse_chorus_change": False,
            "silence_frames": 0,
        })

        self.visualizer._draw_analyzer_hud()
        self.assertGreater(len(self.visualizer._hud_section_cache), 0)
        self.assertGreater(len(self.visualizer._hud_label_cache), 0)
        self.assertGreater(len(self.visualizer._hud_value_cache), 0)
        self.assertIsNotNone(self.visualizer._hud_bg_surf, "HUD background surface must be cached")

        # Subsequent draw should not invoke font.render for cached labels
        mock_label_font = MagicMock(wraps=self.visualizer._hud_label_font)
        real_label_font = self.visualizer._hud_label_font
        self.visualizer._hud_label_font = mock_label_font
        try:
            self.visualizer._draw_analyzer_hud()
            rendered_texts = [call[0][0] for call in mock_label_font.render.call_args_list]
            self.assertNotIn("Phase", rendered_texts)
            self.assertNotIn("BPM", rendered_texts)
            self.assertNotIn("Confidence", rendered_texts)
        finally:
            self.visualizer._hud_label_font = real_label_font

    def test_fake_esp32_socket_draining_multiple_packets(self):
        """Verify that Fake_ESP32.drain_strip_packets drains all queued UDP packets for a channel."""
        strip_id = self.visualizer.register_strip(800)

        # Create two packets: chunk 0..400 and chunk 400..800
        data1 = np.ones((400, 3), dtype=np.uint8) * 10
        pkt1 = struct.pack('<H', 0) + data1.tobytes()

        data2 = np.ones((400, 3), dtype=np.uint8) * 20
        pkt2 = struct.pack('<H', 400) + data2.tobytes()

        mock_sock = MagicMock()
        mock_sock.recvfrom.side_effect = [
            (pkt1, ('127.0.0.1', 9001)),
            (pkt2, ('127.0.0.1', 9001)),
            BlockingIOError("Resource temporarily unavailable"),
        ]

        ch = {"strip_id": strip_id, "sock": mock_sock, "port": 9001, "count": 800}

        has_new_data = Fake_ESP32.drain_strip_packets(ch, self.visualizer)

        self.assertTrue(has_new_data)
        # Verify chunk 1 was applied
        np.testing.assert_array_equal(self.visualizer.strips[strip_id][0:400], data1)
        # Verify chunk 2 was applied in the same tick (no starvation)
        np.testing.assert_array_equal(self.visualizer.strips[strip_id][400:800], data2)

    def test_fake_esp32_out_of_bounds_and_malformed_protection(self):
        """Verify that oversized, truncated, or odd-length packets do not raise ValueError."""
        strip_id = self.visualizer.register_strip(100)
        data = np.ones((150, 3), dtype=np.uint8) * 42
        pkt_oversized = struct.pack('<H', 80) + data.tobytes()
        pkt_odd_bytes = struct.pack('<H', 0) + b'\x10\x20\x30\x40'  # 4 bytes (not a multiple of 3)
        pkt_too_short = struct.pack('<H', 0)  # 2 bytes (no payload)
        pkt_oob_index = struct.pack('<H', 999) + (np.ones((10, 3), dtype=np.uint8)).tobytes()

        mock_sock = MagicMock()
        mock_sock.recvfrom.side_effect = [
            (pkt_too_short, ('127.0.0.1', 9001)),
            (pkt_odd_bytes, ('127.0.0.1', 9001)),
            (pkt_oob_index, ('127.0.0.1', 9001)),
            (pkt_oversized, ('127.0.0.1', 9001)),
            BlockingIOError(),
        ]
        ch = {"strip_id": strip_id, "sock": mock_sock, "port": 9001, "count": 100}

        has_new = Fake_ESP32.drain_strip_packets(ch, self.visualizer)
        self.assertTrue(has_new)

        # Truncated odd packet (4 bytes -> 1 pixel) at index 0
        np.testing.assert_array_equal(self.visualizer.strips[strip_id][0], [0x10, 0x20, 0x30])
        # Oversized chunk (starts at 80, length 150) safely clamped to 80:100 (20 pixels)
        np.testing.assert_array_equal(self.visualizer.strips[strip_id][80:100], data[:20])

    def test_fake_esp32_metadata_draining(self):
        """Verify that drain_metadata_packets updates visualizer state cleanly."""
        mode_payload = json.dumps({"type": "segment_mode", "name": "segment_v3", "mode": "Aurora", "target": None}).encode("utf-8")
        analyzer_payload = json.dumps({"type": "analyzer_state", "bpm": 130.0}).encode("utf-8")

        mock_meta = MagicMock()
        mock_meta.recvfrom.side_effect = [
            (mode_payload, ('127.0.0.1', 9003)),
            (analyzer_payload, ('127.0.0.1', 9003)),
            BlockingIOError(),
        ]

        Fake_ESP32.drain_metadata_packets(mock_meta, self.visualizer)

        self.assertEqual(self.visualizer.segment_modes.get("segment_v3", {}).get("mode"), "Aurora")
        self.assertEqual(self.visualizer._analyzer_data.get("bpm"), 130.0)

    def test_fake_esp32_transition_tester_ui_and_metadata(self):
        """Verify Transition Tester UI selection, duration adjustment, request dispatch, and UDP status draining."""
        trans_payload = json.dumps({
            "type": "transition_state",
            "is_in_transition": True,
            "is_pending": False,
            "progress": 0.42,
            "technique": "silk_wipe",
        }).encode("utf-8")

        mock_meta = MagicMock()
        mock_meta.recvfrom.side_effect = [
            (trans_payload, ("127.0.0.1", 9003)),
            BlockingIOError(),
        ]
        Fake_ESP32.drain_metadata_packets(mock_meta, self.visualizer)
        self.assertEqual(self.visualizer._transition_data.get("technique"), "silk_wipe")
        self.assertAlmostEqual(self.visualizer._transition_data.get("progress"), 0.42)

        # Test stepping transition and duration in HUD
        hud = self.visualizer.hud
        hud.selected_idx = 0
        hud.selected_duration = 1.2
        hud.step_transition(1)
        self.assertEqual(hud.selected_transition, "silk_wipe")
        hud.adjust_duration(0.5)
        self.assertAlmostEqual(hud.selected_duration, 1.7)


    def test_fake_esp32_timer_period_calls(self):
        """Verify Fake_ESP32.main calls timeBeginPeriod(1) and timeEndPeriod(1) on Windows."""
        with patch("sys.platform", "win32"):
            with patch("ctypes.windll.winmm.timeBeginPeriod") as mock_begin:
                with patch("ctypes.windll.winmm.timeEndPeriod") as mock_end:
                    with patch("hardware.Fake_ESP32.FakeLedsVisualizer", side_effect=KeyboardInterrupt):
                        try:
                            Fake_ESP32.main()
                        except KeyboardInterrupt:
                            pass
                        mock_begin.assert_called_with(1)
                        mock_end.assert_called_with(1)

    def test_hud_only_compact_window_and_button_rects(self):
        """Verify HUD-only mode renders compact panels without simulated LEDs and aligns button rects."""
        self.visualizer._analyzer_data = None
        try:
            self.visualizer.set_hud_only(True)
            self.assertTrue(self.visualizer.hud_only)
            self.assertEqual(self.visualizer._current_window_size[0], 732)
            self.assertLess(self.visualizer._current_window_size[1], 400)

            with patch.object(self.visualizer, "handle_events"):
                self.visualizer.show()
                # Transition panel is drawn at (320, 12), so _rect_send is at (334, 131)
                self.assertEqual(self.visualizer.hud._rect_send.topleft, (334, 131))
                self.assertEqual(self.visualizer.hud._rect_prev.topleft, (334, 53))
        finally:
            self.visualizer.set_hud_only(False)

    def test_hardware_factory_esp32_launches_hud_only_when_not_headless(self):
        """Verify HardwareFactory launches Fake_ESP32.py --hud-only in esp32 mode on desktop."""
        import hardware.HardwareFactory as HardwareFactory
        infos = {"HARDWARE_MODE": "esp32", "esp32_ip": "192.168.0.29", "hardware_profile": "small"}
        with patch.dict(os.environ, {"SDL_VIDEODRIVER": ""}, clear=False):
            with patch("hardware.HardwareFactory.subprocess.Popen") as mock_popen:
                with patch("atexit.register"):
                    senders = HardwareFactory.create_hardware(infos)
                    self.assertEqual(len(senders), 1)
                    mock_popen.assert_called_once()
                    cmd = mock_popen.call_args[0][0]
                    self.assertIn("--hud-only", cmd)
                    for s in senders:
                        s.close()

    def test_fake_leds_dynamic_reconstruction_full_and_small(self):
        """Verify Fake_leds dynamically reconstructs 1,304 LEDs (full) and 249 LEDs (small) with vertical_up wiring."""
        infos_full = {"HARDWARE_MODE": "simulation", "hardware_profile": "full"}
        defs_full = Fake_leds._load_visualizer_segments_def(infos_full)
        self.assertEqual(sum(seg[0] for ch in defs_full for seg in ch), 1304)
        self.assertEqual(sum(len(ch) for ch in defs_full), 11)
        verticals = [seg for ch in defs_full for seg in ch if "vertical" in seg[1]]
        self.assertGreater(len(verticals), 0)
        for seg in verticals:
            self.assertEqual(seg[1], "vertical_up")

        infos_small = {"HARDWARE_MODE": "simulation", "hardware_profile": "small"}
        defs_small = Fake_leds._load_visualizer_segments_def(infos_small)
        self.assertEqual(sum(seg[0] for ch in defs_small for seg in ch), 249)
        self.assertEqual(sum(len(ch) for ch in defs_small), 3)
        for ch in defs_small:
            for seg in ch:
                self.assertEqual(seg[1], "vertical_up")


if __name__ == "__main__":
    unittest.main()
