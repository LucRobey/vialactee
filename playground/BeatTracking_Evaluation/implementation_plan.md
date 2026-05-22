# Beat Tracking Evaluation Tuning & Objectives

This document outlines the changes to resolve the issues identified in the evaluation phase, formally updates our objective lists, and presents architectural approaches for solving the phase inversion problem.

## User Review Required

Please review the proposed brainstorming ideas for **Requirement 3 (Downbeat Weighting)**. Let me know which approach you prefer or if you'd like to prototype one immediately.

## Proposed Changes

### 1. Mathematical Tuning

#### [MODIFY] `BeatTracking_Evaluation_Test.ipynb`
* **Reduce Groove Change Threshold:** Inside `run_simulation_with_beats`, the stubbornness of the Flywheel will be reduced. The threshold to abandon a locked groove (`circular_dist > 0.1`) will be lowered from `0.30` to `0.23`. This allows the tracker to switch to the correct tempo on complex electronic tracks like *Nobody Rules the Streets* when presented with a strong but not overwhelming transient.
* **Filterbank / Flux Tuning:** Inside `simulate_audio_ingestion`, the `custom_flux` calculation will be updated to prioritize the Kick drum. Currently, it sums `flux_bands[0:2]` and `flux_bands[-2:]` equally. I will adjust this to weight the low-end heavily (`2.0 * low + 0.5 * high`) to reject mid-range guitar/synth transients like those in *Money For Nothing*.

### 2. Documentation Updates

#### [MODIFY] `history.md`
* Log the full F-measure/AMLt scores for the 12-song benchmark.
* Log the initial tracker behavior (Phase alignment successes, Tempo rubato dropouts, Polyrhythmic Stubbornness, and Phase Inversion issues).
* Log the parameter updates (`Groove Threshold -> 0.23`).

#### [MODIFY] `current_objectives.md`
* Mark the evaluation setup tasks as `[x]` Complete.
* Add new tasks for Phase 3 (Downbeat Phase Inversion logic).
* Add new tasks for porting the validated core math to the Raspberry Pi environment.

---

## Brainstorming Requirement 3: Downbeat Weighting

To solve the issue where the tracker perfectly matches the BPM but aligns its phase exactly on the upbeat (like in *Stayin' Alive*), we need the tracker to inherently understand the difference between a Kick and a Hi-Hat.

Here are three potential approaches:

**Approach A: Dual-Buffer Pearson Correlation (Heavy but Precise)**
Instead of feeding one combined `custom_odf_buffer` into the `FastTemplateBank`, we maintain two separate ODF buffers: a `kick_odf_buffer` (Band 0-1) and an `air_odf_buffer` (Band 30-31). When evaluating candidates, we check the Pearson correlation against the Kick buffer first. If the correlation is strong, it's the downbeat. If correlation is weak but `air_odf_buffer` is strong, it's an upbeat. We penalize the upbeat score.

**Approach B: Phase Anchoring (Lightweight Heuristic)**
We calculate a rolling metric called `Low Frequency Dominance`. Whenever the `custom_flux` detects a peak, we check if `flux_bands[0] > flux_bands[-1]`. If true, we tag that timestamp as a "Kick". During the `class_based_phase_sweep` (Fast Scout), we add a strict +0.10 score bonus to any phase alignment candidate that perfectly intersects with these tagged "Kick" timestamps.

**Approach C: Assymetric Templates**
Currently, our `FastTemplateBank` generates a symmetrical Dirac comb (e.g., spikes at 0.0, 0.5, 1.0, 1.5 seconds). We could build an asymmetric template that has a value of `1.0` on the downbeat, but a slightly negative value (`-0.2`) on the exact sub-beat halfway between. This mathematically punishes candidates that align their "downbeat" spike directly on the musical off-beat, naturally drifting the Flywheel phase toward the real kick.

*Which approach aligns best with the computational limits of the Raspberry Pi?*
