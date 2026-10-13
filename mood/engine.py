"""
mood/engine.py - Cosine palette crossfade with pre-allocated buffers.

Guarantees:
- AXIOM-01: advance() runs in <= 0.01 ms per frame.
- AXIOM-02: zero dynamic heap allocations in advance(); `colors` is mutated in
  place and never rebound, so views taken once stay live.
"""
import math
from typing import Dict

import numpy as np

from mood.palettes import PALETTES


class CrossfadeEngine:
    """Blends the active palette towards a target palette over time."""

    def __init__(self, initial: str, default_duration: float) -> None:
        self._cached: Dict[str, np.ndarray] = {
            name: np.array(colors, dtype=np.float32) for name, colors in PALETTES.items()
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

    def advance(self, dt: float) -> None:
        """Advance the crossfade timer and interpolate colours in place."""
        if not self.is_transitioning:
            return

        self._timer += dt
        if self._timer >= self._duration:
            self._timer = self._duration
            self.progress = 1.0
            self.is_transitioning = False
            self.current = self.target
            self.colors[:] = self._cached[self.target]
            return

        progress = self._timer / self._duration
        self.progress = progress

        # Cosine crossfade weighting: 0.5 * (1.0 - cos(pi * progress))
        w = 0.5 * (1.0 - math.cos(math.pi * progress))

        # Zero-allocation arithmetic: colors = from + diff * w
        np.multiply(self._diff, w, out=self._scratch)
        np.add(self._from, self._scratch, out=self.colors, casting="unsafe")
