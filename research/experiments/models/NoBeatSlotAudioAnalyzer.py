"""
research/experiments/models/NoBeatSlotAudioAnalyzer.py - Candidate of the music lab: the `no_beat` slot.

PROMOTED on 2026-11-27 with the owner's approval (run research/scoreboard/runs/2026-11-27_no_beat, work list
line M01). Its rule now lives in music/BandKickSignals.py (`_no_beat`), next to `kick_present`, and is written
by the production DyadicMetricalAudioAnalyzer. This class is therefore the production model under its old name:
it is kept so that the run's records and tests can still be replayed by name. Do not add code here; a new idea
is a new candidate.

The code as it was graded is kept in research/scoreboard/runs/2026-11-27_no_beat/candidate_as_graded.py.
"""
from __future__ import annotations

from music.DyadicMetricalAudioAnalyzer import DyadicMetricalAudioAnalyzer


class NoBeatSlotAudioAnalyzer(DyadicMetricalAudioAnalyzer):
    """The production model: the `no_beat` slot was promoted into it (music/BandKickSignals.py)."""
