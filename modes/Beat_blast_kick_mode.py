"""
modes/Beat_blast_kick_mode.py - Monolithic Beat Blast adapted to the analyzer's new
outputs (work list C10).
Lead: transient
Secondary: spectrum

One idea: the radial shockwave rings of Monolithic Beat Blast, punched by the kick the analyzer hears instead of
the beat tracker's pump, held calm (no flash, slow drift) while the kick is away, and lit bass at the core,
treble at the rim.

What changes from `modes/Monolithic_beat_blast_mode.py`, and why:

- The punch. The original pumps its rings with `beat_pulse()` (the beat tracker's phase: up on every predicted
  beat, heard or not) and flashes white on `is_real_beat`. Here the rings jump on `kick`, a hit the analyzer
  heard, and the white flash rides on that jump.
- The ration (flash safety, WCAG 2.3.1). A kick gets a full punch only if the last full punch is at least
  0.46 s old (so never four in a second); a kick that comes sooner only brightens the rings a little, inside
  the resting layer. As in `Kick_bands_safe_mode`, the resting layer is measured on each third of the height
  and scaled down as a whole when it goes over 7% of full light, so it can never make a flash on its own.
- The breaks. While `kick_present` is false, or `no_beat` is true, the rings keep drifting (slower, at the
  speed of the loudness), swell with the loudness, and no kick gets a full punch. The owner
  once preferred a break that kept moving (Nobody Rules the Streets), so the break is calmer but never still:
  the breath stays inside the resting layer, too small to be a flash. The first kick after the kick comes back
  gets a full punch at once (the ration allowing).
- The bands. The ring brightness is weighted by distance from the centre: `band_bass` lights the core,
  `band_mid` the middle rings, `band_high` the rim. The palette already goes from its first colour at the core
  to its last at the rim, so bass and treble differ by place and by colour.
- A drop lights every ring for about half a second (only as a full punch, so it counts in the ration).

Signals read from listener.signals, each with a fallback for when the slot is empty:

    kick                    fallback: a real beat while the beat tracker is locked (what the original flashed on)
    kick_present, no_beat   fallback: the beat tracker's lock (rhythm_lock above 0.4 = kick present)
    band_bass / mid / high  fallback: the 16-band spectrum, grouped in three
    drop                    fallback: the drop helper of Mode
    loudness                fallback: the context's energy

Promoted from the choreography lab on 2026-11-27 at the owner's request, before the owner had watched the
lab clips. The lab copy, its gate report and its notes: research/choreography/candidates/Beat_blast_kick_mode.py,
research/choreography/runs/Beat_blast_kick_mode/NOTES.md. No array is created in run().
"""
import math
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from modes.Mode import Mode
from utils.global_mode import SegmentSpatialProfile

FULL_GAP_S: float = 0.46        # a full punch at most this often (four cannot start within one second)
JOIN_S: float = 0.055           # a full punch is held at its top this long; a hit inside it joins it
REST_LIGHT_MAX: float = 0.07    # most light the resting layer may give on any third of the height (under 0.10)
REST_GAIN: float = 0.30         # ring brightness of the resting layer, before the bands weigh it
SOFT_GAIN: float = 0.35         # what a refused kick adds to the resting rings
FULL_GAIN: float = 1.0          # what a full punch adds to the rings
WHITE: float = 90.0             # white added to the rings at the top of a full punch (drive value)
BAND_FLOOR: float = 0.25        # a silent range still leaves this much of its rings
BAND_POWER: float = 2.0         # level to weight: steep, because the eye flattens
KICK_DECAY_S: float = 0.13
DROP_DECAY_S: float = 0.5
BREAK_DIM: float = 0.30         # resting light during a break, against normal, at the bottom of its breath...
BREAK_PUMP: float = 1.0         # ...plus this much on the loudness: the break follows the music's own swells (not
                                # the beat tracker's predicted beats, which drew pulses on beats that are not there),
                                # inside the resting layer (held under REST_LIGHT_MAX), so it moves but cannot flash
BREAK_SPEED: float = 0.45       # ring drift during a break, against normal
LEVEL_RATE_HZ: float = 14.0
PRESENT_RATE_HZ: float = 2.5    # how fast the look follows the kick leaving and coming back
LOCK_FOR_PRESENT: float = 0.4
LIGHT_OF_RGB = (0.2126 / 255.0, 0.7152 / 255.0, 0.0722 / 255.0)


class Beat_blast_kick_mode(Mode):
    """
    Beat Blast, kick: radial rings punched by the heard kick, calm without it, bass at the core, treble at the rim.
    Lead: transient (kick, drop)
    Secondary: spectrum (bass, mid and treble levels)
    """

    IS_GLOBAL: bool = True
    LEAD: str = "transient"
    SECONDARY: tuple = ("spectrum",)

    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]) -> None:
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)
        self.spatial = SegmentSpatialProfile(segment_name=segment_name, nb_of_leds=self.nb_of_leds,
                                             tags=infos.get("tags", ()), orientation=infos.get("orientation"))
        self.wave_speed: float = float(infos.get("wave_speed", 1.0))
        self.wave_width: float = float(infos.get("wave_width", 0.08))
        n = max(1, self.nb_of_leds)
        self._radius = np.zeros(n, dtype=np.float64)
        self._lut_indices = np.zeros(n, dtype=np.int32)
        self._w_bass = np.zeros(n, dtype=np.float64)
        self._w_mid = np.zeros(n, dtype=np.float64)
        self._w_high = np.zeros(n, dtype=np.float64)
        self._weight = np.zeros(n, dtype=np.float64)
        self._ring = np.zeros(n, dtype=np.float64)
        self._ring2d = self._ring[:, None]
        self._scratch = np.zeros(n, dtype=np.float64)
        self._scratch2d = self._scratch[:, None]
        self._lut_rgb = np.zeros((n, 3), dtype=np.int32)
        self._acc = np.zeros((n, 3), dtype=np.float64)
        self._tmp = np.zeros((n, 3), dtype=np.float64)
        self._peak = np.zeros(n, dtype=np.float64)
        self._peak2d = self._peak[:, None]
        self._light = np.zeros(n, dtype=np.float64)
        self._light_of_rgb = np.array(LIGHT_OF_RGB, dtype=np.float64)
        self._zones: List[np.ndarray] = []
        self._recompute_spatial_buffers()

        self.wave_phase = 0.0
        self.prev_beat_phase = 0.0
        self._bass = self._mid = self._high = self._loud = 0.0
        self._present = 1.0                              # 1 = the kick is here, 0 = break (smoothed)
        self._was_present = True
        self._kick_full = self._kick_soft = 0.0
        self._drop_env = 0.0
        self._since_full = 10.0
        self._visible = 1.0

    def _recompute_spatial_buffers(self) -> None:
        """Distance from the installation's centre (as the original), band weights by distance, thirds of height."""
        np.hypot(self.spatial.x_norm - 0.620, self.spatial.y_norm - 0.450, out=self._radius)
        np.clip((self._radius / 0.70 * 255.0).astype(np.int32), 0, 255, out=self._lut_indices)
        r = np.clip(self._radius / 0.70, 0.0, 1.0)
        np.clip(1.0 - r / 0.45, 0.0, 1.0, out=self._w_bass)
        np.clip(1.0 - np.abs(r - 0.5) / 0.32, 0.0, 1.0, out=self._w_mid)
        np.clip((r - 0.55) / 0.40, 0.0, 1.0, out=self._w_high)
        alt = self.spatial.altitude
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
            {"key": "wave_speed", "label": "Shockwave Speed", "valueType": "number", "min": 0.5, "max": 2.5,
             "default": 1.0, "step": 0.1, "attr": "wave_speed"},
            {"key": "wave_width", "label": "Wavefront Thickness", "valueType": "number", "min": 0.04, "max": 0.20,
             "default": 0.08, "step": 0.02, "attr": "wave_width"},
        ]

    # -- signals, each with its fallback ---------------------------------------------------------------
    def _read(self) -> tuple:
        """(kick strength, drop, kick present, bass, mid, high, loudness)."""
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
        no_beat = getattr(sig, "no_beat", None)
        present = bool(present) and not bool(no_beat)
        bass, mid, high = getattr(sig, "band_bass", None), getattr(sig, "band_mid", None), getattr(sig, "band_high", None)
        if bass is None or mid is None or high is None:
            bands = listener.asserved_fft_band
            k = len(bands)
            bass = float(bands[0]) if bass is None else bass
            mid = float(np.add.reduce(bands[1 : k // 2 + 1])) / max(1, k // 2) if mid is None else mid
            high = float(np.add.reduce(bands[k // 2 + 1 :])) / max(1, k - k // 2 - 1) if high is None else high
        loud = getattr(sig, "loudness", None)
        if loud is None:
            loud = float(getattr(ctx, "energy", 0.5)) if ctx is not None else 0.5
        return float(kick), bool(drop), present, float(bass), float(mid), float(high), float(loud)

    # -- drawing -----------------------------------------------------------------------------------------
    def _rings(self) -> None:
        """self._ring = the radial rings of the original at the current phase, 0..1 (pure black between them)."""
        wavelength = 0.30
        d = self._scratch
        np.subtract(self._radius, self.wave_phase * wavelength, out=d)
        np.divide(d, wavelength, out=d)
        np.add(d, 0.5, out=d)
        np.mod(d, 1.0, out=d)
        np.subtract(d, 0.5, out=d)
        np.multiply(d, wavelength, out=d)
        sigma = max(0.01, self.wave_width * 0.75)
        np.multiply(d, d, out=d)
        np.multiply(d, -1.0 / (2.0 * sigma * sigma), out=d)
        np.exp(d, out=self._ring)
        np.subtract(self._ring, 0.05, out=self._ring)
        np.multiply(self._ring, 1.0 / 0.95, out=self._ring)
        np.maximum(self._ring, 0.0, out=self._ring)

    def _add_rings(self, weight: np.ndarray, gain: float) -> None:
        """acc += palette colour by distance * ring * weight * gain."""
        np.multiply(self._ring, weight, out=self._scratch)
        np.multiply(self._scratch, gain, out=self._scratch)
        np.multiply(self._lut_rgb, self._scratch2d, out=self._tmp)
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
        kick, drop, present, bass, mid, high, loud = self._read()

        a = self.alpha(LEVEL_RATE_HZ)
        self._bass += a * (bass - self._bass)
        self._mid += a * (mid - self._mid)
        self._high += a * (high - self._high)
        self._present += self.alpha(PRESENT_RATE_HZ) * ((1.0 if present else 0.0) - self._present)
        came_back = present and not self._was_present
        self._was_present = present

        # ring drift: on the beat phase while locked (as the original), on loudness otherwise; slower in a break
        phase = float(getattr(self.listener, "beat_phase", 0.0))
        delta_p = (phase - self.prev_beat_phase) % 1.0
        if delta_p > 0.5:
            delta_p = 0.0
        self.prev_beat_phase = phase
        lock_gate = min(1.0, self.rhythm_lock / 0.45)
        step = (lock_gate * delta_p + (1.0 - lock_gate) * dt * 1.5 * (0.45 + 0.55 * loud)) * self.mood_pace * self.wave_speed
        step *= BREAK_SPEED + (1.0 - BREAK_SPEED) * self._present
        self.wave_phase = (self.wave_phase + step) % 1.0

        # envelopes and the ration
        self._since_full += dt
        held = self._since_full <= JOIN_S
        fade = math.exp(-dt / KICK_DECAY_S)
        self._kick_soft *= fade
        if not held:
            self._kick_full *= fade
            self._drop_env *= math.exp(-dt / DROP_DECAY_S)
        if came_back:
            self._kick_soft = 0.0
        if kick > 0.0 or drop:
            full = held
            if not held and present and self._since_full >= FULL_GAP_S:
                full = True
                self._since_full = 0.0
            strength = 0.5 + 0.5 * min(1.0, kick) if kick > 0.0 else 0.0
            if full:
                self._kick_full = max(self._kick_full, strength)
                if drop:
                    self._drop_env = 1.0
            elif kick > 0.0:
                self._kick_soft = max(self._kick_soft, strength)

        silent = bool(getattr(ctx, "is_silent", False)) if ctx is not None else False
        self._visible += self.alpha(3.0) * ((0.0 if silent else 1.0) - self._visible)

        # band weight of each LED: bass at the core, mid in between, treble at the rim
        span = 1.0 - BAND_FLOOR
        np.multiply(self._w_bass, BAND_FLOOR + span * self._bass ** BAND_POWER, out=self._weight)
        np.multiply(self._w_mid, BAND_FLOOR + span * self._mid ** BAND_POWER, out=self._scratch)
        np.add(self._weight, self._scratch, out=self._weight)
        np.multiply(self._w_high, BAND_FLOOR + span * self._high ** BAND_POWER, out=self._scratch)
        np.add(self._weight, self._scratch, out=self._weight)
        np.minimum(self._weight, 1.0, out=self._weight)

        self._rings()
        np.take(self.palette_lut, self._lut_indices, axis=0, out=self._lut_rgb)

        # resting layer: dim rings weighted by the bands, plus the small lift of refused kicks
        self._acc.fill(0.0)
        self._loud += self.alpha(LEVEL_RATE_HZ) * (loud - self._loud)
        breath = BREAK_DIM + BREAK_PUMP * self._loud ** BAND_POWER
        rest = (breath + (1.0 - breath) * self._present) * (REST_GAIN + SOFT_GAIN * self._kick_soft)
        self._add_rings(self._weight, rest)
        self._hold_resting_light()

        # flash layer: the rationed full punch lights the rings (band-weighted, but every ring), white on top
        punch = max(self._kick_full, 0.8 * self._drop_env)
        if punch > 0.01:
            np.maximum(self._weight, 0.5, out=self._scratch)
            np.multiply(self._scratch, self._ring, out=self._scratch)
            np.multiply(self._scratch, FULL_GAIN * punch, out=self._scratch)
            np.multiply(self._lut_rgb, self._scratch2d, out=self._tmp)
            np.add(self._acc, self._tmp, out=self._acc)
            np.multiply(self._ring, WHITE * punch, out=self._scratch)
            np.add(self._acc, self._scratch2d, out=self._acc)

        np.multiply(self._acc, self._visible, out=self._acc)
        np.max(self._acc, axis=1, out=self._peak)
        np.maximum(self._peak, 255.0, out=self._peak)
        np.divide(255.0, self._peak, out=self._peak)
        np.multiply(self._acc, self._peak2d, out=self._acc)
        np.clip(self._acc, 0.0, 255.0, out=self._acc)
        np.copyto(self.rgb_list, self._acc, casting="unsafe")
