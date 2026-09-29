---
name: vialactee-dsp-engine
description: Rules, mathematical foundations, and guidelines for modifying audio ingestion, DSP matrix transformations, beat tracking, and the Anticipation Flywheel (Oracle) in AudioIngestion.py, MultiBandOnsetAudioAnalyzer.py, comb_kernels.py, AudioAnalyzer.py, StructuralNoveltyDetector.py, RhythmConfig.py, and Listener.py.
---

# Vialactée DSP & Beat Tracking Engine Skill

Use this skill whenever modifying audio analysis algorithms, FFT filtering, tempo estimation, beat prediction, rhythmic phase synchronization, or structural novelty detection in `core/AudioIngestion.py`, `core/MultiBandOnsetAudioAnalyzer.py`, `core/comb_kernels.py`, `core/AudioAnalyzer.py`, `core/StructuralNoveltyDetector.py`, `core/RhythmConfig.py`, `core/Listener.py`, or `connectors/Local_Microphone.py`.

## Core Guidelines & Invariants

### 1. Vectorized DSP Front-End (No Slow Python Loops)
* All audio analysis must be executed via compiled `numpy` matrices and C-level vectorized operations (`np.dot`, `np.fft.rfft`, `np.convolve`).
* Mel filterbanks and Chromagram transformations use pre-computed transformation matrices. Do not calculate per-bin filters on the fly.
* **Dual-Resolution Mel Invariant:** `AudioIngestion.py` computes an 8-band filterbank (`fft_band_values`) consumed by visual modes, and a 32-band filterbank (`multiband_fft_values`) consumed by `MultiBandOnsetAudioAnalyzer`. Do not reduce the 8-band array size, as visual modes in `modes/` rely on it.
* Maintain ADSR envelopes natively in vector form across all 8 frequency bands and 12 chromagram bins.

### 2. Zero-Division & Floating-Point Safeguards
* In complete silence (or when audio devices disconnect), audio signals can drop to absolute zero.
* **NEVER** divide by sum/mean/variance without asserting `np.where(denom == 0, 1.0, denom)` or adding $\epsilon = 1e-9$ safety floors (e.g., `safe_gm = max(self.total_power_gm, 1e-9)` in `AudioIngestion.asserv_total_power`).
* Ensure all float normalization operations clamp output arrays to $[0.0, 1.0]$.

### 3. Dynamic Latency Calibration
* Do not introduce static latency numbers. Always preserve the dynamic latency equation linking `sounddevice`'s `time_info.inputBufferAdcTime` to the 4096-sample Hanning window center.
* Synchronize capture timestamps strictly within `audio_lock` in `Local_Microphone` to prevent phase jitter race conditions.

### 4. Multi-Band Separation, Oracle Flywheel & Phase Projection
* Production beat tracking in `MultiBandOnsetAudioAnalyzer.py` separates 32-band onset derivatives into 4 instrument streams: Kick ($y_{\text{kick}}$), Snare ($y_{\text{snare}}$), Hi-hat ($y_{\text{hat}}$), and Mid-melodic ($y_{\text{mid}}$).
* Kick-conditioned anti-phase disambiguation ($K_{\text{anti}} > 1.25 \cdot K_1$) prevents 180° upbeat phase locking on synth-heavy tracks.
* Standalone compiled `core/comb_kernels.py` builds the dense pulse template bank for sub-millisecond class correlation without external dependencies.
* Phase estimation is back-projected to speaker time ($T_{\text{speaker}}$).
* Flywheel and onset detection thresholds are centralized in `core/RhythmConfig.py`.
* Consult [flywheel_architecture.md](./references/flywheel_architecture.md) for complete mathematical definitions, Logarithmic Base-Tempo (LBT) octave folding, and dropout immunity rules.

### 5. Structural Novelty Separation
* Structural music events (Verse/Chorus boundaries, Seamless Crossfades, Silence Drops) are managed by `core/StructuralNoveltyDetector.py`.
* Macro-structure tension is computed from Short-Term Memory (STM) vs Long-Term Memory (LTM) Euclidean distance and asserved dynamically via Local Max / Global Max decay envelopes.

### 6. Listener Facade Contract & Zero-Allocation Delay Buffer
* `Listener.py` manages a pre-allocated 2D/1D NumPy circular ring buffer (zero heap allocations per frame) that aligns real-time spectral data with delayed beat triggers.
* Any new property added to `AudioIngestion`, `AudioAnalyzer`, or `StructuralNoveltyDetector` must be exposed via delayed properties in `Listener.py` so visual modes receive time-aligned metrics.

### 7. BaseAudioAnalyzer Contract & Benchmark Verification
* Any modification or replacement of beat tracking algorithms must subclass `core/BaseAudioAnalyzer.py`.
* Always evaluate changes against the immutable benchmark suite (`python -m research.benchmarks.run_benchmark --suite synthetic --save-run`) before merging.
* Enforce the physical refractory lockout ($T_{\min} = \max(0.18\text{s}, 0.40 \times 60/\text{BPM})$) and backward wrap clamp on soft-snapping to prevent double-trigger chatter and phase jitter.

