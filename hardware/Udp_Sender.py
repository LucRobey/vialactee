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
        self._last_analyzer_send = 0.0
        self._last_segment_heartbeats = {}  # {segment_name: monotonic_timestamp}
        self._cached_segment_modes = {}     # {segment_name: (mode_name, target_mode_name)}

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
        """Send analyzer telemetry, throttled to 10 Hz directly at the network boundary."""
        now = time.monotonic()
        if (now - self._last_analyzer_send) < 0.1:  # 10 Hz throttle
            return
        self._last_analyzer_send = now

        try:
            a = self._analyzer
            bpm_val = getattr(a, "bpm", 0.0)
            bpm = round(float(bpm_val), 1) if bpm_val is not None else 0.0

            phase_val = getattr(a, "speaker_phase", getattr(a, "beat_phase", 0.0))
            phase = round(float(phase_val), 3) if phase_val is not None else 0.0

            status = str(getattr(a, "flywheel_status", "coasting"))

            conf_val = getattr(a, "confidence_score", getattr(a, "beat_confidence", 1.0))
            confidence = round(float(conf_val), 3) if conf_val is not None else 0.0

            beat_tag = str(getattr(a, "current_beat_tag", ""))
            is_beat = bool(getattr(a, "is_beat", False))
            is_real_beat = bool(getattr(a, "is_real_beat", False))
            is_dropped_beat = bool(getattr(a, "is_dropped_beat", False))

            flux_val = getattr(a, "rolling_flux_baseline", 0.0)
            flux_baseline = round(float(flux_val), 1) if flux_val is not None else 0.0

            nov_val = getattr(a, "asserved_novelty", 0.0)
            asserved_novelty = round(float(nov_val), 3) if nov_val is not None else 0.0

            comb_val = getattr(a, "combined_novelty", 0.0)
            combined_novelty = round(float(comb_val), 3) if comb_val is not None else 0.0

            is_song_change = bool(getattr(a, "is_song_change", False))
            is_verse_chorus_change = bool(getattr(a, "is_verse_chorus_change", False))

            silence_val = getattr(a, "silence_frames", 0)
            silence_frames = int(silence_val) if silence_val is not None else 0

            payload = {
                "type": "analyzer_state",
                "bpm": bpm,
                "phase": phase,
                "status": status,
                "confidence": confidence,
                "beat_tag": beat_tag,
                "is_beat": is_beat,
                "is_real_beat": is_real_beat,
                "is_dropped_beat": is_dropped_beat,
                "flux_baseline": flux_baseline,
                "asserved_novelty": asserved_novelty,
                "combined_novelty": combined_novelty,
                "is_song_change": is_song_change,
                "is_verse_chorus_change": is_verse_chorus_change,
                "silence_frames": silence_frames,
            }
            self.sock.sendto(
                json.dumps(payload).encode("utf-8"),
                (self.ip, SEGMENT_METADATA_PORT),
            )
        except Exception:
            pass

    def set_segment_mode(self, segment_name, mode_name, target_mode_name=None):
        """
        Directly throttles the existing interface invoked by Segment.py.
        Transmits on mode transition or 1 Hz per-segment heartbeat.
        """
        now = time.monotonic()
        curr_state = (mode_name, target_mode_name)
        prev_state = self._cached_segment_modes.get(segment_name)
        last_hb = self._last_segment_heartbeats.get(segment_name, 0.0)

        is_change = (prev_state != curr_state)
        is_heartbeat = (now - last_hb) >= 1.0

        if not (is_change or is_heartbeat):
            return

        self._cached_segment_modes[segment_name] = curr_state
        self._last_segment_heartbeats[segment_name] = now

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

