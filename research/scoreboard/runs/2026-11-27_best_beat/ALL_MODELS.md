# Every analyzer we have, on the real path (2026-11-27)

Each model of `music/` and `research/experiments/models/` played the 20 truth tracks inside the production
`Listener` with the 5 s look-ahead, and was graded by the scoreboard on truth that may grade. This had never
been done: the older research ranked these models on a bench that did not match the installation.

| Analyzer | Beat | Tempo | Time at double tempo | Time per step on this PC |
|---|---|---|---|---|
| TimbreAdaptiveAudioAnalyzer | 81.5 | 73.6 | 19% | 0.46 ms |
| AudioAnalyzer (the oldest one) | 81.4 | 73.4 | 19% | 0.40 ms |
| **MultiBandOnsetAudioAnalyzer** (base of the candidate of this run) | 80.7 | **74.6** | 18% | 0.31 ms |
| CostasLoopAudioAnalyzer | 79.0 | 74.4 | 18% | 0.28 ms |
| PhaseInertiaAudioAnalyzer | 78.7 | 73.6 | 19% | 0.48 ms |
| **DyadicMetricalAudioAnalyzer (on the installation)** | 78.2 | 66.9 | 26% | 0.33 ms |
| DyadicWaveletAudioAnalyzer | 78.2 | 66.8 | 26% | 0.62 ms |
| DualResonatorAudioAnalyzer | 64.6 | 68.6 | 17% | 0.54 ms |
| SparseImpulseAudioAnalyzer | crashed | | | |
| DualFlywheelAudioAnalyzer | crashed | | | |

What it says:

- **No single best.** Five analyzers are within three points on beat and one point on tempo. Differences of a
  point are not meaningful: the noise of this measure has not been measured.
- **The installation's analyzer is sixth of eight on beat and seventh on tempo.** Its "sub-pulse" (half-beats)
  is the difference with the group above; the other model that has it (DyadicWavelet) scores the same.
- **The oldest analyzer is second.** On the real path, the research cycles that followed it did not improve the
  beat. They were judged on another bench, with some wrong references.
- **Why MultiBandOnset as the base of the candidate:** best on tempo, within a point of the best on beat, among
  the cheapest, and the six new signals are built on its kick stream and its 32 bands, which the oldest
  analyzer and TimbreAdaptive may not offer in the same form (not checked).
- The two crashes are the same error (8 bands where the real audio front end gives 16): those models were only
  ever run on the old bench's simplified front end.

Not verified: any of this by eye or on the Raspberry Pi. The times per step were measured while other work was
running on the PC.
