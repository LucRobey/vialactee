"""
mood/api.py - THE DOOR of the sealed mood sector.

This is the only module the rest of the project may import from `mood`.
It defines the front-door class `MoodService` and the plain, immutable
`MoodStatus` shape that crosses the wall.

Rules (enforced by tests/governance/test_mood_isolation.py):
- Nothing in `mood/` imports from core/, modes/, connectors/, hardware/ or transitions/.
- Nothing outside `mood/` imports from it except `mood.api`.
- Only standard library + numpy appear here.

Doors:
  IN : update(dt, scene) every frame, request_palette(), next_palette(), set_auto_scene()
  OUT: colors() (live read-only (4, 3) int32 view), modifiers() (live read-only (4,) float32 view), get_status() (MoodStatus)

Guarantees:
- AXIOM-01/02: update() mutates the colour and modifier buffers in place with zero allocation.
- colors() and modifiers() always return the SAME read-only arrays, so callers may keep them.
"""
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np


@dataclass(frozen=True)
class MoodStatus:
    """Read-only state of the sector, for the web UI."""
    palette: str = "Cyberpunk"              # active palette (the outgoing one during a fade)
    target_palette: str = "Cyberpunk"
    progress: float = 1.0                   # 0.0 .. 1.0
    is_transitioning: bool = False
    available_palettes: Tuple[str, ...] = ()
    auto_scene: bool = False


class MoodService:
    """The single entry point to the mood sector. Synchronous."""

    # --- inputs --------------------------------------------------------------

    def update(self, dt: float, scene: Optional[str] = None) -> None:
        """Advance the crossfade by dt seconds. `scene` (e.g. "BUILDUP") drives modifiers and (if enabled) auto-palette."""
        raise NotImplementedError

    def request_palette(self, name: str, duration: Optional[float] = None) -> bool:
        """Start a cosine crossfade to `name`. False if the palette is unknown."""
        raise NotImplementedError

    def next_palette(self, duration: Optional[float] = None) -> str:
        """Cycle to the next curated palette and return its name."""
        raise NotImplementedError

    def set_auto_scene(self, enabled: bool) -> None:
        """Let the music scene choose the palette (debounced)."""
        raise NotImplementedError

    # --- outputs -------------------------------------------------------------

    def colors(self) -> np.ndarray:
        """Live blended colours: read-only (4, 3) int32 [primary, secondary, accent, background]."""
        raise NotImplementedError

    def modifiers(self) -> np.ndarray:
        """Live blended scene modifiers: read-only (4,) float32 [pace, sharpness, trail, accent_mix]."""
        raise NotImplementedError

    def get_status(self) -> MoodStatus:
        """Current palette state."""
        raise NotImplementedError


def create_mood_service(
    initial_palette: str = "Cyberpunk",
    transition_duration: float = 2.0,
    auto_scene: bool = False,
) -> MoodService:
    """
    Build the default front door. The only way outside code obtains the sector.

    Args:
        initial_palette: Name of the starting palette (unknown names fall back to the default).
        transition_duration: Default crossfade duration in seconds.
        auto_scene: Whether the music scene drives the palette from the start.
    """
    from mood.service import DefaultMoodService
    return DefaultMoodService(initial_palette, transition_duration, auto_scene)


__all__ = ["MoodStatus", "MoodService", "create_mood_service"]
