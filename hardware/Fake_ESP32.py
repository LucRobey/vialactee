import socket
import numpy as np
import time
import json
import sys
import os
import struct
import logging

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

def main():
    logger.info("Starting Fake ESP32 Visualizer...")
    
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

    while True:
        # Check all active strips
        for ch in strip_channels:
            try:
                data, _ = ch["sock"].recvfrom(65535)
                if len(data) >= 2:
                    start_index = struct.unpack('<H', data[:2])[0]
                    arr = np.frombuffer(data[2:], dtype=np.uint8).reshape(-1, 3)
                    visualizer.strips[ch["strip_id"]][start_index:start_index+len(arr)] = arr
            except BlockingIOError:
                pass

        # Drain pending segment-metadata packets (bounded to keep frame snappy)
        for _ in range(64):
            try:
                data, _ = sock_meta.recvfrom(4096)
            except BlockingIOError:
                break
            try:
                payload = json.loads(data.decode("utf-8"))
                if payload.get("type") == "segment_mode":
                    public_name = payload.get("name", "") or ""
                    internal_name = public_name.lower().replace(" ", "_")
                    if internal_name:
                        visualizer.set_segment_mode(
                            internal_name,
                            payload.get("mode"),
                            payload.get("target"),
                        )
                elif payload.get("type") == "analyzer_state":
                    visualizer.update_analyzer_data(payload)
            except Exception:
                # Ignore malformed packets to avoid killing the visualizer loop
                pass

        # Update PyGame Window
        visualizer.show()
        
        # Keep a steady framerate and prevent 100% CPU usage
        visualizer.clock.tick(60)

if __name__ == "__main__":
    main()
