"""
The candidate NoBeatSlotAudioAnalyzer exactly as it was graded in this run (kept here because it was promoted
before it was ever committed; research/experiments/models/NoBeatSlotAudioAnalyzer.py is now an empty alias of
the production model, and the rule lives in music/BandKickSignals.py, `_no_beat`).

Original docstring:

research/experiments/models/NoBeatSlotAudioAnalyzer.py - Candidate of the music lab: the `no_beat` slot.

Run research/scoreboard/runs/2026-11-27_no_beat (work list line M01). Production model plus one slot:

    no_beat    there is no pulse to follow right now (free intro, break without drums, ending)

How:
- Raw answer for an instant: "no beat" when no kick drum surrounds it (more than NO_KICK_GAP_S between the kick
  before and the kick after) AND the tempo judge of the analyzer is unsure of the 5 s centred on it
  (`confidence_score` under UNSURE_BELOW). Kicks alone are not enough: some songs keep a pulse for long without
  a kick. The confidence alone is not enough either: on some songs it stays low while the kick is steady.
- The answer given is the majority of the raw answers from half a look-ahead before to half a look-ahead after,
  so that it does not flicker.
- Speaker time: the tempo judge speaks about the 5 s that have just arrived. Their middle is half a look-ahead
  (2.5 s) behind the newest audio, and half a look-ahead ahead of the speakers. So each tick gives the raw
  answer for the instant "now minus half a look-ahead", and the raw answers of the last look-ahead seconds are
  centred on what the speakers play now. Until the first audio reaches the speakers the slot stays None.

The kicks are the ones production already finds (music/BandKickSignals.py), read when they are found, before
they reach the speakers. This reads two private fields of that object (`_k_times`, `_k_count`); if the signal
is promoted, the rule belongs inside that module, next to `kick_present`.

Settings chosen on the ten open tracks by research/scoreboard/runs/2026-11-27_no_beat/tune_no_beat.py.

Real-time (AXIOM-02): two fixed-size arrays created in __init__, plain numbers per tick.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np

from music.BandKickSignals import KICK_QUEUE
from music.DyadicMetricalAudioAnalyzer import DyadicMetricalAudioAnalyzer

NO_KICK_GAP_S: float = 2.0      # no kick around: the kick before and the kick after are further apart than this
UNSURE_BELOW: float = 0.45      # the tempo judge is unsure under this confidence (0..1)


class NoBeatSlotAudioAnalyzer(DyadicMetricalAudioAnalyzer):
    """Production model plus the `no_beat` slot."""

    def __init__(self, ingestion: Any = None, infos: Optional[Dict[str, Any]] = None, config: Any = None) -> None:
        super().__init__(ingestion=ingestion, infos=infos, config=config)
        self._nb_half: float = 0.5 * self.lookahead_seconds
        self._nb_cap: int = max(16, int(self.lookahead_seconds * 60 * 1.5) + 2)
        self._nb_time: np.ndarray = np.zeros(self._nb_cap, dtype=np.float64)     # tick time of each raw answer
        self._nb_raw: np.ndarray = np.zeros(self._nb_cap, dtype=np.float64)      # 1.0 = "no beat"
        self._reset_no_beat()

    def _reset_no_beat(self) -> None:
        self._nb_time.fill(0.0)
        self._nb_raw.fill(0.0)
        self._nb_w = self._nb_r = self._nb_n = 0       # write index, read index, answers kept
        self._nb_votes = 0.0                           # how many of the kept answers say "no beat"
        self._nb_next = 0                              # index of the first kick after the instant being decided
        self._nb_start = -1.0                          # time of the first tick, -1 before it

    def reset(self) -> None:
        super().reset()
        if hasattr(self, "_nb_raw"):
            self._reset_no_beat()

    def detect_band_peaks(self, current_time: float, dt: float, fps_ratio: float) -> None:
        super().detect_band_peaks(current_time, dt, fps_ratio)      # everything production does, unchanged
        now = current_time
        if self._nb_start < 0.0:
            self._nb_start = now
        instant = now - self._nb_half                               # the middle of the 5 s the judge has just heard

        # raw answer for that instant
        if instant < self._nb_start:
            raw = 1.0                                               # before the music started there is no beat
        else:
            kicks = self._band_kick
            count = kicks._k_count
            if self._nb_next > count:                               # the kick queue was reset
                self._nb_next = 0
            while self._nb_next < count and kicks._k_times[self._nb_next % KICK_QUEUE] <= instant:
                self._nb_next += 1
            gap = self._nb_half                                     # no kick known after: at least this far away
            if self._nb_next < count:
                gap = kicks._k_times[self._nb_next % KICK_QUEUE] - instant
            if self._nb_next > 0:
                gap += instant - kicks._k_times[(self._nb_next - 1) % KICK_QUEUE]
            else:
                gap = 1e9                                           # no kick yet
            raw = 1.0 if (gap > NO_KICK_GAP_S and self.confidence_score < UNSURE_BELOW) else 0.0

        # keep the raw answers of the last look-ahead seconds
        w = self._nb_w
        if self._nb_n == self._nb_cap:                              # full (only if ticks come faster than planned)
            self._nb_votes -= self._nb_raw[self._nb_r]
            self._nb_r = (self._nb_r + 1) % self._nb_cap
            self._nb_n -= 1
        self._nb_time[w] = now
        self._nb_raw[w] = raw
        self._nb_votes += raw
        self._nb_w = (w + 1) % self._nb_cap
        self._nb_n += 1
        while self._nb_n > 1 and now - self._nb_time[self._nb_r] > self.lookahead_seconds:
            self._nb_votes -= self._nb_raw[self._nb_r]
            self._nb_r = (self._nb_r + 1) % self._nb_cap
            self._nb_n -= 1

        # at speaker time: the majority of the answers centred on what the speakers play now
        if now - self._nb_start >= self.lookahead_seconds:
            self.signals.no_beat = bool(2.0 * self._nb_votes > self._nb_n)
