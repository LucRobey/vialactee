# [2026-10-02] Rhythmic Salience Engine, Audio Analyzer Contract & Mode Modernization

> **Date:** 2026-10-02  
> **Session ID:** `75ef2c7c-9be6-4baa-b95e-a0e89aab02aa`  
> **Agent / Model:** Antigravity (Gemini 3.8 Flash High)  
> **Primary Goal:** Quantify real-time rhythmic importance (`rhythm_salience`), establish the definitive Audio Analyzer contract, fix DSP timing bugs (`beat_tag`), deprecate dead features (`band_peak`), and modernize visual modes.  
> **Status:** COMPLETED  

---

## 1. Context & Motivation

* **User Request:** The user wanted to upgrade chandelier lighting modes to leverage rhythm more dynamically, specifically asking: *"I would like to have an idea of when the rhythm is important or not. How could we do that and use it?"*
* **Core Problem:** In real music, audio transitions between driving rhythmic grooves (drops, drum loops) and harmonic suspension (ambient pads, vocal solos). Rigid metronomic flashing during unmetered ambient sections looks like a software glitch, while lack of percussive punch during drops weakens visual impact.
* **Audit Findings:** Investigating the codebase revealed:
  1. There was no explicit `rhythm_salience` metric in production; modes relied on raw Pearson `beat_confidence` $[-1.0, 1.0]$ which leads speaker audio by 2–5 seconds.
  2. [`beat_tag`](file:///c:/Users/Users/Desktop/vialact%C3%A9e/vialactee/core/Listener.py#L354) had a critical 5-second timing desync bug (evaluating incoming microphone flux at $T_{\text{lookahead}}$ while `is_beat` ticked at $T_{\text{speaker}}$).
  3. [`band_peak`](file:///c:/Users/Users/Desktop/vialact%C3%A9e/vialactee/core/Listener.py#L217) was completely dead (all zeros, never updated) in `MultiBandOnsetAudioAnalyzer`, causing [`modes/Shining_stars_mode.py`](file:///c:/Users/Users/Desktop/vialact%C3%A9e/vialactee/modes/Shining_stars_mode.py) to remain permanently dark.
  4. Phantom stub properties from `BaseAudioAnalyzer.py` (`is_downbeat`, `bar_phase`, `vocals_present`, etc.) were never exposed on `Listener.py` and crashed with `AttributeError` if accessed.

---

## 2. Changes Made

### 1. DSP Engine & Rhythmic Salience
* **[NEW]** Real-time **Rhythmic Salience** ($R_{\text{salience}} \in [0.0, 1.0]$) inside [`core/MultiBandOnsetAudioAnalyzer.py`](file:///c:/Users/Users/Desktop/vialact%C3%A9e/vialactee/core/MultiBandOnsetAudioAnalyzer.py):
  * **4 Acoustic Pillars**:
    * $\rho_{\text{trans}}$ (30%): Half-wave rectified drum flux vs total spectral power ($\Phi_{\text{drum}} / (\Phi_{\text{drum}} + 0.4 \cdot P_{\text{total}})$), isolating drum transients from sustained chords.
    * $C_{\text{norm}}$ (25%): 3-second rolling peak-to-average flux crest factor via circular buffer `_drum_flux_history`.
    * $\gamma_{\text{conf}}$ (25%): Flywheel Pearson template correlation consensus score.
    * $D_{\text{pulse}}$ (20%): 8-beat FIFO ring tracking verified acoustic downbeats (`is_real_beat`).
  * **Asymmetric Temporal Filtering**: Fast attack (~50ms) to snap immediately on drops; slow release (~1.5s) to sustain across bars without inter-beat chatter.
  * Zero dynamic heap allocations; execution time $\le 0.15\text{ms}$ (Axiom 1 & 2 compliant).
  * Maintained line count at 619 lines (Axiom 7 ratchet cap $\le 621$).
* **[MODIFY]** [`core/Listener.py`](file:///c:/Users/Users/Desktop/vialact%C3%A9e/vialactee/core/Listener.py):
  * Pre-allocated `_ring_rhythm_salience` FIFO delay buffer.
  * Ingests `live_rhythm_salience` at $T_{\text{lookahead}}$ and outputs delayed `rhythm_salience` synchronized to speaker playback ($T_{\text{speaker}}$).
  * Exposes `self.listener.rhythm_salience` (speaker time) and `self.listener.live_rhythm_salience` (lookahead time, enabling pre-drop detection $\Delta R$).
* **[MODIFY]** [`core/BaseAudioAnalyzer.py`](file:///c:/Users/Users/Desktop/vialact%C3%A9e/vialactee/core/BaseAudioAnalyzer.py) & [`core/AudioAnalyzer.py`](file:///c:/Users/Users/Desktop/vialact%C3%A9e/vialactee/core/AudioAnalyzer.py):
  * Added contractual properties `rhythm_salience` and `live_rhythm_salience` with safe default fallbacks.

### 2. Audio Analyzer Contract & Documentation
* **[NEW]** [`docs/reference/audio_analyzer_contract.md`](file:///c:/Users/Users/Desktop/vialact%C3%A9e/vialactee/docs/reference/audio_analyzer_contract.md):
  * Comprehensive permanent reference document in version control.
  * Details every variable accessible via `self.listener`, its type, nominal range, timing alignment ($T_{\text{speaker}}$ vs $T_{\text{lookahead}}$), stability/confidence rating, physical meaning, and exact DSP measurement pipeline.
  * Documents standard visual mode recipes (continuous blending, gated strobes, tempo-locked kinematics).

### 3. DSP Bugfixes & Dead Feature Cleanup
* **[FIX]** `beat_tag` timing desync in [`core/MultiBandOnsetAudioAnalyzer.py`](file:///c:/Users/Users/Desktop/vialact%C3%A9e/vialactee/core/MultiBandOnsetAudioAnalyzer.py):
  * Pre-allocated circular ring buffer `band_flux_buffer`.
  * Transient frequency classification now integrates across the speaker playback window (`w_start:w_end`) centered at `speaker_center`.
  * Included mid-frequency bands (`self.snare_mid_bands`) so synth/guitar/brass hits are tagged `"Snare/Mid"` instead of defaulting to `"Bass/Kick"`.
  * Added sub-frame window integration to accurately classify hi-hat transients with timing jitter as `"Hi-hat/Cymbal"`.
* **[DELETE]** Deprecated and removed dead `band_peak`:
  * Excised from `MultiBandOnsetAudioAnalyzer.py`, `AudioAnalyzer.py`, `BaseAudioAnalyzer.py`, and `Listener.py`.
  * Removed `_ring_band_peak` delay buffer from `Listener.py`, saving memory and eliminating per-frame copying overhead.
  * Updated [`tools/music_studio.py`](file:///c:/Users/Users/Desktop/vialact%C3%A9e/vialactee/tools/music_studio.py) to read `band_flux` instead of `band_peak`.

### 4. Mode Modernization
* **[MODIFY]** [`modes/Shining_stars_mode.py`](file:///c:/Users/Users/Desktop/vialact%C3%A9e/vialactee/modes/Shining_stars_mode.py):
  * Migrated from dead `band_peak` to speaker-aligned `self.listener.band_flux[band_index] > self.flux_threshold`.
  * Inlined the ignition hot path to eliminate call frame allocations at 60 FPS.
  * Pre-allocated a 256-entry random position pool within CPython's small-integer cache `[0, 255]`, guaranteeing **zero dynamic heap allocations**.
  * Switched to in-place `self.fade_to_black()`.
  * Added `get_settings_schema()` for GUI configuration.

---

## 3. Verification & Testing

* **Full Pytest Suite**:
  * **Command**: `python -m pytest`
  * **Result**: **129 passed, 5 deselected in 19.56s (100% pass rate)**.
* **Heavy MIR Benchmarks**:
  * **Command**: `python -m pytest -m benchmark`
  * **Result**: **5 passed in 10.45s**.
* **Governance & Axiom Compliance**:
  * `test_axiom_01_frame_budget.py`: PASSED (DSP runtime $\le 0.15\text{ms}$).
  * `test_axiom_02_zero_allocation.py`: PASSED (**0 heap bytes / 0 objects allocated** in 60 FPS update and render loops).
  * `test_axiom_07_code_governance.py`: PASSED (All line count ratchets strictly respected).
* **Synthetic Salience Tests**:
  * Synthetic drum groove: $R_{\text{salience}} > 0.65$ (PASSED).
  * Ambient pad chords: $R_{\text{salience}} < 0.25$ (PASSED).
  * Unmetered silence & stationary noise: $R_{\text{salience}} < 0.25$ (PASSED).
  * Lookahead timing lead: `live_rhythm_salience` leads `rhythm_salience` by exactly `lookahead_seconds` (PASSED).

---

## 4. Architecture Decisions & Trade-offs

1. **4-Pillar Salience vs HPSS**: Offline Librosa HPSS (`margin=2.0`) is non-causal and requires massive FFT convolutions unsuitable for 60 FPS embedded execution. Combining transient-to-total ratio, rolling crest factor, flywheel confidence, and pulse density yields a lightweight ($< 0.15\text{ms}$) causal metric that tracks ground-truth HPSS salience closely.
2. **Deprecating `band_peak` vs Re-implementing 32 Adaptive Trackers**: `band_peak` was a legacy binary trigger. Re-implementing 32 adaptive variance filters would waste CPU cycles and impose rigid thresholds. Continuous onset derivative flux (`band_flux`) and gain-normalized power (`asserved_fft_band`) provide far superior fidelity for visual modes.
3. **Small-Integer Cache for Axiom 2 Compliance**: In Python, integers $\le 256$ are pre-allocated singletons. Sizing random lookup pools to 256 (`& 255`) prevents CPython from allocating new integer objects on the heap during 60 FPS indexing loops.

---

## 5. Pitfalls & Lessons Learned

* **Cold-Start Step Transients on Noise**: Starting unmetered noise from a fresh analyzer reset created a large frame 0 derivative ($dE \approx 9.0$) that lingered in the 3-second crest buffer, falsely inflating salience. Ensuring proper baseline warmup or checking pulse consensus prevents initial false triggers.
* **Lookahead vs Speaker Timing**: Any feature evaluated inside `MultiBandOnsetAudioAnalyzer` operates at $T_{\text{lookahead}}$ (+5s in future) unless read through offset indexing or delay buffers in `Listener.py`. Modes must always consume speaker-aligned features from `Listener.py` unless intentionally anticipating drops.

---

## 6. Open Items & Next Steps

1. **Implement Flagship Rhythmic Modes**:
   * `Dual_nature_mode`: Flagship mode continuously morphing between a quantized rhythmic drum lattice and a fluid 12-TET harmonic watercolor based on `rhythm_salience`.
   * `Drum_nexus_mode`: Multi-instrument spatial percussion (Kick expanding from center, Snare snapping inward from edges, Hi-hats twinkling).
   * `Anticipation_drop_mode`: Exploiting lookahead $\Delta R$ to build visual tension before drops.
2. **Modernize Legacy Modes**:
   * Update [`modes/Metronome_mode.py`](file:///c:/Users/Users/Desktop/vialact%C3%A9e/vialactee/modes/Metronome_mode.py) and [`modes/Hyper_strobe_mode.py`](file:///c:/Users/Users/Desktop/vialact%C3%A9e/vialactee/modes/Hyper_strobe_mode.py) to gate strobes behind `rhythm_salience` and `is_real_beat`.
   * Refactor 9 modes accessing private `_delayed_asserved_fft_band` to use public `asserved_fft_band`.
