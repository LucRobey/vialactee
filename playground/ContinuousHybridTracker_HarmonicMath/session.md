# Research Session Log

**Date:** 2026-05-12
**Notebook:** `playground/ContinuousHybridTracker_HarmonicMath.ipynb`
**Global Goal:** Achieve a more accurate and stable beat prediction and BPM calculation by escaping linear metric constraints.
**Current State:** The tracker experiences "ping-pong" instability when testing polyrhythmic jumps because it treats harmonic subdivisions (e.g., 50 and 100) as wildly diverging tempos instead of equivalent musical spaces.
**Problem to Tackle:** The mathematical representation of BPM. Linear smoothing and tracking metrics corrupt the tempo (e.g., averaging 100 and 200 into 150) and penalize jumps between valid harmonic cousins.
**Final Objective:** Implement a "Tempo Class" math model (Logarithmic Base Tempo) to evaluate the distance between BPMs in $O(1)$ time on a modulo circle. The tracker should run seamlessly over the standard `Listener.py` audio ingestion and 5-second lookahead, but its core logic for stability, divergence, and tracking should be entirely based on this new metric space.
**Research Approach / Notes:** We are NOT modifying the core production classes yet. This is purely experimental research. We will create a fresh notebook specifically for this, cloning the architecture of the previous Options Test but replacing the metrics. We will track the class, and once the class is tracked, explicitly evaluate only a few exact multipliers to output the final BPM.
*Hardware Constraint:* Keep in mind that all algorithms must eventually run on a Raspberry Pi; computational power is not infinite. This mathematical design aligns perfectly by preventing hundreds of array sweep calculations.

---

## 🧪 What was tried?

- Generated `ContinuousHybridTracker_HarmonicMath.ipynb` to isolate and test the "Tempo Class" math.
- Evaluated Option A (Pearson), Option B (Peak/Valley), and Option C (Density). Option A proved mathematically superior. Options B and C were discarded.
- Attempted a "Two-Tier Architecture" (splitting Bass and High frequencies) to force the tracker to ignore polyrhythms.
- Reverted to a Fast Scout (Raw Sweep) and Heavy Judge (Option A) architecture to fix O(N^2) performance issues.

## 📊 Results / Observations

- **Massive Success on Class Tracking:** The bottom plot proved the math is perfect. The `Long Term Class` line stayed flawlessly smooth during polyrhythmic jumps.
- **Two-Tier Acoustic Failure:** Splitting the Bass (Kick) and High (Snare) destroyed the 128 BPM 4/4 groove. Each buffer only saw a 64 BPM sub-rhythm, causing the tracker to collapse entirely.
- **The Unified ODF Recovery:** Recombining the frequencies restored the 128 BPM pulse. The method got better, but it's not enough—the tracker still struggles to confidently choose 128 BPM over the mathematically equivalent 64 BPM sub-harmonic.

## 🐛 Meaningless Observations

- Matplotlib modulo wrapping looks like a vertical straight line dropping from 1.0 to 0.0, but it actually represents a tiny, smooth movement on the circle.

## 💭 Thoughts & Strategy

- **The Human Perception Prior (Gaussian Technique):** Since a 64 BPM template can score identically to 128 BPM in Pearson correlation, we are implementing a Gaussian weighting curve centered around 120-130 BPM (the typical human dance zone). We went with Option A for the core math because it is faster and more reliable, but we apply this Gaussian prior as a mathematical tie-breaker. It penalizes extreme tempos (60 BPM or 230 BPM) so the algorithm must be "really sure of itself" to pick them.
- **The Bass + High Filter (Dropping the Mids):** To further clean the signal, we will refine the ODF by strictly combining the Bass and High bands while completely ignoring the middle frequencies. This drops the muddy vocal/synth noise that confuses the rhythm engine, giving us a pristine Kick + Snare/Hi-hat signal.

## ⏭️ Next Steps (What is left to be done)

- [x] Create `ContinuousHybridTracker_HarmonicMath.ipynb` and duplicate listening infrastructure.
- [x] Refactor tracking variables to $O(1)$ logarithmic circle math (`long_term_class`).
- [x] Fix Candidate Scoring: Discard Options B and C, adopt Option A (True Pearson Correlation).
- [ ] **Implement Bass + High Filter:** Modify the simulation to drop the middle frequencies before calculating the Unified ODF.
- [ ] **Flywheel Integration:** Connect the chosen BPM and Phase to the continuous `standalone_phase` system to predict actual beats on the long run.

---
*Note: Ensure that any major findings or shifts in the overarching goal are also updated in `RESEARCH_BOARD.md`!*
