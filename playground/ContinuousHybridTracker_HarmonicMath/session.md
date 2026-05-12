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
- Replaced the linear `long_term_bpm` tracking with $O(1)$ logarithmic circle math (`long_term_class`).
- Ran a raw continuous sweep to track the changing music, mapped it to a class, and smoothed it to prove it can handle massive octave jumps seamlessly.
- Used the smoothed class to generate exactly 5 explicit harmonic candidates (e.g., 50, 75, 100, 150, 200).
- Used a tau-normalized scoring function to evaluate *only* those 5 candidates to pick the final locked BPM.

## 📊 Results / Observations

- **Massive Success on Class Tracking:** The bottom plot proved the math is perfect. The `Long Term Class` line stayed flawlessly smooth during polyrhythmic jumps. When the song transitioned from 145 BPM to 128 BPM, the class glided elegantly and wrapped around the circle to lock exactly onto ~0.09 (the true class of 128 BPM). No ping-ponging, no linear corruption!
- **Flawed Candidate Evaluator:** The top plot showed violent oscillation between sub-harmonics (96 and 48) instead of tracking the true 128 BPM. 
- **The "Self-Fulfilling Prophecy" Bug:** Initially, the notebook only searched exact candidates based on the first frame's guess, locking the class in place permanently. We fixed this by running a raw continuous sweep to drive the class, but limiting the final output to the candidates.

## 🐛 Meaningless Observations

- Matplotlib modulo wrapping looks like a vertical straight line dropping from 1.0 to 0.0, but it actually represents a tiny, smooth movement on the circle.

## 💭 Thoughts & Strategy

- **The Tau-Normalization Bias:** By dividing the total score by the `expected_beats` (tau), the formula mathematically punishes high BPMs. Slower tempos (like 48 BPM) have fewer beats, meaning fewer chances to hit negative penalties in the audio buffer. This makes them "safer" bets. Our 5% asymmetric penalty was too weak. We need to rework the scoring function to reward high-density positive hits instead of just avoiding negative ones.
- **The Flywheel Integration:** Finding the BPM is only half the battle. The ultimate goal is to find the *beats* (phase). The new architecture gives us a solid foundation: 
  1. The `Long Term Class` gives us the fundamental frequency.
  2. The `Candidate Evaluator` gives us the exact Octave.
  3. We must now map the winning candidate's phase into the `standalone_phase` (the flywheel) to keep the rhythm engine turning consistently over time.

### 🎯 Candidate Scoring Options to Test
We have formulated 3 mathematical strategies to replace the flawed Candidate Evaluator and eliminate the sub-harmonic bias:

**Option A: Pearson Correlation (The Mathematical Standard)**
- **How it works:** We remove the `/ expected_beats` division entirely. Instead, we mathematically normalize the score by the geometric energy of the template itself (`sqrt(sum(template^2))`).
- **Why it's universal:** This turns the score into a pure statistical correlation coefficient [-1.0 to 1.0]. High BPM templates naturally have more peaks (higher geometric energy), so this scales them perfectly fairly against low BPM templates without any arbitrary bias.

**Option B: Peak vs. Valley Ratio (The Sub-Harmonic Killer)**
- **The Secret Bug:** Right now, our template actually rewards off-beats (+0.6). This means a 64 BPM template gets massive positive points when its "off-beat" lands on an actual 128 BPM beat!
- **How it works:** We stop rewarding off-beats. We sum the audio energy exactly on the predicted beats, and divide it by the audio energy exactly in the valleys (the off-beats). `Score = Beat_Energy / (Valley_Energy + epsilon)`.
- **Why it's universal:** If we test 64 BPM on a 128 BPM song, the 64 BPM template's "valleys" will align perfectly with the actual 128 BPM beats! The `Valley_Energy` explodes, instantly tanking the 64 BPM score.

**Option C: Pure Hit Density (The Simplest Approach)**
- **How it works:** We make the template strictly positive at the beats (+1.0) and 0.0 everywhere else. We do not divide or normalize by anything.
- **Why it's universal:** A 128 BPM track naturally has twice as many beats as a 64 BPM track. If we just sum the raw energy, the 128 BPM track will effortlessly accumulate twice as much energy simply by virtue of having more valid hits in the buffer.

## ⏭️ Next Steps (What is left to be done)

- [x] Create `ContinuousHybridTracker_HarmonicMath.ipynb`.
- [x] Duplicate the standard listening infrastructure (FFT, 5-second delay queue, Listener.py).
- [x] Implement `f(BPM) = log2(BPM/60) % 1.0` mapping.
- [x] Implement circular distance `min(|f1 - f2|, 1 - |f1 - f2|)`.
- [x] Refactor tracking variables (`long_term_bpm` to `long_term_class`).
- [x] Test evaluating only the 4 harmonic candidate multipliers against the audio buffer to pick the precise BPM.
- [ ] **Fix Candidate Scoring:** Design a new scoring formula that removes the sub-harmonic bias.
- [ ] **Flywheel Integration:** Connect the chosen BPM and Phase to the continuous `standalone_phase` system to predict actual beats on the long run.

---
*Note: Ensure that any major findings or shifts in the overarching goal are also updated in `RESEARCH_BOARD.md`!*
