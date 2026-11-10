"""
modes/Cast_mode_base.py
Abstract base for "cast" Global Modes: each segment is a light fixture, not a strip of pixels.
Lead: declared by each concrete subclass

Concrete cast modes implement only the cast rule:
  * ``on_step(clock)``   - called once per quantized musical step (and on the first frame),
  * ``on_frame(ctx)``    - optional per-frame event hook (transient-led modes),
  * ``segment_slot(id)`` - colour slot (0 pillar, 1 rung, 2 canopy) for a segment, or ``OFF``.
The base class owns the shared clock, fixture resolution, look rendering, and the silence protocol.
Not registered in config/modes.json (ABSTRACT = True).
"""

from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from modes.Mode import Mode
from utils.cast import OFF, CastClock, build_fixtures, look_setting, render_fixture, LOOKS
from utils.global_mode import SegmentSpatialProfile

# Silence shorter than this is a gap between hits: fixtures hold instead of fading.
SILENCE_FADE_S: float = 0.6
# Seconds of sustained silence before the cast state (clock + held fixtures) is drained.
SILENCE_RESET_S: float = 3.0


class Cast_mode_base(Mode):
    """
    Shared cast-family engine (see docs/contracts/global_mode_contract.md, Cast Mode Laws C1-C6).
    Lead: declared by each concrete subclass
    """

    ABSTRACT: bool = True
    IS_GLOBAL: bool = True
    FAMILY: str = "cast"
    LEAD: str = "beat"
    SECONDARY: tuple = ()
    DEFAULT_LOOK: str = "snap"

    def __init__(
        self,
        name: str,
        segment_name: str,
        listener: Any,
        leds: Any,
        indexes: List[int],
        rgb_list: np.ndarray,
        infos: Dict[str, Any],
    ) -> None:
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)
        self.spatial = SegmentSpatialProfile(
            segment_name=segment_name,
            nb_of_leds=self.nb_of_leds,
            tags=infos.get("tags", ()),
            orientation=infos.get("orientation"),
        )
        self.look: str = str(infos.get("look", self.DEFAULT_LOOK))
        self.clock = CastClock()
        self.energy: float = 0.5
        self._needs_step: bool = True
        self._restrike: bool = False
        self._silent_time: float = 0.0
        self._drained: bool = False

        n = max(1, self.nb_of_leds)
        self._target = np.zeros((n, 3), dtype=np.float64)
        self._coord = np.zeros(n, dtype=np.float64)
        self._mask = np.zeros(n, dtype=bool)
        self._color = np.zeros(3, dtype=np.float64)
        self._scratch3 = np.zeros(3, dtype=np.float64)
        self.fixtures = []
        self._bind_fixtures()

    # Geometry -----------------------------------------------------------------------------
    def _bind_fixtures(self) -> None:
        sp = self.spatial
        self.fixtures = build_fixtures(
            sp.seg_id, sp.role, self.nb_of_leds, sp.split_1, sp.split_2, self._coord, self.segment_phase_offset
        )

    def bind_segment_geometry(
        self,
        seg_id: Optional[str] = None,
        orientation: Optional[str] = None,
        tags: Sequence[str] = (),
        coords_array: Optional[np.ndarray] = None,
    ) -> None:
        """Bind the physical segment identity from Segment and re-resolve fixtures."""
        self.spatial.bind(seg_id, orientation, tags, coords_array)
        self._bind_fixtures()

    # Settings -----------------------------------------------------------------------------
    def get_settings_schema(self) -> List[Dict[str, Any]]:
        return [look_setting(self.DEFAULT_LOOK)] + self.cast_settings()

    def cast_settings(self) -> List[Dict[str, Any]]:
        return []

    # Cast-rule hooks (overridden by concrete modes) ---------------------------------------
    def on_reset(self) -> None:
        pass

    def on_step(self, clock: CastClock) -> None:
        pass

    def on_frame(self, ctx: Any) -> None:
        pass

    def segment_slot(self, seg_id: str) -> int:
        return OFF

    def request_restrike(self) -> None:
        """Re-strike every lit fixture this frame (white crest + look attack), e.g. on drop_hit."""
        self._restrike = True

    # Lifecycle ----------------------------------------------------------------------------
    def _reset_cast_state(self) -> None:
        self.clock.reset()
        for fx in self.fixtures:
            fx.reset()
        self._needs_step = True
        self._restrike = False
        self.on_reset()

    def start(self) -> None:
        super().start()
        self._reset_cast_state()   # Cast Law C5: every segment restarts its clock on the same frame

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return
        ctx = getattr(self.listener, "context", None)

        dt = self.dt
        # Law 1.5 Silence Protocol, debounced for held states: in sparse passages the silence
        # detector fires in the gaps between kicks (~0.1 s bursts). Cast fixtures hold through
        # gaps shorter than SILENCE_FADE_S, then fade to black; the cast state (clock, held
        # fixtures) is drained only after SILENCE_RESET_S of sustained silence.
        if ctx is not None and getattr(ctx, "is_silent", False):
            self._silent_time += dt
            if self._silent_time >= SILENCE_FADE_S:
                if self._silent_time >= SILENCE_RESET_S and not self._drained:
                    self._reset_cast_state()
                    self._drained = True
                self.fade_to_black_segment_vectorized(0.35, 0, self.nb_of_leds - 1)
                return
        else:
            self._silent_time = 0.0
            self._drained = False

        self.energy = float(getattr(ctx, "energy", 0.5)) if ctx is not None else 0.5
        flux = getattr(self.listener, "band_flux", None)
        bass = float(flux[0] + flux[1]) if flux is not None and len(flux) >= 2 else 0.0
        beat_count = int(getattr(self.listener, "beat_count", 0))
        pace = self.mood_pace
        self.clock.update(beat_count, self.rhythm_lock, bass, self.energy, dt, pace)
        if self.clock.stepped or self._needs_step:
            self._needs_step = False
            self.on_step(self.clock)
        self.on_frame(ctx)

        bpm = float(getattr(self.listener, "bpm", 120.0)) or 120.0
        rise_time = min(0.30, max(0.06, 15.0 / max(40.0, bpm) / max(0.5, pace)))
        trail = self.mood_trail
        colors = self.mood_colors
        look = self.look if self.look in LOOKS else self.DEFAULT_LOOK
        restrike = self._restrike
        self._restrike = False

        for fx in self.fixtures:
            slot = self.segment_slot(fx.seg)
            if slot != OFF:
                if not fx.on or restrike or slot != fx.slot:
                    fx.on = True
                    fx.age = 0.0
                else:
                    fx.age += dt
                fx.slot = slot
            elif fx.on:
                fx.on = False
                fx.off_age = 0.0
            else:
                fx.off_age += dt
            np.copyto(self._color, colors[fx.slot], casting="unsafe")
            render_fixture(look, fx, self._target, self._color, self._scratch3,
                           self._coord, self._mask, rise_time, trail)

        np.clip(self._target, 0.0, 255.0, out=self._target)
        np.copyto(self.rgb_list, self._target, casting="unsafe")
