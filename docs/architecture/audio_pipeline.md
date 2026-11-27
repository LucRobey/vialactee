# Audio Pipeline & Feature Extraction Architecture

> **Location:** `docs/architecture/audio_pipeline.md` (Tier 1 Canonical Specification)  
> **Source Directory:** [`music/`](../../music/) (Front Door: [`music/api.py`](../../music/api.py), Contract: [`docs/contracts/music_analyzer_contract.md`](../contracts/music_analyzer_contract.md))  
> **Audio Connector:** [`connectors/Local_Microphone.py`](../../connectors/Local_Microphone.py)  
> **Enforcing Axioms:** [AXIOM-01](../axioms/AXIOM-01_FRAME_BUDGET.md), [AXIOM-02](../axioms/AXIOM-02_ZERO_ALLOCATION.md), [AXIOM-05](../axioms/AXIOM-05_LOOKAHEAD_SYNC.md), [AXIOM-09](../axioms/AXIOM-09_PLATFORM_AGNOSTIC_DSP.md)

---

## 1. Pipeline Overview

The audio pipeline transforms raw acoustic PCM stream data into mathematically structured, frequency-separated energy features for both visual animation modes and rhythm analysis.

```mermaid
graph LR
    PCM["Raw PCM Stream<br/>(44.1 kHz, Mono/Stereo)"] --> FFT["Vectorized rFFT<br/>(np.fft.rfft, 4096 pts)"]
    FFT --> DualMel["Dual-Resolution Mel Filterbanks"]
    DualMel --> Bands16["16 Mel Bands<br/>(Visual Modes)"]
    DualMel --> Bands32["32 Mel Bands<br/>(Rhythm Onsets)"]
    FFT --> Chroma["12-Note Chromagram<br/>(Pitch Analysis)"]
    Bands16 --> ADSR["Vectorized ADSR Envelopes<br/>(Attack/Decay Smoothing)"]
    ADSR --> DelayQueue["5.0s Lookahead Delay Queue<br/>(Listener Facade)"]
    DelayQueue --> VisualModes["Visual Modes (Segment.rgb_list)"]
    Bands32 --> MultiBand["DyadicMetricalAudioAnalyzer (extends MultiBandOnsetAudioAnalyzer)"]
```

### 1.1 Who Advances the Analyzer: the Audio, Never the Display Loop

The rhythm analyzers count time in ticks of 1/60 s (`odf_fps = 60.0`): their memory of the last seconds, their tempo templates and the place of each beat assume exactly 60 ticks per second of music. The display loop ([`core/Mode_master.py`](../../core/Mode_master.py)) runs at `target_fps` (30) and must not be what ticks them.

* **Audio file** ([`connectors/Local_AudioFile.py`](../../connectors/Local_AudioFile.py)): `advance_ingest_frame` makes one tick (`process_raw_audio` + `listener.update(fixed_dt=1/60)`) per 735 samples of playback.
* **Live sound: Spotify, aux, microphone** ([`connectors/Local_Microphone.py`](../../connectors/Local_Microphone.py)): `step_analyzer` makes one tick per 735 samples received from the sound card, on the window ending at that sample, and adds the audio received after the window to `dynamic_audio_latency`.
* Both set `listener.is_externally_clocked = True`, which tells `Mode_master` not to call `listener.update()` itself. When no connector clocks the listener (no audio device), `Mode_master` ticks it once per loop.

Until 2026-11-27 the live connector left the ticking to the display loop; measured offline on 20 tracks, beats scored 22 instead of 77 (`research/scoreboard/runs/live_path/LIVE_PATH.md`). Guarded by `tests/test_local_microphone_clock.py`.

One-frame signals (`is_beat`, `is_real_beat`, `is_dropped_beat`, the structural change flags, `context.is_drop_impact`, the event slots of `listener.signals`) are raised for a single 1/60 s tick. A 30 FPS reader would see about half of them, so the `Listener` holds them: the display loop calls `listener.begin_display_frame()` once per frame, before the modes draw, and each event is then visible for exactly one display frame (contract §1.1, `music/MusicSignals.py` `DisplayHold`, `tests/test_listener_display_hold.py`).

---

## 2. Ingestion & Dual-Resolution Mel Filterbanks

Implemented in `music/AudioIngestion.py`:
1. **Windowing & FFT:**
   - Real FFT (`np.fft.rfft`) computed on 4096-sample audio frames (`buffer_size = 4096`, yielding 2049 frequency bins) with Hanning windowing.
   - Vectorized matrix multiplications map power spectrum bins into Mel frequency bins.
2. **Dual-Resolution Mel Filterbanks:**
   - **16 Bands (`fft_band_values`):** Default visual Mel filterbank fed into lighting modes in `modes/` (Sub-bass through Air).
   - **32 Bands (`multiband_fft_values`):** Fed into `DyadicMetricalAudioAnalyzer` (via its `MultiBandOnsetAudioAnalyzer` parent) to isolate fine-grained transients:
     - Sub-bass: 20–80 Hz
     - Kick fundamental: 60–120 Hz
     - Snare body and crack: 200–4000 Hz
     - Hi-hat shimmer: 8–16 kHz
3. **12-Tone Chromagram:**
   - Pre-computed pitch matrix maps spectral bins ($f > 30\text{ Hz}$) to the 12 chromatic semitones (C, C#, D, ..., B), smoothed with fast-attack/slow-release ADSR (`smoothed_chroma_values`).
   - Exposed on `Listener` for pitch-aware consumers and developer studio visualization (`music_studio.py`, `mode_studio.py`).

---

## 3. The 5.0-Second Lookahead Delay Queue

Implemented in `music/Listener.py`:
- Ingested audio is held in a 5.0-second FIFO circular queue.
- Rhythm tracking and novelty detection operate on the incoming live head of the audio ($T_{\text{ingest}}$).
- Visual animations receive the delayed audio features ($T_{\text{ingest}} - 5.0\text{ s}$), aligning visual animations with physical speaker output cone arrival time ($T_{\text{speaker}}$).
- Adheres strictly to **AXIOM-05 (Audio-Visual Latency Bound $< 50\text{ ms}$)**.

---

## 4. Sealed Sector Modules (`music/`)

`music/` is a sealed sector governed by [`docs/contracts/music_analyzer_contract.md`](../contracts/music_analyzer_contract.md) and enforced by `tests/governance/test_music_isolation.py`. Production code outside `music/` imports **only** from [`music.api`](../../music/api.py).

| Module | Role |
| :--- | :--- |
| [`music/api.py`](../../music/api.py) | **Front Door:** Re-exports `Listener`, `ANALYZER_REGISTRY`, `DEFAULT_ANALYZER_MODEL`, `resolve_analyzer_class`, `MusicalScene`, `MusicalContextEngine`, `ListenerProtocol`, and `MusicalContextProtocol`. |
| [`music/Listener.py`](../../music/Listener.py) | Lookahead delay ring buffer + speaker-time facade + `ANALYZER_REGISTRY`. |
| [`music/AudioIngestion.py`](../../music/AudioIngestion.py) | Vectorized 4096-pt rFFT, 16-band & 32-band Mel filterbanks, 12-bin chromagram, ADSR & GM/LM normalization. |
| [`music/BaseAudioAnalyzer.py`](../../music/BaseAudioAnalyzer.py) | Abstract base contract for all rhythm analyzers. |
| [`music/MusicSignals.py`](../../music/MusicSignals.py) | Truth-mirrored signal record (`listener.signals`): one slot per value of the source of truth, `None` until produced. |
| [`music/DyadicMetricalAudioAnalyzer.py`](../../music/DyadicMetricalAudioAnalyzer.py) | **Production default** (`DEFAULT_ANALYZER_MODEL`): dyadic metrical hierarchy + causal sub-pulse arbiter on top of the 32-band engine. |
| [`music/MultiBandOnsetAudioAnalyzer.py`](../../music/MultiBandOnsetAudioAnalyzer.py) | 32-band 4-stream onset engine (`kick`, `snare`, `hat`, `mid`) + Anticipation Flywheel (stable fallback / parent engine). |
| [`music/AudioAnalyzer.py`](../../music/AudioAnalyzer.py) | Legacy single-ODF baseline analyzer. |
| [`music/comb_kernels.py`](../../music/comb_kernels.py) | Compiled NumPy pulse-template bank for Pearson tempo correlation. |
| [`music/StructuralNoveltyDetector.py`](../../music/StructuralNoveltyDetector.py) | STM/LTM structural novelty, verse/chorus change, and song-cut detection. |
| [`music/MusicalContextEngine.py`](../../music/MusicalContextEngine.py) | 3-tier visual conductor synthesizing raw DSP into `MusicalContext` (`energy`, `tension`, `scene`, badges). |
| [`music/RhythmConfig.py`](../../music/RhythmConfig.py) | Centralized DSP and flywheel constants. |
