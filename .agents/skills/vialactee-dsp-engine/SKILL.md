---
name: vialactee-dsp-engine
description: Rules, mathematical foundations, and guidelines for modifying audio ingestion, DSP matrix transformations, beat tracking, and the Anticipation Flywheel (Oracle) in AudioIngestion.py, AudioAnalyzer.py, StructuralNoveltyDetector.py, RhythmConfig.py, and Listener.py.
---

# Vialactée DSP & Beat Tracking Engine Skill

Use this skill whenever modifying audio analysis algorithms, FFT filtering, tempo estimation, beat prediction, rhythmic phase synchronization, or structural novelty detection in `core/AudioIngestion.py`, `core/AudioAnalyzer.py`, `core/StructuralNoveltyDetector.py`, `core/RhythmConfig.py`, `core/Listener.py`, or `connectors/Local_Microphone.py`.

## Core Guidelines & Invariants

### 1. Vectorized DSP Front-End (No Slow Python Loops)
* All audio analysis must be executed via compiled `numpy` matrices and C-level vectorized operations (`np.dot`, `np.fft.rfft`, `np.convolve`).
* Mel filterbanks and Chromagram transformations use pre-computed transformation matrices. Do not calculate per-bin filters on the fly.
* Maintain ADSR envelopes natively in vector form across all 8 frequency bands and 12 chromagram bins.

### 2. Zero-Division & Floating-Point Safeguards
* In complete silence (or when audio devices disconnect), audio signals can drop to absolute zero.
* **NEVER** divide by sum/mean/variance without asserting `np.where(denom == 0, 1.0, denom)` or adding $\epsilon = 1e-9$ safety floors (e.g., `safe_gm = max(self.total_power_gm, 1e-9)` in `AudioIngestion.asserv_total_power`).
* Ensure all float normalization operations clamp output arrays to $[0.0, 1.0]$.

### 3. Dynamic Latency Calibration
* Do not introduce static latency numbers. Always preserve the dynamic latency equation linking `sounddevice`'s `time_info.inputBufferAdcTime` to the 4096-sample Hanning window center.
* Synchronize capture timestamps strictly within `audio_lock` in `Local_Microphone` to prevent phase jitter race conditions.

### 4. Oracle Flywheel & Phase Projection
* Beat tracking utilizes non-causal 5-second lookahead Pearson correlation template matching (`FastTemplateBank`).
* Phase estimation is back-projected to speaker time ($T_{\text{speaker}}$).
* Flywheel and onset detection thresholds are centralized in `core/RhythmConfig.py`.
* Consult [flywheel_architecture.md](./references/flywheel_architecture.md) for complete mathematical definitions, Logarithmic Base-Tempo (LBT) octave folding, and dropout immunity rules.

### 5. Structural Novelty Separation
* Structural music events (Verse/Chorus boundaries, Seamless Crossfades, Silence Drops) are managed by `core/StructuralNoveltyDetector.py`.
* Macro-structure tension is computed from Short-Term Memory (STM) vs Long-Term Memory (LTM) Euclidean distance and asserved dynamically via Local Max / Global Max decay envelopes.

### 6. Listener Facade Contract & Zero-Allocation Delay Buffer
* `Listener.py` manages a pre-allocated 2D/1D NumPy circular ring buffer (zero heap allocations per frame) that aligns real-time spectral data with delayed beat triggers.
* Any new property added to `AudioIngestion`, `AudioAnalyzer`, or `StructuralNoveltyDetector` must be exposed via delayed properties in `Listener.py` so visual modes receive time-aligned metrics.
