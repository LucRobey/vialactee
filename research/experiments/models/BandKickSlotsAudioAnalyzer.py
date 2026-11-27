"""
research/experiments/models/BandKickSlotsAudioAnalyzer.py - Pilot candidate of the music lab (2026-11-27).

Goal: fill five empty slots of the truth-mirrored signal record (config/music_signals.json) without touching
anything the production model already does:

    band_bass, band_mid, band_high   level of three frequency ranges, 0..1
    kick                             strength of a kick drum hit on this frame, 0.0 when there is none
    kick_present                     the kick keeps coming (a kick in the last 2 s and another in the next 2 s)

It subclasses the production DyadicMetricalAudioAnalyzer and only adds: beats, tempo and every other existing
signal are computed by the parent, unchanged.

How:
- Levels: the 32-band spectrum of the audio front end is summed in three ranges (under 250 Hz, 250 Hz to
  4 kHz, above 4 kHz), turned to dB and placed between a slowly falling ceiling and LEVEL_RANGE_DB under it.
- Kick: the parent already builds a kick stream (rise of the three lowest bands). A kick is a local peak of
  that stream that stands above its recent average, reaches a share of its recent loud peaks, and comes in
  good part from the lowest band.
- Speaker time: all of this is measured when the audio arrives, look-ahead seconds before the speakers play
  it. Each value goes through a delay line and is written to its slot when the speakers reach it. Because the
  kicks of the next seconds are already known, kick_present can look both ways.

Real-time: fixed-size arrays created in __init__, scalar maths per tick, no array created in the update.
"""
from __future__ import annotations

import math
from typing import Any, Dict, Optional

import numpy as np

from music.DyadicMetricalAudioAnalyzer import DyadicMetricalAudioAnalyzer
from music.RhythmConfig import RhythmConfig

BASS_TOP_HZ: float = 250.0
MID_TOP_HZ: float = 4000.0
LEVEL_RANGE_DB: float = 50.0        # a level of 0 is this far under the recent ceiling
CEILING_FALL_DB_S: float = 0.5      # the ceiling falls back at this speed when the music gets quieter
# Settings chosen on the ten open tracks (odd ids) by runs/2026-11-27_bands_kick/tune_kick.py: F1 64 -> 77 there.
KICK_OVER_AVERAGE: float = 4.0      # a kick peak stands this many times above the recent average of the stream
KICK_SHARE_OF_PEAK: float = 0.5     # ...reaches this share of the recent loud peaks
KICK_LOW_SHARE: float = 0.25        # ...and at least this share of it comes from the lowest band (weighted)
KICK_LOW_WEIGHT: float = 2.0        # weight of the lowest band in the parent's kick stream
KICK_AVERAGE_S: float = 1.0
KICK_PEAK_FALL_S: float = 4.0       # the "recent loud peak" halves in this many seconds without a louder one
KICK_REFRACTORY_S: float = 0.09     # two kicks are at least this far apart
KICK_GAP_S: float = 2.0             # kick_present: a kick within this long before and after
N_VALUES: int = 4                   # delay line columns: bass, mid, high, kick strength


def _band_centres_hz(n_bands: int) -> np.ndarray:
    """Centre of each Mel band of AudioIngestion (20 Hz to 20 kHz)."""
    lo, hi = 2595.0 * math.log10(1.0 + 20.0 / 700.0), 2595.0 * math.log10(1.0 + 20000.0 / 700.0)
    mel = np.linspace(lo, hi, n_bands + 2)
    return (700.0 * (10.0 ** (mel / 2595.0) - 1.0))[1:-1]


class BandKickSlotsAudioAnalyzer(DyadicMetricalAudioAnalyzer):
    """Production model plus five truth-mirrored slots: band_bass, band_mid, band_high, kick, kick_present."""

    def __init__(self, ingestion: Any = None, infos: Optional[Dict[str, Any]] = None, config: Optional[RhythmConfig] = None) -> None:
        super().__init__(ingestion=ingestion, infos=infos, config=config)
        centres = _band_centres_hz(self.nb_bands)
        self._n_bass = int(np.sum(centres < BASS_TOP_HZ))                  # bands [0, n_bass) are the bass range
        self._n_mid = int(np.sum(centres < MID_TOP_HZ))                    # bands [n_bass, n_mid) are the middle range
        self._ceiling = [-120.0, -120.0, -120.0]

        cap = max(16, int(self.lookahead_seconds * 60 * 1.5) + 2)
        self._cap = cap
        self._ring_t = np.zeros(cap, dtype=np.float64)
        self._ring_v = np.zeros((cap, N_VALUES), dtype=np.float64)
        self._ring_w = self._ring_r = self._ring_n = 0

        self._k_prev = self._k_prev2 = 0.0        # kick stream one and two ticks ago
        self._low_prev = 0.0                       # rise of the lowest band one tick ago
        self._k_avg = self._k_peak = 0.0
        self._k_last_time = -1e9
        self._k_cap = 512                          # kick times waiting to reach the speakers
        self._k_times = np.zeros(self._k_cap, dtype=np.float64)
        self._k_count = 0                          # kicks found so far
        self._k_next = 0                           # index of the first kick the speakers have not reached yet

    def reset(self) -> None:
        super().reset()
        if not hasattr(self, "_ring_t"):
            return
        self._ring_t.fill(0.0)
        self._ring_v.fill(0.0)
        self._k_times.fill(0.0)
        self._ring_w = self._ring_r = self._ring_n = self._k_count = self._k_next = 0
        self._k_prev = self._k_prev2 = self._k_avg = self._k_peak = self._low_prev = 0.0
        self._k_last_time = -1e9
        self._ceiling = [-120.0, -120.0, -120.0]

    def detect_band_peaks(self, current_time: float, dt: float, fps_ratio: float) -> None:
        super().detect_band_peaks(current_time, dt, fps_ratio)
        self._measure(current_time, max(1e-4, dt))
        self._write_slots(current_time)

    def _level(self, i: int, lo: int, hi: int, dt: float) -> float:
        """Level of one range of bands, 0..1, against a ceiling that follows the loud passages."""
        power = 0.0
        # same fallback as the parent: the old benchmark's mock front end has only the coarse bands
        vals = getattr(self.ingestion, "multiband_fft_values", None)
        if vals is None or len(vals) == 0:
            vals = self.ingestion.fft_band_values
        for b in range(lo, min(hi, len(vals))):
            power += float(vals[b])
        db = 20.0 * math.log10(power + 1.0)
        ceiling = max(db, self._ceiling[i] - CEILING_FALL_DB_S * dt)
        self._ceiling[i] = ceiling
        return max(0.0, min(1.0, 1.0 + (db - ceiling) / LEVEL_RANGE_DB))

    def _measure(self, now: float, dt: float) -> None:
        """Measure at arrival time and push into the delay line."""
        w = self._ring_w
        self._ring_t[w] = now
        row = self._ring_v[w]
        row[0] = self._level(0, 0, self._n_bass, dt)
        row[1] = self._level(1, self._n_bass, self._n_mid, dt)
        row[2] = self._level(2, self._n_mid, self.nb_bands, dt)
        row[3] = 0.0

        # kick: was the previous tick a peak of the kick stream? (one tick late, absorbed by the look-ahead)
        y = float(self.kick_odf_buffer[-1])
        prev, prev2 = self._k_prev, self._k_prev2
        self._k_avg += min(1.0, dt / KICK_AVERAGE_S) * (y - self._k_avg)
        self._k_peak = max(y, self._k_peak * 0.5 ** (dt / KICK_PEAK_FALL_S))
        t_prev = now - dt
        if (prev > prev2 and prev >= y and prev > KICK_OVER_AVERAGE * self._k_avg
                and prev > KICK_SHARE_OF_PEAK * self._k_peak and t_prev - self._k_last_time >= KICK_REFRACTORY_S
                and KICK_LOW_WEIGHT * self._low_prev >= KICK_LOW_SHARE * prev and self._ring_n > 0):
            self._ring_v[(w - 1) % self._cap, 3] = min(1.0, prev / max(1e-9, self._k_peak))
            self._k_times[self._k_count % self._k_cap] = t_prev
            self._k_count += 1
            self._k_last_time = t_prev
        self._k_prev2, self._k_prev = prev, y
        self._low_prev = float(self.dE[0])

        self._ring_w = (w + 1) % self._cap
        if self._ring_n < self._cap:
            self._ring_n += 1
        else:
            self._ring_r = (self._ring_r + 1) % self._cap

    def _write_slots(self, now: float) -> None:
        """Write to the slots what the speakers are playing now: the entries that are look-ahead seconds old."""
        sig = getattr(self, "signals", None)
        if sig is None:
            return
        kick, last = 0.0, -1
        # keep one entry in the line: the newest one may still receive the kick found on the next tick
        while self._ring_n > 1 and now - self._ring_t[self._ring_r] >= self.lookahead_seconds:
            last = self._ring_r
            kick = max(kick, float(self._ring_v[last, 3]))
            self._ring_r = (last + 1) % self._cap
            self._ring_n -= 1
        if last >= 0:
            row = self._ring_v[last]
            sig.band_bass, sig.band_mid, sig.band_high = float(row[0]), float(row[1]), float(row[2])
            sig.kick = kick
        elif sig.band_bass is not None:
            sig.kick = 0.0                         # nothing new reached the speakers on this tick

        # kick_present: the latest kick the speakers have played, and the next one they will play
        speaker_now = now - self.lookahead_seconds
        while self._k_next < self._k_count and self._k_times[self._k_next % self._k_cap] <= speaker_now:
            self._k_next += 1
        if last >= 0 or sig.kick_present is not None:
            before = self._k_next > 0 and self._k_count - self._k_next < self._k_cap and \
                speaker_now - self._k_times[(self._k_next - 1) % self._k_cap] <= KICK_GAP_S
            after = self._k_next < self._k_count and self._k_times[self._k_next % self._k_cap] - speaker_now <= KICK_GAP_S
            sig.kick_present = bool(before and after)
