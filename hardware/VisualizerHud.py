"""hardware/VisualizerHud.py - HUD facade for Fake_leds: Transition Tester panel plus event routing.

Layering: AnalyzerHud (Music Analyzer HUD + drawing primitives)
          -> ShowControlPanel (SHOW CONTROL + SEGMENT MODES pickers)
          -> VisualizerHud (TRANSITION TESTER + mouse/keyboard dispatch).
"""

import time
from typing import Any, Callable, Dict, Optional, Tuple
import pygame
from hardware.ShowControlPanel import CONTROL_PANEL_H, ShowControlPanel
from transitions.api import AVAILABLE_TRANSITIONS

__all__ = ["VisualizerHud", "CONTROL_PANEL_H"]


class VisualizerHud(ShowControlPanel):
    """Renders the Music Analyzer HUD, Transition Tester, and Show Control panels."""

    def __init__(self) -> None:
        super().__init__()
        self._panel_bg_surf = None
        self.transitions = list(AVAILABLE_TRANSITIONS)
        self.selected_idx, self.selected_duration, self._last_request_ts = 0, 3.0, 0.0
        self._update_transition_rects(320, 685)

    def _update_transition_rects(self, px: int, py: int) -> None:
        self._rect_prev = pygame.Rect(px + 14, py + 41, 36, 28)
        self._rect_next = pygame.Rect(px + 350, py + 41, 36, 28)
        self._rect_dur_m5 = pygame.Rect(px + 14, py + 81, 48, 26)
        self._rect_dur_m1 = pygame.Rect(px + 68, py + 81, 44, 26)
        self._rect_dur_p1 = pygame.Rect(px + 288, py + 81, 44, 26)
        self._rect_dur_p5 = pygame.Rect(px + 338, py + 81, 48, 26)
        self._rect_send = pygame.Rect(px + 14, py + 119, 372, 34)

    @property
    def selected_transition(self) -> str:
        return self.transitions[self.selected_idx % len(self.transitions)]

    def step_transition(self, delta: int) -> None:
        self.selected_idx = (self.selected_idx + delta) % len(self.transitions)

    def adjust_duration(self, delta: float) -> None:
        self.selected_duration = round(max(0.2, min(10.0, self.selected_duration + delta)), 1)

    def _send_transition(self, on_send: Callable[[str, float], None]) -> None:
        self._last_request_ts = time.monotonic()
        on_send(self.selected_transition, self.selected_duration)

    def handle_event(
        self, event: Any, on_send: Callable[[str, float], None],
        on_command: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> bool:
        """Handle mouse clicks and hotkeys for the Transition Tester and show-control panels."""
        if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, "button", 0) == 1:
            return self._handle_click(event.pos, on_send, on_command)
        if event.type == pygame.KEYDOWN:
            return self._handle_key(event, on_send, on_command)
        return False

    def _handle_click(
        self, pos: Tuple[int, int], on_send: Callable[[str, float], None],
        on_command: Optional[Callable[[Dict[str, Any]], None]],
    ) -> bool:
        if on_command is not None and self._handle_control_click(pos, on_command):
            return True
        if self._rect_prev.collidepoint(pos) or self._rect_next.collidepoint(pos):
            self.step_transition(-1 if self._rect_prev.collidepoint(pos) else 1)
            return True
        duration_steps = (
            (self._rect_dur_m5, -0.5), (self._rect_dur_m1, -0.1),
            (self._rect_dur_p1, 0.1), (self._rect_dur_p5, 0.5),
        )
        for rect, delta in duration_steps:
            if rect.collidepoint(pos):
                self.adjust_duration(delta)
                return True
        if self._rect_send.collidepoint(pos):
            self._send_transition(on_send)
            return True
        return False

    def _handle_key(
        self, event: Any, on_send: Callable[[str, float], None],
        on_command: Optional[Callable[[Dict[str, Any]], None]],
    ) -> bool:
        if event.key in (pygame.K_LEFTBRACKET, pygame.K_RIGHTBRACKET):
            self.step_transition(-1 if event.key == pygame.K_LEFTBRACKET else 1)
            return True
        if event.key in (pygame.K_MINUS, pygame.K_EQUALS):
            self.adjust_duration(-0.1 if event.key == pygame.K_MINUS else 0.1)
            return True
        if event.key == pygame.K_t:
            self._send_transition(on_send)
            return True
        return on_command is not None and self._handle_control_key(event, on_command)

    def _build_panel_surfaces(self) -> None:
        super()._build_panel_surfaces()
        self._panel_title_surf = self._hud_title_font.render("TRANSITION TESTER", True, (180, 240, 255))
        self._panel_bg_surf = pygame.Surface((400, 205), pygame.SRCALPHA)
        self._panel_bg_surf.fill((12, 18, 26, 225))

    def draw_transition_panel(
        self, screen: Any, transition_data: Optional[Dict[str, Any]], px: int = 320, py: int = 685,
    ) -> None:
        """Draw the interactive Transition Selector + Duration + Send Request panel."""
        self._ensure_fonts()
        pw, ph = 400, 205
        self._update_transition_rects(px, py)
        screen.blit(self._panel_bg_surf, (px, py))
        pygame.draw.rect(screen, (60, 180, 220), (px, py, pw, ph), 2)
        screen.blit(self._panel_title_surf, (px + pw // 2 - self._panel_title_surf.get_width() // 2, py + 8))
        pygame.draw.line(screen, (40, 100, 130), (px + 8, py + 28), (px + pw - 8, py + 28), 1)

        self._draw_button(screen, self._rect_prev, "<", (45, 65, 85), (100, 190, 230))
        self._draw_button(screen, self._rect_next, ">", (45, 65, 85), (100, 190, 230))
        sel_w = self._rect_next.left - self._rect_prev.right - 12
        sel_rect = pygame.Rect(self._rect_prev.right + 6, self._rect_prev.top, sel_w, 28)
        self._draw_box(screen, sel_rect, (22, 30, 42), (70, 120, 150), radius=0)
        idx_str = f"[{self.selected_idx + 1}/{len(self.transitions)}] {self.selected_transition}"
        surf = self._hud_value(idx_str, (255, 240, 150) if self.selected_transition == "AUTO" else (140, 240, 255))
        screen.blit(surf, surf.get_rect(center=sel_rect.center))

        duration_buttons = (
            (self._rect_dur_m5, "-0.5"), (self._rect_dur_m1, "-0.1"),
            (self._rect_dur_p1, "+0.1"), (self._rect_dur_p5, "+0.5"),
        )
        for rect, lbl in duration_buttons:
            self._draw_button(screen, rect, lbl, (40, 55, 70), (90, 150, 190))
        dur_w = self._rect_dur_p1.left - self._rect_dur_m1.right - 12
        dur_rect = pygame.Rect(self._rect_dur_m1.right + 6, self._rect_dur_m1.top, dur_w, 26)
        self._draw_box(screen, dur_rect, (22, 30, 42), (70, 120, 150), radius=0)
        dur_surf = self._hud_value(f"Duration: {self.selected_duration:.1f}s", (240, 240, 255))
        screen.blit(dur_surf, dur_surf.get_rect(center=dur_rect.center))

        just_clicked = (time.monotonic() - self._last_request_ts) < 0.25
        self._draw_button(
            screen, self._rect_send, "SEND REQUEST (Hotkey: T)",
            (40, 170, 110) if just_clicked else (28, 110, 145),
            (120, 255, 190) if just_clicked else (90, 210, 250),
        )

        td = transition_data or {}
        is_in_trans = bool(td.get("is_in_transition", False))
        recently_sent = (time.monotonic() - self._last_request_ts) < 1.2
        is_pending = bool(td.get("is_pending", False)) or (recently_sent and not is_in_trans)
        progress, active_tech = float(td.get("progress", 0.0)), td.get("technique") or self.selected_transition

        if is_in_trans:
            status_txt, status_col = f"ACTIVE: {active_tech} ({int(progress * 100)}%)", (80, 255, 160)
        elif is_pending:
            status_txt, status_col = "QUEUED: waiting for beat (<= 1.2s)...", (255, 210, 70)
        else:
            status_txt, status_col = "READY  |  Keys: [ / ] Select, - / = Duration, T Send", (160, 185, 200)
        screen.blit(self._hud_value(status_txt, status_col), (px + 14, py + 162))
        bar_value = progress if is_in_trans else (1.0 if is_pending else 0.0)
        self._hud_bar(screen, px + 14, py + 180, pw - 28, 12, bar_value, status_col)
