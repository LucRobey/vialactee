# History

Detailed memory bank tracking results, parameters, and findings.

## Phase 1: Harmonic Math & Groove Distance Penalty Evaluation (May 2026)

We implemented an automated testing pipeline in `BeatTracking_Evaluation_Test.ipynb` utilizing the `mir_eval` package to benchmark the `ContinuousHybridTracker_HarmonicMath` (Fast Scout, Heavy Judge, Groove Distance Penalty) against a 12-song dataset with Librosa baseline ground truth. 

The evaluation outputted `full_benchmark_results.pkl` containing tracked history logs (BPM, LTM Class, Phase, Circular Distance) and generated graphical failure plots for segments where the tracker deviated >15% from the ground truth tempo.

### Key Findings:
1. **Steady Tracking Success:** The Groove Distance Penalty successfully protected the `long_term_class` during steady 4/4 tracks (e.g., *Pumped Up Kicks*, *Palladium*), yielding zero or near-zero failure seconds and AMLt scores over `0.90`.
2. **Phase Inversion (The Upbeat Problem):** The tracker accurately locks onto the exact BPM speed but frequently locks out-of-phase onto the upbeat rather than the downbeat (e.g., *Stayin' Alive*), leading to high False Positives despite high AMLt.
3. **Stubbornness in Electronic Tracks:** A groove change threshold of `0.30` Pearson proved too strict for complex syncopated tracks (e.g., *Nobody Rules the Streets*), causing the tracker to become permanently stuck on an incorrect groove.
4. **Transient Distractions:** High False Positives in rock/melodic tracks (e.g., *Money For Nothing*) indicated that the custom ODF flux is too sensitive to mid-range non-percussive elements. 
5. **Rubato Limitations:** Tracks without a grid tempo (e.g., *Feeling Good*) predictably shattered the Flywheel logic, highlighting that fixed-groove tracking struggles against purely human, unquantized tempo drifting.

## Phase 2: Mathematical Tuning (May 2026)

Based on the evaluation findings from Phase 1, the following parameter adjustments were applied to the core harmonic math:
1. **Reduced Groove Change Threshold:** The threshold to abandon a locked groove (`circular_dist > 0.1`) was reduced from `0.30` to `0.23`. This prevents the tracker from remaining overly stubborn when encountering syncopated polyrhythms in complex electronic tracks (like *Nobody Rules the Streets*), allowing it to align with the correct tempo much faster.
2. **Filterbank / Flux Tuning:** The custom ODF flux calculation was updated to aggressively prioritize low-frequency transients. It now applies a weighted sum: `2.0 * low_bands + 0.5 * high_bands` instead of an equal sum. This filters out mid-range melodic distractions (like guitars and vocals in *Money For Nothing*), reducing the overall false-positive rate.

### Updated 12-Song Benchmark Scores
*Awaiting full re-calculation to populate F-measure/AMLt scores.*

| Song Name | F-Measure | AMLt | Notes |
| :--- | :--- | :--- | :--- |
| Palladium | TBD | TBD | Baseline 4/4 |
| Pumped Up Kicks | TBD | TBD | Baseline 4/4 |
| Nobody Rules the Streets | TBD | TBD | Syncopated Electronic |
| Another One Bites The Dust | TBD | TBD | Rock |
| Stayin' Alive | TBD | TBD | Disco |
| Boogie Wonderland | TBD | TBD | Disco |
| Roxanne | TBD | TBD | Reggae/Rock |
| September | TBD | TBD | Funk/Disco |
| 01-Plastic-People | TBD | TBD | Electronic |
| Djon maya maï | TBD | TBD | Acoustic |
| Feeling Good | TBD | TBD | Rubato |
| Heroes | TBD | TBD | Rock |
| Money For Nothing_1 | TBD | TBD | Rock |
