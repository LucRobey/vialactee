"""hardware/AnalyzerHud.py - Music Analyzer HUD overlay and the cached drawing primitives shared by the simulator panels."""

from typing import Any, Dict, Optional, Tuple
import pygame


class AnalyzerHud:
    """Draws the Music Analyzer HUD and provides cached text/bar/button primitives to subclasses."""

    def __init__(self) -> None:
        self._fonts_ready = False
        self._hud_section_cache: Dict[Tuple[str, Tuple[int, int, int]], Any] = {}
        self._hud_label_cache: Dict[str, Any] = {}
        self._hud_value_cache: Dict[Tuple[str, Tuple[int, int, int]], Any] = {}
        self._hud_small_val_cache: Dict[str, Any] = {}
        self._hud_bg_surf = None

    def _ensure_fonts(self) -> None:
        """Create fonts and static surfaces once (pygame must be initialised first)."""
        if self._fonts_ready:
            return
        self._fonts_ready = True
        self._hud_title_font = pygame.font.SysFont("consolas", 14, bold=True)
        self._hud_section_font = pygame.font.SysFont("consolas", 12, bold=True)
        self._hud_label_font = pygame.font.SysFont("consolas", 11)
        self._hud_value_font = pygame.font.SysFont("consolas", 11, bold=True)
        self._hud_title_surf = self._hud_title_font.render("MUSIC ANALYZER", True, (220, 220, 255))
        self._hud_bg_surf = pygame.Surface((295, 345), pygame.SRCALPHA)
        self._hud_bg_surf.fill((12, 12, 20, 215))
        self._build_panel_surfaces()

    def _build_panel_surfaces(self) -> None:
        """Hook for subclasses to pre-render their own static surfaces once fonts exist."""

    def draw_analyzer_hud(self, screen: Any, d: Optional[Dict[str, Any]], px: int = 10, py: int = 545) -> None:
        """Draw the music analyzer HUD overlay in the bottom-left corner."""
        if d is None:
            return
        self._ensure_fonts()
        pw, ph = 295, 345
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
        conf_col = (50, 255, 100) if conf >= 0.3 else (255, 60, 60)
        self._hud_bar(screen, vx, cy + 1, bar_w, 11, min(1.0, max(0.0, conf)), conf_col)
        self._hud_small_val(screen, f"{conf:.2f}", vx + bar_w + 6, cy)
        cy += 16

        self._hud_label(screen, "Beat Tag", lx, cy)
        screen.blit(self._hud_value(d.get("beat_tag", ""), (100, 220, 255)), (vx, cy))
        cy += 22
        pygame.draw.line(screen, (80, 40, 120), (px + 8, cy), (px + pw - 8, cy), 1)
        cy += 8

        self._hud_section(screen, "ONSETS", lx, cy, (200, 80, 255))
        cy += 18
        onsets = (
            ("Beat", 0, 40, "is_beat", (50, 120, 255)),
            ("Real", 65, 100, "is_real_beat", (50, 255, 50)),
            ("Drop", 125, 160, "is_dropped_beat", (255, 50, 50)),
        )
        for lbl, ldx, id_dx, k, col in onsets:
            self._hud_label(screen, lbl, lx + ldx, cy)
            self._hud_indicator(screen, lx + id_dx, cy + 5, d.get(k, False), col)
        cy += 16
        self._hud_row(screen, "Flux Base", f"{d.get('flux_baseline', 0):.1f}", lx, vx, cy)
        cy += 22
        pygame.draw.line(screen, (80, 40, 120), (px + 8, cy), (px + pw - 8, cy), 1)
        cy += 8

        self._hud_section(screen, "STRUCTURE", lx, cy, (200, 80, 255))
        cy += 18
        nov = d.get("asserved_novelty", 0)
        self._hud_label(screen, "Novelty", lx, cy)
        nov_col = (255, 220, 50) if nov < 0.6 else (255, 60, 60)
        self._hud_bar(screen, vx, cy + 1, bar_w, 11, min(1.0, max(0.0, nov)), nov_col)
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

    def _draw_button(
        self, screen: Any, rect: pygame.Rect, label: str,
        bg: Tuple[int, int, int], border: Tuple[int, int, int],
    ) -> None:
        self._draw_box(screen, rect, bg, border)
        surf = self._hud_value(label, (240, 248, 255))
        screen.blit(surf, surf.get_rect(center=rect.center))

    @staticmethod
    def _draw_box(
        screen: Any, rect: pygame.Rect, bg: Tuple[int, int, int],
        border: Tuple[int, int, int], radius: int = 4,
    ) -> None:
        """Filled rounded rectangle with a 1px border."""
        pygame.draw.rect(screen, bg, rect, border_radius=radius)
        pygame.draw.rect(screen, border, rect, 1, border_radius=radius)

    @staticmethod
    def _blit_clipped(screen: Any, surf: Any, rect: pygame.Rect) -> None:
        """Blit `surf` centred in `rect`, clipped to its inner area."""
        old_clip = screen.get_clip()
        screen.set_clip(rect.inflate(-6, -2))
        screen.blit(surf, surf.get_rect(center=rect.center))
        screen.set_clip(old_clip)

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
        self._hud_label(screen, label, lx, y)
        screen.blit(self._hud_value(value), (vx, y))

    def _hud_small_val(self, screen: Any, text: str, x: int, y: int) -> None:
        if text not in self._hud_small_val_cache:
            if len(self._hud_small_val_cache) > 128:
                self._hud_small_val_cache.clear()
            self._hud_small_val_cache[text] = self._hud_label_font.render(str(text), True, (200, 200, 200))
        screen.blit(self._hud_small_val_cache[text], (x, y))

    def _hud_bar(
        self, screen: Any, x: int, y: int, w: int, h: int,
        value: float, fill_color: Tuple[int, int, int],
    ) -> None:
        pygame.draw.rect(screen, (40, 40, 50), (x, y, w, h))
        if (fw := int(max(0.0, min(1.0, value)) * w)) > 0:
            pygame.draw.rect(screen, fill_color, (x, y, fw, h))
        pygame.draw.rect(screen, (70, 70, 80), (x, y, w, h), 1)

    def _hud_indicator(self, screen: Any, x: int, y: int, active: bool, active_color: Tuple[int, int, int]) -> None:
        pygame.draw.circle(screen, active_color if active else (45, 45, 50), (x, y), 5)
        pygame.draw.circle(screen, (80, 80, 90), (x, y), 5, 1)
