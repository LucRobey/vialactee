"""
research/experiments/models/MultiBandSixSignalsAudioAnalyzer.py - Candidate of the music lab (2026-11-27).

Run research/scoreboard/runs/2026-11-27_best_beat (work list line M08, asked by the owner: "prepare our best
analyser by adding all the new variables to it").

The analyzer that scores best on beat and tempo is MultiBandOnsetAudioAnalyzer, the model the production
DyadicMetricalAudioAnalyzer was built on. Production adds to it a "sub-pulse" that inserts half-beats and doubles
the tempo; against the corrected truth that costs points. But the six signals promoted on 2026-11-27 (band_bass,
band_mid, band_high, kick, kick_present, no_beat) were wired into the production model only.

This candidate is MultiBandOnsetAudioAnalyzer plus those six signals, through the same production helper
(music/BandKickSignals.py) fed the same way. No new rule, no setting to tune: the question is only whether the
six signals keep their scores on this model.

Real-time (AXIOM-02): the helper creates its arrays once; nothing is created per tick here.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from music.BandKickSignals import BandKickSignals
from music.MultiBandOnsetAudioAnalyzer import MultiBandOnsetAudioAnalyzer


class MultiBandSixSignalsAudioAnalyzer(MultiBandOnsetAudioAnalyzer):
    """MultiBandOnsetAudioAnalyzer (best beat and tempo) plus the six truth-mirrored slots of production."""

    def __init__(self, ingestion: Any = None, infos: Optional[Dict[str, Any]] = None, config: Any = None) -> None:
        super().__init__(ingestion=ingestion, infos=infos, config=config)
        self._band_kick: BandKickSignals = BandKickSignals(self.nb_bands, self.lookahead_seconds)

    def reset(self) -> None:
        super().reset()
        if hasattr(self, "_band_kick"):
            self._band_kick.reset()

    def detect_band_peaks(self, current_time: float, dt: float, fps_ratio: float) -> None:
        super().detect_band_peaks(current_time, dt, fps_ratio)      # beats and tempo of the parent, unchanged
        bands = getattr(self.ingestion, "multiband_fft_values", None)
        if bands is None or len(bands) == 0:
            bands = self.ingestion.fft_band_values
        self._band_kick.update(current_time, dt, bands, float(self.kick_odf_buffer[-1]), float(self.dE[0]), self.signals,
                               float(self.confidence_score))
