# ContinuousHybridTracker: Agent Handoff Document

Welcome, new agent. This document summarizes the complete architectural state and mathematical logic of the `ContinuousHybridTracker` math engine. Your objective is likely to port this logic into the main project, test it on hardware, or connect it to the visualizer.

## 1. Project Context & Goal
The goal of this module is to perform real-time BPM and phase tracking of live audio for a visual system running on a **Raspberry Pi**. Because of hardware constraints, the math must be extremely computationally lightweight while remaining robust against missing beats, polyrhythms, and tempo drifts.

## 2. The LBT (Logarithmic Base Tempo) Class Architecture
We completely decoupled **"Rhythmic Grid Detection"** from **"Octave/Multiplier Selection"** using the `bpm_class` system.
* A BPM is mapped to a float `[0.0, 1.0)` representing its octave-agnostic grid: `class = log2(bpm / 60.0) % 1.0`.
* Example: 60 BPM, 120 BPM, and 240 BPM all share class `0.0`. 
* This allows the system to easily track the continuous drift of a tempo grid without getting confused by whether the song is playing in half-time or double-time.

## 3. The Math Engine Pipeline
The pipeline runs continuously on the audio stream (simulated at 60 FPS) and is defined in both `ContinuousHybridTracker_HarmonicMath.ipynb` and `run_nb.py`.

### A. Pristine ODF (Onset Detection Function)
To prevent vocal and synth noise from confusing the tracker, we use a **Bass + High filter**. We sum only the lowest and highest FFT mel-bands (`flux_bands[0:2]` + `flux_bands[-2:]`), creating a clean, percussive ODF.

### B. The Fast Scout (`class_based_phase_sweep`)
The Fast Scout evaluates phase alignment. To save CPU, it does **not** evaluate hundreds of BPMs. It evaluates `bpm_classes`.
*   **Evaluation Math:** For a given class `c`, it generates a representative BPM strictly in the `[90, 180)` range. It generates a simple $O(N)$ triangle pulse template for that BPM and slides it across the ODF to find the highest grid-alignment score.
*   **Local Sweep (Every 1 second):** It sweeps `±0.05` around the current `long_term_class` (only 11 evaluations). This tracks continuous tempo drifts for practically zero CPU cost.
*   **Strong Sweep (Every 10 seconds):** It sweeps the full `[0.0, 1.0)` class range (100 evaluations) to catch completely abrupt song transitions.

### C. The Flywheel Smoothing
The winning class from the Fast Scout is aligned to the `long_term_class` (accounting for circular wrapping and perfect fifths/0.75x shifts) and smoothed using an Exponential Moving Average. This creates a "flywheel" effect that prevents momentary noise from derailing the tracker.

### D. The Heavy Judge (`evaluate_specific_bpms`)
While the Fast Scout finds the *grid*, the Heavy Judge finds the *octave*.
*   It generates 5-6 exact harmonic candidates from the `long_term_class` (e.g., 0.5x, 0.75x, 1.0x, 1.25x, 1.5x, 2.0x).
*   It evaluates ONLY these candidates using high-precision **True Pearson Correlation**.
*   **The Human Perception Prior:** It applies a Gaussian weighting curve centered at `125 BPM` to the Pearson scores. This heavily penalizes sub-harmonics (like 64 BPM) and forces the tracker to lock onto the "human-danceable" tempo (like 128 BPM), completely curing the previous "ping-pong" instability.

## 4. Current State
*   The math has been entirely validated in simulation (`run_nb.py`).
*   It successfully tracks 145 BPM and 128 BPM songs without sub-harmonic collapse.
*   The transition from a 160-candidate brute-force sweep to the Local/Strong Class Sweep slashed computational overhead by roughly ~80%.

## 5. Next Steps for You
1.  **Code Porting:** Refactor the logic verified in `run_nb.py` into the main `core/` modules.
2.  **Hardware Profiling:** Deploy the math to the actual Raspberry Pi. Ensure the 1-second Local Sweep loop executes without stuttering the audio thread.
3.  **Visual Integrations:** Hook the cleanly smoothed `listener.analyzer.bpm` and phase outputs to the `standalone_phase` system to drive the visualizer synchronizations.
4.  **Cleanup:** Remove experimental files (like `modify_nb.py` or old scratch files) from the `playground/` directory to keep the repository clean.
