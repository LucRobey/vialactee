"""
research/experiments/models/DyadicMetricalAudioAnalyzer.py - Cycle 012 (PROMOTED TO PRODUCTION).

The Dyadic Metrical Sub-Pulse Arbiter was promoted to `music/DyadicMetricalAudioAnalyzer.py`
and is now the default production analyzer. This module is kept only as an alias so that
historical commands (`--model DyadicMetricalAudioAnalyzer`) and the experiment ledger keep
resolving to the single, canonical implementation.

The original standalone research implementation (subclass of the research fork of
MultiBandOnsetAudioAnalyzer) is preserved in git history (`git show c37e9e2:research/experiments/models/DyadicMetricalAudioAnalyzer.py`)
and its results are recorded in research/experiments/RESEARCH_HISTORY.md (Cycle 012).
"""

from music.DyadicMetricalAudioAnalyzer import DyadicMetricalAudioAnalyzer  # noqa: F401

__all__ = ["DyadicMetricalAudioAnalyzer"]
