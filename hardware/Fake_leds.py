import numpy as np
import os
import sys
import time
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame

class FakeLedsVisualizer:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FakeLedsVisualizer, cls).__new__(cls)
            try:
                pygame.init()
            except:
                pass
            
            # Larger window to fit the mapped schematic
            cls._instance.screen = pygame.display.set_mode((1300, 900))
            pygame.display.set_caption("Vialactée - LED Simulator")
            cls._instance.strips = []
            cls._instance.clock = pygame.time.Clock()
            # Maps the segment_def internal name (e.g. "segment_v4") to its current mode info
            cls._instance.segment_modes = {}
            # Latest analyzer state received from the main process (for HUD overlay)
            cls._instance._analyzer_data = None
            cls._instance.audio_player = None
            cls._instance._last_caption_update = 0.0
            
            # Text and label surface caches to avoid allocation churn in hot path
            cls._instance.font = None
            cls._instance.mode_font = None
            cls._instance._segment_label_cache, cls._instance._mode_label_cache = {}, {}
            cls._instance._hud_section_cache, cls._instance._hud_label_cache = {}, {}
            cls._instance._hud_value_cache, cls._instance._hud_small_val_cache = {}, {}
            cls._instance._hud_bg_surf = None

            # Dynamic geometry mapping based on active profile
            cls._instance.segments_def = cls._instance._load_visualizer_segments_def()
            
        return cls._instance

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
            import json
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
        """
        Register the current active mode for a segment so it can be rendered as
        a label next to that segment in the simulator. `internal_name` matches
        the keys defined in `segments_def` (e.g. "segment_v4").
        """
        self.segment_modes[internal_name] = {
            "mode": mode_name,
            "target": target_mode_name,
        }

    def set_audio_player(self, player):
        self.audio_player = player

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)
            elif event.type == pygame.KEYDOWN and self.audio_player is not None:
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

        for strip_id, strip_data in enumerate(self.strips):
            if strip_id >= len(self.segments_def):
                continue
                
            cursor = 0
            for (size, orientation, start_x, start_y, name, border_color) in self.segments_def[strip_id]:
                # Draw the cached Text Label Box
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

                # Draw the cached active mode label
                mode_info = self.segment_modes.get(name)
                if mode_info is not None and mode_info.get("mode"):
                    mode_label = mode_info["mode"]
                    if mode_info.get("target"):
                        mode_label = f"{mode_label} -> {mode_info['target']}"

                    m_key = (mode_label, bg_rect.centerx, bg_rect.bottom)
                    if m_key not in self._mode_label_cache:
                        m_surf = self.mode_font.render(mode_label, True, (35, 35, 35))
                        m_rect = m_surf.get_rect(center=(bg_rect.centerx, bg_rect.bottom + 10))
                        self._mode_label_cache[m_key] = (m_surf, m_rect, m_rect.inflate(8, 4))

                    m_surf, m_rect, m_bg = self._mode_label_cache[m_key]
                    pygame.draw.rect(self.screen, (255, 255, 255), m_bg)
                    pygame.draw.rect(self.screen, border_color, m_bg, 1)
                    self.screen.blit(m_surf, m_rect)
            
                x, y = start_x, start_y
                for _ in range(size):
                    if cursor >= len(strip_data):
                        break
                    
                    color = strip_data[cursor]
                    r = max(0, min(255, int(color[0])))
                    g = max(0, min(255, int(color[1])))
                    b = max(0, min(255, int(color[2])))
                    
                    pygame.draw.circle(self.screen, (r, g, b), (x, y), 2) # small dot
                    
                    if orientation == "horizontal":
                        x += 2
                    elif orientation == "vertical_up":
                        y -= 2
                    else:
                        y += 2
                        
                    cursor += 1
            
        self._draw_analyzer_hud()
        pygame.display.flip()

    # ==========================================
    # ANALYZER HUD OVERLAY
    # ==========================================

    def update_analyzer_data(self, data):
        """Store latest analyzer state received from the main process via UDP."""
        self._analyzer_data = data

    def _draw_analyzer_hud(self):
        """Draw the music analyzer HUD overlay in the bottom-left corner."""
        if self._analyzer_data is None:
            return
        d = self._analyzer_data

        # Lazy-init HUD fonts
        if not hasattr(self, '_hud_fonts_ready'):
            self._hud_fonts_ready = True
            self._hud_title_font = pygame.font.SysFont('consolas', 14, bold=True)
            self._hud_section_font = pygame.font.SysFont('consolas', 12, bold=True)
            self._hud_label_font = pygame.font.SysFont('consolas', 11)
            self._hud_value_font = pygame.font.SysFont('consolas', 11, bold=True)
            self._hud_title_surf = self._hud_title_font.render("MUSIC ANALYZER", True, (220, 220, 255))
            self._hud_bg_surf = pygame.Surface((295, 345), pygame.SRCALPHA)
            self._hud_bg_surf.fill((12, 12, 20, 215))

        # Panel geometry
        px, py = 10, 545
        pw, ph = 295, 345

        # Semi-transparent background
        self.screen.blit(self._hud_bg_surf, (px, py))
        pygame.draw.rect(self.screen, (160, 60, 220), (px, py, pw, ph), 2)

        # Title
        self.screen.blit(self._hud_title_surf, (px + pw // 2 - self._hud_title_surf.get_width() // 2, py + 8))
        pygame.draw.line(self.screen, (80, 40, 120),
                         (px + 8, py + 28), (px + pw - 8, py + 28), 1)

        lx = px + 12          # label x
        vx = px + 120         # value x
        bar_w = 120           # bar width
        cy = py + 36          # cursor y

        # ── FLYWHEEL ──────────────────────────────────
        self._hud_section("FLYWHEEL", lx, cy, (200, 80, 255))
        cy += 18

        # BPM
        self._hud_row("BPM", f"{d.get('bpm', 0):.1f}", lx, vx, cy)
        cy += 16

        # Phase bar
        phase = d.get('phase', 0)
        self._hud_label("Phase", lx, cy)
        self._hud_bar(vx, cy + 1, bar_w, 11, phase, (0, 200, 255))
        self._hud_small_val(f"{phase:.2f}", vx + bar_w + 6, cy)
        cy += 16

        # Status
        status = d.get('status', 'coasting')
        locked = status == 'locked'
        color = (50, 255, 100) if locked else (255, 200, 50)
        self._hud_label("Status", lx, cy)
        pygame.draw.circle(self.screen, color, (vx + 5, cy + 6), 4)
        self.screen.blit(self._hud_value(status, color), (vx + 14, cy))
        cy += 16

        # Confidence bar
        conf = d.get('confidence', 0)
        self._hud_label("Confidence", lx, cy)
        bar_color = (50, 255, 100) if conf >= 0.3 else (255, 60, 60)
        self._hud_bar(vx, cy + 1, bar_w, 11, min(1.0, max(0.0, conf)), bar_color)
        self._hud_small_val(f"{conf:.2f}", vx + bar_w + 6, cy)
        cy += 16

        # Beat Tag
        tag = d.get('beat_tag', '')
        self._hud_label("Beat Tag", lx, cy)
        self.screen.blit(self._hud_value(tag, (100, 220, 255)), (vx, cy))
        cy += 22

        # ── separator ──
        pygame.draw.line(self.screen, (80, 40, 120),
                         (px + 8, cy), (px + pw - 8, cy), 1)
        cy += 8

        # ── ONSETS ────────────────────────────────────
        self._hud_section("ONSETS", lx, cy, (200, 80, 255))
        cy += 18

        # Beat / Real / Dropped indicators
        self._hud_label("Beat", lx, cy)
        self._hud_indicator(lx + 40, cy + 5, d.get('is_beat', False), (50, 120, 255))
        self._hud_label("Real", lx + 65, cy)
        self._hud_indicator(lx + 100, cy + 5, d.get('is_real_beat', False), (50, 255, 50))
        self._hud_label("Drop", lx + 125, cy)
        self._hud_indicator(lx + 160, cy + 5, d.get('is_dropped_beat', False), (255, 50, 50))
        cy += 16

        # Flux Baseline
        self._hud_row("Flux Base", f"{d.get('flux_baseline', 0):.1f}", lx, vx, cy)
        cy += 22

        # ── separator ──
        pygame.draw.line(self.screen, (80, 40, 120),
                         (px + 8, cy), (px + pw - 8, cy), 1)
        cy += 8

        # ── STRUCTURE ─────────────────────────────────
        self._hud_section("STRUCTURE", lx, cy, (200, 80, 255))
        cy += 18

        # Asserved Novelty bar
        nov = d.get('asserved_novelty', 0)
        self._hud_label("Novelty", lx, cy)
        bar_color = (255, 220, 50) if nov < 0.6 else (255, 60, 60)
        self._hud_bar(vx, cy + 1, bar_w, 11, min(1.0, max(0.0, nov)), bar_color)
        self._hud_small_val(f"{nov:.2f}", vx + bar_w + 6, cy)
        cy += 16

        # Combined Novelty
        self._hud_row("Combined", f"{d.get('combined_novelty', 0):.3f}", lx, vx, cy)
        cy += 16

        # Song / V-C / Silence row
        self._hud_label("Song", lx, cy)
        self._hud_indicator(lx + 38, cy + 5, d.get('is_song_change', False), (255, 50, 50))
        self._hud_label("V/C", lx + 63, cy)
        self._hud_indicator(lx + 93, cy + 5, d.get('is_verse_chorus_change', False), (255, 220, 50))
        sil = d.get('silence_frames', 0)
        self._hud_label("Silence", lx + 118, cy)
        sil_color = (255, 60, 60) if sil > 30 else (200, 200, 200)
        self.screen.blit(self._hud_value(str(sil), sil_color), (lx + 170, cy))

    # ── HUD drawing helpers ──

    def _hud_value(self, text, color=(255, 255, 255)):
        key = (text, color)
        s = self._hud_value_cache.get(key)
        if s is None:
            if len(self._hud_value_cache) > 128:
                self._hud_value_cache.clear()
            s = self._hud_value_cache[key] = self._hud_value_font.render(str(text), True, color)
        return s

    def _hud_section(self, text, x, y, color):
        s = self._hud_section_cache.get((text, color))
        if s is None:
            s = self._hud_section_cache[(text, color)] = self._hud_section_font.render(text, True, color)
        self.screen.blit(s, (x, y))

    def _hud_label(self, text, x, y):
        s = self._hud_label_cache.get(text)
        if s is None:
            s = self._hud_label_cache[text] = self._hud_label_font.render(text, True, (150, 150, 160))
        self.screen.blit(s, (x, y))

    def _hud_row(self, label, value, lx, vx, y):
        self._hud_label(label, lx, y)
        self.screen.blit(self._hud_value(value), (vx, y))

    def _hud_small_val(self, text, x, y):
        s = self._hud_small_val_cache.get(text)
        if s is None:
            if len(self._hud_small_val_cache) > 128:
                self._hud_small_val_cache.clear()
            s = self._hud_small_val_cache[text] = self._hud_label_font.render(str(text), True, (200, 200, 200))
        self.screen.blit(s, (x, y))

    def _hud_bar(self, x, y, w, h, value, fill_color):
        pygame.draw.rect(self.screen, (40, 40, 50), (x, y, w, h))
        fw = int(max(0.0, min(1.0, value)) * w)
        if fw > 0:
            pygame.draw.rect(self.screen, fill_color, (x, y, fw, h))
        pygame.draw.rect(self.screen, (70, 70, 80), (x, y, w, h), 1)

    def _hud_indicator(self, x, y, active, active_color):
        color = active_color if active else (45, 45, 50)
        pygame.draw.circle(self.screen, color, (x, y), 5)
        pygame.draw.circle(self.screen, (80, 80, 90), (x, y), 5, 1)

visualizer = FakeLedsVisualizer()

from hardware.HardwareInterface import HardwareInterface

class Fake_leds(HardwareInterface):
    def __init__(self, nb_of_leds):
        self.nb_of_leds = nb_of_leds
        self.data = np.zeros((nb_of_leds, 3), dtype=int)
        self.strip_id = visualizer.register_strip(nb_of_leds)
        self._analyzer = None

    def set_analyzer(self, analyzer):
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
        visualizer.update_strip(self.strip_id, self.data)
        visualizer.show()

    def set_audio_player(self, audio_player):
        visualizer.set_audio_player(audio_player)

    def set_segment_mode(self, segment_name, mode_name, target_mode_name=None):
        """
        Forward the current active mode (and optional in-transition target mode)
        for a logical segment to the shared visualizer so it can be rendered.
        Converts the public segment name (e.g. "Segment v4") to the internal
        key used by the visualizer (e.g. "segment_v4").
        """
        internal_name = segment_name.lower().replace(" ", "_")
        visualizer.set_segment_mode(internal_name, mode_name, target_mode_name)

    @staticmethod
    def _load_visualizer_segments_def(infos=None):
        return FakeLedsVisualizer._load_visualizer_segments_def(infos)

