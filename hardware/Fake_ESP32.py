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
    
    # Register the two strips (sizes from the main code)
    strip1_id = visualizer.register_strip(785)
    strip2_id = visualizer.register_strip(519)
    
    # Setup UDP sockets for listening
    sock1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock1.bind(('127.0.0.1', PORT_STRIP_1))
    sock1.setblocking(False)

    sock2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock2.bind(('127.0.0.1', PORT_STRIP_2))
    sock2.setblocking(False)

    sock_meta = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock_meta.bind(('127.0.0.1', PORT_METADATA))
    sock_meta.setblocking(False)

    logger.info(f"Fake ESP32 listening on UDP ports {PORT_STRIP_1}, {PORT_STRIP_2} (pixels) and {PORT_METADATA} (metadata)...")

    while True:
        # Check Strip 1
        try:
            data, _ = sock1.recvfrom(65535)
            if len(data) >= 2:
                start_index = struct.unpack('<H', data[:2])[0]
                arr = np.frombuffer(data[2:], dtype=np.uint8).reshape(-1, 3)
                visualizer.strips[strip1_id][start_index:start_index+len(arr)] = arr
        except BlockingIOError:
            pass

        # Check Strip 2
        try:
            data, _ = sock2.recvfrom(65535)
            if len(data) >= 2:
                start_index = struct.unpack('<H', data[:2])[0]
                arr = np.frombuffer(data[2:], dtype=np.uint8).reshape(-1, 3)
                visualizer.strips[strip2_id][start_index:start_index+len(arr)] = arr
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
