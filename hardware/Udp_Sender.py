import numpy as np
import socket
import json
import struct
import time
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
        self.data = np.zeros((nb_of_leds, 3), dtype=np.uint8)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._analyzer = None

    def set_analyzer(self, analyzer):
        """Store a reference to the AudioAnalyzer so show() can stream its state to the simulator."""
        self._analyzer = analyzer

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
        chunk_size = 400  # 400 LEDs = 1200 bytes, fits safely under 1472 MTU
        for i in range(0, self.nb_of_leds, chunk_size):
            end = min(i + chunk_size, self.nb_of_leds)
            chunk_data = self.data[i:end].tobytes()
            header = struct.pack('<H', i)
            packet = header + chunk_data
            try:
                self.sock.sendto(packet, (self.ip, self.port))
            except Exception as e:
                print(f"UDP Error to {self.ip}:{self.port} -> {e}")

        if self._analyzer is not None:
            self._send_analyzer_state()

    def _send_analyzer_state(self):
        """Send a compact JSON snapshot of the analyzer state on the metadata port."""
        a = self._analyzer
        payload = {
            "type": "analyzer_state",
            "bpm": round(a.bpm, 1),
            "phase": round(a.speaker_phase, 3),
            "status": a.flywheel_status,
            "confidence": round(a.confidence_score, 3),
            "beat_tag": a.current_beat_tag,
            "is_beat": bool(a.is_beat),
            "is_real_beat": bool(a.is_real_beat),
            "is_dropped_beat": bool(a.is_dropped_beat),
            "flux_baseline": round(a.rolling_flux_baseline, 1),
            "asserved_novelty": round(a.asserved_novelty, 3),
            "combined_novelty": round(a.combined_novelty, 3),
            "is_song_change": bool(a.is_song_change),
            "is_verse_chorus_change": bool(a.is_verse_chorus_change),
            "silence_frames": int(a.silence_frames),
        }
        try:
            self.sock.sendto(
                json.dumps(payload).encode("utf-8"),
                (self.ip, SEGMENT_METADATA_PORT),
            )
        except Exception:
            pass

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

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass
            
    def __del__(self):
        self.close()

