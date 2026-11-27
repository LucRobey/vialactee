"""
modes/Avalanche_bands_mode.py - Spectral Avalanche adapted to the analyzer's new
outputs (work list C12, second half).
Lead: transient
Secondary: spectrum

One idea: the waterfall of Spectral Avalanche, flowing down at a calm pace set by the loudness, lit by the three
bands of the analyzer at their heights (treble high, middle in between, bass low), and every heard kick makes
it flare at once and drops a bright front from the canopy.

What changes from `modes/Spectral_avalanche_mode.py`, and why:

- The flow. The original moves its stripes by the frame-to-frame change of the raw 16 bands, times 45: on busy
  music the stripes jump by a large part of their length from one frame to the next and strobe (up to 19.5
  flashes in one second on the gate's passages). Here the flow speed follows the loudness, smoothed, and never
  goes over FLOW_MAX heights a second.
- The bands. The original reads one of the 16 raw bands per height. Here `band_high` lights the top,
  `band_mid` the middle, `band_bass` the bottom; each band is read against its own recent range (as in
  `Band_vu_mode`), so it uses its whole span on any song.
- The kick. The original nudges its gain on the beat tracker's pulse (15%). Here a heard `kick` (while
  `kick_present`) makes the whole waterfall flare, and drops a white front from the canopy to the floor in
  0.35 s. A full flare at most every 0.44 s; a kick that comes sooner only drops the front, dimmer. The fronts
  belong to the resting layer below, so they cannot flash.
- Flash safety by construction (as `Kick_bands_safe_mode`): the resting layer (the waterfall and the thin
  fronts) is measured on each third of the height and scaled down when it gives more than 7% of full light, so
  it cannot make a flash alone; the flare is rationed.
- The breaks: no flare and no front; the waterfall keeps flowing with the loudness.

Signals read from listener.signals, each with a fallback for when the slot is empty:

    band_bass / mid / high  fallback: the 16-band spectrum, grouped in three
    kick                    fallback: a beat whose dominant drum is tagged kick by the production analyzer
    kick_present, no_beat   fallback: the beat tracker's lock (rhythm_lock above 0.4 = kick present)
    loudness                fallback: the context's energy

Promoted from the choreography lab on 2026-11-27 at the owner's request, before the owner had watched the
lab clips. The lab copy, its gate report and its notes: research/choreography/candidates/Avalanche_bands_mode.py,
research/choreography/runs/Avalanche_bands_mode/NOTES.md. No array is created in run().
"""
import math
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from modes.Mode import Mode
from utils.global_mode import SegmentSpatialProfile

FLOW_MIN: float = 0.08          # waterfall speed, in installation heights a second, in silence...
FLOW_MAX: float = 0.45          # ...and at full loudness. A stripe passes a point at most about once a second
FLOW_RATE_HZ: float = 1.5       # smoothing of the speed
WAVE_DEPTH: float = 0.55        # how dark the gaps between stripes are (0 = no stripes, 1 = black gaps)
RANGE_DRIFT: float = 0.08       # each band read against its own recent range (see Band_vu_mode)
MIN_SPAN: float = 0.25
LEVEL_RATE_HZ: float = 14.0
BAND_FLOOR: float = 0.15        # a silent band still leaves this much of its stripes
REST_GAIN: float = 0.55         # drive of the waterfall at rest (before the limit below)
REST_LIGHT_MAX: float = 0.07    # most light the resting layer may give on any third of the height
FULL_GAP_S: float = 0.44        # a full flare at most this often
FLARE: float = 1.0              # what a full flare adds to the waterfall (drive, share of full)
FLARE_DECAY_S: float = 0.14
FRONT_TIME_S: float = 0.35      # a kick front falls from the canopy to the floor in this time
FRONT_WIDTH: float = 0.07
FRONT_FULL: float = 0.9         # the front of a full flare, in white
FRONT_SOFT: float = 0.45        # the front of a refused kick (in the resting layer)
FRONT_DECAY_S: float = 0.30
PRESENT_RATE_HZ: float = 2.5
LOCK_FOR_PRESENT: float = 0.4
TRUST_FOR_FALLBACK: float = 0.3
LIGHT_OF_RGB = (0.2126 / 255.0, 0.7152 / 255.0, 0.0722 / 255.0)


class Avalanche_bands_mode(Mode):
    """
    Avalanche, bands: a calm waterfall lit by the three bands at their heights, flaring on every heard kick.
    Lead: transient (kick: the flare carries most of the motion, as measured by the driver mute test)
    Secondary: spectrum (bass, mid and treble levels)
    """

    IS_GLOBAL: bool = True
    LEAD: str = "transient"
    SECONDARY: tuple = ("spectrum",)

    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]) -> None:
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)
        self.spatial = SegmentSpatialProfile(segment_name=segment_name, nb_of_leds=self.nb_of_leds,
                                             tags=infos.get("tags", ()), orientation=infos.get("orientation"))
        self.gravity: float = float(infos.get("gravity", 1.0))
        n = max(1, self.nb_of_leds)
        self._alt = np.zeros(n, dtype=np.float64)
        self._w_bass = np.zeros(n, dtype=np.float64)
        self._w_mid = np.zeros(n, dtype=np.float64)
        self._w_high = np.zeros(n, dtype=np.float64)
        self._lut_indices = np.zeros(n, dtype=np.int32)
        self._wave = np.zeros(n, dtype=np.float64)
        self._weight = np.zeros(n, dtype=np.float64)
        self._scratch = np.zeros(n, dtype=np.float64)
        self._scratch2d = self._scratch[:, None]
        self._base_rgb = np.zeros((n, 3), dtype=np.int32)
        self._acc = np.zeros((n, 3), dtype=np.float64)
        self._tmp = np.zeros((n, 3), dtype=np.float64)
        self._peak = np.zeros(n, dtype=np.float64)
        self._peak2d = self._peak[:, None]
        self._light = np.zeros(n, dtype=np.float64)
        self._light_of_rgb = np.array(LIGHT_OF_RGB, dtype=np.float64)
        self._white = np.array([255.0, 255.0, 255.0])
        self._zones: List[np.ndarray] = []
        self._recompute_spatial_buffers()

        self.flow_offset = 0.0
        self._speed = FLOW_MIN
        self._levels = np.zeros(3, dtype=np.float64)     # smoothed bass, mid, high, each 0..1 in its own range
        self._lo = np.array([0.3, 0.3, 0.3])
        self._hi = np.array([0.9, 0.9, 0.9])
        self._present = 1.0
        self._flare = 0.0
        self._front_full = self._front_soft = 0.0
        self._since_full = self._since_front_full = self._since_front_soft = 10.0
        self._visible = 1.0

    def _recompute_spatial_buffers(self) -> None:
        alt = self.spatial.altitude
        np.copyto(self._alt, alt)
        np.clip(1.0 - alt / 0.45, 0.0, 1.0, out=self._w_bass)
        np.clip(1.0 - np.abs(alt - 0.5) / 0.32, 0.0, 1.0, out=self._w_mid)
        np.clip((alt - 0.55) / 0.40, 0.0, 1.0, out=self._w_high)
        self._lut_indices[:] = np.clip((alt * 255.0).astype(np.int32), 0, 255)
        self._zones = []
        for mask in (alt < 1.0 / 3.0, (alt >= 1.0 / 3.0) & (alt <= 2.0 / 3.0), alt > 2.0 / 3.0):
            if mask.any():
                self._zones.append(mask.astype(np.float64) / float(mask.sum()))

    def bind_segment_geometry(self, seg_id: Optional[str] = None, orientation: Optional[str] = None,
                              tags: Sequence[str] = (), coords_array: Optional[np.ndarray] = None) -> None:
        self.spatial.bind(seg_id, orientation, tags, coords_array)
        self._recompute_spatial_buffers()

    def get_settings_schema(self) -> List[Dict[str, Any]]:
        return [
            {"key": "gravity", "label": "Downward Flow Speed", "valueType": "number", "min": 0.5, "max": 2.5,
             "default": 1.0, "step": 0.1, "attr": "gravity"},
        ]

    # -- signals, each with its fallback ---------------------------------------------------------------
    def _read(self) -> tuple:
        """(bass, mid, high, kick strength, kick present, loudness)."""
        listener = self.listener
        sig = getattr(listener, "signals", None)
        ctx = getattr(listener, "context", None)
        bass, mid, high = getattr(sig, "band_bass", None), getattr(sig, "band_mid", None), getattr(sig, "band_high", None)
        if bass is None or mid is None or high is None:
            bands = listener.asserved_fft_band
            k = len(bands)
            bass = float(bands[0]) if bass is None else bass
            mid = float(np.add.reduce(bands[1 : k // 2 + 1])) / max(1, k // 2) if mid is None else mid
            high = float(np.add.reduce(bands[k // 2 + 1 :])) / max(1, k - k // 2 - 1) if high is None else high
        kick = getattr(sig, "kick", None)
        if kick is None:
            tagged = bool(getattr(listener, "is_beat", False)) and float(getattr(listener, "beat_trust", 0.0)) > TRUST_FOR_FALLBACK
            kick = 0.8 if tagged and getattr(listener, "beat_tag", "") == "Bass/Kick" else 0.0
        present = getattr(sig, "kick_present", None)
        if present is None:
            present = self.rhythm_lock > LOCK_FOR_PRESENT
        present = bool(present) and not bool(getattr(sig, "no_beat", None))
        loud = getattr(sig, "loudness", None)
        if loud is None:
            loud = float(getattr(ctx, "energy", 0.5)) if ctx is not None else 0.5
        return float(bass), float(mid), float(high), float(kick), present, float(loud)

    # -- drawing -----------------------------------------------------------------------------------------
    def _add_front(self, since_s: float, gain: float, colour: np.ndarray) -> None:
        """acc += colour * a bright band at the height a front launched `since_s` ago has fallen to."""
        np.subtract(self._alt, 1.0 - since_s / FRONT_TIME_S, out=self._scratch)
        np.multiply(self._scratch, self._scratch, out=self._scratch)
        np.multiply(self._scratch, -1.0 / (FRONT_WIDTH * FRONT_WIDTH), out=self._scratch)
        np.exp(self._scratch, out=self._scratch)
        np.multiply(self._scratch, gain, out=self._scratch)
        np.multiply(self._scratch2d, colour, out=self._tmp)
        np.add(self._acc, self._tmp, out=self._acc)

    def _hold_resting_light(self) -> None:
        np.dot(self._acc, self._light_of_rgb, out=self._light)
        most = 0.0
        for zone in self._zones:                         # at most three zones: not a loop over LEDs
            most = max(most, float(np.dot(self._light, zone)))
        if most > REST_LIGHT_MAX:
            np.multiply(self._acc, REST_LIGHT_MAX / most, out=self._acc)

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return
        dt = self.dt
        ctx = getattr(self.listener, "context", None)
        bass, mid, high, kick, present, loud = self._read()
        self._present += self.alpha(PRESENT_RATE_HZ) * ((1.0 if present else 0.0) - self._present)

        # each band against its own recent range, then smoothed
        drift = RANGE_DRIFT * dt
        a = self.alpha(LEVEL_RATE_HZ)
        for i, level in enumerate((bass, mid, high)):    # three bands: not a loop over LEDs
            hi = max(level, float(self._hi[i]) - drift)
            lo = min(level, float(self._lo[i]) + drift)
            if hi - lo < MIN_SPAN:
                m = 0.5 * (hi + lo)
                lo, hi = m - 0.5 * MIN_SPAN, m + 0.5 * MIN_SPAN
            self._hi[i], self._lo[i] = hi, lo
            target = min(1.0, max(0.0, (level - lo) / (hi - lo)))
            self._levels[i] += a * (target - float(self._levels[i]))

        # the flow: calm, set by the loudness
        speed_target = (FLOW_MIN + (FLOW_MAX - FLOW_MIN) * min(1.0, max(0.0, loud))) * self.gravity * self.mood_pace
        self._speed += self.alpha(FLOW_RATE_HZ) * (min(FLOW_MAX * self.gravity, speed_target) - self._speed)
        self.flow_offset = (self.flow_offset + self._speed * dt) % 1.0

        # kicks: the ration
        self._since_full += dt
        self._since_front_full += dt
        self._since_front_soft += dt
        self._flare *= math.exp(-dt / FLARE_DECAY_S)
        front_fade = math.exp(-dt / FRONT_DECAY_S)
        self._front_full *= front_fade
        self._front_soft *= front_fade
        if kick > 0.0 and present:
            strength = 0.5 + 0.5 * min(1.0, kick)
            if self._since_full >= FULL_GAP_S:
                self._since_full = 0.0
                self._flare = strength
                self._front_full, self._since_front_full = strength, 0.0
            else:
                self._front_soft, self._since_front_soft = strength, 0.0

        silent = bool(getattr(ctx, "is_silent", False)) if ctx is not None else False
        self._visible += self.alpha(3.0) * ((0.0 if silent else 1.0) - self._visible)

        # stripes falling down (the wave moves toward the floor as the offset grows)
        np.add(self._alt, self.flow_offset, out=self._wave)
        np.multiply(self._wave, 4.0 * math.pi, out=self._wave)
        np.sin(self._wave, out=self._wave)
        np.multiply(self._wave, 0.5 * WAVE_DEPTH, out=self._wave)
        np.add(self._wave, 1.0 - 0.5 * WAVE_DEPTH, out=self._wave)

        # band weight of each height
        span = 1.0 - BAND_FLOOR
        np.multiply(self._w_bass, BAND_FLOOR + span * float(self._levels[0]), out=self._weight)
        np.multiply(self._w_mid, BAND_FLOOR + span * float(self._levels[1]), out=self._scratch)
        np.add(self._weight, self._scratch, out=self._weight)
        np.multiply(self._w_high, BAND_FLOOR + span * float(self._levels[2]), out=self._scratch)
        np.add(self._weight, self._scratch, out=self._weight)
        np.minimum(self._weight, 1.0, out=self._weight)
        np.multiply(self._wave, self._weight, out=self._wave)          # the waterfall, 0..1

        np.take(self.palette_lut, self._lut_indices, axis=0, out=self._base_rgb, mode="clip")

        # resting layer: the waterfall and the soft fronts
        np.multiply(self._wave, REST_GAIN, out=self._scratch)
        np.multiply(self._base_rgb, self._scratch2d, out=self._acc)
        if self._front_soft > 0.01 and self._since_front_soft < FRONT_TIME_S * 1.3:
            self._add_front(self._since_front_soft, FRONT_SOFT * self._front_soft, self._white)
        if self._front_full > 0.01 and self._since_front_full < FRONT_TIME_S * 1.3:
            self._add_front(self._since_front_full, FRONT_FULL * self._front_full, self._white)
        self._hold_resting_light()

        # flash layer: the flare of the whole waterfall. The white front stays in the resting layer: as a flash it
        # made a second bump in each third of the height as it fell through (4.5 flashes a second on fast kicks)
        if self._flare > 0.01:
            np.multiply(self._wave, FLARE * self._flare, out=self._scratch)
            np.multiply(self._base_rgb, self._scratch2d, out=self._tmp)
            np.add(self._acc, self._tmp, out=self._acc)

        np.multiply(self._acc, self._visible, out=self._acc)
        np.max(self._acc, axis=1, out=self._peak)
        np.maximum(self._peak, 255.0, out=self._peak)
        np.divide(255.0, self._peak, out=self._peak)
        np.multiply(self._acc, self._peak2d, out=self._acc)
        np.clip(self._acc, 0.0, 255.0, out=self._acc)
        np.copyto(self.rgb_list, self._acc, casting="unsafe")
