import json
import numpy as np
import os
import socket
import sys
import time
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame
from hardware.VisualizerHud import VisualizerHud

CONTROL_PORT = 9004


class FakeLedsVisualizer:
    _instance = None
    
    def __new__(cls, hud_only=None):
        if cls._instance is None:
            cls._instance = super(FakeLedsVisualizer, cls).__new__(cls)
            try:
                pygame.init()
            except Exception:
                pass
            
            cls._instance.screen = None
            cls._instance._current_window_size = None
            cls._instance.strips = []
            cls._instance.clock = pygame.time.Clock()
            # Maps the segment_def internal name (e.g. "segment_v4") to its current mode info
            cls._instance.segment_modes = {}
            # Latest analyzer and transition state received from the main process (for HUD overlay)
            cls._instance._analyzer_data = None
            cls._instance._transition_data = None
            cls._instance._transition_controller = None
            cls._instance._control_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            cls._instance.audio_player = None
            cls._instance._last_caption_update = 0.0
            
            # Text and label surface caches to avoid allocation churn in hot path
            cls._instance.font = None
            cls._instance.mode_font = None
            cls._instance._segment_label_cache, cls._instance._mode_label_cache = {}, {}
            cls._instance.hud = VisualizerHud()
            cls._instance._hud_section_cache = cls._instance.hud._hud_section_cache
            cls._instance._hud_label_cache = cls._instance.hud._hud_label_cache
            cls._instance._hud_value_cache = cls._instance.hud._hud_value_cache
            cls._instance._hud_small_val_cache = cls._instance.hud._hud_small_val_cache

            # Dynamic geometry mapping based on active profile
            cls._instance.segments_def = cls._instance._load_visualizer_segments_def()
            cls._instance.hud_only = False
            initial_hud_only = (
                hud_only
                if hud_only is not None
                else ("--hud-only" in sys.argv or os.environ.get("VIALACTEE_HUD_ONLY") == "1")
            )
            cls._instance.set_hud_only(bool(initial_hud_only))
        elif hud_only is not None and bool(hud_only) != cls._instance.hud_only:
            cls._instance.set_hud_only(bool(hud_only))

        return cls._instance

    def _compute_hud_only_size(self):
        seen = {
            name
            for ch_defs in self.segments_def
            for (_s, _o, _sx, _sy, name, _c) in ch_defs
        }
        modes_h = 38 + max(1, len(seen)) * 22
        left_h = (modes_h + 12 + 345) if self._analyzer_data is not None else modes_h
        return (732, max(205, left_h) + 24)

    def set_hud_only(self, hud_only):
        self.hud_only = bool(hud_only)
        target_size = self._compute_hud_only_size() if self.hud_only else (1300, 900)
        if getattr(self, "_current_window_size", None) != target_size:
            self.screen = pygame.display.set_mode(target_size)
            self._current_window_size = target_size
        caption = "Vialactée - ESP32 Control Panel" if self.hud_only else "Vialactée - LED Simulator"
        pygame.display.set_caption(caption)

    @property
    def _hud_bg_surf(self):
        return self.hud._hud_bg_surf

    @property
    def _hud_label_font(self):
        return getattr(self.hud, "_hud_label_font", None)

    @_hud_label_font.setter
    def _hud_label_font(self, val):
        self.hud._hud_label_font = val

    @staticmethod
    def _hex_to_rgb(hex_str):
        if not hex_str or not isinstance(hex_str, str) or not hex_str.startswith("#") or len(hex_str) < 7:
            return (200, 200, 200)
        try:
            return (int(hex_str[1:3], 16), int(hex_str[3:5], 16), int(hex_str[5:7], 16))
        except ValueError:
            return (200, 200, 200)

    @classmethod
    def _load_visualizer_segments_def(cls, infos=None):
        """
        Build segments_def dynamically based on active hardware profile.
        Reconstructs the layout directly from the active segment JSON file
        (resolved via resolve_segments_file_path) to maintain a single source of truth.
        """
        try:
            from config.Configuration_manager import resolve_segments_file_path
            seg_path = resolve_segments_file_path(infos)
            with open(seg_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            channel_keys = [k for k in data.keys() if k.startswith("segs_")]
            channel_keys.sort(key=lambda k: int(k.split("_")[1]) if k.split("_")[1].isdigit() else 0)

            strips_defs = []
            for ch_key in channel_keys:
                segs = data.get(ch_key, [])
                sorted_segs = sorted(segs, key=lambda s: s.get("order", 0))
                channel_defs = []
                for s in sorted_segs:
                    size = int(s.get("size", 0))
                    orientation_raw = s.get("orientation", "horizontal")
                    step = s.get("step", {})
                    step_y = step.get("y", 0)
                    if orientation_raw == "vertical" and step_y < 0:
                        orientation = "vertical_up"
                    else:
                        orientation = orientation_raw

                    start = s.get("start", {})
                    start_x_grid = start.get("x", 0)
                    start_y_grid = start.get("y", 0)

                    # Scale factor 2, Offset 100
                    start_x = 100 + (start_x_grid * 2)
                    start_y = 100 + (start_y_grid * 2) + (2 if orientation == "vertical_up" else 0)

                    name = f"segment_{s.get('id', s.get('name', ''))}"
                    border_color = cls._hex_to_rgb(s.get("ui", {}).get("color", "#ffffff"))
                    channel_defs.append((size, orientation, start_x, start_y, name, border_color))
                strips_defs.append(channel_defs)

            if strips_defs and any(len(c) > 0 for c in strips_defs):
                return strips_defs
        except Exception as exc:
            print(f"(Fake_leds) Warning: Could not dynamically load segment geometry from JSON: {exc}")

        # Fallback to default chandelier geometry if JSON load fails
        return [
            # Strip 0 (segs_1)
            [
                (173, "vertical_up", 962, 510, "segment_v4", (50, 100, 255)), (48, "horizontal", 866, 270, "segment_h32", (255, 50, 50)),
                (48, "horizontal", 866, 442, "segment_h31", (255, 0, 255)), (47, "horizontal", 866, 102, "segment_h30", (150, 150, 150)),
                (173, "vertical_up", 866, 592, "segment_v3", (0, 255, 255)), (91, "horizontal", 684, 132, "segment_h20", (150, 255, 150)),
                (205, "horizontal", 100, 132, "segment_h00", (0, 0, 255)),
            ],
            # Strip 1 (segs_2)
            [
                (173, "vertical_up", 684, 592, "segment_v2", (0, 255, 0)), (87, "horizontal", 510, 246, "segment_h11", (255, 150, 100)),
                (86, "horizontal", 510, 478, "segment_h10", (150, 50, 200)), (173, "vertical_up", 510, 478, "segment_v1", (255, 255, 0)),
            ],
        ]

    def register_strip(self, nb_of_leds):
        strip_id = len(self.strips)
        self.strips.append(np.zeros((nb_of_leds, 3), dtype=int))
        return strip_id

    def update_strip(self, strip_id, data):
        self.strips[strip_id] = data

    def set_segment_mode(self, internal_name, mode_name, target_mode_name=None):
        """Register the current active mode for a segment so it can be rendered as a label."""
        self.segment_modes[internal_name] = {
            "mode": mode_name,
            "target": target_mode_name,
        }

    def set_audio_player(self, player):
        self.audio_player = player

    def set_transition_controller(self, transitions):
        self._transition_controller = transitions

    def send_transition_request(self, technique: str, duration: float) -> None:
        """Dispatch a transition request either directly in-process or over localhost UDP."""
        tech = None if technique == "AUTO" else technique
        if self._transition_controller is not None:
            try:
                self._transition_controller.request_next(technique=tech, duration=float(duration))
            except Exception:
                pass
        payload = {
            "type": "request_transition",
            "technique": technique,
            "duration": float(duration),
        }
        try:
            self._control_sock.sendto(json.dumps(payload).encode("utf-8"), ("127.0.0.1", CONTROL_PORT))
        except Exception:
            pass

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)
            if self.hud.handle_event(event, self.send_transition_request):
                continue
            if event.type == pygame.KEYDOWN and self.audio_player is not None:
                p = self.audio_player
                if event.key == pygame.K_SPACE: p.toggle_pause()
                elif event.key == pygame.K_RIGHT: p.seek_relative(5.0)
                elif event.key == pygame.K_LEFT: p.seek_relative(-5.0)
                elif event.key == pygame.K_n: p.next_song()
                elif event.key == pygame.K_p: p.prev_song()
                elif pygame.K_1 <= event.key <= pygame.K_9: p.change_song_number(event.key - pygame.K_1)

    def show(self):
        self.handle_events()
        
        if self.audio_player is not None:
            now = time.time()
            if now - self._last_caption_update >= 0.5:
                self._last_caption_update = now
                p = self.audio_player
                cur = p.get_current_time()
                tot = max(1.0, p.total_duration)
                st = "PLAYING" if p.is_playing else "PAUSED"
                name = os.path.basename(p.file_path)
                pygame.display.set_caption(f"Vialactée Simulator [{st}: {name} ({int(cur)//60:02d}:{int(cur)%60:02d}/{int(tot)//60:02d}:{int(tot)%60:02d}) | Space: Pause, ←/→: Seek, N/P: Tracks]")

        self.screen.fill((15, 15, 15))
        if self.font is None:
            pygame.font.init()
            self.font = pygame.font.SysFont('arial', 16, bold=True)
            self.mode_font = pygame.font.SysFont('arial', 11, italic=True)

        if self.hud_only:
            target_size = self._compute_hud_only_size()
            if self._current_window_size != target_size:
                self.screen = pygame.display.set_mode(target_size)
                self._current_window_size = target_size
            modes_h = self.hud.draw_segment_modes_table(
                self.screen,
                self.segments_def,
                self.segment_modes,
                self.mode_font,
                self._mode_label_cache,
                px=12,
                py=12,
            )
            self.hud.draw_transition_panel(self.screen, self._transition_data, px=320, py=12)
            if self._analyzer_data is not None:
                self.hud.draw_analyzer_hud(self.screen, self._analyzer_data, px=12, py=12 + modes_h + 12)
            pygame.display.flip()
            return

        for strip_id, strip_data in enumerate(self.strips):
            if strip_id >= len(self.segments_def):
                continue
                
            cursor = 0
            for (size, orientation, start_x, start_y, name, border_color) in self.segments_def[strip_id]:
                key = (name, start_x, start_y, size, orientation)
                if key not in self._segment_label_cache:
                    surf = self.font.render(name, True, (0, 0, 0))
                    rect = surf.get_rect()
                    if orientation == "horizontal":
                        rect.center = (start_x + size, start_y + 25)
                    elif orientation == "vertical_up":
                        rect.center = (start_x - 55, start_y - size)
                    else:
                        rect.center = (start_x - 55, start_y + size)
                    self._segment_label_cache[key] = (surf, rect, rect.inflate(10, 8))

                text_surface, text_rect, bg_rect = self._segment_label_cache[key]
                pygame.draw.rect(self.screen, (245, 245, 245), bg_rect)
                pygame.draw.rect(self.screen, border_color, bg_rect, 2)
                self.screen.blit(text_surface, text_rect)

                x, y = start_x, start_y
                for _ in range(size):
                    if cursor >= len(strip_data):
                        break
                    
                    color = strip_data[cursor]
                    r = max(0, min(255, int(color[0])))
                    g = max(0, min(255, int(color[1])))
                    b = max(0, min(255, int(color[2])))
                    
                    pygame.draw.circle(self.screen, (r, g, b), (x, y), 2)
                    
                    if orientation == "horizontal":
                        x += 2
                    elif orientation == "vertical_up":
                        y -= 2
                    else:
                        y += 2
                        
                    cursor += 1
            
        self.hud.draw_segment_modes_table(
            self.screen,
            self.segments_def,
            self.segment_modes,
            self.mode_font,
            self._mode_label_cache,
        )
        self._draw_analyzer_hud()
        self.hud.draw_transition_panel(self.screen, self._transition_data)
        pygame.display.flip()

    def update_analyzer_data(self, data):
        """Store latest analyzer state received from the main process via UDP."""
        self._analyzer_data = data

    def update_transition_data(self, data):
        """Store latest transition state received from the main process via UDP."""
        self._transition_data = data

    def _draw_analyzer_hud(self):
        """Draw the music analyzer HUD overlay in the bottom-left corner."""
        self.hud.draw_analyzer_hud(self.screen, self._analyzer_data)


visualizer = FakeLedsVisualizer()

from hardware.HardwareInterface import HardwareInterface


class Fake_leds(HardwareInterface):
    def __init__(self, nb_of_leds):
        self.nb_of_leds = nb_of_leds
        self.data = np.zeros((nb_of_leds, 3), dtype=int)
        self.strip_id = visualizer.register_strip(nb_of_leds)
        self._analyzer = None
        self._transitions = None

    def set_analyzer(self, analyzer):
        self._analyzer = analyzer

    def set_transition_controller(self, transitions):
        self._transitions = transitions
        visualizer.set_transition_controller(transitions)

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

    def append(self, value):
        pass

    def show(self):
        if self._analyzer is not None:
            a = self._analyzer
            visualizer.update_analyzer_data({
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
            })
        if self._transitions is not None:
            st = self._transitions.get_status()
            visualizer.update_transition_data({
                "type": "transition_state",
                "is_in_transition": bool(st.is_in_transition),
                "is_pending": bool(st.is_pending),
                "progress": round(float(st.progress), 3),
                "technique": st.technique,
            })
        visualizer.update_strip(self.strip_id, self.data)
        visualizer.show()

    def set_audio_player(self, audio_player):
        visualizer.set_audio_player(audio_player)

    def set_segment_mode(self, segment_name, mode_name, target_mode_name=None):
        """Forward the current active mode for a logical segment to the shared visualizer."""
        internal_name = segment_name.lower().replace(" ", "_")
        visualizer.set_segment_mode(internal_name, mode_name, target_mode_name)

    @staticmethod
    def _load_visualizer_segments_def(infos=None):
        return FakeLedsVisualizer._load_visualizer_segments_def(infos)

