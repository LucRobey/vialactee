"""
utils/cast.py - Shared building blocks for "cast" Global Modes (segment-as-fixture family).

A cast mode treats each of the 11 chandelier segments as one light fixture with an architectural
identity (group, mirror partner, build order) instead of sampling a continuous 2D field. This module
provides, with zero per-frame heap allocation:

* ``CAST_TOPOLOGY`` and group tuples: the identity of every canonical full-profile segment.
* ``build_fixtures``: resolves the fixtures a single segment instance renders (1 for a real segment,
  one per group member for small-profile / tag-only strips, a miniature 11-fixture chandelier for
  composite studio/test strips).
* ``TABLEAUX_POSES``: hand-designed held poses grouped by density.
* ``CastClock``: quantized musical step counter (beat-locked, with onset/timer fallback).
* ``render_fixture``: the shared fixture looks (snap, neon, rise, flash, steady).

Every decision is a pure function of (segment id, clock counters) so the 11 independent segment
instances agree without sharing state (Cast Law C5 in docs/contracts/global_mode_contract.md).
"""

import math
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

# Colour slots into Mode.mood_colors (Law 9 complementary segregation by structure).
SLOT_PILLAR: int = 0
SLOT_RUNG: int = 1
SLOT_CANOPY: int = 2
OFF: int = -1

# seg_id -> (group, colour slot, mirror partner, build order)
CAST_TOPOLOGY: Dict[str, Tuple[str, int, str, int]] = {
    "v2":  ("core_pillar",  SLOT_PILLAR, "v3",  0),
    "v3":  ("core_pillar",  SLOT_PILLAR, "v2",  1),
    "h10": ("low_rung",     SLOT_RUNG,   "h31", 2),
    "h31": ("low_rung",     SLOT_RUNG,   "h10", 3),
    "v1":  ("outer_pillar", SLOT_PILLAR, "v4",  4),
    "v4":  ("outer_pillar", SLOT_PILLAR, "v1",  5),
    "h11": ("mid_rung",     SLOT_RUNG,   "h32", 6),
    "h32": ("mid_rung",     SLOT_RUNG,   "h11", 7),
    "h00": ("wing",         SLOT_CANOPY, "h30", 8),
    "h30": ("wing",         SLOT_CANOPY, "h00", 9),
    "h20": ("crown",        SLOT_CANOPY, "",    10),
}

PILLARS: Tuple[str, ...] = ("v1", "v2", "v3", "v4")
RUNGS: Tuple[str, ...] = ("h10", "h11", "h31", "h32")
CANOPY: Tuple[str, ...] = ("h00", "h20", "h30")
ALL_SEGMENTS: Tuple[str, ...] = PILLARS + RUNGS + CANOPY
BUILD_ORDER: Tuple[str, ...] = tuple(sorted(CAST_TOPOLOGY, key=lambda s: CAST_TOPOLOGY[s][3]))
MIRROR_PAIRS: Tuple[Tuple[str, str], ...] = (
    ("v1", "v4"), ("v2", "v3"), ("h10", "h31"), ("h11", "h32"), ("h00", "h30"),
)

# Small profile (3 strips) and tag-only strips stand in for a whole architectural group.
_ZONE_MEMBERS: Dict[str, Tuple[str, ...]] = {
    "s1": CANOPY, "s2": PILLARS, "s3": RUNGS,
    "pillar": PILLARS, "bridge": RUNGS, "canopy": CANOPY,
}

AXIS_FLOOR_UP: str = "floor_up"   # fill from LED 0 (physical floor on pillars, Law 10)
AXIS_CENTER: str = "center_out"   # fill from the strip centre outward

# Held poses for Tableaux, grouped by density (sparse / medium / full).
_ALL = frozenset(ALL_SEGMENTS)
TABLEAUX_POSES: Tuple[Tuple[frozenset, ...], ...] = (
    (
        frozenset(("v2", "v3", "h20")),          # the gate
        frozenset(("v2", "v3")),                 # the core
        frozenset(CANOPY),                       # canopy alone
        frozenset(("v1", "v4")),                 # outer pillars
        frozenset(("h10", "h31")),               # low floor
        frozenset(("h11", "h32", "h20")),        # upper floors
    ),
    (
        frozenset(PILLARS),                      # the four pillars
        frozenset(("v1", "v2", "h10", "h11")),   # left ladder
        frozenset(("v3", "v4", "h31", "h32")),   # right ladder
        frozenset(RUNGS),                        # all rungs
        frozenset(("v1", "v4", "h00", "h30", "h20")),  # outer frame
        frozenset(("v2", "v3", "h20", "h10", "h31")),  # gate + low floor
    ),
    (
        _ALL,                                    # everything
        frozenset(PILLARS + RUNGS),              # both ladders
        frozenset(PILLARS + CANOPY),             # pillars + canopy
        _ALL - frozenset(("v2", "v3")),          # everything but the core
    ),
)


def topology_slot(seg_id: str) -> int:
    """Colour slot of a canonical segment (pillars 0, rungs 1, canopy 2)."""
    entry = CAST_TOPOLOGY.get(seg_id)
    return entry[1] if entry is not None else SLOT_PILLAR


def mix_index(a: int, b: int, modulo: int) -> int:
    """Deterministic integer hash of (a, b) in [0, modulo): identical on every segment instance."""
    h = (a * 2654435761 + b * 40503 + 12345) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 1274126177) & 0xFFFFFFFF
    return (h ^ (h >> 16)) % max(1, modulo)


class Fixture:
    """One renderable fixture: an LED slice standing for exactly one architectural segment."""

    __slots__ = ("start", "stop", "seg", "pattern", "on", "age", "off_age", "slot")

    def __init__(self, start: int, stop: int, seg: str, pattern: int) -> None:
        self.start = start
        self.stop = stop
        self.seg = seg
        self.pattern = pattern
        self.on = False
        self.age = 0.0
        self.off_age = 99.0
        self.slot = topology_slot(seg)

    def reset(self) -> None:
        self.on = False
        self.age = 0.0
        self.off_age = 99.0


def _fill_coords(coord: np.ndarray, start: int, stop: int, axis: str) -> None:
    """Write the local [0, 1] fill coordinate of a fixture slice into ``coord`` (init/bind time only)."""
    length = stop - start
    if length <= 0:
        return
    local = np.linspace(0.0, 1.0, length) if length > 1 else np.zeros(1)
    coord[start:stop] = local if axis == AXIS_FLOOR_UP else np.abs(local * 2.0 - 1.0)


def build_fixtures(
    seg_id: str, role: str, nb_of_leds: int, split_1: int, split_2: int,
    coord: np.ndarray, phase_offset: float,
) -> List[Fixture]:
    """
    Resolve the fixtures one segment instance renders and fill ``coord`` (bind time only).

    * Canonical full-profile segment -> 1 fixture (itself).
    * Small-profile / tag-only strip -> its architectural group, split into one sub-fixture per member.
    * Composite studio/test strip -> a miniature chandelier: pillars (bottom third), rungs, canopy (top),
      each split into one sub-fixture per member (11 fixtures in total).
    """
    n = max(0, int(nb_of_leds))
    zones: List[Tuple[int, int, Tuple[str, ...]]] = []
    if seg_id in CAST_TOPOLOGY:
        zones.append((0, n, (seg_id,)))
    elif seg_id in _ZONE_MEMBERS or role in _ZONE_MEMBERS:
        zones.append((0, n, _ZONE_MEMBERS.get(seg_id) or _ZONE_MEMBERS[role]))
    else:
        a, b = max(0, min(split_1, n)), max(0, min(split_2, n))
        zones.extend(((0, a, PILLARS), (a, b, RUNGS), (b, n, CANOPY)))
    seed = int(phase_offset * 1000.0)
    fixtures: List[Fixture] = []
    for z_start, z_stop, members in zones:
        span = z_stop - z_start
        if span <= 0:
            continue
        k = len(members)
        for i, seg in enumerate(members):
            start = z_start + (span * i) // k
            stop = z_start + (span * (i + 1)) // k
            if stop <= start:
                continue
            _fill_coords(coord, start, stop, AXIS_FLOOR_UP if seg in PILLARS else AXIS_CENTER)
            pattern = (seed + 3 * CAST_TOPOLOGY[seg][3]) % len(NEON_STRIKES)
            fixtures.append(Fixture(start, stop, seg, pattern))
    return fixtures


class CastClock:
    """
    Quantized musical step counter shared (by determinism) across all segment instances.

    Locked (``rhythm_lock`` >= 0.45, exit < 0.30): one step per ``beat_count`` increment.
    Unlocked: one step per bass onset (refractory-gated) or, failing that, per energy-scaled timer,
    so cast modes never freeze when the flywheel loses lock (Cast Law C3).
    """

    __slots__ = ("step", "stepped", "since_step", "locked", "_last_beat_count", "_primed",
                 "refractory", "onset_threshold", "min_interval", "max_interval")

    def __init__(self, refractory: float = 0.25, onset_threshold: float = 0.30,
                 min_interval: float = 0.55, max_interval: float = 1.25) -> None:
        self.refractory = refractory
        self.onset_threshold = onset_threshold
        self.min_interval = min_interval
        self.max_interval = max_interval
        self.reset()

    def reset(self) -> None:
        self.step = 0
        self.stepped = False
        self.since_step = 0.0
        self.locked = False
        self._last_beat_count = 0
        self._primed = False

    @property
    def bar(self) -> int:
        return self.step // 4

    @property
    def beat_in_bar(self) -> int:
        return self.step % 4

    @property
    def phrase(self) -> int:
        return self.step // 16

    @property
    def step_in_phrase(self) -> int:
        return self.step % 16

    def update(self, beat_count: int, rhythm_lock: float, bass_flux: float,
               energy: float, dt: float, pace: float = 1.0) -> bool:
        """Advance by one frame; returns True on the frame a new step begins."""
        self.stepped = False
        self.since_step += dt
        if self.locked:
            if rhythm_lock < 0.30:
                self.locked = False
        elif rhythm_lock >= 0.45:
            self.locked = True
        if not self._primed:
            self._primed = True
            self._last_beat_count = beat_count
            return False
        if self.locked:
            fire = beat_count > self._last_beat_count
        else:
            e = 0.0 if energy < 0.0 else (1.0 if energy > 1.0 else energy)
            interval = (self.max_interval - (self.max_interval - self.min_interval) * e) / max(0.5, pace)
            onset = bass_flux >= self.onset_threshold and self.since_step >= self.refractory
            fire = onset or self.since_step >= interval
        self._last_beat_count = beat_count
        if fire:
            self.step += 1
            self.stepped = True
            self.since_step = 0.0
        return fire


# Fixture looks ------------------------------------------------------------------------------
LOOKS: Tuple[str, ...] = ("snap", "neon", "rise", "flash", "steady")
LOOK_OPTIONS: Tuple[Tuple[str, str], ...] = (
    ("Snap (hard cut)", "snap"),
    ("Neon Tube (strike flicker)", "neon"),
    ("Rise (fill from base)", "rise"),
    ("Flash (strike and fade)", "flash"),
    ("Steady (no strike, plain colour)", "steady"),
)
LOOK_FRAME_S: float = 1.0 / 30.0   # look timing is authored in 30 FPS hardware frames
NEON_STRIKES: Tuple[Tuple[float, ...], ...] = (
    (0.0, 0.55, 0.0, 1.0),
    (0.4, 0.0, 0.8, 0.0),
    (0.0, 0.0, 0.7, 0.2),
    (0.6, 0.0, 1.0, 0.0),
)
NEON_RELEASE: Tuple[float, ...] = (0.35, 0.0, 0.2)
_WHITE: float = 255.0


def _fill(target: np.ndarray, start: int, stop: int, color: np.ndarray, gain: float, scratch: np.ndarray) -> None:
    np.multiply(color, gain, out=scratch)
    target[start:stop] = scratch


def render_fixture(
    look: str, fx: Fixture, target: np.ndarray, color: np.ndarray, scratch: np.ndarray,
    coord: np.ndarray, mask: np.ndarray, rise_time: float, trail: float,
) -> None:
    """Render one fixture into ``target`` (float64, (n, 3)) in place. Off pixels are pure black."""
    a, b = fx.start, fx.stop
    if look == "steady":                          # no strike crest, no decay: plain on / off
        if fx.on:
            target[a:b] = color
        else:
            target[a:b] = 0.0
        return
    if not fx.on:
        gain = 0.0
        if look == "neon":
            k = int(fx.off_age / LOOK_FRAME_S)
            if k < len(NEON_RELEASE):
                gain = NEON_RELEASE[k]
        if gain <= 0.0:
            target[a:b] = 0.0
        else:
            _fill(target, a, b, color, gain, scratch)
        return

    frame = int(fx.age / LOOK_FRAME_S)
    if frame == 0:
        target[a:b] = _WHITE                      # Law 3 white crest: exactly the strike frame
        if look == "rise":
            np.less_equal(coord[a:b], 0.15, out=mask[a:b])
            np.multiply(target[a:b], mask[a:b, np.newaxis], out=target[a:b])
        return

    if look == "neon":
        strike = NEON_STRIKES[fx.pattern]
        gain = strike[frame - 1] if frame - 1 < len(strike) else 1.0
        _fill(target, a, b, color, gain, scratch)
    elif look == "rise":
        target[a:b] = color
        frac = fx.age / max(1e-3, rise_time)
        if frac < 1.0:
            np.less_equal(coord[a:b], frac, out=mask[a:b])
            np.multiply(target[a:b], mask[a:b, np.newaxis], out=target[a:b])
    elif look == "flash":
        gain = math.exp(-fx.age / max(0.05, 0.30 * trail))
        if gain < 0.04:
            target[a:b] = 0.0
        else:
            _fill(target, a, b, color, gain, scratch)
    else:
        target[a:b] = color


def look_setting(default: str) -> Dict[str, object]:
    """Settings-schema descriptor for the shared ``look`` list control."""
    return {
        "key": "look",
        "label": "Fixture Look",
        "control": "list",
        "valueType": "string",
        "default": default,
        "options": [{"label": label, "value": value} for label, value in LOOK_OPTIONS],
        "attr": "look",
    }
