"""
music/BandKickSignals.py - Six truth-mirrored signals: band_bass, band_mid, band_high, kick, kick_present, no_beat.

Promoted from the music lab on 2026-11-27 with the owner's approval (pilot cycle,
research/scoreboard/runs/2026-11-27_bands_kick/PROPOSAL.md). Used by MultiBandOnsetAudioAnalyzer (the main
analyzer since 2026-11-27) and by every model built on it, which call `update_from()` once per tick after their own
work; nothing the analyzer already computes is changed.

    band_bass, band_mid, band_high   level of three frequency ranges, 0..1
    kick                             strength of a kick drum hit on this tick, 0.0 when there is none
    kick_present                     the kick keeps coming (a kick in the last 2 s and another in the next 2 s)
    no_beat                          there is no pulse to follow right now (free intro, break without drums, ending).
                                     Promoted on 2026-11-27 (research/scoreboard/runs/2026-11-27_no_beat/PROPOSAL.md)

These are the slots listed in MusicSignals.PRODUCED.

How:
- Levels: the spectrum bands of the audio front end are summed in three ranges (under 250 Hz, 250 Hz to
  4 kHz, above 4 kHz), turned to dB and placed between a slowly falling ceiling and LEVEL_RANGE_DB under it.
- Kick: the analyzer already builds a kick stream (rise of the three lowest bands). A kick is a local peak of
  that stream that stands above its recent average, reaches a share of its recent loud peaks, and comes in
  good part from the lowest band.
- Speaker time: all of this is measured when the audio arrives, look-ahead seconds before the speakers play
  it. Each value goes through a delay line and is written to its slot when the speakers reach it. Because the
  kicks of the next seconds are already known, kick_present can look both ways. Until the first audio reaches
  the speakers the slots stay None.
- No beat: for an instant, the raw answer is "no beat" when no kick surrounds it (more than NO_BEAT_KICK_GAP_S
  between the kick before and the kick after) AND the analyzer's tempo judge is unsure of the look-ahead seconds
  centred on it (confidence under NO_BEAT_UNSURE_BELOW). The judge speaks about the audio that has just arrived,
  whose middle is half a look-ahead ahead of the speakers; so the raw answers of the last look-ahead seconds
  are centred on what the speakers play now, and the slot is their majority.

Real-time (AXIOM-02): fixed-size arrays created in __init__, scalar maths per tick, no array created in update().
"""
from __future__ import annotations

import math
from typing import Any, Sequence

import numpy as np

BASS_TOP_HZ: float = 250.0
MID_TOP_HZ: float = 4000.0
LEVEL_RANGE_DB: float = 50.0        # a level of 0 is this far under the recent ceiling
CEILING_FALL_DB_S: float = 0.5      # the ceiling falls back at this speed when the music gets quieter
# Settings chosen on the ten open tracks (odd ids) by research/scoreboard/runs/2026-11-27_bands_kick/tune_kick.py.
KICK_OVER_AVERAGE: float = 4.0      # a kick peak stands this many times above the recent average of the stream
KICK_SHARE_OF_PEAK: float = 0.5     # ...reaches this share of the recent loud peaks
KICK_LOW_SHARE: float = 0.25        # ...and at least this share of it comes from the lowest band (weighted)
KICK_LOW_WEIGHT: float = 2.0        # weight of the lowest band in the analyzer's kick stream
KICK_AVERAGE_S: float = 1.0
KICK_PEAK_FALL_S: float = 4.0       # the "recent loud peak" halves in this many seconds without a louder one
KICK_REFRACTORY_S: float = 0.09     # two kicks are at least this far apart
KICK_GAP_S: float = 2.0             # kick_present: a kick within this long before and after
N_VALUES: int = 4                   # delay line columns: bass, mid, high, kick strength
KICK_QUEUE: int = 512               # kick times waiting to reach the speakers
# Settings chosen on the ten open tracks by research/scoreboard/runs/2026-11-27_no_beat/tune_no_beat.py.
NO_BEAT_KICK_GAP_S: float = 2.0     # no kick around: the kick before and the kick after are further apart than this
NO_BEAT_UNSURE_BELOW: float = 0.45  # the tempo judge is unsure under this confidence (0..1)


def band_centres_hz(n_bands: int) -> np.ndarray:
    """Centre of each Mel band of AudioIngestion (20 Hz to 20 kHz)."""
    lo, hi = 2595.0 * math.log10(1.0 + 20.0 / 700.0), 2595.0 * math.log10(1.0 + 20000.0 / 700.0)
    mel = np.linspace(lo, hi, n_bands + 2)
    return (700.0 * (10.0 ** (mel / 2595.0) - 1.0))[1:-1]


class BandKickSignals:
    """Measures three band levels and the kick at arrival time; writes them to the record at speaker time."""

    def __init__(self, nb_bands: int, lookahead_seconds: float) -> None:
        self.nb_bands: int = int(nb_bands)
        self.lookahead_seconds: float = float(lookahead_seconds)
        centres = band_centres_hz(self.nb_bands)
        self._n_bass: int = int(np.sum(centres < BASS_TOP_HZ))             # bands [0, n_bass) are the bass range
        self._n_mid: int = int(np.sum(centres < MID_TOP_HZ))               # bands [n_bass, n_mid) are the middle range
        self._ceiling = [-120.0, -120.0, -120.0]

        self._cap: int = max(16, int(self.lookahead_seconds * 60 * 1.5) + 2)
        self._ring_t: np.ndarray = np.zeros(self._cap, dtype=np.float64)
        self._ring_v: np.ndarray = np.zeros((self._cap, N_VALUES), dtype=np.float64)
        self._k_times: np.ndarray = np.zeros(KICK_QUEUE, dtype=np.float64)
        self._nb_half: float = 0.5 * self.lookahead_seconds
        self._nb_time: np.ndarray = np.zeros(self._cap, dtype=np.float64)        # tick time of each raw no-beat answer
        self._nb_raw: np.ndarray = np.zeros(self._cap, dtype=np.float64)         # 1.0 = "no beat"
        self.reset()

    def reset(self) -> None:
        self._ring_t.fill(0.0)
        self._ring_v.fill(0.0)
        self._k_times.fill(0.0)
        self._ring_w = self._ring_r = self._ring_n = 0
        self._k_count = 0                          # kicks found so far
        self._k_next = 0                           # index of the first kick the speakers have not reached yet
        self._k_prev = self._k_prev2 = 0.0         # kick stream one and two ticks ago
        self._low_prev = 0.0                       # rise of the lowest band one tick ago
        self._k_avg = self._k_peak = 0.0
        self._k_last_time = -1e9
        self._ceiling[0] = self._ceiling[1] = self._ceiling[2] = -120.0
        self._nb_time.fill(0.0)
        self._nb_raw.fill(0.0)
        self._nb_w = self._nb_r = self._nb_n = 0   # write index, read index, answers kept
        self._nb_votes = 0.0                       # how many of the kept answers say "no beat"
        self._nb_next = 0                          # index of the first kick after the instant being decided
        self._nb_start = -1.0                      # time of the first tick, -1 before it

    def update(self, now: float, dt: float, bands: Sequence[float], kick_stream: float, low_rise: float, signals: Any,
               confidence: float = 1.0) -> None:
        """One tick. `bands`: spectrum of the front end; `kick_stream`, `low_rise`, `confidence` (of the tempo judge,
        0..1): the analyzer's values for this tick."""
        self._measure(now, max(1e-4, dt), bands, kick_stream, low_rise)
        if signals is not None:
            self._write_slots(now, signals)
        self._no_beat(now, confidence, signals)

    def update_from(self, analyzer: Any, now: float, dt: float) -> None:
        """One tick, reading the values from a MultiBandOnsetAudioAnalyzer (or a model built on it)."""
        bands = getattr(analyzer.ingestion, 'multiband_fft_values', None)
        if bands is None or len(bands) == 0:
            bands = analyzer.ingestion.fft_band_values
        self.update(now, dt, bands, float(analyzer.kick_odf_buffer[-1]), float(analyzer.dE[0]), analyzer.signals,
                    float(analyzer.confidence_score))

    def _no_beat(self, now: float, confidence: float, sig: Any) -> None:
        """Raw answer for the instant half a look-ahead ago; the slot is the majority over the last look-ahead seconds."""
        if self._nb_start < 0.0:
            self._nb_start = now
        instant = now - self._nb_half                               # the middle of the audio the judge has just heard
        if instant < self._nb_start:
            raw = 1.0                                               # before the music started there is no beat
        else:
            count = self._k_count
            while self._nb_next < count and self._k_times[self._nb_next % KICK_QUEUE] <= instant:
                self._nb_next += 1
            gap = self._nb_half                                     # no kick known after: at least this far away
            if self._nb_next < count:
                gap = self._k_times[self._nb_next % KICK_QUEUE] - instant
            if self._nb_next > 0:
                gap += instant - self._k_times[(self._nb_next - 1) % KICK_QUEUE]
            else:
                gap = 1e9                                           # no kick yet
            raw = 1.0 if (gap > NO_BEAT_KICK_GAP_S and confidence < NO_BEAT_UNSURE_BELOW) else 0.0

        w = self._nb_w
        if self._nb_n == self._cap:                                 # full (only if ticks come faster than planned)
            self._nb_votes -= self._nb_raw[self._nb_r]
            self._nb_r = (self._nb_r + 1) % self._cap
            self._nb_n -= 1
        self._nb_time[w] = now
        self._nb_raw[w] = raw
        self._nb_votes += raw
        self._nb_w = (w + 1) % self._cap
        self._nb_n += 1
        while self._nb_n > 1 and now - self._nb_time[self._nb_r] > self.lookahead_seconds:
            self._nb_votes -= self._nb_raw[self._nb_r]
            self._nb_r = (self._nb_r + 1) % self._cap
            self._nb_n -= 1
        if sig is not None and now - self._nb_start >= self.lookahead_seconds:
            sig.no_beat = bool(2.0 * self._nb_votes > self._nb_n)

    def _level(self, i: int, lo: int, hi: int, dt: float, bands: Sequence[float]) -> float:
        """Level of one range of bands, 0..1, against a ceiling that follows the loud passages."""
        power = 0.0
        for b in range(lo, min(hi, len(bands))):
            power += float(bands[b])
        db = 20.0 * math.log10(power + 1.0)
        ceiling = max(db, self._ceiling[i] - CEILING_FALL_DB_S * dt)
        self._ceiling[i] = ceiling
        return max(0.0, min(1.0, 1.0 + (db - ceiling) / LEVEL_RANGE_DB))

    def _measure(self, now: float, dt: float, bands: Sequence[float], y: float, low_rise: float) -> None:
        """Measure at arrival time and push into the delay line."""
        w, v = self._ring_w, self._ring_v
        self._ring_t[w] = now
        v[w, 0] = self._level(0, 0, self._n_bass, dt, bands)
        v[w, 1] = self._level(1, self._n_bass, self._n_mid, dt, bands)
        v[w, 2] = self._level(2, self._n_mid, self.nb_bands, dt, bands)
        v[w, 3] = 0.0

        # kick: was the previous tick a peak of the kick stream? (one tick late, absorbed by the look-ahead)
        prev, prev2 = self._k_prev, self._k_prev2
        self._k_avg += min(1.0, dt / KICK_AVERAGE_S) * (y - self._k_avg)
        self._k_peak = max(y, self._k_peak * 0.5 ** (dt / KICK_PEAK_FALL_S))
        t_prev = now - dt
        if (prev > prev2 and prev >= y and prev > KICK_OVER_AVERAGE * self._k_avg
                and prev > KICK_SHARE_OF_PEAK * self._k_peak and t_prev - self._k_last_time >= KICK_REFRACTORY_S
                and KICK_LOW_WEIGHT * self._low_prev >= KICK_LOW_SHARE * prev and self._ring_n > 0):
            v[(w - 1) % self._cap, 3] = min(1.0, prev / max(1e-9, self._k_peak))
            self._k_times[self._k_count % KICK_QUEUE] = t_prev
            self._k_count += 1
            self._k_last_time = t_prev
        self._k_prev2, self._k_prev = prev, y
        self._low_prev = low_rise

        self._ring_w = (w + 1) % self._cap
        if self._ring_n < self._cap:
            self._ring_n += 1
        else:
            self._ring_r = (self._ring_r + 1) % self._cap

    def _write_slots(self, now: float, sig: Any) -> None:
        """Write to the slots what the speakers are playing now: the entries that are look-ahead seconds old."""
        kick, last, v = 0.0, -1, self._ring_v
        # keep one entry in the line: the newest one may still receive the kick found on the next tick
        while self._ring_n > 1 and now - self._ring_t[self._ring_r] >= self.lookahead_seconds:
            last = self._ring_r
            kick = max(kick, float(v[last, 3]))
            self._ring_r = (last + 1) % self._cap
            self._ring_n -= 1
        if last >= 0:
            sig.band_bass, sig.band_mid, sig.band_high = float(v[last, 0]), float(v[last, 1]), float(v[last, 2])
            sig.kick = kick
        elif sig.band_bass is not None:
            sig.kick = 0.0                         # nothing new reached the speakers on this tick

        # kick_present: the latest kick the speakers have played, and the next one they will play
        speaker_now = now - self.lookahead_seconds
        while self._k_next < self._k_count and self._k_times[self._k_next % KICK_QUEUE] <= speaker_now:
            self._k_next += 1
        if last >= 0 or sig.kick_present is not None:
            before = self._k_next > 0 and self._k_count - self._k_next < KICK_QUEUE and \
                speaker_now - self._k_times[(self._k_next - 1) % KICK_QUEUE] <= KICK_GAP_S
            after = self._k_next < self._k_count and self._k_times[self._k_next % KICK_QUEUE] - speaker_now <= KICK_GAP_S
            sig.kick_present = bool(before and after)
