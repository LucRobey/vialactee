# Agent Handoff: Beat Tracking Underutilization & Optimization

## Context
We are working inside `playground/BeatTracking_Evaluation/algorithm_code.py`. The goal is to optimize our custom harmonic beat tracker, which currently suffers from occasional phase inversion (locking onto the upbeat instead of the downbeat) and relies on greedy local heuristics to correct its phase.

Upon reviewing the core mathematical processes, we discovered that we are calculating highly precise data but throwing away the most valuable insights it produces. Your task is to refactor the algorithm to extract and utilize this full potential.

## Task 1: Heavy Judge Phase Extraction (The `argmax` Insight)

### The Problem
In both the Fast Scout (`class_based_phase_sweep`) and the Heavy Judge (`evaluate_specific_bpms`), we perform an $O(1)$ Vectorized Pearson Correlation:
```python
p_scores_pearson = (normalized_template @ buffer_centered) / buffer_std
```
This returns an array of correlation scores for *every possible phase alignment*. However, we currently only use `np.max(p_scores_pearson)` to determine if the BPM is a good fit. We completely throw away `np.argmax(p_scores_pearson)`. 

Because we discard the `argmax`, the tracker doesn't know the exact offset of the optimal beat grid. Instead, in `run_simulation_with_beats`, it attempts to fix phase drift using a crude, greedy local heuristic at the exact moment a peak arrives:
```python
phase_err = phase
if phase > 0.5:
    phase_err = phase - 1.0
phase -= 0.20 * phase_err
```

### Your Objective
1. Modify `evaluate_specific_bpms` (and potentially `class_based_phase_sweep`) to return the `best_phase_index` (`np.argmax(p_scores_pearson)`).
2. Refactor `run_simulation_with_beats` to use this extracted index. The index corresponds to a time offset from the end of the buffer where the mathematically optimal beat grid aligns. Use it to directly snap or intelligently guide the Flywheel's internal `phase` variable instead of the current localized `phase_err` nudge.

## Task 2: Multi-Buffer Spectral Correlation (Stop Crushing FFT Data)

### The Problem
To solve the downbeat vs. upbeat phase inversion issue, we proposed a "Dual-Buffer Pearson Correlation" approach (e.g., evaluating Kicks vs. Hi-hats separately).

Currently, `simulate_audio_ingestion` (and the `FakeListener` it mimics) calculates FFTs and extracts 32 precise Mel filterbands into an array called `flux_bands`. However, we immediately squash this rich spectral data into a 1D scalar:
```python
custom_flux = 2.0 * np.sum(flux_bands[0:2]) + 0.5 * np.sum(flux_bands[-2:])
```
This means our 300-frame history buffer only contains 1D data. We are paying the heavy CPU cost of calculating the 32 frequency bands, but throwing away the dimensionality before storing it.

### Your Objective
1. Modify `simulate_audio_ingestion` and the tracker state to store `flux_bands` as a 2D matrix (`300 frames x N bands`), or at the very least, split it into two parallel buffers (e.g., `kick_buffer` and `air_buffer`).
2. Update the Heavy Judge to evaluate candidates against these specific frequency signatures (e.g., penalize candidates whose "downbeat" template strongly correlates with the `air_buffer`).

## Files to Edit
- `playground/BeatTracking_Evaluation/algorithm_code.py` (Contains the math core, FastTemplateBank, and Flywheel simulation).
- You may also need to test your changes using `run_simulation_with_beats` over the provided benchmark datasets to verify F-measure/AMLt improvements.

Good luck!
