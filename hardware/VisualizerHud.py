"""hardware/VisualizerHud.py - HUD overlays, Transition Tester & Show Control panels for Fake_leds."""

import json
import os
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
import pygame
from mood.api import create_mood_service
from transitions.api import AVAILABLE_TRANSITIONS

# Height of the SHOW CONTROL (HOLD / LIVE + Global Mode Picker + Mood Picker) panel drawn under the Transition Tester.
CONTROL_PANEL_H = 205


def _load_global_mode_names() -> List[str]:
    """Load sorted Global Mode names from config/modes.json."""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config", "modes.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            names = sorted(str(m["name"]) for m in json.load(f).get("global_modes", []) if isinstance(m, dict) and m.get("name"))
        if names:
            return names
    except Exception:
        pass
    return ["Architectural VU Equalizer", "Concentric Radial Ripple", "Horizon Scanning Blade", "Monolithic Beat Blast", "Spectral Avalanche"]


def _load_mood_catalog() -> Tuple[List[str], Dict[str, List[Tuple[int, int, int]]]]:
    """Query mood.api once at init for curated palette names and their 4 RGB swatches."""
    names = list(create_mood_service().get_status().available_palettes)
    swatches = {n: [(int(c[0]), int(c[1]), int(c[2])) for c in create_mood_service(initial_palette=n).colors()] for n in names}
    return names, swatches


class VisualizerHud:
    """Renders the Music Analyzer HUD, Transition Tester, and Show Control panels."""

    def __init__(self) -> None:
        self._fonts_ready = False
        self._hud_section_cache: Dict[Tuple[str, Tuple[int, int, int]], Any] = {}
        self._hud_label_cache: Dict[str, Any] = {}
        self._hud_value_cache: Dict[Tuple[str, Tuple[int, int, int]], Any] = {}
        self._hud_small_val_cache: Dict[str, Any] = {}
        self._hud_bg_surf = self._panel_bg_surf = self._control_bg_surf = self._modes_bg_surf = None

        self.transitions = list(AVAILABLE_TRANSITIONS)
        self.selected_idx, self.selected_duration, self._last_request_ts = 0, 3.0, 0.0
        self.is_locked, self.global_scope, self.selected_global_idx = False, False, 0
        self.mode_catalog: Dict[str, Any] = {}
        self.global_modes: List[str] = _load_global_mode_names()
        self.mood_palettes, self._palette_swatches = _load_mood_catalog()
        self.selected_mood_idx: int = 0
        self.mood_palette: str = self.mood_palettes[0] if self.mood_palettes else "Cyberpunk"
        self.mood_target: str = self.mood_palette
        self.mood_progress, self.mood_is_transitioning, self.mood_auto_scene = 1.0, False, True
        self.mood_colors: List[Tuple[int, int, int]] = list(self._palette_swatches.get(self.mood_palette, ()))
        self._row_rects: list = []
        self._modes_snapshot: Dict[str, Dict[str, Any]] = {}
        self._optimistic_modes: Dict[str, Tuple[str, float]] = {}
        self._last_hold_ts, self._last_scope_ts, self._last_mood_ts, self._last_auto_ts = 0.0, 0.0, 0.0, 0.0
        self._update_control_rects(320, 229)
        self._update_transition_rects(320, 685)

    def _update_control_rects(self, px: int, py: int) -> None:
        self._rect_hold = pygame.Rect(px + 14, py + 34, 372, 30)
        self._rect_scope = pygame.Rect(px + 14, py + 69, 372, 28)
        self._rect_global_prev, self._rect_global_next = pygame.Rect(px + 14, py + 102, 36, 26), pygame.Rect(px + 350, py + 102, 36, 26)
        self._rect_global_apply = pygame.Rect(px + 56, py + 102, 288, 26)
        self._rect_mood_prev, self._rect_mood_next = pygame.Rect(px + 14, py + 134, 36, 26), pygame.Rect(px + 350, py + 134, 36, 26)
        self._rect_mood_apply = pygame.Rect(px + 56, py + 134, 288, 26)
        self._rect_mood_auto = pygame.Rect(px + 14, py + 166, 86, 20)

    def _update_transition_rects(self, px: int, py: int) -> None:
        self._rect_prev, self._rect_next = pygame.Rect(px + 14, py + 41, 36, 28), pygame.Rect(px + 350, py + 41, 36, 28)
        self._rect_dur_m5, self._rect_dur_m1 = pygame.Rect(px + 14, py + 81, 48, 26), pygame.Rect(px + 68, py + 81, 44, 26)
        self._rect_dur_p1, self._rect_dur_p5 = pygame.Rect(px + 288, py + 81, 44, 26), pygame.Rect(px + 338, py + 81, 48, 26)
        self._rect_send = pygame.Rect(px + 14, py + 119, 372, 34)

    @property
    def selected_transition(self) -> str:
        return self.transitions[self.selected_idx % len(self.transitions)]

    @property
    def selected_global_mode(self) -> str:
        return self.global_modes[self.selected_global_idx % len(self.global_modes)] if self.global_modes else ""

    @property
    def selected_mood(self) -> str:
        return self.mood_palettes[self.selected_mood_idx % len(self.mood_palettes)] if self.mood_palettes else ""

    def step_transition(self, delta: int) -> None:
        self.selected_idx = (self.selected_idx + delta) % len(self.transitions)

    def adjust_duration(self, delta: float) -> None:
        self.selected_duration = round(max(0.2, min(10.0, self.selected_duration + delta)), 1)

    def _toggle_hold(self, on_command: Callable[[Dict[str, Any]], None]) -> None:
        self._last_hold_ts = time.monotonic()
        on_command({"type": "set_locked", "locked": not self.is_locked})

    def _toggle_scope(self, on_command: Callable[[Dict[str, Any]], None]) -> None:
        now = time.monotonic()
        self._last_scope_ts, self.global_scope = now, not self.global_scope
        if self.global_scope and self.global_modes:
            gmode = self.selected_global_mode
            self._optimistic_modes.update({k: (gmode, now) for k in self._modes_snapshot})
            on_command({"type": "set_mode_scope", "scope": "global", "mode": gmode})
        else:
            self._optimistic_modes.clear()
            on_command({"type": "set_mode_scope", "scope": "local"})

    def _step_global_mode(self, delta: int, on_command: Callable[[Dict[str, Any]], None]) -> None:
        if not self.global_modes:
            return
        now = time.monotonic()
        self._last_scope_ts, self.global_scope = now, True
        if delta != 0:
            self.selected_global_idx = (self.selected_global_idx + delta) % len(self.global_modes)
        gmode = self.selected_global_mode
        self._optimistic_modes.update({k: (gmode, now) for k in self._modes_snapshot})
        on_command({"type": "set_global_mode", "mode": gmode})

    def _step_mood(self, delta: int, on_command: Callable[[Dict[str, Any]], None]) -> None:
        if not self.mood_palettes:
            return
        self._last_mood_ts = time.monotonic()
        if delta != 0:
            self.selected_mood_idx = (self.selected_mood_idx + delta) % len(self.mood_palettes)
        self.mood_target = pal = self.selected_mood
        if pal in self._palette_swatches and not self.mood_is_transitioning:
            self.mood_colors = list(self._palette_swatches[pal])
        on_command({"type": "set_mood", "palette": pal})

    def _toggle_mood_auto(self, on_command: Callable[[Dict[str, Any]], None]) -> None:
        self._last_auto_ts, self.mood_auto_scene = time.monotonic(), not self.mood_auto_scene
        on_command({"type": "set_mood_auto", "auto_scene": self.mood_auto_scene})

    def _cycle_segment_mode(self, name: str, delta: int, on_command: Callable[[Dict[str, Any]], None]) -> None:
        """Send the previous/next local mode (wrapping) of a segment."""
        seg_id = name[len("segment_"):] if name.startswith("segment_") else name
        raw_modes = self.mode_catalog.get(seg_id) or []
        modes = [m for m in raw_modes if m not in self.global_modes] or raw_modes
        if not modes:
            return
        now = time.monotonic()
        current = (self._modes_snapshot.get(name) or {}).get("mode")
        pending = self._optimistic_modes.get(name)
        if pending is not None and now - pending[1] < 0.5:
            current = pending[0]
        new_mode = modes[(modes.index(current) + delta) % len(modes)] if current in modes else (modes[0] if delta > 0 else modes[-1])
        self.global_scope, self._last_scope_ts = False, now
        self._optimistic_modes[name] = (new_mode, now)
        on_command({"type": "set_segment_mode", "segment": seg_id, "mode": new_mode})

    def handle_event(self, event: Any, on_send: Callable[[str, float], None], on_command: Optional[Callable[[Dict[str, Any]], None]] = None) -> bool:
        """Handle mouse clicks and hotkeys for the Transition Tester and show-control panels."""
        if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, "button", 0) == 1:
            pos = event.pos
            if on_command is not None:
                if self._rect_hold.collidepoint(pos):
                    self._toggle_hold(on_command); return True
                if self._rect_scope.collidepoint(pos):
                    self._toggle_scope(on_command); return True
                for rect, delta in ((self._rect_global_prev, -1), (self._rect_global_next, 1), (self._rect_global_apply, 0)):
                    if rect.collidepoint(pos):
                        self._step_global_mode(delta, on_command); return True
                for rect, delta in ((self._rect_mood_prev, -1), (self._rect_mood_next, 1), (self._rect_mood_apply, 0)):
                    if rect.collidepoint(pos):
                        self._step_mood(delta, on_command); return True
                if self._rect_mood_auto.collidepoint(pos):
                    self._toggle_mood_auto(on_command); return True
                for name, rect_prev, rect_next in self._row_rects:
                    if rect_prev.collidepoint(pos) or rect_next.collidepoint(pos):
                        self._cycle_segment_mode(name, -1 if rect_prev.collidepoint(pos) else 1, on_command); return True
            if self._rect_prev.collidepoint(pos) or self._rect_next.collidepoint(pos):
                self.step_transition(-1 if self._rect_prev.collidepoint(pos) else 1); return True
            for rect, delta in ((self._rect_dur_m5, -0.5), (self._rect_dur_m1, -0.1), (self._rect_dur_p1, 0.1), (self._rect_dur_p5, 0.5)):
                if rect.collidepoint(pos):
                    self.adjust_duration(delta); return True
            if self._rect_send.collidepoint(pos):
                self._last_request_ts = time.monotonic()
                on_send(self.selected_transition, self.selected_duration); return True
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LEFTBRACKET, pygame.K_RIGHTBRACKET):
                self.step_transition(-1 if event.key == pygame.K_LEFTBRACKET else 1); return True
            if event.key in (pygame.K_MINUS, pygame.K_EQUALS):
                self.adjust_duration(-0.1 if event.key == pygame.K_MINUS else 0.1); return True
            if event.key == pygame.K_t:
                self._last_request_ts = time.monotonic()
                on_send(self.selected_transition, self.selected_duration); return True
            if event.key == pygame.K_h and on_command is not None:
                self._toggle_hold(on_command); return True
            if event.key == pygame.K_g and on_command is not None:
                self._toggle_scope(on_command); return True
            if event.key == pygame.K_m and on_command is not None:
                self._step_mood(-1 if (getattr(event, "mod", 0) & pygame.KMOD_SHIFT) else 1, on_command); return True
            if event.key == pygame.K_a and on_command is not None:
                self._toggle_mood_auto(on_command); return True
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
        self._control_title_surf = self._hud_title_font.render("SHOW CONTROL", True, (255, 225, 160))
        self._modes_title_surf = self._hud_title_font.render("SEGMENT MODES", True, (200, 235, 255))
        self._hud_bg_surf = pygame.Surface((295, 345), pygame.SRCALPHA); self._hud_bg_surf.fill((12, 12, 20, 215))
        self._panel_bg_surf = pygame.Surface((400, 205), pygame.SRCALPHA); self._panel_bg_surf.fill((12, 18, 26, 225))

    def draw_segment_modes_table(
        self, screen: Any, segments_def: Any, segment_modes: Dict[str, Dict[str, Any]],
        mode_font: Any, mode_label_cache: Dict[Any, Any], px: int = 10, py: int = 185,
    ) -> int:
        """Draw the segment-to-mode table on the left side of the simulator screen."""
        self._ensure_fonts()
        rows, seen = [], set()
        for ch_defs in segments_def:
            for (_size, _orient, _sx, _sy, name, border_color) in ch_defs:
                if name not in seen:
                    seen.add(name); rows.append((name, border_color))
        rows.sort(key=lambda r: (0 if "_v" in r[0] else 1, r[0]))
        self._row_rects, self._modes_snapshot = [], segment_modes

        row_h, pw = 22, 295
        ph = 38 + max(1, len(rows)) * row_h
        if self._modes_bg_surf is None or self._modes_bg_surf.get_height() != ph:
            self._modes_bg_surf = pygame.Surface((pw, ph), pygame.SRCALPHA); self._modes_bg_surf.fill((12, 16, 24, 220))

        screen.blit(self._modes_bg_surf, (px, py))
        pygame.draw.rect(screen, (70, 140, 200), (px, py, pw, ph), 2)
        screen.blit(self._modes_title_surf, (px + pw // 2 - self._modes_title_surf.get_width() // 2, py + 7))
        pygame.draw.line(screen, (45, 90, 130), (px + 8, py + 27), (px + pw - 8, py + 27), 1)

        cy = py + 33
        for idx, (name, border_color) in enumerate(rows):
            if idx % 2 == 1:
                pygame.draw.rect(screen, (20, 26, 38), (px + 4, cy - 2, pw - 8, row_h - 1))
            pygame.draw.circle(screen, border_color, (px + 14, cy + 7), 4)
            self._hud_label(screen, name.replace("segment_", ""), px + 24, cy + 1)

            mode_info = segment_modes.get(name)
            if mode_info is not None and mode_info.get("mode"):
                mode_label = mode_info["mode"]
                has_target, is_global_m = bool(mode_info.get("target")), mode_label in self.global_modes
                if has_target:
                    mode_label = f"{mode_label} -> {mode_info['target']}"
                color = (255, 215, 90) if has_target else ((255, 195, 110) if is_global_m else (130, 235, 255))
            else:
                mode_label, color = "-", (100, 110, 125)

            if (m_key := (mode_label, color)) not in mode_label_cache:
                if len(mode_label_cache) > 256:
                    mode_label_cache.clear()
                mode_label_cache[m_key] = mode_font.render(mode_label, True, color)

            has_buttons = bool(self.mode_catalog.get(name[len("segment_"):] if name.startswith("segment_") else name))
            old_clip = screen.get_clip()
            screen.set_clip(pygame.Rect(px + 72, cy, pw - 72 - (52 if has_buttons else 6), row_h))
            screen.blit(mode_label_cache[m_key], (px + 72, cy + 1))
            screen.set_clip(old_clip)
            if has_buttons:
                rect_prev, rect_next = pygame.Rect(px + pw - 50, cy - 1, 20, row_h - 3), pygame.Rect(px + pw - 27, cy - 1, 20, row_h - 3)
                self._draw_button(screen, rect_prev, "<", (40, 55, 70), (90, 150, 190))
                self._draw_button(screen, rect_next, ">", (40, 55, 70), (90, 150, 190))
                self._row_rects.append((name, rect_prev, rect_next))
            cy += row_h
        return ph

    def draw_transition_panel(self, screen: Any, transition_data: Optional[Dict[str, Any]], px: int = 320, py: int = 685) -> None:
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
        sel_rect = pygame.Rect(self._rect_prev.right + 6, self._rect_prev.top, self._rect_next.left - self._rect_prev.right - 12, 28)
        pygame.draw.rect(screen, (22, 30, 42), sel_rect); pygame.draw.rect(screen, (70, 120, 150), sel_rect, 1)
        idx_str = f"[{self.selected_idx + 1}/{len(self.transitions)}] {self.selected_transition}"
        surf = self._hud_value(idx_str, (255, 240, 150) if self.selected_transition == "AUTO" else (140, 240, 255))
        screen.blit(surf, surf.get_rect(center=sel_rect.center))

        for rect, lbl in ((self._rect_dur_m5, "-0.5"), (self._rect_dur_m1, "-0.1"), (self._rect_dur_p1, "+0.1"), (self._rect_dur_p5, "+0.5")):
            self._draw_button(screen, rect, lbl, (40, 55, 70), (90, 150, 190))
        dur_rect = pygame.Rect(self._rect_dur_m1.right + 6, self._rect_dur_m1.top, self._rect_dur_p1.left - self._rect_dur_m1.right - 12, 26)
        pygame.draw.rect(screen, (22, 30, 42), dur_rect); pygame.draw.rect(screen, (70, 120, 150), dur_rect, 1)
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
        is_pending = bool(td.get("is_pending", False)) or ((time.monotonic() - self._last_request_ts) < 1.2 and not is_in_trans)
        progress, active_tech = float(td.get("progress", 0.0)), td.get("technique") or self.selected_transition

        if is_in_trans:
            status_txt, status_col = f"ACTIVE: {active_tech} ({int(progress * 100)}%)", (80, 255, 160)
        elif is_pending:
            status_txt, status_col = "QUEUED: waiting for beat (<= 1.2s)...", (255, 210, 70)
        else:
            status_txt, status_col = "READY  |  Keys: [ / ] Select, - / = Duration, T Send", (160, 185, 200)
        screen.blit(self._hud_value(status_txt, status_col), (px + 14, py + 162))
        self._hud_bar(screen, px + 14, py + 180, pw - 28, 12, progress if is_in_trans else (1.0 if is_pending else 0.0), status_col)

    def draw_control_panel(self, screen: Any, transition_data: Optional[Dict[str, Any]], px: int = 320, py: int = 229) -> None:
        """Draw the SHOW CONTROL panel: HOLD / LIVE switch, Global vs Local mode selector, and Mood selector."""
        self._ensure_fonts()
        pw, ph, now, td = 400, CONTROL_PANEL_H, time.monotonic(), transition_data or {}
        self.is_locked = bool(td.get("is_locked", False))

        if now - self._last_scope_ts >= 0.5 and self._modes_snapshot:
            active = [v.get("mode") for v in self._modes_snapshot.values() if isinstance(v, dict) and v.get("mode")]
            if active and all(m in self.global_modes for m in active):
                self.global_scope, self.selected_global_idx = True, self.global_modes.index(active[0])
            elif active:
                self.global_scope = False

        avail_m = td.get("available_moods") or td.get("available_palettes")
        if isinstance(avail_m, (list, tuple)) and avail_m:
            self.mood_palettes = [str(m) for m in avail_m]
        if "mood_progress" in td:
            self.mood_progress = float(td["mood_progress"])
        self.mood_is_transitioning = bool(td.get("mood_is_transitioning", False))
        raw_cols = td.get("mood_colors") or td.get("colors")
        if isinstance(raw_cols, (list, tuple)) and len(raw_cols) == 4:
            self.mood_colors = [(int(c[0]), int(c[1]), int(c[2])) for c in raw_cols]
        m_target = td.get("mood_target") or td.get("target_palette") or td.get("mood_palette") or td.get("palette")
        m_curr = td.get("mood_palette") or td.get("palette") or m_target
        if isinstance(m_curr, str) and m_curr:
            self.mood_palette = m_curr
        if "mood_auto_scene" in td or "auto_scene" in td:
            self.mood_auto_scene = bool(td.get("mood_auto_scene", td.get("auto_scene", True)))
        if (now - self._last_mood_ts >= 0.5 or (self.mood_is_transitioning and m_target != self.mood_palette)) and isinstance(m_target, str) and m_target:
            self.mood_target = m_target
            if m_target in self.mood_palettes:
                self.selected_mood_idx = self.mood_palettes.index(m_target)
            if not raw_cols and m_target in self._palette_swatches:
                self.mood_colors = list(self._palette_swatches[m_target])

        self._update_control_rects(px, py)
        if self._control_bg_surf is None or self._control_bg_surf.get_height() != ph:
            self._control_bg_surf = pygame.Surface((pw, ph), pygame.SRCALPHA); self._control_bg_surf.fill((12, 18, 26, 225))
        screen.blit(self._control_bg_surf, (px, py))

        border, btn_bg, btn_border, label = (
            ((230, 150, 40), (150, 70, 20), (255, 190, 90), "HOLD - AUTO TRANSITIONS OFF  (Hotkey: H)")
            if self.is_locked else ((60, 180, 220), (28, 110, 90), (90, 230, 170), "LIVE - AUTO TRANSITIONS ON  (Hotkey: H)")
        )
        pygame.draw.rect(screen, border, (px, py, pw, ph), 2)
        screen.blit(self._control_title_surf, (px + pw // 2 - self._control_title_surf.get_width() // 2, py + 8))
        pygame.draw.line(screen, (60, 80, 100), (px + 8, py + 28), (px + pw - 8, py + 28), 1)
        self._draw_button(screen, self._rect_hold, label, btn_bg, (255, 255, 255) if (now - self._last_hold_ts) < 0.25 else btn_border)

        sc_bg, sc_border, sc_label, hint, hint_col = (
            ((32, 95, 138), (110, 235, 255), "MODE SCOPE: GLOBAL (All Segments)  (Hotkey: G)", "Global < > cycles all segs | Keys: H Hold, G Scope, M/A Mood", (130, 235, 255))
            if self.global_scope else ((38, 52, 68), (90, 145, 185), "MODE SCOPE: LOCAL (Per-Segment)  (Hotkey: G)", "Local < > in SEGMENT MODES | Keys: H Hold, G Scope, M/A Mood", (160, 185, 200))
        )
        self._draw_button(screen, self._rect_scope, sc_label, sc_bg, (255, 255, 255) if (now - self._last_scope_ts) < 0.25 else sc_border)
        self._draw_button(screen, self._rect_global_prev, "<", (45, 65, 85), (100, 190, 230))
        self._draw_button(screen, self._rect_global_next, ">", (45, 65, 85), (100, 190, 230))
        g_bg, g_border = ((30, 46, 66), (255, 200, 95)) if self.global_scope else ((22, 30, 42), (70, 120, 150))
        pygame.draw.rect(screen, g_bg, self._rect_global_apply, border_radius=4); pygame.draw.rect(screen, g_border, self._rect_global_apply, 1, border_radius=4)
        g_str = f"GLOBAL [{(self.selected_global_idx % len(self.global_modes)) + 1}/{len(self.global_modes)}]: {self.selected_global_mode}" if self.global_modes else "GLOBAL: (none)"
        g_surf = self._hud_value(g_str, (255, 225, 120) if self.global_scope else (175, 215, 235))
        old_clip = screen.get_clip(); screen.set_clip(self._rect_global_apply.inflate(-6, -2))
        screen.blit(g_surf, g_surf.get_rect(center=self._rect_global_apply.center)); screen.set_clip(old_clip)

        self._draw_button(screen, self._rect_mood_prev, "<", (55, 45, 85), (180, 130, 240))
        self._draw_button(screen, self._rect_mood_next, ">", (55, 45, 85), (180, 130, 240))
        m_border = (255, 255, 255) if (now - self._last_mood_ts) < 0.25 else ((120, 230, 255) if self.mood_is_transitioning else (150, 110, 210))
        pygame.draw.rect(screen, (28, 24, 44), self._rect_mood_apply, border_radius=4); pygame.draw.rect(screen, m_border, self._rect_mood_apply, 1, border_radius=4)
        m_str = (
            f"MOOD: {self.mood_palette} -> {self.mood_target} ({int(self.mood_progress * 100)}%)" if self.mood_is_transitioning
            else (f"MOOD [{(self.selected_mood_idx % len(self.mood_palettes)) + 1}/{len(self.mood_palettes)}]: {self.selected_mood}" if self.mood_palettes else "MOOD: (none)")
        )
        m_surf = self._hud_value(m_str, (140, 240, 255) if self.mood_is_transitioning else (230, 210, 255))
        screen.set_clip(self._rect_mood_apply.inflate(-6, -2)); screen.blit(m_surf, m_surf.get_rect(center=self._rect_mood_apply.center)); screen.set_clip(old_clip)

        a_bg, a_border = ((24, 78, 56), (90, 230, 160)) if self.mood_auto_scene else ((95, 58, 20), (245, 180, 80))
        self._draw_button(screen, self._rect_mood_auto, "AUTO: ON" if self.mood_auto_scene else "AUTO: OFF", a_bg, (255, 255, 255) if (now - self._last_auto_ts) < 0.25 else a_border)
        for i, rgb_col in enumerate(self.mood_colors[:4]):
            sw_r = pygame.Rect(px + 108 + i * 26, py + 167, 22, 18)
            pygame.draw.rect(screen, rgb_col, sw_r, border_radius=3); pygame.draw.rect(screen, (90, 100, 120), sw_r, 1, border_radius=3)
        if self.mood_is_transitioning:
            self._hud_bar(screen, px + 216, py + 170, 170, 12, self.mood_progress, (160, 110, 255))
        else:
            screen.blit(self._hud_value(f"Active: {self.mood_target}", (190, 205, 225)), (px + 216, py + 168))
        screen.blit(self._hud_value(hint, hint_col), (px + 14, py + 188))

    def _draw_button(self, screen: Any, rect: pygame.Rect, label: str, bg: Tuple[int, int, int], border: Tuple[int, int, int]) -> None:
        pygame.draw.rect(screen, bg, rect, border_radius=4); pygame.draw.rect(screen, border, rect, 1, border_radius=4)
        surf = self._hud_value(label, (240, 248, 255))
        screen.blit(surf, surf.get_rect(center=rect.center))

    def draw_analyzer_hud(self, screen: Any, d: Optional[Dict[str, Any]], px: int = 10, py: int = 545) -> None:
        """Draw the music analyzer HUD overlay in the bottom-left corner."""
        if d is None:
            return
        self._ensure_fonts()
        pw, ph = 295, 345
        screen.blit(self._hud_bg_surf, (px, py)); pygame.draw.rect(screen, (160, 60, 220), (px, py, pw, ph), 2)
        screen.blit(self._hud_title_surf, (px + pw // 2 - self._hud_title_surf.get_width() // 2, py + 8))
        pygame.draw.line(screen, (80, 40, 120), (px + 8, py + 28), (px + pw - 8, py + 28), 1)

        lx, vx, bar_w, cy = px + 12, px + 120, 120, py + 36
        self._hud_section(screen, "FLYWHEEL", lx, cy, (200, 80, 255)); cy += 18
        self._hud_row(screen, "BPM", f"{d.get('bpm', 0):.1f}", lx, vx, cy); cy += 16

        phase = d.get("phase", 0)
        self._hud_label(screen, "Phase", lx, cy); self._hud_bar(screen, vx, cy + 1, bar_w, 11, phase, (0, 200, 255))
        self._hud_small_val(screen, f"{phase:.2f}", vx + bar_w + 6, cy); cy += 16

        status = d.get("status", "coasting")
        color = (50, 255, 100) if status == "locked" else (255, 200, 50)
        self._hud_label(screen, "Status", lx, cy); pygame.draw.circle(screen, color, (vx + 5, cy + 6), 4)
        screen.blit(self._hud_value(status, color), (vx + 14, cy)); cy += 16

        conf = d.get("confidence", 0)
        self._hud_label(screen, "Confidence", lx, cy)
        self._hud_bar(screen, vx, cy + 1, bar_w, 11, min(1.0, max(0.0, conf)), (50, 255, 100) if conf >= 0.3 else (255, 60, 60))
        self._hud_small_val(screen, f"{conf:.2f}", vx + bar_w + 6, cy); cy += 16

        self._hud_label(screen, "Beat Tag", lx, cy); screen.blit(self._hud_value(d.get("beat_tag", ""), (100, 220, 255)), (vx, cy)); cy += 22
        pygame.draw.line(screen, (80, 40, 120), (px + 8, cy), (px + pw - 8, cy), 1); cy += 8

        self._hud_section(screen, "ONSETS", lx, cy, (200, 80, 255)); cy += 18
        for lbl, ldx, id_dx, k, col in (("Beat", 0, 40, "is_beat", (50, 120, 255)), ("Real", 65, 100, "is_real_beat", (50, 255, 50)), ("Drop", 125, 160, "is_dropped_beat", (255, 50, 50))):
            self._hud_label(screen, lbl, lx + ldx, cy); self._hud_indicator(screen, lx + id_dx, cy + 5, d.get(k, False), col)
        cy += 16
        self._hud_row(screen, "Flux Base", f"{d.get('flux_baseline', 0):.1f}", lx, vx, cy); cy += 22
        pygame.draw.line(screen, (80, 40, 120), (px + 8, cy), (px + pw - 8, cy), 1); cy += 8

        self._hud_section(screen, "STRUCTURE", lx, cy, (200, 80, 255)); cy += 18
        nov = d.get("asserved_novelty", 0)
        self._hud_label(screen, "Novelty", lx, cy)
        self._hud_bar(screen, vx, cy + 1, bar_w, 11, min(1.0, max(0.0, nov)), (255, 220, 50) if nov < 0.6 else (255, 60, 60))
        self._hud_small_val(screen, f"{nov:.2f}", vx + bar_w + 6, cy); cy += 16
        self._hud_row(screen, "Combined", f"{d.get('combined_novelty', 0):.3f}", lx, vx, cy); cy += 16
        self._hud_label(screen, "Song", lx, cy); self._hud_indicator(screen, lx + 38, cy + 5, d.get("is_song_change", False), (255, 50, 50))
        self._hud_label(screen, "V/C", lx + 63, cy); self._hud_indicator(screen, lx + 93, cy + 5, d.get("is_verse_chorus_change", False), (255, 220, 50))
        sil = d.get("silence_frames", 0)
        self._hud_label(screen, "Silence", lx + 118, cy)
        screen.blit(self._hud_value(str(sil), (255, 60, 60) if sil > 30 else (200, 200, 200)), (lx + 170, cy))

    def _hud_value(self, text: str, color: Tuple[int, int, int] = (255, 255, 255)) -> Any:
        key = (text, color)
        if key not in self._hud_value_cache:
            if len(self._hud_value_cache) > 128:
                self._hud_value_cache.clear()
            self._hud_value_cache[key] = self._hud_value_font.render(str(text), True, color)
        return self._hud_value_cache[key]

    def _hud_section(self, screen: Any, text: str, x: int, y: int, color: Tuple[int, int, int]) -> None:
        key = (text, color)
        if key not in self._hud_section_cache:
            self._hud_section_cache[key] = self._hud_section_font.render(text, True, color)
        screen.blit(self._hud_section_cache[key], (x, y))

    def _hud_label(self, screen: Any, text: str, x: int, y: int) -> None:
        if text not in self._hud_label_cache:
            self._hud_label_cache[text] = self._hud_label_font.render(text, True, (150, 150, 160))
        screen.blit(self._hud_label_cache[text], (x, y))

    def _hud_row(self, screen: Any, label: str, value: str, lx: int, vx: int, y: int) -> None:
        self._hud_label(screen, label, lx, y); screen.blit(self._hud_value(value), (vx, y))

    def _hud_small_val(self, screen: Any, text: str, x: int, y: int) -> None:
        if text not in self._hud_small_val_cache:
            if len(self._hud_small_val_cache) > 128:
                self._hud_small_val_cache.clear()
            self._hud_small_val_cache[text] = self._hud_label_font.render(str(text), True, (200, 200, 200))
        screen.blit(self._hud_small_val_cache[text], (x, y))

    def _hud_bar(self, screen: Any, x: int, y: int, w: int, h: int, value: float, fill_color: Tuple[int, int, int]) -> None:
        pygame.draw.rect(screen, (40, 40, 50), (x, y, w, h))
        if (fw := int(max(0.0, min(1.0, value)) * w)) > 0:
            pygame.draw.rect(screen, fill_color, (x, y, fw, h))
        pygame.draw.rect(screen, (70, 70, 80), (x, y, w, h), 1)

    def _hud_indicator(self, screen: Any, x: int, y: int, active: bool, active_color: Tuple[int, int, int]) -> None:
        pygame.draw.circle(screen, active_color if active else (45, 45, 50), (x, y), 5); pygame.draw.circle(screen, (80, 80, 90), (x, y), 5, 1)
