"""
research/choreography/candidates/Band_vu_mode.py - Architectural VU Equalizer adapted to the analyzer's new
outputs (work list C12).
Lead: spectrum
Secondary: transient

One idea: the installation becomes a three-band equalizer - bass rises in the outer pillars and runs along the
low bridges in red, the middle rises in the inner pillars and the middle bridges in amber, the treble spreads
along the canopy in cool white - and each heard kick puts a white cap on the bass meters.

What changes from `modes/Architectural_vu_equalizer_mode.py`, and why:

- Each meter reads its band against the band's own range over the last seconds (an auto-ranging meter), so it
  uses its whole height on any song.
- Three meters instead of one. The original lifts one column on every segment with the context's energy, tilted
  a little by the spectral tilt: bass and treble cannot be told apart. Here each band of the analyzer
  (`band_bass`, `band_mid`, `band_high`) has its own place and its own colour.
- The kick. A heard `kick` (only while `kick_present`) lights the whole bass meter (outer pillars, low bridges)
  in a white-tinted punch that fades in 0.13 s, at most every 0.44 s; a kick that comes sooner only gets a white
  cap at the top of the bass meter (a thin line, too little light to be a flash). Round 1 had the cap alone: the
  kick lifted the seen light by 3% to 5% and the gate's "follows the music" rule failed (every flash came from
  the levels, which the control does not move).
- Flash safety by construction. A meter rises as fast as the music, but falls at most FALL_PER_S of its height
  in a second, so a meter cannot swing up and down more than about twice a second. The kick cap is a thin line.
- The breaks. Nothing pumps on the beat tracker: in a break the meters follow the levels, and no cap is drawn.

Signals read from listener.signals, each with a fallback for when the slot is empty:

    band_bass / mid / high  fallback: the 16-band spectrum, grouped in three
    kick                    fallback: a beat whose dominant drum is tagged kick by the production analyzer
    kick_present, no_beat   fallback: the beat tracker's lock (rhythm_lock above 0.4 = kick present)

A lab candidate: it is not registered and never runs on the installation. No array is created in run().
"""
import math
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from modes.Mode import Mode
from utils.global_mode import SegmentSpatialProfile

RANGE_DRIFT: float = 0.08       # each meter reads its band against the band's own recent range: the top and the
                                # bottom of that range follow the level at once outward and drift back inward at
                                # this rate (level units a second). With a fixed range (round 3) the bass and middle
                                # meters sat near full most of the time and hardly moved
MIN_SPAN: float = 0.25          # the range is never narrower than this, so a quiet passage is not blown up
RISE_RATE_HZ: float = 30.0      # a meter rises as fast as the music
FALL_PER_S: float = 0.9         # and falls at most this share of its height in a second
BODY: float = 0.10              # drive of a meter's body (share of full); the top is brighter. Round 1 had 0.40
                                # (55% to 63% seen brightness), round 2 had 0.25 (48% to 57%): no room for a kick
TOP: float = 1.0
TOP_WIDTH: float = 0.05         # the bright top of a meter, in share of the segment
EDGE: float = 14.0              # sharpness of the meniscus (as the original)
KICK_JUMP: float = 0.10         # a heard kick lifts the bass meters by this much
CAP: float = 1.0                # the white cap of a kick, at the top of the bass meters
CAP_WIDTH: float = 0.035
CAP_DECAY_S: float = 0.15
FULL_GAP_S: float = 0.44        # a full punch of the bass meters at most this often (see Ripple_kick_mode)
PUNCH: float = 0.85             # drive of the whole bass meter at the top of a punch, tinted toward white
PUNCH_WHITE: float = 0.45       # share of white in the punch colour
PUNCH_DECAY_S: float = 0.13
PRESENT_RATE_HZ: float = 2.5
LOCK_FOR_PRESENT: float = 0.4
TRUST_FOR_FALLBACK: float = 0.3
BASS_RGB = (255.0, 40.0, 10.0)
MID_RGB = (255.0, 170.0, 0.0)
HIGH_RGB = (150.0, 210.0, 255.0)


class Band_vu_mode(Mode):
    """
    Band VU: bass in the outer pillars and low bridges, mid in the inner pillars and middle bridges, treble on the
    canopy; a white cap on the bass meters for every heard kick.
    Lead: spectrum (bass, mid and treble levels)
    Secondary: transient (kick)
    """

    IS_GLOBAL: bool = True
    LEAD: str = "spectrum"
    SECONDARY: tuple = ("transient",)

    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]) -> None:
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)
        self.spatial = SegmentSpatialProfile(segment_name=segment_name, nb_of_leds=self.nb_of_leds,
                                             tags=infos.get("tags", ()), orientation=infos.get("orientation"))
        n = max(1, self.nb_of_leds)
        self._pos = np.zeros(n, dtype=np.float64)        # 0 at the foot of the meter, 1 at its far end
        self._light = np.zeros(n, dtype=np.float64)
        self._light2d = self._light[:, None]
        self._scratch = np.zeros(n, dtype=np.float64)
        self._cap = np.zeros(n, dtype=np.float64)
        self._cap2d = self._cap[:, None]
        self._acc = np.zeros((n, 3), dtype=np.float64)
        self._colour = np.zeros(3, dtype=np.float64)
        self._colour_tmp = np.zeros(3, dtype=np.float64)
        self._punch_rgb = np.zeros(3, dtype=np.float64)
        self._band = 0
        self._recompute_spatial_buffers()
        self._height = 0.0
        self._lo, self._hi = 0.3, 0.9                    # the band's recent range
        self._present = 1.0
        self._cap_env = 0.0
        self._punch = 0.0
        self._since_full = 10.0

    def _recompute_spatial_buffers(self) -> None:
        """Which band this segment shows, and where along it a meter starts."""
        sp = self.spatial
        n = max(1, self.nb_of_leds)
        if sp.role == "pillar":
            self._band = 1 if sp.is_inner_pillar else 0
            alt = sp.altitude                            # each pillar is its own full meter: v1 spans 0.23 to
            lo, hi = float(alt.min()), float(alt.max())  # 0.93 of the height, v3 0.0 to 0.7
            np.copyto(self._pos, (alt - lo) / max(1e-6, hi - lo))
        else:
            if sp.role == "canopy":
                self._band = 2
            else:
                self._band = 0 if sp.tier == "low" else 1
            np.copyto(self._pos, np.linspace(0.0, 1.0, n) if n > 1 else np.zeros(1))
        np.copyto(self._colour, (BASS_RGB, MID_RGB, HIGH_RGB)[self._band])
        self._punch_rgb[:] = self._colour * (1.0 - PUNCH_WHITE) + 255.0 * PUNCH_WHITE

    def bind_segment_geometry(self, seg_id: Optional[str] = None, orientation: Optional[str] = None,
                              tags: Sequence[str] = (), coords_array: Optional[np.ndarray] = None) -> None:
        self.spatial.bind(seg_id, orientation, tags, coords_array)
        self._recompute_spatial_buffers()

    # -- signals, each with its fallback ---------------------------------------------------------------
    def _read(self) -> tuple:
        """(level of this segment's band, kick strength, kick present)."""
        listener = self.listener
        sig = getattr(listener, "signals", None)
        name = ("band_bass", "band_mid", "band_high")[self._band]
        level = getattr(sig, name, None)
        if level is None:
            bands = listener.asserved_fft_band
            k = len(bands)
            if self._band == 0:
                level = float(bands[0])
            elif self._band == 1:
                level = float(np.add.reduce(bands[1 : k // 2 + 1])) / max(1, k // 2)
            else:
                level = float(np.add.reduce(bands[k // 2 + 1 :])) / max(1, k - k // 2 - 1)
        kick = getattr(sig, "kick", None)
        if kick is None:
            tagged = bool(getattr(listener, "is_beat", False)) and float(getattr(listener, "beat_trust", 0.0)) > TRUST_FOR_FALLBACK
            kick = 0.8 if tagged and getattr(listener, "beat_tag", "") == "Bass/Kick" else 0.0
        present = getattr(sig, "kick_present", None)
        if present is None:
            present = self.rhythm_lock > LOCK_FOR_PRESENT
        present = bool(present) and not bool(getattr(sig, "no_beat", None))
        return float(level), float(kick), present

    def _band_at(self, centre: float, width: float, out: np.ndarray) -> None:
        """out = a soft band of width `width` around position `centre` (1 at the centre)."""
        np.subtract(self._pos, centre, out=out)
        np.multiply(out, out, out=out)
        np.multiply(out, -1.0 / (width * width), out=out)
        np.exp(out, out=out)

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return
        dt = self.dt
        ctx = getattr(self.listener, "context", None)
        level, kick, present = self._read()
        self._present += self.alpha(PRESENT_RATE_HZ) * ((1.0 if present else 0.0) - self._present)

        drift = RANGE_DRIFT * dt
        self._hi = max(level, self._hi - drift)
        self._lo = min(level, self._lo + drift)
        span = self._hi - self._lo
        if span < MIN_SPAN:                              # widen it around its middle
            mid = 0.5 * (self._hi + self._lo)
            self._lo, self._hi = mid - 0.5 * MIN_SPAN, mid + 0.5 * MIN_SPAN
        target = min(1.0, max(0.0, (level - self._lo) / (self._hi - self._lo)))
        self._cap_env *= math.exp(-dt / CAP_DECAY_S)
        self._punch *= math.exp(-dt / PUNCH_DECAY_S)
        self._since_full += dt
        if self._band == 0 and kick > 0.0 and present:
            target = min(1.0, target + KICK_JUMP)
            strength = 0.5 + 0.5 * min(1.0, kick)
            if self._since_full >= FULL_GAP_S:
                self._punch = strength
                self._since_full = 0.0
            else:
                self._cap_env = max(self._cap_env, strength)
        if target > self._height:
            self._height += (target - self._height) * self.alpha(RISE_RATE_HZ)
        else:
            self._height = max(target, self._height - FALL_PER_S * dt)
        h = self._height

        silent = bool(getattr(ctx, "is_silent", False)) if ctx is not None else False
        visible = 0.0 if silent else 1.0

        # body: full under the top, a meniscus above it (as the original); brighter near the top
        np.subtract(self._pos, h, out=self._scratch)
        np.maximum(self._scratch, 0.0, out=self._scratch)
        np.multiply(self._scratch, -EDGE, out=self._scratch)
        np.exp(self._scratch, out=self._light)
        np.multiply(self._light, BODY, out=self._light)
        self._band_at(h, TOP_WIDTH, self._scratch)
        np.multiply(self._scratch, (TOP - BODY) * min(1.0, h * 4.0), out=self._scratch)
        np.add(self._light, self._scratch, out=self._light)
        np.multiply(self._light, visible, out=self._light)
        np.multiply(self._light2d, self._colour, out=self._acc)
        if self._punch > 0.01:                           # the whole bass meter, tinted toward white
            np.multiply(self._punch_rgb, PUNCH * self._punch * visible, out=self._colour_tmp)
            np.maximum(self._acc, self._colour_tmp, out=self._acc)

        if self._cap_env > 0.01:
            self._band_at(h + 0.5 * CAP_WIDTH, CAP_WIDTH, self._cap)
            np.multiply(self._cap, 255.0 * CAP * self._cap_env * visible, out=self._cap)
            np.maximum(self._acc, self._cap2d, out=self._acc)            # white where the cap is brighter

        np.clip(self._acc, 0.0, 255.0, out=self._acc)
        np.copyto(self.rgb_list, self._acc, casting="unsafe")
