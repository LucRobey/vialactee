"""
modes/Stalagmites_mode.py
Ensemble global mode: every bass hit throws a red bar up from the floor, every snare hit throws a
blue bar down from the ceiling.
Lead: transient
Secondary: spectrum
"""

import math
from typing import Any, Dict, List

import numpy as np

from modes.Ensemble_mode_base import Ensemble_mode_base
from utils.cast import CAST_TOPOLOGY, Fixture

STALAGMITES: str = "stalagmites"
STALACTITES: str = "stalactites"
BASS_RUNGS: str = "bass_rungs"
TREBLE_RUNGS: str = "treble_rungs"
CANOPY: str = "canopy"

# The physical chandelier decides the casting: the inner pillars stand on the floor and stop at the
# mid rungs; the outer pillars hang from the canopy and stop at the low rungs.
_GROUP_PART: Dict[str, str] = {
    "core_pillar": STALAGMITES,
    "outer_pillar": STALACTITES,
    "mid_rung": BASS_RUNGS,
    "low_rung": TREBLE_RUNGS,
    "wing": CANOPY,
    "crown": CANOPY,
}

# Band ranges as fractions of the Mel axis (16 bands, 20 Hz - 20 kHz).
BASS_BANDS = (0.0, 0.125)          # 20 - 400 Hz: kick drum, bass notes ("boum")
SNAP_BANDS = (0.375, 0.625)        # 1.8 - 5 kHz: snare crack, claps ("tchak")
AIR_BANDS = (0.6875, 1.0)          # 6.5 - 20 kHz: hi-hats, cymbals

# Fixed warm / cold colours so "red is the bass, blue is the treble" never changes.
OWN_BASS = np.array((255.0, 24.0, 0.0))
OWN_TREBLE = np.array((0.0, 110.0, 255.0))
OWN_CANOPY = np.array((0.0, 235.0, 255.0))

FLUX_PEAK_DECAY_HZ: float = 0.07   # per-band onset scale: slow, so hit strength stays readable
SLOW_PEAK_DECAY_HZ: float = 0.01
FLOOR_FRACTION: float = 0.20       # a band's scale never drops below 20% of its long-term peak
FLUX_FLOOR: float = 1.0
BASS_GATE: float = 0.12            # onsets weaker than this fraction of the scale are noise
SNAP_GATE: float = 0.35            # higher: hi-hats and voices leak into the snare range
SNAP_CURVE: float = 1.3            # weak snaps stay small, only a real snare throws the bar far
SNARE_DUCK: float = 0.25           # a snare also thumps the low range: hold the red bar back a little
BASS_BOOST: float = 1.3            # the low scale is set by kick + snare together; let a lone kick reach the top
GRAVITY_PER_FALL_RATE: float = 2.5  # fall_rate 4.5 -> a full bar falls back in 0.42 s
RISE_HZ_RAW: float = 60.0          # bar rise rate at smoothness just above 0 ...
RISE_HZ_SOFT: float = 8.0          # ... and at smoothness 1 (0.5 -> about 22 Hz, ~0.1 s to rise)
CREST_MAX_SMOOTHNESS: float = 0.25  # the white rung strike frame only exists for near-raw hits
SUSTAIN_FLOOR: float = 0.18        # a held note keeps at most this much of the pillar lit
SUSTAIN_ATTACK_HZ: float = 20.0
SUSTAIN_RELEASE_HZ: float = 4.0
SUSTAIN_PEAK_DECAY_HZ: float = 0.15
SUSTAIN_AGC_FLOOR: float = 0.12
RUNG_ON: float = 0.75              # only a hit that throws the bar this far strikes the rung
RUNG_RELEASE_HZ: float = 7.0
RUNG_REARM: float = 0.25
SPARK_DECAY_HZ: float = 9.0
SPARK_ONSET: float = 0.35
ONSET_REFRACTORY_S: float = 0.12
SPARK_PATTERNS: int = 16
SPARK_CELL_LEDS: int = 8


class Stalagmites_mode(Ensemble_mode_base):
    """
    Stalagmites: the drum kit drawn on the chandelier (Ensemble Laws E1-E6). Each bass hit throws a
    red bar up from the floor, each snare hit throws a blue bar down from the ceiling; both fall back
    under gravity. A bar thrown all the way strikes the rung at its end. Hi-hats sparkle on the canopy.
    Lead: transient (onset strength per frequency range, from band_flux)
    Secondary: spectrum (a held note keeps a short stub of its bar lit)
    Part stalagmites:  inner pillars; red bar thrown up from the floor by each bass onset (transient)
    Part stalactites:  outer pillars; blue bar thrown down from the top by each snare onset (transient)
    Part bass_rungs:   mid rungs; struck when a bass hit throws its bar to the top (transient)
    Part treble_rungs: low rungs; struck when a snare hit throws its bar to the bottom (transient)
    Part canopy:       sparkles on hi-hat onsets (transient)
    """

    LEAD: str = "transient"
    SECONDARY: tuple = ("spectrum",)
    PARTS: Dict[str, str] = {
        STALAGMITES: "transient",
        STALACTITES: "transient",
        BASS_RUNGS: "transient",
        TREBLE_RUNGS: "transient",
        CANOPY: "transient",
    }

    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any,
                 indexes: List[int], rgb_list: Any, infos: Dict[str, Any]) -> None:
        self.gain: float = float(infos.get("gain", 1.0))
        self.fall_rate: float = float(infos.get("fall_rate", 4.5))
        self.smoothness: float = float(infos.get("smoothness", 0.5))
        self.sparkle_density: float = float(infos.get("sparkle_density", 0.30))
        self.mood_palette: bool = bool(infos.get("mood_palette", False))

        self.h_bass: float = 0.0           # displayed bar heights (0..1 of the pillar)
        self.h_treble: float = 0.0
        self.rung_bass: float = 0.0
        self.rung_treble: float = 0.0
        self._show_bass: float = 0.0       # thrown part of each bar as displayed (smoothed rise)
        self._show_treble: float = 0.0
        self._hit_bass: float = 0.0        # thrown part of each bar as thrown, and its fall speed
        self._hit_treble: float = 0.0
        self._vel_bass: float = 0.0
        self._vel_treble: float = 0.0
        self._env_low: float = 0.0         # held-note stub (spectrum)
        self._env_high: float = 0.0
        self._peak_low: float = SUSTAIN_AGC_FLOOR
        self._peak_high: float = SUSTAIN_AGC_FLOOR
        self._armed_bass: bool = True
        self._armed_treble: bool = True
        self._crest_bass: bool = False
        self._crest_treble: bool = False
        self._cooldown: float = 0.0
        self._onsets: int = 0

        self._col_bass = np.zeros(3, dtype=np.float64)
        self._col_treble = np.zeros(3, dtype=np.float64)
        self._col_canopy = np.zeros(3, dtype=np.float64)
        self._nb: int = 0
        flux = getattr(listener, "band_flux", None)
        self._alloc_bands(len(flux) if flux is not None and len(flux) > 0 else 16)
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)

    # Geometry -----------------------------------------------------------------------------
    def _alloc_bands(self, nb: int) -> None:
        """Per-band onset scales and the three band ranges (init, or when the band count changes)."""
        self._nb = nb
        self._flux_peak = np.full(nb, FLUX_FLOOR, dtype=np.float64)
        self._flux_slow = np.full(nb, FLUX_FLOOR, dtype=np.float64)
        self._flux_floor = np.full(nb, FLUX_FLOOR, dtype=np.float64)
        self._ratio = np.zeros(nb, dtype=np.float64)
        self._ranges = []
        for lo, hi in (BASS_BANDS, SNAP_BANDS, AIR_BANDS):
            a = min(nb - 1, int(round(lo * nb)))
            self._ranges.append((a, max(a + 1, min(nb, int(round(hi * nb))))))
        self._r_bass = self._ratio[self._ranges[0][0]:self._ranges[0][1]]
        self._r_snap = self._ratio[self._ranges[1][0]:self._ranges[1][1]]
        self._r_air = self._ratio[self._ranges[2][0]:self._ranges[2][1]]

    def part_of(self, seg_id: str) -> str:
        entry = CAST_TOPOLOGY.get(seg_id)
        return _GROUP_PART[entry[0]] if entry is not None else CANOPY

    def on_bind(self) -> None:
        """Cut the canopy into sparkle cells and build the deterministic sparkle table (bind time)."""
        n = max(1, self.nb_of_leds)
        shortest = n
        for i, fx in enumerate(self.fixtures):
            if self.fixture_parts[i] == CANOPY:
                shortest = min(shortest, fx.stop - fx.start)
        cell = max(2, min(SPARK_CELL_LEDS, shortest // 6))
        self._cell_idx = np.arange(n, dtype=np.intp) // cell
        nb_cells = int(self._cell_idx[-1]) + 1
        self._cells = np.zeros(nb_cells, dtype=np.float64)
        self._crest = np.zeros(nb_cells, dtype=np.float64)
        self._hit = np.zeros(nb_cells, dtype=bool)
        seed = int(self.segment_phase_offset * 1000.0)
        self._rand = np.random.RandomState(seed).random_sample((SPARK_PATTERNS, nb_cells))
        self._spark = np.zeros(n, dtype=np.float64)
        self._spark_2d = self._spark[:, np.newaxis]
        self._white = np.zeros((n, 3), dtype=np.float64)

    def get_settings_schema(self) -> List[Dict[str, Any]]:
        return [
            {"key": "gain", "label": "Hit Sensitivity", "valueType": "number",
             "min": 0.5, "max": 2.0, "default": 1.0, "step": 0.1, "attr": "gain"},
            {"key": "fall_rate", "label": "Bar Fall Speed", "valueType": "number",
             "min": 2.0, "max": 12.0, "default": 4.5, "step": 0.5, "attr": "fall_rate"},
            {"key": "smoothness", "label": "Smoothness (0: raw hits with white rung strikes)",
             "valueType": "number", "min": 0.0, "max": 1.0, "default": 0.5, "step": 0.05, "attr": "smoothness"},
            {"key": "sparkle_density", "label": "Canopy Sparkle Density", "valueType": "number",
             "min": 0.1, "max": 0.8, "default": 0.30, "step": 0.05, "attr": "sparkle_density"},
            {"key": "mood_palette", "label": "Use Mood Palette (off: red bass, blue treble)",
             "valueType": "boolean", "default": False, "attr": "mood_palette"},
        ]

    # State --------------------------------------------------------------------------------
    def on_reset(self) -> None:
        self.h_bass = self.h_treble = 0.0
        self.rung_bass = self.rung_treble = 0.0
        self._hit_bass = self._hit_treble = 0.0
        self._show_bass = self._show_treble = 0.0
        self._vel_bass = self._vel_treble = 0.0
        self._env_low = self._env_high = 0.0
        self._peak_low = self._peak_high = SUSTAIN_AGC_FLOOR
        self._armed_bass = self._armed_treble = True
        self._crest_bass = self._crest_treble = False
        self._cooldown = 0.0
        self._onsets = 0
        self._flux_peak.fill(FLUX_FLOOR)
        self._flux_slow.fill(FLUX_FLOOR)
        self._cells.fill(0.0)
        self._crest.fill(0.0)

    def _onset_strengths(self, dt: float) -> None:
        """Fill self._ratio with each band's onset strength in [0, 1], relative to its own scale."""
        flux = getattr(self.listener, "band_flux", None)
        nf = len(flux) if flux is not None else 0
        if nf == 0:
            self._ratio.fill(0.0)
            return
        if nf != self._nb:
            self._alloc_bands(nf)
        np.multiply(self._flux_slow, math.exp(-dt * SLOW_PEAK_DECAY_HZ), out=self._flux_slow)
        np.maximum(self._flux_slow, flux, out=self._flux_slow)
        np.multiply(self._flux_slow, FLOOR_FRACTION, out=self._flux_floor)
        np.maximum(self._flux_floor, FLUX_FLOOR, out=self._flux_floor)
        np.multiply(self._flux_peak, math.exp(-dt * FLUX_PEAK_DECAY_HZ), out=self._flux_peak)
        np.maximum(self._flux_peak, flux, out=self._flux_peak)
        np.maximum(self._flux_peak, self._flux_floor, out=self._flux_peak)
        np.divide(flux, self._flux_peak, out=self._ratio)

    def _sustain(self, low: float, high: float, dt: float, trail: float) -> None:
        """Held-note stubs: slow-peak normalised band energy (spectrum)."""
        a_atk = self.alpha(SUSTAIN_ATTACK_HZ)
        a_rel = self.alpha(SUSTAIN_RELEASE_HZ / trail)
        self._env_low += (a_atk if low > self._env_low else a_rel) * (low - self._env_low)
        self._env_high += (a_atk if high > self._env_high else a_rel) * (high - self._env_high)
        peak_decay = math.exp(-dt * SUSTAIN_PEAK_DECAY_HZ)
        self._peak_low = max(SUSTAIN_AGC_FLOOR, low, self._peak_low * peak_decay)
        self._peak_high = max(SUSTAIN_AGC_FLOOR, high, self._peak_high * peak_decay)

    def on_frame(self, ctx: Any, dt: float) -> None:
        if self.mood_palette:
            colors = self.mood_colors
            np.copyto(self._col_bass, colors[0], casting="unsafe")
            np.copyto(self._col_treble, colors[1], casting="unsafe")
            np.copyto(self._col_canopy, colors[2], casting="unsafe")
        else:
            np.copyto(self._col_bass, OWN_BASS)
            np.copyto(self._col_treble, OWN_TREBLE)
            np.copyto(self._col_canopy, OWN_CANOPY)
        trail = max(0.5, self.mood_trail)

        # Transient: how hard each frequency range was just hit.
        self._onset_strengths(dt)
        s_bass = float(self._r_bass.max())
        s_snap = float(self._r_snap.max())
        s_air = float(self._r_air.max())

        # Bars: a hit throws the bar to a height set by its strength; gravity pulls it back.
        # A snare hits both ranges, a kick only the low one: that difference is the "boum tchak".
        gravity = self.fall_rate * GRAVITY_PER_FALL_RATE / trail
        tchak = min(1.0, self.gain * (max(0.0, s_snap - SNAP_GATE) / (1.0 - SNAP_GATE)) ** SNAP_CURVE)
        boum = min(1.0, self.gain * BASS_BOOST * max(0.0, s_bass - BASS_GATE) / (1.0 - BASS_GATE))
        throw = boum * (1.0 - SNARE_DUCK * tchak)
        if throw > self._hit_bass:
            self._hit_bass = throw
            self._vel_bass = 0.0
        else:
            self._vel_bass += gravity * dt
            self._hit_bass = max(0.0, self._hit_bass - self._vel_bass * dt)
        if tchak > self._hit_treble:
            self._hit_treble = tchak
            self._vel_treble = 0.0
        else:
            self._vel_treble += gravity * dt
            self._hit_treble = max(0.0, self._hit_treble - self._vel_treble * dt)

        # Spectrum: a held note keeps a short stub lit, so the bar never vanishes under a pad.
        bands = getattr(self.listener, "asserved_fft_band", None)
        low = 0.0
        high = 0.0
        nb = len(bands) if bands is not None else 0
        if nb == self._nb:
            a, b = self._ranges[0]
            for i in range(a, b):
                low += float(bands[i])
            low = max(0.0, low / (b - a))
            a, b = self._ranges[1]
            for i in range(a, b):
                high += float(bands[i])
            high = max(0.0, high / (b - a))
        self._sustain(low, high, dt, trail)
        # Smoothness: the displayed bar rises toward the thrown height instead of jumping to it,
        # then rides the gravity curve down.
        smooth = max(0.0, min(1.0, self.smoothness))
        rise = 1.0 if smooth <= 0.0 else self.alpha(RISE_HZ_RAW * (RISE_HZ_SOFT / RISE_HZ_RAW) ** smooth)
        if self._hit_bass > self._show_bass:
            self._show_bass += rise * (self._hit_bass - self._show_bass)
        else:
            self._show_bass = self._hit_bass
        if self._hit_treble > self._show_treble:
            self._show_treble += rise * (self._hit_treble - self._show_treble)
        else:
            self._show_treble = self._hit_treble
        stub = SUSTAIN_FLOOR * min(1.0, self._env_low / self._peak_low)
        self.h_bass = stub + (1.0 - stub) * self._show_bass
        stub = SUSTAIN_FLOOR * min(1.0, self._env_high / self._peak_high)
        self.h_treble = stub + (1.0 - stub) * self._show_treble

        # Rungs: struck when a hit throws its bar all the way, then ring down.
        rung_decay = math.exp(-dt * RUNG_RELEASE_HZ / trail)
        crisp = smooth < CREST_MAX_SMOOTHNESS
        hit = max(0.0, (self._show_bass - RUNG_ON) / (1.0 - RUNG_ON))
        self.rung_bass = max(hit, self.rung_bass * rung_decay)
        self._crest_bass = crisp and self._armed_bass and hit >= 0.5
        if self._crest_bass:
            self._armed_bass = False
        elif self.rung_bass < RUNG_REARM:
            self._armed_bass = True
        hit = max(0.0, (self._show_treble - RUNG_ON) / (1.0 - RUNG_ON))
        self.rung_treble = max(hit, self.rung_treble * rung_decay)
        self._crest_treble = crisp and self._armed_treble and hit >= 0.5
        if self._crest_treble:
            self._armed_treble = False
        elif self.rung_treble < RUNG_REARM:
            self._armed_treble = True

        # Canopy: each hi-hat onset lights a new random handful of cells.
        self._cooldown = max(0.0, self._cooldown - dt)
        np.multiply(self._cells, math.exp(-dt * SPARK_DECAY_HZ / trail), out=self._cells)
        self._crest.fill(0.0)
        if self.drop_hit:
            self._cells.fill(1.0)
            self._crest.fill(1.0)
            self._cooldown = ONSET_REFRACTORY_S
        elif s_air > SPARK_ONSET and self._cooldown <= 0.0:
            self._onsets += 1
            row = self._rand[self._onsets % SPARK_PATTERNS]
            np.less(row, self.sparkle_density * (0.5 + s_air), out=self._hit)
            np.copyto(self._crest, self._hit)
            np.maximum(self._cells, self._crest, out=self._cells)
            self._cooldown = ONSET_REFRACTORY_S

    # Rendering ----------------------------------------------------------------------------
    def render_part(self, part: str, fx: Fixture, out: np.ndarray) -> None:
        if part == STALAGMITES:
            self.draw_bar(fx, out, self._col_bass, self.h_bass)
        elif part == STALACTITES:
            self.draw_bar(fx, out, self._col_treble, self.h_treble, from_end=True)
        elif part == BASS_RUNGS:
            self.draw_solid(fx, out, self._col_bass, self.rung_bass, self._crest_bass)
        elif part == TREBLE_RUNGS:
            self.draw_solid(fx, out, self._col_treble, self.rung_treble, self._crest_treble)
        else:
            a, b = fx.start, fx.stop
            cells = self._cell_idx[a:b]
            np.take(self._cells, cells, out=self._gain[a:b], mode="clip")
            np.multiply(self._gain_2d[a:b], self._col_canopy, out=out[a:b])
            np.take(self._crest, cells, out=self._spark[a:b], mode="clip")     # Law 3 white crest
            np.multiply(self._spark_2d[a:b], 255.0, out=self._white[a:b])
            np.add(out[a:b], self._white[a:b], out=out[a:b])
