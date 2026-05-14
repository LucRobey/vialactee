# Harmonic Math Tracker: Algorithm Inputs and Tuning Guide

Based on the structure in the `ContinuousHybridTracker_HarmonicMath.ipynb` notebook, the algorithm is modularly designed across several distinct stages (Ingestion -> Peak Detection -> Scout -> Judge -> Flywheel). 

Because of this design, you have several highly impactful hyperparameters that you can tweak to balance **Responsiveness** (how fast it adapts to changes) versus **Stability** (how well it ignores noise/polyrhythms), as well as **Compute Cost**.

Here is a breakdown of the key inputs you can play with and how they affect the algorithm's performance:

## 1. Peak Detection (Onset Thresholds)
This determines what the algorithm considers a "beat" versus "noise".
* **`smoothed_flux = 0.95 * smoothed_flux + 0.05 * custom_flux`**
  * **What it is:** The adaptive moving average of the audio energy.
  * **Effect:** Changing the `0.95/0.05` ratio changes how fast the baseline adapts. A faster adaptation (e.g., `0.90/0.10`) tracks rapid volume drops better, but might accidentally absorb rapid drum fills into the baseline.
* **`is_peak = custom_flux > (smoothed_flux * 1.8 + 0.1)`**
  * **What it is:** The multiplier (`1.8`) and the noise floor offset (`0.1`).
  * **Effect:** 
    * **Increasing `1.8` (e.g., to `2.5`):** The tracker becomes extremely strict, only triggering on massive kick drums. This makes it very stable but it might lose the beat during quiet sections.
    * **Decreasing `1.8` (e.g., to `1.3`):** It captures every hi-hat and ghost note. This gives the Scout/Judge more data to work with, but increases the risk of locking onto polyrhythmic noise.

## 2. The Memory Window (Buffer & Decay)
This dictates how much "past" the tracker remembers when judging the current tempo.
* **`odf_size = 300`** (at 60 FPS, this is a **5.0 second** window)
  * **Effect:** A shorter window (e.g., `150` / 2.5s) makes the tracker very snappy and quick to adapt to sudden tempo changes, but it will easily get thrown off by a 1-second drum fill. A longer window (e.g., `600` / 10s) creates massive stability but sluggish tempo transitions.
* **`decay_curve = np.exp(-1.5 * np.linspace(1.0, 0.0, odf_size))`**
  * **What it is:** Weights recent beats more heavily than older beats in the buffer.
  * **Effect:** 
    * **Steeper decay (e.g., `-3.0`):** Makes the algorithm highly biased toward what just happened in the last 1 second. Fast reacting.
    * **Flatter decay (e.g., `-0.5`):** Treats all beats in the 5-second window almost equally. High inertia, great for ignoring sudden mistakes.

## 3. The Human Prior (Tempo Bias)
This mathematical curve penalizes extreme tempos (like 60 BPM or 180 BPM) to prevent the algorithm from doubling/halving incorrectly.
* **`human_prior = 0.5 + 0.5 * np.exp(-0.5 * ((bpm_val - 125.0) / 40.0)**2)`**
  * **What it is:** A Gaussian bell curve centered at `125.0` BPM with a spread (standard deviation) of `40.0`.
  * **Effect:** 
    * **Changing the Center (`125.0`):** If you are tracking Hip-Hop, you might want to lower this to `90.0`. If tracking Drum & Bass, raise it to `170.0`.
    * **Changing the Spread (`40.0`):** A wider spread (e.g., `60.0`) makes the tracker more open-minded to extreme tempos. A tighter spread (e.g., `20.0`) forces it to stay glued to standard dance/pop tempos.

## 4. The Groove Distance Penalty (Confidence Gates)
This logic (Test 6) protects the `long_term_class` from sudden, unrelated tempo spikes.
* **`required_threshold = 0.15` (In-Groove) vs `0.30` (Out-of-Groove)**
  * **What it is:** The Pearson correlation score required to update the tempo.
  * **Effect:** 
    * **Raising the out-of-groove threshold (e.g., `0.40`):** The tracker will almost *never* change to a completely new tempo unless the drum beat is undeniably clear and perfectly steady. Ultimate protection against polyrhythms.
    * **Lowering the in-groove threshold (e.g., `0.10`):** Allows the tracker to "coast" and maintain its current tempo even through messy, complex ambient sequences where the beat is faint.

## 5. Flywheel Inertia (Update Speeds)
When a new beat is detected, how fast do we pull the flywheel toward it?
* **`long_term_class = (long_term_class + 0.1 * diff_scout) % 1.0`** (Scout weight: `0.1`)
* **`long_term_class = (long_term_class + 0.5 * diff_judge) % 1.0`** (Judge weight: `0.5`)
  * **Effect:** 
    * **Higher values (e.g., `0.9`):** The tracker snaps instantly to the new phase. Good for mechanical precision, but can cause audible jitter/wobble.
    * **Lower values (e.g., `0.05`):** The tracker acts like a massive heavy wheel, slowly gliding toward the true beat. Very smooth, but might "drag" for a second or two if the live band pushes the tempo.

## 6. Compute Cost vs. Precision
* **`class_evals = np.arange(0.0, 1.0, 0.01)`**
  * **What it is:** Checks 100 slices of the tempo circle during a strong sweep.
  * **Effect:** Changing to `0.005` doubles the tracking resolution (smoother locking) but doubles the CPU cost of the Fast Scout.
* **Pulse sharpness:** `mask_beat = beat_dist < 0.1` (in `FastTemplateBank`)
  * **Effect:** A wider pulse (`0.2`) makes the tracker more forgiving of sloppy drumming (higher correlation scores overall). A sharper pulse (`0.05`) demands perfect mechanical timing, making it act strictly like a metronome.
