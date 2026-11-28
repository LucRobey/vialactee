"""
research/experiments/models/MultiBandSixSignalsAudioAnalyzer.py - Candidate of the music lab (2026-11-27).

PROMOTED on 2026-11-27 on the owner's decision (run research/scoreboard/runs/2026-11-27_best_beat): the six
signals were added to music/MultiBandOnsetAudioAnalyzer.py itself, and that model became the main analyzer of
the installation. This class is therefore the main analyzer under its old name, kept so that the run's records
and tests can still be replayed by name. Do not add code here; a new idea is a new candidate.

The code as it was graded is kept in research/scoreboard/runs/2026-11-27_best_beat/candidate_as_graded.py.
"""
from __future__ import annotations

from music.MultiBandOnsetAudioAnalyzer import MultiBandOnsetAudioAnalyzer


class MultiBandSixSignalsAudioAnalyzer(MultiBandOnsetAudioAnalyzer):
    """The main analyzer: the six slots were added to MultiBandOnsetAudioAnalyzer itself."""
