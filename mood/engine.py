"""
mood/engine.py - Cosine palette and scene-modifier crossfade with pre-allocated buffers.

Guarantees:
- AXIOM-01: advance() runs in <= 0.01 ms per frame.
- AXIOM-02: zero dynamic heap allocations in advance(); `colors` and `modifiers` are
  mutated in place and never rebound, so views taken once stay live.
"""
import math
from typing import Dict

import numpy as np

from mood.palettes import PALETTES
from mood.scene_policy import DEFAULT_MODIFIERS, SCENE_TO_MODIFIERS


class CrossfadeEngine:
    """Blends the active palette and scene modifiers towards target states over time."""

    def __init__(self, initial: str, default_duration: float) -> None:
        self._cached: Dict[str, np.ndarray] = {
            name: np.array(colors, dtype=np.float32) for name, colors in PALETTES.items()
        }
        self._cached_mods: Dict[str, np.ndarray] = {
            scene: np.array(mods, dtype=np.float32) for scene, mods in SCENE_TO_MODIFIERS.items()
        }
        self.default_duration: float = max(0.01, float(default_duration))
        self._duration: float = self.default_duration
        self._timer: float = self._duration
        self.current: str = initial
        self.target: str = initial
        self.progress: float = 1.0
        self.is_transitioning: bool = False

        self._from = np.array(self._cached[initial], copy=True)
        self._to = np.array(self._cached[initial], copy=True)
        self._diff = np.zeros((4, 3), dtype=np.float32)
        self._scratch = np.zeros((4, 3), dtype=np.float32)
        self.colors: np.ndarray = np.array(PALETTES[initial], dtype=np.int32)

        # Pre-allocated (4,) float32 modifier buffers: [pace, sharpness, trail, accent_mix]
        self.modifiers: np.ndarray = np.array(DEFAULT_MODIFIERS, dtype=np.float32)
        self._mod_from = np.array(self.modifiers, copy=True)
        self._mod_to = np.array(self.modifiers, copy=True)
        self._mod_diff = np.zeros(4, dtype=np.float32)
        self._mod_scratch = np.zeros(4, dtype=np.float32)
        self._mod_duration: float = 2.5
        self._mod_timer: float = 2.5
        self.is_mod_transitioning: bool = False

    def start(self, target: str, duration: float) -> None:
        """Begin a crossfade from the current blended colours to `target` (must be a known palette)."""
        self._from[:] = self.colors
        self._to[:] = self._cached[target]
        np.subtract(self._to, self._from, out=self._diff)
        self.target = target
        self._duration = max(0.01, float(duration))
        self._timer = 0.0
        self.progress = 0.0
        self.is_transitioning = True

    def start_modifiers(self, scene: str, duration: float) -> None:
        """Begin a cosine crossfade from the current blended modifiers to `scene` modifiers."""
        target_mods = self._cached_mods.get(scene)
        if target_mods is None:
            return
        self._mod_from[:] = self.modifiers
        self._mod_to[:] = target_mods
        np.subtract(self._mod_to, self._mod_from, out=self._mod_diff)
        self._mod_duration = max(0.01, float(duration))
        self._mod_timer = 0.0
        self.is_mod_transitioning = True

    def advance(self, dt: float) -> None:
        """Advance the crossfade timers and interpolate colours and modifiers in place."""
        if self.is_transitioning:
            self._timer += dt
            if self._timer >= self._duration:
                self._timer = self._duration
                self.progress = 1.0
                self.is_transitioning = False
                self.current = self.target
                self.colors[:] = self._cached[self.target]
            else:
                progress = self._timer / self._duration
                self.progress = progress
                w = 0.5 * (1.0 - math.cos(math.pi * progress))
                np.multiply(self._diff, w, out=self._scratch)
                np.add(self._from, self._scratch, out=self.colors, casting="unsafe")

        if self.is_mod_transitioning:
            self._mod_timer += dt
            if self._mod_timer >= self._mod_duration:
                self._mod_timer = self._mod_duration
                self.is_mod_transitioning = False
                self.modifiers[:] = self._mod_to
            else:
                w_mod = 0.5 * (1.0 - math.cos(math.pi * (self._mod_timer / self._mod_duration)))
                np.multiply(self._mod_diff, w_mod, out=self._mod_scratch)
                np.add(self._mod_from, self._mod_scratch, out=self.modifiers)
