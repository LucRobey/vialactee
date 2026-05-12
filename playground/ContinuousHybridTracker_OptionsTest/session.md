# Research Session Log

**Date:** 2026-05-12
**Notebook:** `playground/ContinuousHybridTracker_OptionsTest.ipynb`
**Global Goal:** Achieve a more accurate beat prediction and BPM calculation.
**Current State:** The tracker works very well for now but has a tendency to miss some beats even though it has a good rhythm.
**Problem to Tackle:** The polyrhythmic trap. The system has a tendency to choose a lower BPM because testing fewer beats mathematically results in fewer missed beats.
**Final Objective:** Have the true, accurate BPM. We don't want the BPM with the fewest mistakes; we want the most accurate one, even if it means having some mistakes (e.g., 1 mistake every 10 seconds) rather than a "prude" system that doesn't take any risks.
**Research Approach / Notes:** The focus is purely on the mathematical logic of the BPM tracking. Minor coding errors (such as the FileNotFoundError) are irrelevant to the core experiment and will be ignored. *Hardware Constraint:* Keep in mind that all algorithms must eventually run on a Raspberry Pi; computational power is not infinite.

---

## 🧪 What was tried?

The user implemented and batch-tested three distinct "jailbreak" algorithms to force the system out of sub-harmonic tempo traps:

1. **Option 1 (The Smart Global Scout):** Compares the local continuous sweep against the `AudioAnalyzer`'s global BPM. If they diverge significantly and the global trust is high, it triggers a jump.
2. **Option 2 (Harmonic Cousins):** Explicitly probes common polyrhythmic multiples (0.5x, 0.75x, 1.5x, 2.0x) against the center BPM and applies a penalty/divider mathematical comparison to determine if a cousin is definitively a better fit.
3. **Option 3 (Tau-Normalized Sweep):** Directly alters the core mathematical evaluation by dividing the raw phase score by the expected number of beats (`tau`). This fundamentally levels the playing field so lower BPMs lose their statistical "fewer beats tested" advantage.

A batch simulation script was executed, running all three options through various configurations against ground-truth audio to generate a comparative JSON dataset.

## 📊 Results / Observations

- **Option 1 (The Smart Global Scout):** Appears to not be working at all.
- **Option 2 (Harmonic Cousins):** Shows some promise but suffers from severe "ping-pong" instability. It constantly challenges the current beat (e.g., if it finds a BPM of $N$, it tries to jump to $2N$; once at $2N$, it jumps back to $0.5N$), resulting in a completely unstable BPM.
- **Option 3 (Tau-Normalized Sweep):** Looks very promising conceptually, but so far the actual results are not showing it.
- **General Note:** The simulation successfully ran across all configurations for the options, allowing these baseline observations.

## 🐛 Meaningless Observations

- At the end of the notebook execution, a `FileNotFoundError` occurred because the JSON export attempted to save to a missing directory path (`../assets/musics/librosa/jailbreak_options_results.json`). Since the core experiment was unaffected, this is purely a minor execution flaw.

## 💭 Thoughts & Strategy

The ultimate goal is to find a way to test each option at its absolute best to see their true potential before dismissing any:
- **Option 1:** Not working currently, but maybe it's just being used wrong. It needs a proper configuration test.
- **Option 2:** Promising. The "ping-pong" instability is likely easily fixable (e.g., with a cooldown or penalty threshold).
- **Option 3:** Has potential but isn't working at all right now, which is concerning since it's the most computationally heavy option.

We need to optimize the mathematical implementation for *each* option independently, so we can run a fair, confronted comparison.

## ⏭️ Next Steps (What is left to be done)

- [ ] Debug and optimize Option 1 to ensure it's not failing due to misconfiguration.
- [ ] Fix the ping-pong problem in Option 2 (e.g., test a lockout or penalty threshold).
- [ ] Debug Option 3's mathematical implementation to see why the tau-normalization isn't yielding results, keeping in mind the heavy computational cost.
- [ ] Run a confronted comparison between the fully optimized versions of all three options.

---
*Note: This session log has been linked and aggregated into `RESEARCH_BOARD.md`.*
