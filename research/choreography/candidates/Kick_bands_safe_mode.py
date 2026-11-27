"""
research/choreography/candidates/Kick_bands_safe_mode.py - Kick_bands_mode made safe for the eyes (work list C01).
Lead: transient
Secondary: spectrum

One idea: the picture of the sound sorted by height, punched by the drums, where a full flash is rationed (at
most one every 0.46 s, so never more than three in a second) and everything else stays too small to be a flash.

It is a copy of Kick_bands_mode with three changes, all there for flash safety (WCAG 2.3.1: no more than three
general flashes in any one second, a flash being a swing of 10% or more of full light):

- The light has two layers.
  The resting layer is the three coloured zones (bass low, mid in the middle, treble on the canopy) plus the
  soft pulses. Its light is measured on every frame, on each third of the height of this segment, and scaled
  down as a whole when it goes over 7% of full light. It can therefore never swing by 10%: whatever the
  music does, the resting layer alone cannot make a flash.
  The flash layer is the full punch: the kick lights the lower part and sends a front up the pillars, the
  snare answers from the top, a drop lights everything.
- Full punches are rationed. A hit (kick, snare or drop) gets a full punch only if the last full punch is at
  least 0.46 s old. A hit that comes sooner gets a soft pulse in the resting layer: a thin line climbing the
  pillars for a kick, one LED in ten sparkling up high for a snare. On time, bright where it is, but too little
  light to be a flash. One exception: a full punch is held at its top for three frames, and a hit that falls
  inside (a drop two frames after its kick) joins that punch instead of being refused.
- The three zones are much dimmer than in Kick_bands_mode, and follow their level more steeply. A tenth of the
  light already looks a third as bright: the zones stay readable, the limit on the resting layer rarely has to
  act on them, and the full punch has room above them.

Signals read from listener.signals, each with a fallback for when the slot is empty:

    kick, snare            fallback: a beat whose dominant drum is tagged kick / snare by the production analyzer
    band_bass / mid / high fallback: the 16-band spectrum, grouped in three
    drop                   fallback: the drop helper of Mode

A lab candidate: it is not registered and never runs on the installation. No array is created in run().
"""
import math
from typing import Any, Dict, List

import numpy as np

from modes.Mode import Mode
from utils.global_mode import SegmentSpatialProfile

FULL_GAP_S: float = 0.46        # a full punch at most this often: four cannot start within one second, and a
                                # fourth flash in a second would need one punch to fade 0.38 s later than another
JOIN_S: float = 0.055           # a full punch is held this long at its top before it fades, and a hit that falls
                                # inside (a drop two frames after its kick) joins it instead of being refused
REST_LIGHT_MAX: float = 0.07    # most light the resting layer may give on any third of the height (share of full
                                # light, as the flash rule counts it). Under 0.10, so it cannot make a flash alone
GLOW_FLOOR: float = 0.012       # the three zones: drive value of a zone whose range is silent...
GLOW_FULL: float = 0.11         # ...and what a range at full level adds (bass and treble; the middle a little less).
GLOW_MID_FULL: float = 0.09     # Low on purpose: the limit above should rarely have to act on the zones alone
GLOW_POWER: float = 3.0         # level to light. Steep, because the eye flattens: a usual level (0.5 to 0.95)
                                # then spreads from about 15% to 40% of full brightness as the eye sees it
KICK_DECAY_S: float = 0.14
SNARE_DECAY_S: float = 0.09
DROP_DECAY_S: float = 0.6
FRONT_SPEED: float = 2.6        # how fast the kick front climbs, in installation heights per second
FRONT_WIDTH: float = 0.16
SOFT_FRONT: float = 0.35        # the soft pulse of a kick that gets no full punch: a thin line climbing the pillars.
SOFT_FRONT_WIDTH: float = 0.04  # Thin, because it may add very little light: bright where it is, small over a third
SOFT_SPARK: float = 0.5         # the soft pulse of a snare that gets no full punch: up high, one LED in...
SOFT_SPARK_EVERY: int = 10      # ...this many sparkles
LEVEL_RATE_HZ: float = 14.0     # smoothing of the three levels
TRUST_FOR_FALLBACK: float = 0.3
LIGHT_OF_RGB = (0.2126 / 255.0, 0.7152 / 255.0, 0.0722 / 255.0)     # light given off by a drive value (relative luminance)


class Kick_bands_safe_mode(Mode):
    """
    Kick & Bands, safe: height is pitch, the drums punch, and a full flash comes at most every 0.46 s.
    Lead: transient (kick, snare, drop)
    Secondary: spectrum (bass, mid and treble levels)
    """

    IS_GLOBAL: bool = True
    LEAD: str = "transient"
    SECONDARY: tuple = ("spectrum",)

    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]) -> None:
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)
        self.spatial = SegmentSpatialProfile(segment_name=segment_name, nb_of_leds=self.nb_of_leds,
                                             tags=infos.get("tags", ()), orientation=infos.get("orientation"))
        n = max(1, self.nb_of_leds)
        alt = self.spatial.altitude
        self._alt = alt
        self._w_bass = np.clip(1.0 - alt / 0.45, 0.0, 1.0)[:, None]
        self._w_mid = np.clip(1.0 - np.abs(alt - 0.5) / 0.32, 0.0, 1.0)[:, None]
        self._w_high = np.clip((alt - 0.55) / 0.40, 0.0, 1.0)[:, None]
        self._w_spark = self._w_high * (np.arange(n) % SOFT_SPARK_EVERY == 0)[:, None]
        self._acc = np.zeros((n, 3), dtype=np.float64)
        self._tmp = np.zeros((n, 3), dtype=np.float64)
        self._front = np.zeros(n, dtype=np.float64)
        self._front2d = self._front[:, None]
        self._peak = np.zeros(n, dtype=np.float64)
        self._peak2d = self._peak[:, None]
        self._colour = np.zeros(3, dtype=np.float64)
        self._white = np.array([255.0, 255.0, 255.0])
        # the light of the resting layer is read on each third of the height present in this segment: the mean of
        # a third of the whole installation is a mix of these means, so it obeys the same limit
        self._light = np.zeros(n, dtype=np.float64)
        self._light_of_rgb = np.array(LIGHT_OF_RGB, dtype=np.float64)
        self._zones: List[np.ndarray] = []
        for mask in (alt < 1.0 / 3.0, (alt >= 1.0 / 3.0) & (alt <= 2.0 / 3.0), alt > 2.0 / 3.0):
            if mask.any():
                self._zones.append(mask.astype(np.float64) / float(mask.sum()))
        self._bass = self._mid = self._high = 0.0
        self._kick_full = self._kick_soft = 0.0          # envelopes: full punch (flash layer), soft pulse (resting layer)
        self._snare_full = self._snare_soft = 0.0
        self._drop_env = 0.0
        self._since_full = 10.0                          # seconds since the last full punch was granted
        self._since_kick_full = self._since_kick_soft = 10.0
        self._front_sent = False                         # the full punch being held has already sent its kick front
        self._visible = 1.0

    # -- signals, each with its fallback ---------------------------------------------------------------
    def _hits(self) -> tuple:
        """(kick strength, snare strength, drop) on this frame."""
        listener = self.listener
        sig = getattr(listener, "signals", None)
        kick = getattr(sig, "kick", None)
        snare = getattr(sig, "snare", None)
        drop = getattr(sig, "drop", None)
        if kick is None or snare is None:
            tagged = bool(getattr(listener, "is_beat", False)) and float(getattr(listener, "beat_trust", 0.0)) > TRUST_FOR_FALLBACK
            tag = getattr(listener, "beat_tag", "") if tagged else ""
            if kick is None:
                kick = 0.8 if tag == "Bass/Kick" else 0.0
            if snare is None:
                snare = 0.8 if tag == "Snare/Mid" else 0.0
        if drop is None:
            drop = self.drop_hit
        return float(kick), float(snare), bool(drop)

    def _levels(self) -> tuple:
        """(bass, mid, treble) levels, 0..1."""
        listener = self.listener
        sig = getattr(listener, "signals", None)
        bass, mid, high = getattr(sig, "band_bass", None), getattr(sig, "band_mid", None), getattr(sig, "band_high", None)
        if bass is None or mid is None or high is None:
            bands = listener.asserved_fft_band
            k = len(bands)
            bass = float(bands[0]) if bass is None else bass
            mid = float(np.add.reduce(bands[1 : k // 2 + 1])) / max(1, k // 2) if mid is None else mid
            high = float(np.add.reduce(bands[k // 2 + 1 :])) / max(1, k - k // 2 - 1) if high is None else high
        return float(bass), float(mid), float(high)

    # -- drawing -----------------------------------------------------------------------------------------
    def _add(self, weight: np.ndarray, lut_index: int, gain: float) -> None:
        np.multiply(self.palette_lut[lut_index], gain, out=self._colour)
        np.multiply(weight, self._colour, out=self._tmp)
        np.add(self._acc, self._tmp, out=self._acc)

    def _add_front(self, since_s: float, gain: float, width: float) -> None:
        """A bright band at the height a front launched `since_s` ago has reached, in the highlight colour."""
        np.subtract(self._alt, since_s * FRONT_SPEED, out=self._front)
        np.multiply(self._front, self._front, out=self._front)
        np.multiply(self._front, -1.0 / (width * width), out=self._front)
        np.exp(self._front, out=self._front)
        np.multiply(self._front, gain, out=self._front)
        np.multiply(self._front2d, self.highlight_color, out=self._tmp)
        np.add(self._acc, self._tmp, out=self._acc)

    def _hold_resting_light(self) -> None:
        """Scale the resting layer down as a whole if any third of the height gives more light than REST_LIGHT_MAX."""
        np.dot(self._acc, self._light_of_rgb, out=self._light)
        most = 0.0
        for zone in self._zones:                         # at most three zones: not a loop over LEDs
            most = max(most, float(np.dot(self._light, zone)))
        if most > REST_LIGHT_MAX:
            np.multiply(self._acc, REST_LIGHT_MAX / most, out=self._acc)

    def run(self) -> None:
        dt = self.dt
        ctx = getattr(self.listener, "context", None)
        kick, snare, drop = self._hits()
        bass, mid, high = self._levels()

        a = self.alpha(LEVEL_RATE_HZ)
        self._bass += a * (bass - self._bass)
        self._mid += a * (mid - self._mid)
        self._high += a * (high - self._high)

        self._since_full += dt
        self._since_kick_full += dt
        self._since_kick_soft += dt
        held = self._since_full <= JOIN_S                # the last full punch is still being held at its top
        kick_fade, snare_fade = math.exp(-dt / KICK_DECAY_S), math.exp(-dt / SNARE_DECAY_S)
        self._kick_soft *= kick_fade
        self._snare_soft *= snare_fade
        if not held:
            self._kick_full *= kick_fade
            self._snare_full *= snare_fade
            self._drop_env *= math.exp(-dt / DROP_DECAY_S)

        # the ration: a hit joins the full punch that is being held, or starts a new one if the last is old enough
        if kick > 0.0 or snare > 0.0 or drop:
            full = held
            if not held and self._since_full >= FULL_GAP_S:
                full = True
                self._since_full = 0.0
                self._front_sent = False
            if kick > 0.0:
                strength = 0.45 + 0.55 * min(1.0, kick)
                if full:
                    self._kick_full = max(self._kick_full, strength)
                    if not self._front_sent:             # one front per full punch: a second kick that joins the punch
                        self._since_kick_full = 0.0      # must not call the front back to the floor (the light low
                        self._front_sent = True          # down would fall and rise again: one more flash)
                else:
                    self._kick_soft = max(self._kick_soft, strength)
                    self._since_kick_soft = 0.0
            if snare > 0.0:
                strength = 0.4 + 0.6 * min(1.0, snare)
                if full:
                    self._snare_full = max(self._snare_full, strength)
                else:
                    self._snare_soft = max(self._snare_soft, strength)
            if drop and full:
                self._drop_env = 1.0

        silent = bool(getattr(ctx, "is_silent", False)) if ctx is not None else False
        self._visible += self.alpha(3.0) * ((0.0 if silent else 1.0) - self._visible)

        # the resting layer: three coloured zones by height, and the soft pulses of the hits that got no full punch
        self._acc.fill(0.0)
        self._add(self._w_bass, 0, GLOW_FLOOR + GLOW_FULL * self._bass ** GLOW_POWER)
        self._add(self._w_mid, 127, GLOW_FLOOR + GLOW_MID_FULL * self._mid ** GLOW_POWER)
        self._add(self._w_high, 255, GLOW_FLOOR + GLOW_FULL * self._high ** GLOW_POWER)
        if self._kick_soft > 0.01:
            self._add_front(self._since_kick_soft, SOFT_FRONT * self._kick_soft, SOFT_FRONT_WIDTH)
        if self._snare_soft > 0.01:
            np.multiply(self._w_spark, self._white, out=self._tmp)
            np.multiply(self._tmp, SOFT_SPARK * self._snare_soft, out=self._tmp)
            np.add(self._acc, self._tmp, out=self._acc)
        self._hold_resting_light()

        # the flash layer, on top: the rationed full punches
        if self._kick_full > 0.01:
            self._add_front(self._since_kick_full, 0.9 * self._kick_full, FRONT_WIDTH)
            self._add(self._w_bass, 0, 1.3 * self._kick_full)
        if self._snare_full > 0.01:
            np.multiply(self._w_high, self._white, out=self._tmp)
            np.multiply(self._tmp, 0.75 * self._snare_full, out=self._tmp)
            np.add(self._acc, self._tmp, out=self._acc)
        if self._drop_env > 0.01:
            np.multiply(self.highlight_color, 0.8 * self._drop_env, out=self._colour)
            np.add(self._acc, self._colour, out=self._acc)

        np.multiply(self._acc, self._visible, out=self._acc)
        # too bright: scale the LED down as a whole instead of clipping each channel, so a flash keeps its colour
        np.max(self._acc, axis=1, out=self._peak)
        np.maximum(self._peak, 255.0, out=self._peak)
        np.divide(255.0, self._peak, out=self._peak)
        np.multiply(self._acc, self._peak2d, out=self._acc)
        np.clip(self._acc, 0.0, 255.0, out=self._acc)
        np.copyto(self.rgb_list, self._acc, casting="unsafe")
