# Notebook History Log

This document serves as the permanent knowledge base and historical record for this notebook. While `session.md` is for scratchpad notes and active task tracking during a coding session, `history.md` summarizes the long-term findings.

## What has been done
- Implemented the new BPM logic to track the tempo class (Logarithmic Base Tempo) instead of the precise BPM.
- Proved that the tempo class handles massive octave jumps seamlessly without ping-ponging.
- Tested and evaluated 3 Candidate Evaluator mathematical models (Pearson Correlation, Peak vs Valley Ratio, Pure Hit Density).

## What has been changed
- Shifted approach from tracking precise BPM to using a "Tempo Class" math model ($O(1)$ logarithmic circle math) to evaluate distances on a modulo circle.
- Replaced tau-normalization and arbitrary masking with True Pearson Correlation scoring for both the Initial Phase Sweep and the Candidate Evaluator.
- Replaced the flawed target pulse templates with a centered, sharp triangle pulse (`+1.0` at beat, `-0.5` everywhere else) combined with a zero-mean buffer calculation.

## What was tested (and didn't work)
- **Tau-Normalization Bias:** The initial model divided by `expected_beats`. It mathematically punished high BPMs and exhibited severe *sub-harmonic bias*, violently oscillating between sub-harmonics.
- **Option B: Peak vs Valley Ratio:** Evaluated, but failed due to extreme volatility. Any noise or hi-hats in the valleys destroyed the denominator, causing wild instability.
- **Option C: Pure Hit Density:** Evaluated, but failed due to *super-harmonic bias*. Without normalization, the template simply added up hits, naturally pegging itself to the highest possible BPM multiplier because more beats = more points.
- **Option A (Original Flawed Pearson):** The initial implementation of Pearson Correlation failed because the mathematical mask unintentionally rewarded off-beats (`+0.6`), causing 64 BPM templates to perfectly score on 128 BPM songs.

## What is currently working
- **Long Term Class:** Tracking the tempo class perfectly follows the fundamental rhythm space without "ping-ponging" during octave transitions.
- **True Pearson Correlation:** After fixing the template bug to use a sharp triangle pulse on the beats and negative baseline elsewhere, True Pearson Correlation naturally solves *both* sub-harmonic and super-harmonic biases.

## What will be done next
- Evaluate the True Pearson Correlation Candidate Evaluator's performance on the simulation.
- Integrate the winning Candidate and Tempo Class into the Flywheel (`standalone_phase`) for long-term continuous prediction.
