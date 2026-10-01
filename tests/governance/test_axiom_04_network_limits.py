"""
tests/governance/test_axiom_04_network_limits.py
Enforces AXIOM-04: Network Transport Protocols & UDP MTU Bounds
- UDP chunk size <= 1,202 bytes (< 1,472 byte MTU limit)
- Sideband telemetry rate limit <= 10 Hz
- WebSocket transition telemetry throttled to <= 10 Hz
"""
import inspect
import unittest
from unittest.mock import MagicMock, patch

from hardware.Udp_Sender import Udp_Sender, SEGMENT_METADATA_PORT
from connectors.Connector import Connector


class TestAxiom04NetworkLimits(unittest.TestCase):
    def test_udp_datagram_mtu_bounds(self):
        """Verify maximum UDP datagram size does not exceed 1,472 bytes MTU."""
        sender = Udp_Sender("127.0.0.1", 9001, 1304)
        sender.sock.close()
        sender.sock = MagicMock()
        sender.show()

        # Check all sent packets
        for call in sender.sock.sendto.call_args_list:
            packet, (ip, port) = call[0]
            if port in (9001, 9002):
                # Pixel packet must be <= 1,202 bytes (400 LEDs * 3 + 2 header bytes)
                self.assertLessEqual(
                    len(packet), 1202,
                    f"Pixel packet size {len(packet)} exceeds 1,202 byte ceiling"
                )
                self.assertLess(
                    len(packet), 1472,
                    f"AXIOM-04 violation: Packet size {len(packet)} exceeds Wi-Fi MTU (1,472)"
                )

    def test_sideband_telemetry_throttled_to_10hz(self):
        """Verify Port 9003 analyzer state telemetry is throttled to 10 Hz (0.1s)."""
        sender = Udp_Sender("127.0.0.1", 9001, 100)
        sender.sock.close()
        sender.sock = MagicMock()
        analyzer = MagicMock()
        analyzer.bpm = 120.0
        sender.set_analyzer(analyzer)

        start = 1000.0
        with patch("time.monotonic", return_value=start):
            for _ in range(20):
                sender.show()

        calls_9003 = [c for c in sender.sock.sendto.call_args_list if c[0][1][1] == SEGMENT_METADATA_PORT]
        self.assertEqual(len(calls_9003), 1, "Must only send 1 telemetry packet in same 0.1s window")

    def test_connector_telemetry_throttling_interval(self):
        """Verify Connector.on_frame_tick throttles transitions to 10 Hz (0.1s interval)."""
        source = inspect.getsource(Connector.on_frame_tick)
        self.assertIn("0.1", source, "AXIOM-04 violation: Connector must throttle transition telemetry to 0.1s (10 Hz)")

    def test_connector_on_frame_tick_transition_throttling_runtime(self):
        """Verify Connector.on_frame_tick only broadcasts at 10 Hz during active transitions."""
        import asyncio
        from unittest.mock import AsyncMock
        connector = Connector(None, {"startServer": False})
        mock_ws = MagicMock()
        connector.active_websockets.add(mock_ws)
        connector.send_state = AsyncMock()

        mock_mm = MagicMock()
        mock_mm.transition_director.is_in_transition = True
        mock_mm._state_dirty = False
        mock_mm.get_state_snapshot.return_value = {"active": True}

        # First call at t=100.0: edge detection (transition start) triggers broadcast
        with patch("time.monotonic", return_value=100.0):
            asyncio.run(connector.on_frame_tick(mock_mm))
        self.assertEqual(connector.send_state.call_count, 1)

        # Second call 0.05s later (t=100.05): throttled (< 0.1s)
        mock_mm._state_dirty = False
        with patch("time.monotonic", return_value=100.05):
            asyncio.run(connector.on_frame_tick(mock_mm))
        self.assertEqual(connector.send_state.call_count, 1)

        # Third call 0.12s later (t=100.12): allowed (>= 0.1s)
        mock_mm._state_dirty = False
        with patch("time.monotonic", return_value=100.12):
            asyncio.run(connector.on_frame_tick(mock_mm))
        self.assertEqual(connector.send_state.call_count, 2)


if __name__ == "__main__":
    unittest.main()
