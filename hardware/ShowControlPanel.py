"""hardware/ShowControlPanel.py - SHOW CONTROL panel (HOLD / LIVE, mode scope, Global Mode & Mood pickers) and the
SEGMENT MODES table with its per-segment pickers, drawn by the Fake_leds simulator."""

import json
import os
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
import pygame
from hardware.AnalyzerHud import AnalyzerHud
from mood.api import create_mood_service

# Height of the SHOW CONTROL (HOLD / LIVE + Global Mode Picker + Mood Picker) panel drawn under the Transition Tester.
CONTROL_PANEL_H = 205

_FALLBACK_GLOBAL_MODES = [
    "Architectural VU Equalizer", "Concentric Radial Ripple", "Horizon Scanning Blade",
    "Monolithic Beat Blast", "Spectral Avalanche",
]

Command = Callable[[Dict[str, Any]], None]


def _load_global_mode_names() -> List[str]:
    """Load sorted Global Mode names from config/modes.json."""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config", "modes.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            entries = json.load(f).get("global_modes", [])
        names = sorted(str(m["name"]) for m in entries if isinstance(m, dict) and m.get("name"))
        if names:
            return names
    except Exception:
        pass
    return list(_FALLBACK_GLOBAL_MODES)


def _load_mood_catalog() -> Tuple[List[str], Dict[str, List[Tuple[int, int, int]]]]:
    """Query mood.api once at init for curated palette names and their 4 RGB swatches."""
    names = list(create_mood_service().get_status().available_palettes)
    swatches = {
        n: [(int(c[0]), int(c[1]), int(c[2])) for c in create_mood_service(initial_palette=n).colors()]
        for n in names
    }
    return names, swatches


class ShowControlPanel(AnalyzerHud):
    """State, input handling and drawing for the SHOW CONTROL panel and the SEGMENT MODES table."""

    def __init__(self) -> None:
        super().__init__()
        self._control_bg_surf = self._modes_bg_surf = None
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
        self._last_hold_ts = self._last_scope_ts = self._last_mood_ts = self._last_auto_ts = 0.0
        self._update_control_rects(320, 229)

    def _update_control_rects(self, px: int, py: int) -> None:
        self._rect_hold = pygame.Rect(px + 14, py + 34, 372, 30)
        self._rect_scope = pygame.Rect(px + 14, py + 69, 372, 28)
        self._rect_global_prev = pygame.Rect(px + 14, py + 102, 36, 26)
        self._rect_global_next = pygame.Rect(px + 350, py + 102, 36, 26)
        self._rect_global_apply = pygame.Rect(px + 56, py + 102, 288, 26)
        self._rect_mood_prev = pygame.Rect(px + 14, py + 134, 36, 26)
        self._rect_mood_next = pygame.Rect(px + 350, py + 134, 36, 26)
        self._rect_mood_apply = pygame.Rect(px + 56, py + 134, 288, 26)
        self._rect_mood_auto = pygame.Rect(px + 14, py + 166, 86, 20)

    @property
    def selected_global_mode(self) -> str:
        return self.global_modes[self.selected_global_idx % len(self.global_modes)] if self.global_modes else ""

    @property
    def selected_mood(self) -> str:
        return self.mood_palettes[self.selected_mood_idx % len(self.mood_palettes)] if self.mood_palettes else ""

    # ------------------------------------------------------------------ input

    def _toggle_hold(self, on_command: Command) -> None:
        self._last_hold_ts = time.monotonic()
        on_command({"type": "set_locked", "locked": not self.is_locked})

    def _toggle_scope(self, on_command: Command) -> None:
        now = time.monotonic()
        self._last_scope_ts, self.global_scope = now, not self.global_scope
        if self.global_scope and self.global_modes:
            gmode = self.selected_global_mode
            self._optimistic_modes.update({k: (gmode, now) for k in self._modes_snapshot})
            on_command({"type": "set_mode_scope", "scope": "global", "mode": gmode})
        else:
            self._optimistic_modes.clear()
            on_command({"type": "set_mode_scope", "scope": "local"})

    def _step_global_mode(self, delta: int, on_command: Command) -> None:
        if not self.global_modes:
            return
        now = time.monotonic()
        self._last_scope_ts, self.global_scope = now, True
        if delta != 0:
            self.selected_global_idx = (self.selected_global_idx + delta) % len(self.global_modes)
        gmode = self.selected_global_mode
        self._optimistic_modes.update({k: (gmode, now) for k in self._modes_snapshot})
        on_command({"type": "set_global_mode", "mode": gmode})

    def _step_mood(self, delta: int, on_command: Command) -> None:
        if not self.mood_palettes:
            return
        self._last_mood_ts = time.monotonic()
        if delta != 0:
            self.selected_mood_idx = (self.selected_mood_idx + delta) % len(self.mood_palettes)
        self.mood_target = pal = self.selected_mood
        if pal in self._palette_swatches and not self.mood_is_transitioning:
            self.mood_colors = list(self._palette_swatches[pal])
        on_command({"type": "set_mood", "palette": pal})

    def _toggle_mood_auto(self, on_command: Command) -> None:
        self._last_auto_ts, self.mood_auto_scene = time.monotonic(), not self.mood_auto_scene
        on_command({"type": "set_mood_auto", "auto_scene": self.mood_auto_scene})

    def _cycle_segment_mode(self, name: str, delta: int, on_command: Command) -> None:
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
        if current in modes:
            new_mode = modes[(modes.index(current) + delta) % len(modes)]
        else:
            new_mode = modes[0] if delta > 0 else modes[-1]
        self.global_scope, self._last_scope_ts = False, now
        self._optimistic_modes[name] = (new_mode, now)
        on_command({"type": "set_segment_mode", "segment": seg_id, "mode": new_mode})

    def _handle_control_click(self, pos: Tuple[int, int], on_command: Command) -> bool:
        """Clicks on the SHOW CONTROL panel and the SEGMENT MODES pickers."""
        if self._rect_hold.collidepoint(pos):
            self._toggle_hold(on_command)
            return True
        if self._rect_scope.collidepoint(pos):
            self._toggle_scope(on_command)
            return True
        for rect, delta in ((self._rect_global_prev, -1), (self._rect_global_next, 1), (self._rect_global_apply, 0)):
            if rect.collidepoint(pos):
                self._step_global_mode(delta, on_command)
                return True
        for rect, delta in ((self._rect_mood_prev, -1), (self._rect_mood_next, 1), (self._rect_mood_apply, 0)):
            if rect.collidepoint(pos):
                self._step_mood(delta, on_command)
                return True
        if self._rect_mood_auto.collidepoint(pos):
            self._toggle_mood_auto(on_command)
            return True
        for name, rect_prev, rect_next in self._row_rects:
            if rect_prev.collidepoint(pos) or rect_next.collidepoint(pos):
                self._cycle_segment_mode(name, -1 if rect_prev.collidepoint(pos) else 1, on_command)
                return True
        return False

    def _handle_control_key(self, event: Any, on_command: Command) -> bool:
        """Hotkeys H (hold), G (scope), M / Shift+M (mood) and A (mood auto)."""
        if event.key == pygame.K_h:
            self._toggle_hold(on_command)
            return True
        if event.key == pygame.K_g:
            self._toggle_scope(on_command)
            return True
        if event.key == pygame.K_m:
            self._step_mood(-1 if (getattr(event, "mod", 0) & pygame.KMOD_SHIFT) else 1, on_command)
            return True
        if event.key == pygame.K_a:
            self._toggle_mood_auto(on_command)
            return True
        return False

    # ---------------------------------------------------------------- drawing

    def _build_panel_surfaces(self) -> None:
        self._control_title_surf = self._hud_title_font.render("SHOW CONTROL", True, (255, 225, 160))
        self._modes_title_surf = self._hud_title_font.render("SEGMENT MODES", True, (200, 235, 255))

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
                    seen.add(name)
                    rows.append((name, border_color))
        rows.sort(key=lambda r: (0 if "_v" in r[0] else 1, r[0]))
        self._row_rects, self._modes_snapshot = [], segment_modes

        row_h, pw = 22, 295
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
                rect_prev = pygame.Rect(px + pw - 50, cy - 1, 20, row_h - 3)
                rect_next = pygame.Rect(px + pw - 27, cy - 1, 20, row_h - 3)
                self._draw_button(screen, rect_prev, "<", (40, 55, 70), (90, 150, 190))
                self._draw_button(screen, rect_next, ">", (40, 55, 70), (90, 150, 190))
                self._row_rects.append((name, rect_prev, rect_next))
            cy += row_h
        return ph

    def _sync_control_state(self, td: Dict[str, Any], now: float) -> None:
        """Reconcile the panel's selections with the latest scope, lock and mood telemetry."""
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

        user_idle = now - self._last_mood_ts >= 0.5
        server_moving = self.mood_is_transitioning and m_target != self.mood_palette
        if (user_idle or server_moving) and isinstance(m_target, str) and m_target:
            self.mood_target = m_target
            if m_target in self.mood_palettes:
                self.selected_mood_idx = self.mood_palettes.index(m_target)
            if not raw_cols and m_target in self._palette_swatches:
                self.mood_colors = list(self._palette_swatches[m_target])

    def draw_control_panel(
        self, screen: Any, transition_data: Optional[Dict[str, Any]], px: int = 320, py: int = 229,
    ) -> None:
        """Draw the SHOW CONTROL panel: HOLD / LIVE switch, Global vs Local mode selector, and Mood selector."""
        self._ensure_fonts()
        pw, ph, now = 400, CONTROL_PANEL_H, time.monotonic()
        self._sync_control_state(transition_data or {}, now)

        self._update_control_rects(px, py)
        if self._control_bg_surf is None or self._control_bg_surf.get_height() != ph:
            self._control_bg_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
            self._control_bg_surf.fill((12, 18, 26, 225))
        screen.blit(self._control_bg_surf, (px, py))

        if self.is_locked:
            border, btn_bg, btn_border = (230, 150, 40), (150, 70, 20), (255, 190, 90)
            label = "HOLD - AUTO TRANSITIONS OFF  (Hotkey: H)"
        else:
            border, btn_bg, btn_border = (60, 180, 220), (28, 110, 90), (90, 230, 170)
            label = "LIVE - AUTO TRANSITIONS ON  (Hotkey: H)"
        pygame.draw.rect(screen, border, (px, py, pw, ph), 2)
        screen.blit(self._control_title_surf, (px + pw // 2 - self._control_title_surf.get_width() // 2, py + 8))
        pygame.draw.line(screen, (60, 80, 100), (px + 8, py + 28), (px + pw - 8, py + 28), 1)
        self._draw_button(screen, self._rect_hold, label, btn_bg, self._flash(now, self._last_hold_ts, btn_border))

        hint = self._draw_scope_rows(screen, now)
        self._draw_mood_rows(screen, now, px, py)
        screen.blit(self._hud_value(*hint), (px + 14, py + 188))

    @staticmethod
    def _flash(now: float, last_ts: float, border: Tuple[int, int, int]) -> Tuple[int, int, int]:
        """White border for 0.25s after a click, else `border`."""
        return (255, 255, 255) if (now - last_ts) < 0.25 else border

    def _draw_scope_rows(self, screen: Any, now: float) -> Tuple[str, Tuple[int, int, int]]:
        """Draw the MODE SCOPE button and the Global Mode picker; return the footer hint (text, colour)."""
        if self.global_scope:
            sc_bg, sc_border = (32, 95, 138), (110, 235, 255)
            sc_label = "MODE SCOPE: GLOBAL (All Segments)  (Hotkey: G)"
            hint = ("Global < > cycles all segs | Keys: H Hold, G Scope, M/A Mood", (130, 235, 255))
        else:
            sc_bg, sc_border = (38, 52, 68), (90, 145, 185)
            sc_label = "MODE SCOPE: LOCAL (Per-Segment)  (Hotkey: G)"
            hint = ("Local < > in SEGMENT MODES | Keys: H Hold, G Scope, M/A Mood", (160, 185, 200))
        self._draw_button(screen, self._rect_scope, sc_label, sc_bg, self._flash(now, self._last_scope_ts, sc_border))

        self._draw_button(screen, self._rect_global_prev, "<", (45, 65, 85), (100, 190, 230))
        self._draw_button(screen, self._rect_global_next, ">", (45, 65, 85), (100, 190, 230))
        g_bg, g_border = ((30, 46, 66), (255, 200, 95)) if self.global_scope else ((22, 30, 42), (70, 120, 150))
        self._draw_box(screen, self._rect_global_apply, g_bg, g_border)
        if self.global_modes:
            g_pos = (self.selected_global_idx % len(self.global_modes)) + 1
            g_str = f"GLOBAL [{g_pos}/{len(self.global_modes)}]: {self.selected_global_mode}"
        else:
            g_str = "GLOBAL: (none)"
        g_surf = self._hud_value(g_str, (255, 225, 120) if self.global_scope else (175, 215, 235))
        self._blit_clipped(screen, g_surf, self._rect_global_apply)
        return hint

    def _draw_mood_rows(self, screen: Any, now: float, px: int, py: int) -> None:
        """Draw the Mood picker, AUTO toggle, RGB swatches and crossfade progress."""
        self._draw_button(screen, self._rect_mood_prev, "<", (55, 45, 85), (180, 130, 240))
        self._draw_button(screen, self._rect_mood_next, ">", (55, 45, 85), (180, 130, 240))
        m_idle_border = (120, 230, 255) if self.mood_is_transitioning else (150, 110, 210)
        self._draw_box(screen, self._rect_mood_apply, (28, 24, 44), self._flash(now, self._last_mood_ts, m_idle_border))
        if self.mood_is_transitioning:
            m_str = f"MOOD: {self.mood_palette} -> {self.mood_target} ({int(self.mood_progress * 100)}%)"
        elif self.mood_palettes:
            m_pos = (self.selected_mood_idx % len(self.mood_palettes)) + 1
            m_str = f"MOOD [{m_pos}/{len(self.mood_palettes)}]: {self.selected_mood}"
        else:
            m_str = "MOOD: (none)"
        m_surf = self._hud_value(m_str, (140, 240, 255) if self.mood_is_transitioning else (230, 210, 255))
        self._blit_clipped(screen, m_surf, self._rect_mood_apply)

        a_bg, a_border = ((24, 78, 56), (90, 230, 160)) if self.mood_auto_scene else ((95, 58, 20), (245, 180, 80))
        a_label = "AUTO: ON" if self.mood_auto_scene else "AUTO: OFF"
        self._draw_button(screen, self._rect_mood_auto, a_label, a_bg, self._flash(now, self._last_auto_ts, a_border))
        for i, rgb_col in enumerate(self.mood_colors[:4]):
            self._draw_box(screen, pygame.Rect(px + 108 + i * 26, py + 167, 22, 18), rgb_col, (90, 100, 120), radius=3)
        if self.mood_is_transitioning:
            self._hud_bar(screen, px + 216, py + 170, 170, 12, self.mood_progress, (160, 110, 255))
        else:
            screen.blit(self._hud_value(f"Active: {self.mood_target}", (190, 205, 225)), (px + 216, py + 168))
