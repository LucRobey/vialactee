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
CONTROL_PORT = 9004

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
        self._transitions = None
        self._mood = None
        self._control_sock = None
        self._last_analyzer_send = 0.0
        self._last_transition_send = 0.0
        self._last_transition_state = None
        self._last_segment_heartbeats = {}  # {segment_name: monotonic_timestamp}
        self._cached_segment_modes = {}     # {segment_name: (mode_name, target_mode_name)}
        self._control_handler = None        # callable(dict) applying panel commands (HOLD, segment mode)
        self._mode_catalog = None           # {segment_id: [mode names]} behind the panel's < > buttons
        self._last_catalog_send = 0.0

    def _ensure_control_sock(self):
        if self._control_sock is None:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.bind(("127.0.0.1", CONTROL_PORT))
                sock.setblocking(False)
                self._control_sock = sock
            except OSError:
                self._control_sock = None

    def set_control_handler(self, handler, mode_catalog=None):
        """
        Let the simulator/ESP32 panel drive the show.

        Args:
            handler: callable receiving every panel command dict other than
                `request_transition` (e.g. `set_locked`, `set_segment_mode`).
            mode_catalog: {segment_id: [mode names]} streamed to the panel at 1 Hz so
                it knows which modes each segment accepts.
        """
        self._control_handler = handler
        self._mode_catalog = mode_catalog
        if handler is not None:
            self._ensure_control_sock()

    def set_analyzer(self, analyzer):
        """Store a reference to the AudioAnalyzer so show() can stream its state to the simulator."""
        self._analyzer = analyzer

    def set_mood_controller(self, mood):
        """Attach the MoodService so show() can stream palette status & swatches to the simulator."""
        self._mood = mood
        if mood is not None:
            self._ensure_control_sock()

    def set_transition_controller(self, transitions):
        """Attach the TransitionService so simulator UI requests on CONTROL_PORT can trigger transitions."""
        self._transitions = transitions
        if transitions is not None:
            self._ensure_control_sock()

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
        if self._transitions is not None or self._mood is not None or self._control_handler is not None:
            self._poll_control_requests()
            self._send_transition_state()
            self._send_mode_catalog()

    def _poll_control_requests(self):
        """Drain simulator UI transition requests from CONTROL_PORT in non-blocking mode."""
        if self._control_sock is None or (self._transitions is None and self._control_handler is None):
            return
        for _ in range(8):
            try:
                data, _ = self._control_sock.recvfrom(2048)
            except (BlockingIOError, OSError):
                break
            try:
                payload = json.loads(data.decode("utf-8"))
                if payload.get("type") == "request_transition" and self._transitions is not None:
                    raw_tech = payload.get("technique")
                    tech = None if raw_tech in (None, "", "AUTO") else str(raw_tech)
                    dur = payload.get("duration")
                    self._transitions.request_next(
                        technique=tech,
                        duration=float(dur) if dur is not None else None,
                    )
                elif self._control_handler is not None:
                    self._control_handler(payload)
            except Exception:
                pass

    def _send_transition_state(self):
        """Send transition and mood status to the simulator UI on state change or 10 Hz heartbeat."""
        if self._transitions is None and self._mood is None:
            return
        try:
            now = time.monotonic()
            st = self._transitions.get_status() if self._transitions is not None else None
            is_locked = bool(getattr(st, "is_locked", False)) if st is not None else False
            mood_st = self._mood.get_status() if self._mood is not None else None
            mood_sig = (
                (mood_st.palette, mood_st.target_palette, round(float(mood_st.progress), 2),
                 bool(mood_st.is_transitioning), bool(mood_st.auto_scene))
                if mood_st is not None else None
            )
            trans_sig = (
                (bool(st.is_in_transition), bool(st.is_pending), round(float(st.progress), 2), st.technique, is_locked)
                if st is not None else None
            )
            curr = (trans_sig, mood_sig)
            if curr == self._last_transition_state and (now - self._last_transition_send) < 0.1:
                return
            self._last_transition_state = curr
            self._last_transition_send = now
            payload = {"type": "transition_state"}
            if st is not None:
                payload.update({
                    "is_in_transition": bool(st.is_in_transition),
                    "is_pending": bool(st.is_pending),
                    "progress": round(float(st.progress), 3),
                    "technique": st.technique,
                    "is_locked": is_locked,
                })
            if mood_st is not None:
                payload.update({
                    "mood_palette": mood_st.palette,
                    "mood_target": mood_st.target_palette,
                    "mood_progress": round(float(mood_st.progress), 3),
                    "mood_is_transitioning": bool(mood_st.is_transitioning),
                    "mood_auto_scene": bool(mood_st.auto_scene),
                    "available_moods": list(mood_st.available_palettes),
                    "mood_colors": self._mood.colors().tolist(),
                })
            self.sock.sendto(json.dumps(payload).encode("utf-8"), ("127.0.0.1", SEGMENT_METADATA_PORT))
        except Exception:
            pass

    def _send_mode_catalog(self):
        """Send the per-segment list of selectable modes to the panel at 1 Hz."""
        if self._mode_catalog is None:
            return
        now = time.monotonic()
        if (now - self._last_catalog_send) < 1.0:
            return
        self._last_catalog_send = now
        try:
            payload = {"type": "mode_catalog", "modes": self._mode_catalog}
            self.sock.sendto(json.dumps(payload).encode("utf-8"), ("127.0.0.1", SEGMENT_METADATA_PORT))
        except Exception:
            pass

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
                ("127.0.0.1", SEGMENT_METADATA_PORT),
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
                ("127.0.0.1", SEGMENT_METADATA_PORT),
            )
        except Exception:
            pass

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass
        if self._control_sock is not None:
            try:
                self._control_sock.close()
            except Exception:
                pass
            self._control_sock = None
            
    def __del__(self):
        self.close()

