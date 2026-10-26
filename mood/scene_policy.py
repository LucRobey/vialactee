"""
mood/scene_policy.py - Which palette and continuous modifiers suit each musical scene.

Pure logic (no numpy, no project imports): scenes arrive as plain strings.
"""
from typing import Dict, Optional, Tuple

SCENE_TO_PALETTE: Dict[str, str] = {
    "CHILL": "Deep Ocean",
    "GROOVE": "Cyberpunk",
    "BUILDUP": "Solar Ember",
    "DROP_IMPACT": "Neon Acid",
}

# Seconds a scene must persist before its palette is requested in auto-scene mode.
# All scenes share the same 4.0s dwell (no 0.0s DROP_IMPACT palette hijack).
DEFAULT_DWELL = 4.0
SCENE_DWELL: Dict[str, float] = {}
AUTO_PALETTE_DURATION = 3.0

# Bounded scene modifiers: (pace, sharpness, trail, accent_mix)
DEFAULT_MODIFIERS: Tuple[float, float, float, float] = (1.00, 1.00, 1.00, 0.00)
SCENE_TO_MODIFIERS: Dict[str, Tuple[float, float, float, float]] = {
    "CHILL": (0.82, 0.78, 1.18, 0.00),
    "GROOVE": (1.00, 1.00, 1.00, 0.05),
    "BUILDUP": (1.12, 1.12, 0.92, 0.15),
    "DROP_IMPACT": (1.22, 1.22, 0.88, 0.28),
}
MODIFIER_DWELL = 0.30
MODIFIER_FADE_DURATION = 2.5


def palette_for_scene(scene: str) -> Optional[str]:
    """Palette suited to `scene`, or None when the scene has no opinion."""
    return SCENE_TO_PALETTE.get(scene.upper())


def modifiers_for_scene(scene: str) -> Optional[Tuple[float, float, float, float]]:
    """Modifier tuple (pace, sharpness, trail, accent_mix) suited to `scene`, or None."""
    return SCENE_TO_MODIFIERS.get(scene.upper())


class SceneGovernor:
    """Debounces scene changes so flickering scenes don't flicker the colours."""

    def __init__(self) -> None:
        self._pending: Optional[str] = None
        self._timer: float = 0.0
        self._applied: Optional[str] = None

    def update(self, dt: float, scene: str) -> Optional[str]:
        """Returns a palette name to request on the frame it becomes due, else None."""
        wanted = SCENE_TO_PALETTE.get(scene)  # canonical uppercase names: no per-frame allocation
        if wanted is None or wanted == self._applied:
            self._pending = None
            return None

        if wanted != self._pending:
            self._pending = wanted
            self._timer = 0.0
        self._timer += dt

        if self._timer >= SCENE_DWELL.get(scene, DEFAULT_DWELL):
            self._applied = wanted
            self._pending = None
            return wanted
        return None


class ModifierGovernor:
    """Debounces scene changes before triggering a 2.5s modifier cosine crossfade."""

    def __init__(self) -> None:
        self._pending: Optional[str] = None
        self._timer: float = 0.0
        self._applied: Optional[str] = None

    def update(self, dt: float, scene: str) -> Optional[str]:
        """Returns the canonical scene key when its modifier vector becomes due, else None."""
        if scene not in SCENE_TO_MODIFIERS or scene == self._applied:
            self._pending = None
            return None

        if scene != self._pending:
            self._pending = scene
            self._timer = 0.0
        self._timer += dt

        if self._timer >= MODIFIER_DWELL:
            self._applied = scene
            self._pending = None
            return scene
        return None
