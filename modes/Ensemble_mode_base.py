"""
modes/Ensemble_mode_base.py
Abstract base for "ensemble" Global Modes: each part of the chandelier is an instrument with its own job.
Lead: declared by each concrete subclass

Concrete ensemble modes declare ``PARTS`` (part name -> driver) and implement:
  * ``part_of(seg_id)``            - the part a canonical segment belongs to,
  * ``on_frame(ctx, dt)``          - compute the shared per-frame state once (envelopes, onsets),
  * ``render_part(part, fx, out)`` - draw one part into ``out[fx.start:fx.stop]`` (float64, 0..255).
The base class owns part resolution, the silence protocol and the final clip / copy.
Not registered in config/modes.json (ABSTRACT = True).
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from modes.Mode import Mode
from utils.cast import Fixture, build_fixtures
from utils.global_mode import SegmentSpatialProfile

# Silence shorter than this is a gap between hits: parts keep rendering (Ensemble Law E4).
SILENCE_FADE_S: float = 0.6
_WHITE: float = 255.0


class Ensemble_mode_base(Mode):
    """
    Shared ensemble-family engine (see docs/contracts/global_mode_contract.md, Ensemble Laws E1-E6).
    Lead: declared by each concrete subclass
    """

    ABSTRACT: bool = True
    IS_GLOBAL: bool = True
    FAMILY: str = "ensemble"
    LEAD: str = "spectrum"
    SECONDARY: tuple = ()
    PARTS: Dict[str, str] = {}

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
        self._silent_time: float = 0.0

        n = max(1, self.nb_of_leds)
        self._target = np.zeros((n, 3), dtype=np.float64)
        self._gain = np.zeros(n, dtype=np.float64)
        self._gain_2d = self._gain[:, np.newaxis]
        # Rank of every LED inside its own part, counted from the part's first / last LED.
        self._from_start = np.zeros(n, dtype=np.float64)
        self._from_end = np.zeros(n, dtype=np.float64)
        self._fixture_coord = np.zeros(n, dtype=np.float64)
        self.fixtures: List[Fixture] = []
        self.fixture_parts: List[str] = []
        self._bind_parts()

    # Geometry -----------------------------------------------------------------------------
    def _bind_parts(self) -> None:
        """Resolve the parts this segment instance renders (init / bind time only)."""
        sp = self.spatial
        self.fixtures = build_fixtures(
            sp.seg_id, sp.role, self.nb_of_leds, sp.split_1, sp.split_2,
            self._fixture_coord, self.segment_phase_offset,
        )
        self.fixture_parts = [self.part_of(fx.seg) for fx in self.fixtures]
        for fx in self.fixtures:
            length = fx.stop - fx.start
            rank = np.arange(length, dtype=np.float64)
            self._from_start[fx.start:fx.stop] = rank
            self._from_end[fx.start:fx.stop] = (length - 1) - rank
        self.on_bind()

    def bind_segment_geometry(
        self,
        seg_id: Optional[str] = None,
        orientation: Optional[str] = None,
        tags: Sequence[str] = (),
        coords_array: Optional[np.ndarray] = None,
    ) -> None:
        """Bind the physical segment identity from Segment and re-resolve parts."""
        self.spatial.bind(seg_id, orientation, tags, coords_array)
        self._bind_parts()

    def part_slices(self) -> List[Tuple[str, int, int]]:
        """(part, start, stop) for every LED slice this instance renders (tests and tooling)."""
        return [(self.fixture_parts[i], fx.start, fx.stop) for i, fx in enumerate(self.fixtures)]

    # Hooks (overridden by concrete modes) -------------------------------------------------
    def part_of(self, seg_id: str) -> str:
        return ""

    def on_bind(self) -> None:
        pass

    def on_reset(self) -> None:
        pass

    def on_frame(self, ctx: Any, dt: float) -> None:
        pass

    def render_part(self, part: str, fx: Fixture, out: np.ndarray) -> None:
        out[fx.start:fx.stop] = 0.0

    # Shared mechanics (zero allocation) ---------------------------------------------------
    def draw_bar(self, fx: Fixture, out: np.ndarray, color: np.ndarray, height: float,
                 from_end: bool = False) -> None:
        """Solid bar covering ``height`` (0..1) of the part, grown from its first or last LED."""
        a, b = fx.start, fx.stop
        rank = self._from_end if from_end else self._from_start
        gain = self._gain[a:b]
        np.subtract(height * (b - a), rank[a:b], out=gain)
        np.clip(gain, 0.0, 1.0, out=gain)
        np.multiply(self._gain_2d[a:b], color, out=out[a:b])

    def draw_solid(self, fx: Fixture, out: np.ndarray, color: np.ndarray, level: float,
                   crest: bool = False) -> None:
        """Whole part at ``level`` (0..1) of ``color``; ``crest`` paints the Law 3 white strike frame."""
        a, b = fx.start, fx.stop
        if crest:
            out[a:b] = _WHITE
        elif level <= 0.004:
            out[a:b] = 0.0
        else:
            np.multiply(color, level, out=self._scratch_color)
            out[a:b] = self._scratch_color

    # Lifecycle ----------------------------------------------------------------------------
    def start(self) -> None:
        super().start()
        self._silent_time = 0.0
        self.on_reset()            # Ensemble Law E5: every segment restarts from the same state

    def run(self) -> None:
        n = self.nb_of_leds
        if n <= 0:
            return
        ctx = getattr(self.listener, "context", None)
        dt = self.dt

        # Law 1.5 Silence Protocol with the E4 debounce: short gaps between hits keep rendering
        # (the audio itself pulls every part down); sustained silence drains state and fades.
        if ctx is not None and getattr(ctx, "is_silent", False):
            self._silent_time += dt
            if self._silent_time >= SILENCE_FADE_S:
                self.on_reset()
                self.fade_to_black_segment_vectorized(0.35, 0, n - 1)
                return
        else:
            self._silent_time = 0.0

        self.on_frame(ctx, dt)
        fixtures = self.fixtures
        parts = self.fixture_parts
        for i in range(len(fixtures)):
            self.render_part(parts[i], fixtures[i], self._target)

        np.clip(self._target, 0.0, 255.0, out=self._target)
        np.copyto(self.rgb_list, self._target, casting="unsafe")
