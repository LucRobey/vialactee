this document stores random ideas by luc, not organised or anything

- whe could probably use the derivative as a tool too. Meaning sometimes the beat is also just the timing where there is a change
- we should work more on this idea of "beat confidence". with that, whenever we have a doubt in our beat/bpm, we could start another flywheel (while keeping the main one) and if, a few seconds later, we realize this new flywheel is working, we swith to this one
- maybe using more bands could help? Going beyond 8 bands (e.g., 16, 24, or 32 bands / mel-spectrogram bins) to isolate instruments much more cleanly so electric guitars and vocals don't bleed into kicks and snares.
- don't be afraid to take a step back and test new radical ways rather than only incremental tweaks.

---

## 3 Radical Multi-Band Leads (Elaborated from the Above Ideas)

### 1. Per-Band Onset Derivatives (Combining Derivative + More Bands)
* **Problem it solves:** Distorted guitars and vocal swells create continuous loudness that tricks the beat tracker.
* **Concept:** Increase from 8 to 16-32 bands, and compute $\frac{d}{dt}\text{Energy}$ (rate of onset jump) *independently per band*.
* **Mechanism:** A kick drum creates an explosive vertical slope in the lowest 2 bands (and 0 slope in upper bands). An electric guitar chord has continuous energy across mid-bands but flat/gentle slope. By filtering by slope per band, guitar noise is rejected before it can corrupt the beat.

### 2. Dual-Flywheel Rhythm Separation (Kick Flywheel + Snare Flywheel)
* **Problem it solves:** Tracking all instruments with a single flywheel causes confusion when upbeats, hi-hats, and syncopation compete with the downbeat.
* **Concept:** Run two independent, synchronized flywheels:
  * **Flywheel A (Sub / Kick bands):** Dedicated strictly to locking onto the downbeats (beats 1 & 3).
  * **Flywheel B (Mid / Snare bands):** Dedicated strictly to locking onto backbeats (beats 2 & 4).
* **Mechanism:** In 4/4 time, Flywheel A and Flywheel B must run at the same tempo with an exact 180° phase relationship. When both agree, confidence is 100%. If one is ambiguous (e.g. during a guitar solo), the other maintains stability.

### 3. Adaptive Band Squelch / Dynamic Weighting per Song
* **Problem it solves:** Fixed band weights ($2.0 \times \text{Kick} + 1.2 \times \text{Snare}$) fail when a song has unusually loud guitar drone or synth pads in the snare frequency range.
* **Concept:** During the first 2-3 seconds of a song (and continuously via rolling baseline), measure the variance and saturation of each frequency band.
* **Mechanism:** If a band exhibits high continuous energy with low peakiness (like an overdriven guitar or organ pad), dynamically squelch/attenuate its weight to zero so it cannot inject noise into the beat detector.


