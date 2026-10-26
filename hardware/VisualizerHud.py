"""
hardware/VisualizerHud.py - HUD overlays and interactive Transition Tester panel for Fake_leds.
"""

import time
from typing import Any, Callable, Dict, Optional, Tuple
import pygame
from transitions.api import AVAILABLE_TRANSITIONS


class VisualizerHud:
    """Renders the Music Analyzer HUD and the interactive Transition Tester panel."""

    def __init__(self) -> None:
        self._fonts_ready = False
        self._hud_section_cache: Dict[Tuple[str, Tuple[int, int, int]], Any] = {}
        self._hud_label_cache: Dict[str, Any] = {}
        self._hud_value_cache: Dict[Tuple[str, Tuple[int, int, int]], Any] = {}
        self._hud_small_val_cache: Dict[str, Any] = {}
        self._hud_bg_surf: Optional[Any] = None
        self._panel_bg_surf: Optional[Any] = None

        # Transition Tester state
        self.transitions = list(AVAILABLE_TRANSITIONS)
        self.selected_idx: int = 0
        self.selected_duration: float = 1.2
        self._last_request_ts: float = 0.0

        # Clickable rects populated on draw
        self._rect_prev = pygame.Rect(334, 726, 36, 28)
        self._rect_next = pygame.Rect(670, 726, 36, 28)
        self._rect_dur_m5 = pygame.Rect(334, 766, 48, 26)
        self._rect_dur_m1 = pygame.Rect(388, 766, 44, 26)
        self._rect_dur_p1 = pygame.Rect(608, 766, 44, 26)
        self._rect_dur_p5 = pygame.Rect(658, 766, 48, 26)
        self._rect_send = pygame.Rect(334, 804, 372, 34)

    @property
    def selected_transition(self) -> str:
        return self.transitions[self.selected_idx % len(self.transitions)]

    def step_transition(self, delta: int) -> None:
        self.selected_idx = (self.selected_idx + delta) % len(self.transitions)

    def adjust_duration(self, delta: float) -> None:
        self.selected_duration = round(max(0.2, min(10.0, self.selected_duration + delta)), 1)

    def handle_event(self, event: Any, on_send: Callable[[str, float], None]) -> bool:
        """Handle mouse clicks and hotkeys for the Transition Tester panel."""
        if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, "button", 0) == 1:
            pos = event.pos
            if self._rect_prev.collidepoint(pos):
                self.step_transition(-1)
                return True
            if self._rect_next.collidepoint(pos):
                self.step_transition(1)
                return True
            if self._rect_dur_m5.collidepoint(pos):
                self.adjust_duration(-0.5)
                return True
            if self._rect_dur_m1.collidepoint(pos):
                self.adjust_duration(-0.1)
                return True
            if self._rect_dur_p1.collidepoint(pos):
                self.adjust_duration(0.1)
                return True
            if self._rect_dur_p5.collidepoint(pos):
                self.adjust_duration(0.5)
                return True
            if self._rect_send.collidepoint(pos):
                self._last_request_ts = time.monotonic()
                on_send(self.selected_transition, self.selected_duration)
                return True
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFTBRACKET:
                self.step_transition(-1)
                return True
            if event.key == pygame.K_RIGHTBRACKET:
                self.step_transition(1)
                return True
            if event.key == pygame.K_MINUS:
                self.adjust_duration(-0.1)
                return True
            if event.key == pygame.K_EQUALS:
                self.adjust_duration(0.1)
                return True
            if event.key == pygame.K_t:
                self._last_request_ts = time.monotonic()
                on_send(self.selected_transition, self.selected_duration)
                return True
        return False

    def _ensure_fonts(self) -> None:
        if self._fonts_ready:
            return
        self._fonts_ready = True
        self._hud_title_font = pygame.font.SysFont("consolas", 14, bold=True)
        self._hud_section_font = pygame.font.SysFont("consolas", 12, bold=True)
        self._hud_label_font = pygame.font.SysFont("consolas", 11)
        self._hud_value_font = pygame.font.SysFont("consolas", 11, bold=True)
        self._hud_title_surf = self._hud_title_font.render("MUSIC ANALYZER", True, (220, 220, 255))
        self._panel_title_surf = self._hud_title_font.render("TRANSITION TESTER", True, (180, 240, 255))
        self._modes_title_surf = self._hud_title_font.render("SEGMENT MODES", True, (200, 235, 255))
        self._hud_bg_surf = pygame.Surface((295, 345), pygame.SRCALPHA)
        self._hud_bg_surf.fill((12, 12, 20, 215))
        self._panel_bg_surf = pygame.Surface((400, 205), pygame.SRCALPHA)
        self._panel_bg_surf.fill((12, 18, 26, 225))
        self._modes_bg_surf: Optional[Any] = None

    def draw_segment_modes_table(
        self,
        screen: Any,
        segments_def: Any,
        segment_modes: Dict[str, Dict[str, Any]],
        mode_font: Any,
        mode_label_cache: Dict[Any, Any],
    ) -> None:
        """Draw the segment-to-mode table on the left side of the simulator screen."""
        self._ensure_fonts()
        rows = []
        seen = set()
        for ch_defs in segments_def:
            for (_size, _orient, _sx, _sy, name, border_color) in ch_defs:
                if name not in seen:
                    seen.add(name)
                    rows.append((name, border_color))
        rows.sort(key=lambda r: (0 if "_v" in r[0] else 1, r[0]))

        row_h = 22
        px, py, pw = 10, 185, 295
        ph = 38 + max(1, len(rows)) * row_h
        if self._modes_bg_surf is None or self._modes_bg_surf.get_height() != ph:
            self._modes_bg_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
            self._modes_bg_surf.fill((12, 16, 24, 220))

        screen.blit(self._modes_bg_surf, (px, py))
        pygame.draw.rect(screen, (70, 140, 200), (px, py, pw, ph), 2)
        screen.blit(self._modes_title_surf, (px + pw // 2 - self._modes_title_surf.get_width() // 2, py + 7))
        pygame.draw.line(screen, (45, 90, 130), (px + 8, py + 27), (px + pw - 8, py + 27), 1)

        cy = py + 33
        for idx, (name, border_color) in enumerate(rows):
            if idx % 2 == 1:
                pygame.draw.rect(screen, (20, 26, 38), (px + 4, cy - 2, pw - 8, row_h - 1))
            pygame.draw.circle(screen, border_color, (px + 14, cy + 7), 4)
            short_name = name.replace("segment_", "")
            self._hud_label(screen, short_name, px + 24, cy + 1)

            mode_info = segment_modes.get(name)
            if mode_info is not None and mode_info.get("mode"):
                mode_label = mode_info["mode"]
                has_target = bool(mode_info.get("target"))
                if has_target:
                    mode_label = f"{mode_label} -> {mode_info['target']}"
                color = (255, 215, 90) if has_target else (130, 235, 255)
            else:
                mode_label = "-"
                color = (100, 110, 125)

            m_key = (mode_label, color)
            m_surf = mode_label_cache.get(m_key)
            if m_surf is None:
                if len(mode_label_cache) > 256:
                    mode_label_cache.clear()
                m_surf = mode_label_cache[m_key] = mode_font.render(mode_label, True, color)
            screen.blit(m_surf, (px + 72, cy + 1))
            cy += row_h

    def draw_transition_panel(self, screen: Any, transition_data: Optional[Dict[str, Any]]) -> None:
        """Draw the interactive Transition Selector + Duration + Send Request panel."""
        self._ensure_fonts()
        px, py, pw, ph = 320, 685, 400, 205
        screen.blit(self._panel_bg_surf, (px, py))
        pygame.draw.rect(screen, (60, 180, 220), (px, py, pw, ph), 2)

        # Header
        screen.blit(self._panel_title_surf, (px + pw // 2 - self._panel_title_surf.get_width() // 2, py + 8))
        pygame.draw.line(screen, (40, 100, 130), (px + 8, py + 28), (px + pw - 8, py + 28), 1)

        # Row 1: Transition Selector
        self._draw_button(screen, self._rect_prev, "<", (45, 65, 85), (100, 190, 230))
        self._draw_button(screen, self._rect_next, ">", (45, 65, 85), (100, 190, 230))
        sel_rect = pygame.Rect(self._rect_prev.right + 6, self._rect_prev.top, self._rect_next.left - self._rect_prev.right - 12, 28)
        pygame.draw.rect(screen, (22, 30, 42), sel_rect)
        pygame.draw.rect(screen, (70, 120, 150), sel_rect, 1)
        idx_str = f"[{self.selected_idx + 1}/{len(self.transitions)}] {self.selected_transition}"
        surf = self._hud_value(idx_str, (255, 240, 150) if self.selected_transition == "AUTO" else (140, 240, 255))
        screen.blit(surf, surf.get_rect(center=sel_rect.center))

        # Row 2: Duration Selector (N seconds)
        self._draw_button(screen, self._rect_dur_m5, "-0.5", (40, 55, 70), (90, 150, 190))
        self._draw_button(screen, self._rect_dur_m1, "-0.1", (40, 55, 70), (90, 150, 190))
        self._draw_button(screen, self._rect_dur_p1, "+0.1", (40, 55, 70), (90, 150, 190))
        self._draw_button(screen, self._rect_dur_p5, "+0.5", (40, 55, 70), (90, 150, 190))
        dur_rect = pygame.Rect(self._rect_dur_m1.right + 6, self._rect_dur_m1.top, self._rect_dur_p1.left - self._rect_dur_m1.right - 12, 26)
        pygame.draw.rect(screen, (22, 30, 42), dur_rect)
        pygame.draw.rect(screen, (70, 120, 150), dur_rect, 1)
        dur_surf = self._hud_value(f"Duration: {self.selected_duration:.1f}s", (240, 240, 255))
        screen.blit(dur_surf, dur_surf.get_rect(center=dur_rect.center))

        # Row 3: SEND REQUEST Button
        just_clicked = (time.monotonic() - self._last_request_ts) < 0.25
        btn_bg = (40, 170, 110) if just_clicked else (28, 110, 145)
        btn_border = (120, 255, 190) if just_clicked else (90, 210, 250)
        self._draw_button(screen, self._rect_send, "SEND REQUEST (Hotkey: T)", btn_bg, btn_border)

        # Row 4: Live Status & Progress Bar
        td = transition_data or {}
        is_in_trans = bool(td.get("is_in_transition", False))
        is_pending = bool(td.get("is_pending", False)) or ((time.monotonic() - self._last_request_ts) < 1.2 and not is_in_trans)
        progress = float(td.get("progress", 0.0))
        active_tech = td.get("technique") or self.selected_transition

        sy = py + 162
        if is_in_trans:
            status_txt = f"ACTIVE: {active_tech} ({int(progress * 100)}%)"
            status_col = (80, 255, 160)
        elif is_pending:
            status_txt = f"QUEUED: waiting for beat (<= 1.2s)..."
            status_col = (255, 210, 70)
        else:
            status_txt = "READY  |  Keys: [ / ] Select, - / = Duration, T Send"
            status_col = (160, 185, 200)

        st_surf = self._hud_value(status_txt, status_col)
        screen.blit(st_surf, (px + 14, sy))
        self._hud_bar(screen, px + 14, sy + 18, pw - 28, 12, progress if is_in_trans else (1.0 if is_pending else 0.0), status_col)

    def _draw_button(self, screen: Any, rect: pygame.Rect, label: str, bg: Tuple[int, int, int], border: Tuple[int, int, int]) -> None:
        pygame.draw.rect(screen, bg, rect, border_radius=4)
        pygame.draw.rect(screen, border, rect, 1, border_radius=4)
        surf = self._hud_value(label, (240, 248, 255))
        screen.blit(surf, surf.get_rect(center=rect.center))

    def draw_analyzer_hud(self, screen: Any, d: Optional[Dict[str, Any]]) -> None:
        """Draw the music analyzer HUD overlay in the bottom-left corner."""
        if d is None:
            return
        self._ensure_fonts()
        px, py, pw, ph = 10, 545, 295, 345
        screen.blit(self._hud_bg_surf, (px, py))
        pygame.draw.rect(screen, (160, 60, 220), (px, py, pw, ph), 2)
        screen.blit(self._hud_title_surf, (px + pw // 2 - self._hud_title_surf.get_width() // 2, py + 8))
        pygame.draw.line(screen, (80, 40, 120), (px + 8, py + 28), (px + pw - 8, py + 28), 1)

        lx, vx, bar_w, cy = px + 12, px + 120, 120, py + 36
        self._hud_section(screen, "FLYWHEEL", lx, cy, (200, 80, 255))
        cy += 18
        self._hud_row(screen, "BPM", f"{d.get('bpm', 0):.1f}", lx, vx, cy)
        cy += 16

        phase = d.get("phase", 0)
        self._hud_label(screen, "Phase", lx, cy)
        self._hud_bar(screen, vx, cy + 1, bar_w, 11, phase, (0, 200, 255))
        self._hud_small_val(screen, f"{phase:.2f}", vx + bar_w + 6, cy)
        cy += 16

        status = d.get("status", "coasting")
        color = (50, 255, 100) if status == "locked" else (255, 200, 50)
        self._hud_label(screen, "Status", lx, cy)
        pygame.draw.circle(screen, color, (vx + 5, cy + 6), 4)
        screen.blit(self._hud_value(status, color), (vx + 14, cy))
        cy += 16

        conf = d.get("confidence", 0)
        self._hud_label(screen, "Confidence", lx, cy)
        self._hud_bar(screen, vx, cy + 1, bar_w, 11, min(1.0, max(0.0, conf)), (50, 255, 100) if conf >= 0.3 else (255, 60, 60))
        self._hud_small_val(screen, f"{conf:.2f}", vx + bar_w + 6, cy)
        cy += 16

        self._hud_label(screen, "Beat Tag", lx, cy)
        screen.blit(self._hud_value(d.get("beat_tag", ""), (100, 220, 255)), (vx, cy))
        cy += 22
        pygame.draw.line(screen, (80, 40, 120), (px + 8, cy), (px + pw - 8, cy), 1)
        cy += 8

        self._hud_section(screen, "ONSETS", lx, cy, (200, 80, 255))
        cy += 18
        self._hud_label(screen, "Beat", lx, cy)
        self._hud_indicator(screen, lx + 40, cy + 5, d.get("is_beat", False), (50, 120, 255))
        self._hud_label(screen, "Real", lx + 65, cy)
        self._hud_indicator(screen, lx + 100, cy + 5, d.get("is_real_beat", False), (50, 255, 50))
        self._hud_label(screen, "Drop", lx + 125, cy)
        self._hud_indicator(screen, lx + 160, cy + 5, d.get("is_dropped_beat", False), (255, 50, 50))
        cy += 16
        self._hud_row(screen, "Flux Base", f"{d.get('flux_baseline', 0):.1f}", lx, vx, cy)
        cy += 22
        pygame.draw.line(screen, (80, 40, 120), (px + 8, cy), (px + pw - 8, cy), 1)
        cy += 8

        self._hud_section(screen, "STRUCTURE", lx, cy, (200, 80, 255))
        cy += 18
        nov = d.get("asserved_novelty", 0)
        self._hud_label(screen, "Novelty", lx, cy)
        self._hud_bar(screen, vx, cy + 1, bar_w, 11, min(1.0, max(0.0, nov)), (255, 220, 50) if nov < 0.6 else (255, 60, 60))
        self._hud_small_val(screen, f"{nov:.2f}", vx + bar_w + 6, cy)
        cy += 16
        self._hud_row(screen, "Combined", f"{d.get('combined_novelty', 0):.3f}", lx, vx, cy)
        cy += 16
        self._hud_label(screen, "Song", lx, cy)
        self._hud_indicator(screen, lx + 38, cy + 5, d.get("is_song_change", False), (255, 50, 50))
        self._hud_label(screen, "V/C", lx + 63, cy)
        self._hud_indicator(screen, lx + 93, cy + 5, d.get("is_verse_chorus_change", False), (255, 220, 50))
        sil = d.get("silence_frames", 0)
        self._hud_label(screen, "Silence", lx + 118, cy)
        screen.blit(self._hud_value(str(sil), (255, 60, 60) if sil > 30 else (200, 200, 200)), (lx + 170, cy))

    def _hud_value(self, text: str, color: Tuple[int, int, int] = (255, 255, 255)) -> Any:
        key = (text, color)
        s = self._hud_value_cache.get(key)
        if s is None:
            if len(self._hud_value_cache) > 128:
                self._hud_value_cache.clear()
            s = self._hud_value_cache[key] = self._hud_value_font.render(str(text), True, color)
        return s

    def _hud_section(self, screen: Any, text: str, x: int, y: int, color: Tuple[int, int, int]) -> None:
        s = self._hud_section_cache.get((text, color))
        if s is None:
            s = self._hud_section_cache[(text, color)] = self._hud_section_font.render(text, True, color)
        screen.blit(s, (x, y))

    def _hud_label(self, screen: Any, text: str, x: int, y: int) -> None:
        s = self._hud_label_cache.get(text)
        if s is None:
            s = self._hud_label_cache[text] = self._hud_label_font.render(text, True, (150, 150, 160))
        screen.blit(s, (x, y))

    def _hud_row(self, screen: Any, label: str, value: str, lx: int, vx: int, y: int) -> None:
        self._hud_label(screen, label, lx, y)
        screen.blit(self._hud_value(value), (vx, y))

    def _hud_small_val(self, screen: Any, text: str, x: int, y: int) -> None:
        s = self._hud_small_val_cache.get(text)
        if s is None:
            if len(self._hud_small_val_cache) > 128:
                self._hud_small_val_cache.clear()
            s = self._hud_small_val_cache[text] = self._hud_label_font.render(str(text), True, (200, 200, 200))
        screen.blit(s, (x, y))

    def _hud_bar(self, screen: Any, x: int, y: int, w: int, h: int, value: float, fill_color: Tuple[int, int, int]) -> None:
        pygame.draw.rect(screen, (40, 40, 50), (x, y, w, h))
        fw = int(max(0.0, min(1.0, value)) * w)
        if fw > 0:
            pygame.draw.rect(screen, fill_color, (x, y, fw, h))
        pygame.draw.rect(screen, (70, 70, 80), (x, y, w, h), 1)

    def _hud_indicator(self, screen: Any, x: int, y: int, active: bool, active_color: Tuple[int, int, int]) -> None:
        pygame.draw.circle(screen, active_color if active else (45, 45, 50), (x, y), 5)
        pygame.draw.circle(screen, (80, 80, 90), (x, y), 5, 1)
