"""
mood/scene_policy.py - Which palette suits which musical scene.

Pure logic (no numpy, no project imports): scenes arrive as plain strings.
"""
from typing import Dict, Optional

SCENE_TO_PALETTE: Dict[str, str] = {
    "CHILL": "Deep Ocean",
    "GROOVE": "Cyberpunk",
    "BUILDUP": "Solar Ember",
    "DROP_IMPACT": "Neon Acid",
}

# Seconds a scene must persist before its palette is requested.
DEFAULT_DWELL = 3.0
SCENE_DWELL: Dict[str, float] = {"DROP_IMPACT": 0.0}  # drops are short: react at once


def palette_for_scene(scene: str) -> Optional[str]:
    """Palette suited to `scene`, or None when the scene has no opinion."""
    return SCENE_TO_PALETTE.get(scene.upper())


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
