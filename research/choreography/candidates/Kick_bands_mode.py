"""
research/choreography/candidates/Kick_bands_mode.py - first candidate mode of the choreography lab.
Lead: transient
Secondary: spectrum

One idea: the installation is a picture of the sound, sorted by height, and the kick punches it.

- Height is pitch. The bottom of the pillars glows with the bass level, the middle with the mid level, the
  canopy with the treble level, each in its own colour of the mood palette. Bass and treble can be read apart
  at a glance.
- The kick is a punch. Each kick flashes the lower part of the installation in the bass colour and sends a
  bright front up the pillars. A harder kick punches harder. A flash never washes out to white: an LED that
  is too bright is scaled down as a whole, so it keeps its colour.
- The snare (or clap) answers from the top with a short pale flash.
- A drop lights everything once.

Signals read from listener.signals (the truth-mirrored record), each with a fallback for when the slot is empty:

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

KICK_DECAY_S: float = 0.14
SNARE_DECAY_S: float = 0.09
DROP_DECAY_S: float = 0.6
FRONT_SPEED: float = 2.6        # how fast the kick front climbs, in installation heights per second
FRONT_WIDTH: float = 0.16
LEVEL_RATE_HZ: float = 14.0     # smoothing of the three levels
TRUST_FOR_FALLBACK: float = 0.3


class Kick_bands_mode(Mode):
    """
    Kick & Bands: height is pitch, the kick punches from the floor.
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
        self._acc = np.zeros((n, 3), dtype=np.float64)
        self._tmp = np.zeros((n, 3), dtype=np.float64)
        self._front = np.zeros(n, dtype=np.float64)
        self._front2d = self._front[:, None]
        self._peak = np.zeros(n, dtype=np.float64)
        self._peak2d = self._peak[:, None]
        self._colour = np.zeros(3, dtype=np.float64)
        self._white = np.array([255.0, 255.0, 255.0])
        self._bass = self._mid = self._high = 0.0
        self._kick_env = self._snare_env = self._drop_env = 0.0
        self._since_kick = 10.0
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

    def run(self) -> None:
        dt = self.dt
        ctx = getattr(self.listener, "context", None)
        kick, snare, drop = self._hits()
        bass, mid, high = self._levels()

        a = self.alpha(LEVEL_RATE_HZ)
        self._bass += a * (bass - self._bass)
        self._mid += a * (mid - self._mid)
        self._high += a * (high - self._high)

        self._kick_env *= math.exp(-dt / KICK_DECAY_S)
        self._snare_env *= math.exp(-dt / SNARE_DECAY_S)
        self._drop_env *= math.exp(-dt / DROP_DECAY_S)
        self._since_kick += dt
        if kick > 0.0:
            self._kick_env = max(self._kick_env, 0.45 + 0.55 * min(1.0, kick))
            self._since_kick = 0.0
        if snare > 0.0:
            self._snare_env = max(self._snare_env, 0.4 + 0.6 * min(1.0, snare))
        if drop:
            self._drop_env = 1.0

        silent = bool(getattr(ctx, "is_silent", False)) if ctx is not None else False
        self._visible += self.alpha(3.0) * ((0.0 if silent else 1.0) - self._visible)

        # the picture of the sound: three coloured zones by height
        self._acc.fill(0.0)
        self._add(self._w_bass, 0, 0.10 + 0.55 * self._bass ** 1.5)
        self._add(self._w_mid, 127, 0.06 + 0.45 * self._mid ** 1.5)
        self._add(self._w_high, 255, 0.06 + 0.55 * self._high ** 1.5)

        # the kick: a flash low down, and a front climbing from the floor
        np.subtract(self._alt, self._since_kick * FRONT_SPEED, out=self._front)
        np.multiply(self._front, self._front, out=self._front)
        np.multiply(self._front, -1.0 / (FRONT_WIDTH * FRONT_WIDTH), out=self._front)
        np.exp(self._front, out=self._front)
        np.multiply(self._front, 0.9 * self._kick_env, out=self._front)
        np.multiply(self._front2d, self.highlight_color, out=self._tmp)
        np.add(self._acc, self._tmp, out=self._acc)
        self._add(self._w_bass, 0, 1.3 * self._kick_env)

        # the snare from the top, the drop everywhere
        np.multiply(self._w_high, self._white, out=self._tmp)
        np.multiply(self._tmp, 0.75 * self._snare_env, out=self._tmp)
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
