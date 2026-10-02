import socket
import numpy as np
import time
import json
import sys
import os
import struct
import logging
import atexit

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Fake_ESP32")

# Add the project root (parent directory) to sys.path so we can import 'hardware.xxx'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hardware.Fake_leds import FakeLedsVisualizer

# Define the UDP ports for the two segments
PORT_STRIP_1 = 9001
PORT_STRIP_2 = 9002
# Sideband port used by Udp_Sender.set_segment_mode() to push the currently
# active mode of each logical segment so we can render a label next to it.
PORT_METADATA = 9003


def drain_strip_packets(ch, visualizer):
    """
    Drain all queued UDP packets for a strip channel in non-blocking mode.
    Returns True if at least one valid LED pixel slice was updated.
    """
    has_new_led_data = False
    max_len = len(visualizer.strips[ch["strip_id"]])
    sock = ch["sock"]
    while True:
        try:
            data, _ = sock.recvfrom(65535)
        except (BlockingIOError, OSError):
            break
        if len(data) > 2:
            start_index = struct.unpack('<H', data[:2])[0]
            if start_index < max_len:
                payload = data[2:]
                pixel_count = len(payload) // 3
                if pixel_count > 0:
                    arr = np.frombuffer(payload[:pixel_count * 3], dtype=np.uint8).reshape(-1, 3)
                    slice_len = min(len(arr), max_len - start_index)
                    if slice_len > 0:
                        visualizer.strips[ch["strip_id"]][start_index:start_index + slice_len] = arr[:slice_len]
                        has_new_led_data = True
    return has_new_led_data


def drain_metadata_packets(sock_meta, visualizer, max_packets=64):
    """
    Drain pending segment metadata and analyzer telemetry packets.
    Updates visualizer state without disrupting LED render cadence.
    """
    for _ in range(max_packets):
        try:
            data, _ = sock_meta.recvfrom(4096)
        except (BlockingIOError, OSError):
            break
        try:
            payload = json.loads(data.decode("utf-8"))
            p_type = payload.get("type")
            if p_type == "segment_mode":
                public_name = payload.get("name", "") or ""
                internal_name = public_name.lower().replace(" ", "_")
                if internal_name:
                    visualizer.set_segment_mode(
                        internal_name,
                        payload.get("mode"),
                        payload.get("target"),
                    )
            elif p_type == "analyzer_state":
                visualizer.update_analyzer_data(payload)
        except Exception:
            pass


def main():
    logger.info("Starting Fake ESP32 Visualizer...")

    is_win = (sys.platform == "win32")
    timer_period_active = False
    if is_win:
        try:
            import ctypes
            ctypes.windll.winmm.timeBeginPeriod(1)
            timer_period_active = True

            def _cleanup_timer():
                nonlocal timer_period_active
                if timer_period_active:
                    timer_period_active = False
                    ctypes.windll.winmm.timeEndPeriod(1)

            atexit.register(_cleanup_timer)
        except Exception:
            pass

    try:
        # Initialize the visualizer
        visualizer = FakeLedsVisualizer()
        
        from hardware.HardwareFactory import _get_channel_specs
        channel_specs = _get_channel_specs()

        strip_channels = []
        for spec in channel_specs:
            strip_id = visualizer.register_strip(spec["count"])
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(('127.0.0.1', spec["port"]))
            sock.setblocking(False)
            strip_channels.append({
                "strip_id": strip_id,
                "sock": sock,
                "port": spec["port"],
                "count": spec["count"],
            })
        
        sock_meta = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock_meta.bind(('127.0.0.1', PORT_METADATA))
        sock_meta.setblocking(False)

        listening_ports = [ch["port"] for ch in strip_channels]
        logger.info(f"Fake ESP32 listening on UDP ports {listening_ports} (pixels) and {PORT_METADATA} (metadata)...")

        last_render = 0.0
        first_frame = True

        while True:
            has_new_data = False

            # Drain all active strips to prevent socket starvation, judder, and tearing
            for ch in strip_channels:
                if drain_strip_packets(ch, visualizer):
                    has_new_data = True

            # Drain pending segment-metadata packets without resetting frame cadence
            drain_metadata_packets(sock_meta, visualizer)

            now = time.monotonic()
            if has_new_data or first_frame or (now - last_render >= 0.25):
                visualizer.show()
                last_render = now
                first_frame = False
                # Keep a steady framerate capped at 60 FPS
                visualizer.clock.tick(60)
            else:
                visualizer.handle_events()
                time.sleep(0.001)
    finally:
        if is_win and timer_period_active:
            try:
                timer_period_active = False
                ctypes.windll.winmm.timeEndPeriod(1)
            except Exception:
                pass


if __name__ == "__main__":
    main()
