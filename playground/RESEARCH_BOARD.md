# 🔬 Research Board

This document tracks the high-level progress of all experimental work in the `playground/` directory.

---

## 🎯 Current Final Objective

**Optimizing Rhythm Tracker with Harmonic Math Metric (Tempo Class)**
*Goal:* Eliminate polyrhythmic tempo traps and "ping-pong" instability by tracking BPM in a circular logarithmic space. This separates the stability tracking (the fundamental rhythm) from the multiplier selection (the precise BPM), ensuring the rhythm engine prioritizes the global peak energy without corrupting memory through linear averaging.

---

## 📈 Overall Progress

- **Status:** Active
- **Key Focus:** Benchmarking and evaluating "Continuous Tau Normalization" versus "Global Scout" and "Harmonic Cousins".
- **Current Blocker/Challenge:** Accelerating simulation runtime and fixing environment execution errors while comparing math against ground-truth BPM.

---

## 📋 To Do (Left to be done)

- [x] Create `ContinuousHybridTracker_HarmonicMath.ipynb`.
- [x] Implement the Logarithmic Base Tempo (LBT) circle math in the new notebook.
- [x] Adapt the 5-second Magnetic Snap Execution engine to track `long_term_class` instead of `long_term_bpm`.
- [x] Run the evaluation and compare stability to the older Jailbreak options.
- [ ] Evaluate 3 new techniques to find real BPM (Pearson correlation, Peak vs Valley ratio, Pure hit density) to eliminate sub-harmonic bias.
- [ ] Integrate the Tempo Class and selected Candidate into the Flywheel (`standalone_phase`) for long-term beat prediction.
- [ ] If successful, integrate the winning mathematical strategy back into the main pipeline.

---

## 🚧 In Progress

- **Harmonic Math Metric (Tempo Class) Sandbox**
  - *Notebook:* `playground/ContinuousHybridTracker_HarmonicMath/ContinuousHybridTracker_HarmonicMath.ipynb`
  - *Details:* Building a brand new experimental tracker notebook. Instead of using raw linear BPMs, this evaluates tempos using $f(BPM) = \log_2(BPM/60) \pmod 1$. This correctly groups 50, 100, and 200 into the same exact mathematical equivalence class, allowing O(1) comparison distance and absolute tracking stability.

- **Jailbreak Options Configuration Test** 
  - *Notebook:* `playground/ContinuousHybridTracker_OptionsTest/ContinuousHybridTracker_OptionsTest.ipynb`
  - *Details:* Tested three mathematical jailbreak strategies. Paused temporarily to solve the linear BPM metric flaw that was corrupting LTM and divergence measurements during polyrhythmic jumps.

---

## ✅ Completed (What has been done)

- **Identified Polyrhythmic Traps:** Confirmed the baseline tracker easily gets stuck in sub-harmonic locks.
- **Formulated 3 Jailbreak Strategies:** Global Scout, Harmonic Cousins, and Tau-Normalized Sweep.
- **Fixed `librosa` kernel crashes:** Handled numba recursion issues causing stack overflows.
- **Resolved numpy/soxr binary incompatibility:** Stabilized the audio loading pipeline.
- **Implemented 5-second lookahead:** Synced the DSP pipeline with the audio ingestion buffer (`DelayedMusicAnalyzer.ipynb`).

---

## 💀 Dead Ends (What didn't work)

- *None logged yet.*
