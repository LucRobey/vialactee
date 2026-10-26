"""
mood/service.py - Default implementation of the front door (MoodService).

Wires the crossfade engine and the scene governor behind mood/api.py.
"""
from typing import Optional, Tuple

import numpy as np

from mood.api import MoodService, MoodStatus
from mood.engine import CrossfadeEngine
from mood.palettes import DEFAULT_PALETTE, PALETTES
from mood.scene_policy import (
    AUTO_PALETTE_DURATION,
    MODIFIER_FADE_DURATION,
    ModifierGovernor,
    SceneGovernor,
)


class DefaultMoodService(MoodService):
    """Synchronous front door of the mood sector."""

    def __init__(self, initial_palette: str = DEFAULT_PALETTE, transition_duration: float = 2.0,
                 auto_scene: bool = False) -> None:
        initial = initial_palette if initial_palette in PALETTES else DEFAULT_PALETTE
        self._engine = CrossfadeEngine(initial, transition_duration)
        self._governor = SceneGovernor()
        self._mod_governor = ModifierGovernor()
        self._auto_scene = bool(auto_scene)
        self._names: Tuple[str, ...] = tuple(PALETTES.keys())

        # Read-only views of the live buffers: the engine mutates the base arrays in place.
        self._view: np.ndarray = self._engine.colors.view()
        self._view.flags.writeable = False
        self._mod_view: np.ndarray = self._engine.modifiers.view()
        self._mod_view.flags.writeable = False

    def update(self, dt: float, scene: Optional[str] = None) -> None:
        self._engine.advance(dt)
        if scene is not None:
            if self._auto_scene:
                due = self._governor.update(dt, scene)
                if due is not None:
                    self.request_palette(due, duration=AUTO_PALETTE_DURATION)
            mod_due = self._mod_governor.update(dt, scene)
            if mod_due is not None:
                self._engine.start_modifiers(mod_due, MODIFIER_FADE_DURATION)

    def request_palette(self, name: str, duration: Optional[float] = None) -> bool:
        if name not in PALETTES:
            return False
        if name == self._engine.target:
            return True
        self._engine.start(name, duration if duration is not None else self._engine.default_duration)
        return True

    def next_palette(self, duration: Optional[float] = None) -> str:
        try:
            nxt = (self._names.index(self._engine.target) + 1) % len(self._names)
        except ValueError:
            nxt = 0
        target = self._names[nxt]
        self.request_palette(target, duration)
        return target

    def set_auto_scene(self, enabled: bool) -> None:
        self._auto_scene = bool(enabled)

    def colors(self) -> np.ndarray:
        return self._view

    def modifiers(self) -> np.ndarray:
        return self._mod_view

    def get_status(self) -> MoodStatus:
        e = self._engine
        return MoodStatus(
            palette=e.current,
            target_palette=e.target,
            progress=e.progress,
            is_transitioning=e.is_transitioning,
            available_palettes=self._names,
            auto_scene=self._auto_scene,
        )
