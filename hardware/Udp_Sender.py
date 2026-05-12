import numpy as np
import socket
import json
from hardware.HardwareInterface import HardwareInterface

# Sideband UDP port used by Udp_Sender to ship segment metadata (current mode,
# transition target) to the Fake_ESP32 simulator. Pixel data still flows on the
# main ports (9001/9002) untouched.
SEGMENT_METADATA_PORT = 9003

class Udp_Sender(HardwareInterface):
    """
    Sends the LED RGB frames over UDP.
    Acts as the main brain output to either a real ESP32 or the Fake_ESP32 simulator.
    """
    def __init__(self, ip, port, nb_of_leds):
        self.ip = ip
        self.port = port
        self.nb_of_leds = nb_of_leds
        self.data = np.zeros((nb_of_leds, 3), dtype=np.int32)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def __getitem__(self, index):
        return self.data[index]

    def __setitem__(self, index, value):
        self.data[index] = value

    def __len__(self):
        return len(self.data)

    def set_pixel(self, index, color):
        self.data[index] = color

    def clear(self):
        self.data.fill(0)
        self.show()

    def show(self):
        # Convert to bytes and send via UDP
        # Depending on network MTU, 785 * 3 * 4 bytes = ~9.4KB.
        # This is larger than the standard 1500 MTU but works over local loopback.
        # For real Wi-Fi, it will be fragmented by IP automatically.
        packet = self.data.tobytes()
        try:
            self.sock.sendto(packet, (self.ip, self.port))
        except Exception as e:
            pass # Ignore network errors to avoid crashing the main loop

    def set_segment_mode(self, segment_name, mode_name, target_mode_name=None):
        """
        Ship a small JSON UDP packet describing the active mode of a segment so
        the Fake_ESP32 simulator can render it as a label. Sent on every frame
        so the simulator self-recovers if it boots after the main process or
        misses a packet. Real ESP32 hardware will simply receive packets on a
        port it does not listen to, which is harmless.
        """
        payload = {
            "type": "segment_mode",
            "name": segment_name,
            "mode": mode_name,
            "target": target_mode_name,
        }
        try:
            self.sock.sendto(
                json.dumps(payload).encode("utf-8"),
                (self.ip, SEGMENT_METADATA_PORT),
            )
        except Exception:
            pass
