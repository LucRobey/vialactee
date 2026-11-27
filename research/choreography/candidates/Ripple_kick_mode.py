"""
research/choreography/candidates/Ripple_kick_mode.py - Concentric Radial Ripple adapted to the analyzer's new
outputs (work list C11).
Lead: transient
Secondary: spectrum

One idea: every kick the analyzer hears throws one violet ring out from the core of the installation (the
strongest ones with a white heart), while the kick is away only a slow steady ripple drifts, and the bass glows
at the core, the treble at the rim.

What changes from `modes/Concentric_radial_ripple_mode.py`, and why:

- The rings. The original keeps three rings travelling at the speed of the beat tracker's phase and pumps them
  with `beat_pulse()`: they swell on every predicted beat, heard or not (2.2 to 2.4 visible pulses a second in
  the breaks of the gate's passages). Here a ring is born on a heard `kick`, at the core, and travels to the rim
  in about 0.6 s: one ring = one kick, so the eye can count them.
- The ration (flash safety). The violet of the original gives little light (about a fifth of full light at full
  drive), so a ring alone cannot make a large flash. The white heart can: it is given to a kick only if the last
  one is at least 0.44 s old, so never more than three in a second. A kick that comes sooner throws a ring
  without the white heart.
- The breaks. While `kick_present` is false or `no_beat` is true, no ring is thrown with a white heart, and the
  three steady rings of the original (the "bed") drift at the speed of the loudness, at a constant brightness:
  the light moves but the total light does not pulse. Outside a break the bed is dimmer, so the kick rings stand out.
- The bands. A soft violet glow at the core follows `band_bass`; a cool blue-white glow at the rim follows
  `band_high`: bass and treble are read apart by place and by colour.

Signals read from listener.signals, each with a fallback for when the slot is empty:

    kick                    fallback: a real beat while the beat tracker is locked (what the original pumped on)
    kick_present, no_beat   fallback: the beat tracker's lock (rhythm_lock above 0.4 = kick present)
    band_bass, band_high    fallback: the 16-band spectrum (first band, upper half)
    drop                    fallback: the drop helper of Mode
    loudness                fallback: the context's energy

A lab candidate: it is not registered and never runs on the installation. No array is created in run().
"""
import math
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from modes.Mode import Mode
from utils.global_mode import SegmentSpatialProfile

FULL_GAP_S: float = 0.44        # a white heart at most this often: four cannot start within one second (3 gaps =
                                # 1.32 s). Not 0.46 as in Kick_bands_safe_mode: kicks 0.469 s apart (128 a minute)
                                # land 27 or 28 frames apart at 60 frames a second, and 27 frames (0.45 s) was refused
MAX_RINGS: int = 6              # kick rings alive at once (a ring lives about 0.6 s)
RIM: float = 0.78               # radius where a ring dies (as the original)
RING_SPEED: float = 1.3         # kick rings, in radius units per second: core to rim in about 0.6 s
RING_SIGMA: float = 0.06
RING_FADE_S: float = 0.30       # a kick ring fades while it travels
SOFT_RING: float = 0.30         # brightness of a ring thrown by a kick that gets no white heart
RING_TOP: float = 0.55          # brightness of a kick ring at birth. The violet is dim as light but bright to the
                                # eye: round 1 (1.0, with a brighter bed) sat at 54% to 63% seen brightness and a kick
                                # lifted it by 3% to 12%. The white heart carries the punch
HEART_R: float = 0.40           # radius of the white heart (about 57% of the LEDs are nearer the core than this;
                                # at 0.22 a heart held 20% of them and the kick lifted the seen light by only 3-5%)
HEART_WHITE: float = 230.0      # white added at the top of a heart (drive value)
HEART_DECAY_S: float = 0.12
BED_GROOVE: float = 0.07        # brightness of the three steady rings while the kick is here...
BED_BREAK: float = 0.22         # ...and in a break
CORE_GLOW: float = 0.18         # bass glow at the core, at full bass
RIM_GLOW: float = 0.16          # treble glow at the rim, at full treble
LEVEL_RATE_HZ: float = 14.0
PRESENT_RATE_HZ: float = 2.5
LOCK_FOR_PRESENT: float = 0.4
VIOLET = (157.0, 0.0, 255.0)    # the original's colour
COOL = (120.0, 200.0, 255.0)    # the treble glow


class Ripple_kick_mode(Mode):
    """
    Ripple, kick: one ring out from the core per heard kick, a steady drift without it, bass core, treble rim.
    Lead: transient (kick)
    Secondary: spectrum (bass and treble levels)
    """

    IS_GLOBAL: bool = True
    LEAD: str = "transient"
    SECONDARY: tuple = ("spectrum",)

    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]) -> None:
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)
        self.spatial = SegmentSpatialProfile(segment_name=segment_name, nb_of_leds=self.nb_of_leds,
                                             tags=infos.get("tags", ()), orientation=infos.get("orientation"))
        self.ring_speed: float = float(infos.get("ring_speed", 1.2))
        n = max(1, self.nb_of_leds)
        self._radius = np.zeros(n, dtype=np.float64)
        self._core = np.zeros(n, dtype=np.float64)
        self._rim = np.zeros(n, dtype=np.float64)
        self._heart = np.zeros(n, dtype=np.float64)
        self._violet_i = np.zeros(n, dtype=np.float64)   # violet intensity of every LED, 0..1+
        self._scratch = np.zeros(n, dtype=np.float64)
        self._scratch2d = self._scratch[:, None]
        self._violet_i2d = self._violet_i[:, None]
        self._acc = np.zeros((n, 3), dtype=np.float64)
        self._tmp = np.zeros((n, 3), dtype=np.float64)
        self._peak = np.zeros(n, dtype=np.float64)
        self._peak2d = self._peak[:, None]
        self._violet = np.array(VIOLET, dtype=np.float64)
        self._cool = np.array(COOL, dtype=np.float64)
        self._recompute_spatial_buffers()

        self.bed_r = np.array([0.08, 0.34, 0.60], dtype=np.float64)   # the original's three steady rings
        self.kick_r = np.zeros(MAX_RINGS, dtype=np.float64)
        self.kick_a = np.zeros(MAX_RINGS, dtype=np.float64)
        self._next = 0
        self._bass = self._high = 0.0
        self._present = 1.0
        self._heart_env = 0.0
        self._since_heart = 10.0
        self._visible = 1.0

    def _recompute_spatial_buffers(self) -> None:
        np.hypot(self.spatial.x_norm - 0.620, self.spatial.y_norm - 0.450, out=self._radius)
        r = np.clip(self._radius / RIM, 0.0, 1.0)
        np.clip(1.0 - r / 0.35, 0.0, 1.0, out=self._core)
        np.clip((r - 0.60) / 0.35, 0.0, 1.0, out=self._rim)
        np.clip(1.0 - (self._radius / HEART_R) ** 2, 0.0, 1.0, out=self._heart)

    def bind_segment_geometry(self, seg_id: Optional[str] = None, orientation: Optional[str] = None,
                              tags: Sequence[str] = (), coords_array: Optional[np.ndarray] = None) -> None:
        self.spatial.bind(seg_id, orientation, tags, coords_array)
        self._recompute_spatial_buffers()

    # -- signals, each with its fallback ---------------------------------------------------------------
    def _read(self) -> tuple:
        """(kick strength, drop, kick present, bass, high, loudness)."""
        listener = self.listener
        sig = getattr(listener, "signals", None)
        ctx = getattr(listener, "context", None)
        locked = self.rhythm_lock > LOCK_FOR_PRESENT
        kick = getattr(sig, "kick", None)
        if kick is None:
            kick = 0.8 if (ctx is not None and getattr(ctx, "is_real_beat", False) and locked) else 0.0
        drop = getattr(sig, "drop", None)
        if drop is None:
            drop = self.drop_hit
        present = getattr(sig, "kick_present", None)
        if present is None:
            present = locked
        present = bool(present) and not bool(getattr(sig, "no_beat", None))
        bass, high = getattr(sig, "band_bass", None), getattr(sig, "band_high", None)
        if bass is None or high is None:
            bands = listener.asserved_fft_band
            k = len(bands)
            bass = float(bands[0]) if bass is None else bass
            high = float(np.add.reduce(bands[k // 2 + 1 :])) / max(1, k - k // 2 - 1) if high is None else high
        loud = getattr(sig, "loudness", None)
        if loud is None:
            loud = float(getattr(ctx, "energy", 0.5)) if ctx is not None else 0.5
        return float(kick), bool(drop), present, float(bass), float(high), float(loud)

    def _add_ring(self, r: float, amp: float) -> None:
        """violet intensity += amp * gaussian ring at radius r."""
        np.subtract(self._radius, r, out=self._scratch)
        np.multiply(self._scratch, self._scratch, out=self._scratch)
        np.multiply(self._scratch, -1.0 / (2.0 * RING_SIGMA * RING_SIGMA), out=self._scratch)
        np.exp(self._scratch, out=self._scratch)
        np.multiply(self._scratch, amp, out=self._scratch)
        np.add(self._violet_i, self._scratch, out=self._violet_i)

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return
        dt = self.dt
        ctx = getattr(self.listener, "context", None)
        kick, drop, present, bass, high, loud = self._read()

        a = self.alpha(LEVEL_RATE_HZ)
        self._bass += a * (bass - self._bass)
        self._high += a * (high - self._high)
        self._present += self.alpha(PRESENT_RATE_HZ) * ((1.0 if present else 0.0) - self._present)

        # kick rings travel out and fade; a new kick (or a drop) throws one from the core
        pace = self.mood_pace * self.ring_speed / 1.2
        np.add(self.kick_r, dt * RING_SPEED * pace, out=self.kick_r)
        np.multiply(self.kick_a, math.exp(-dt / RING_FADE_S), out=self.kick_a)
        self._since_heart += dt
        self._heart_env *= math.exp(-dt / HEART_DECAY_S)
        if kick > 0.0 or drop:
            strength = RING_TOP * (0.6 + 0.4 * min(1.0, kick)) if kick > 0.0 else RING_TOP
            heart = present and self._since_heart >= FULL_GAP_S
            self.kick_r[self._next] = 0.0
            self.kick_a[self._next] = strength if heart else SOFT_RING * strength
            self._next = (self._next + 1) % MAX_RINGS
            if heart:
                self._heart_env = min(1.0, strength / RING_TOP)
                self._since_heart = 0.0

        # the bed: the original's three rings, drifting at the speed of the loudness, at a constant brightness
        bed_speed = dt * 1.15 * pace * (0.45 + 0.55 * loud) * (0.5 + 0.5 * self._present)
        np.add(self.bed_r, bed_speed, out=self.bed_r)
        np.mod(self.bed_r, RIM, out=self.bed_r)
        bed = BED_BREAK + (BED_GROOVE - BED_BREAK) * self._present

        silent = bool(getattr(ctx, "is_silent", False)) if ctx is not None else False
        self._visible += self.alpha(3.0) * ((0.0 if silent else 1.0) - self._visible)

        self._violet_i.fill(0.0)
        for k in range(3):                               # three rings: not a loop over LEDs
            self._add_ring(float(self.bed_r[k]), bed)
        for k in range(MAX_RINGS):                       # at most six rings
            if self.kick_a[k] > 0.01 and self.kick_r[k] < RIM + 0.1:
                self._add_ring(float(self.kick_r[k]), float(self.kick_a[k]))
        np.multiply(self._core, CORE_GLOW * self._bass * self._bass, out=self._scratch)
        np.add(self._violet_i, self._scratch, out=self._violet_i)
        np.minimum(self._violet_i, 1.0, out=self._violet_i)

        np.multiply(self._violet_i2d, self._violet, out=self._acc)
        np.multiply(self._rim, RIM_GLOW * self._high * self._high, out=self._scratch)
        np.multiply(self._scratch2d, self._cool, out=self._tmp)
        np.add(self._acc, self._tmp, out=self._acc)
        if self._heart_env > 0.01:
            np.multiply(self._heart, HEART_WHITE * self._heart_env, out=self._scratch)
            np.add(self._acc, self._scratch2d, out=self._acc)

        np.multiply(self._acc, self._visible, out=self._acc)
        np.max(self._acc, axis=1, out=self._peak)
        np.maximum(self._peak, 255.0, out=self._peak)
        np.divide(255.0, self._peak, out=self._peak)
        np.multiply(self._acc, self._peak2d, out=self._acc)
        np.clip(self._acc, 0.0, 255.0, out=self._acc)
        np.copyto(self.rgb_list, self._acc, casting="unsafe")
