"""
research/experiments/models/BandKickSlotsAudioAnalyzer.py - Pilot candidate of the music lab (2026-11-27).

PROMOTED on 2026-11-27 with the owner's approval. Its five signals (band_bass, band_mid, band_high, kick,
kick_present) now live in music/BandKickSignals.py and are written by the production
DyadicMetricalAudioAnalyzer. This class is therefore the production model under its old name: it is kept so
that the pilot's records (research/scoreboard/runs/2026-11-27_bands_kick/, LEADERBOARD.md, the choreography
lab's candidate feed) can still be replayed by name. Do not add code here; a new idea is a new candidate.

The code as it was graded in the pilot is in git, as committed in b516564.
"""
from __future__ import annotations

from music.DyadicMetricalAudioAnalyzer import DyadicMetricalAudioAnalyzer


class BandKickSlotsAudioAnalyzer(DyadicMetricalAudioAnalyzer):
    """The production model: the pilot's five slots were promoted into it (music/BandKickSignals.py)."""
