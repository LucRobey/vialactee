# AGENT HANDOFF: Vialactée Music Analysis, Benchmark & Ground Truth Engine

> **Date:** September 5, 2026  
> **Repository:** `vialactee`  
> **Domain:** Audio DSP, Real-time Beat Tracking, Anticipation Flywheel ("Oracle"), Evaluation Benchmark Harness  
> **Current Leaderboard Macro F1@50ms:** **92.0%** (Synthetic Suite)

---

## 1. Executive Summary & Objective

The user is building **Vialactée**, an interactive LED chandelier whose lighting patterns react to music in real-time.
The user was dissatisfied with past exploratory research in `playground/` because:
1. There were no objective, fixed metrics to determine if an algorithm was actually improving.
2. Evaluated models often claimed "flawless" BPM accuracy (e.g. 0.2% BPM error on *Palladium*), yet in reality had terrible beat tracking (F1@50ms of 6.1%) due to double-trigger chatter and phase misalignment.
3. The user wants to radically change the math logic of `AudioAnalyzer.py` in the future while keeping the research, evaluation harness, and ground truth **fixed, reproducible, and immutable**.
4. The system must capture rich telemetry (larger than human capacity) formatted into semantic **Failure Episodes** for AI agents to analyze failure patterns.

---

## 2. What Was Accomplished (Current Architecture)

### A. Universal Model Contract
- **[`core/BaseAudioAnalyzer.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/BaseAudioAnalyzer.py)**: Universal abstract base class defining 6 functional domains:
  1. *Execution & Clocking*: `update()`, `reset()`, `lookahead_seconds`, `hardware_latency`.
  2. *Rhythm & Metronome*: `bpm`, `beat_phase`, `is_beat`, `is_real_beat`, `is_dropped_beat`, `beat_confidence`, `flywheel_status`, `is_downbeat`.
  3. *Spectral Dynamics*: `band_flux`, `band_peak`, `spectral_centroid`.
  4. *Macro-Structure*: `is_song_change`, `is_verse_chorus_change`, `asserved_novelty`, `combined_novelty`.
  5. *Semantics*: `current_beat_tag`, `vocals_present`, `musical_key`.
  6. *AI Telemetry Hook*: `capture_frame_telemetry()`, `get_model_metadata()`.
- **[`core/AudioAnalyzer.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/AudioAnalyzer.py)**: Production model refactored to inherit from `BaseAudioAnalyzer`. 100% backwards-compatible with `core/Listener.py` (all 22 unit tests pass).

### B. Immutable Benchmark & Scorecard Engine
- **[`benchmarks/engine/evaluator.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/benchmarks/engine/evaluator.py)**:
  - 60 FPS headless simulation loop.
  - Computes standardized MIR metrics via `mir_eval`: `F1@50ms` (visual perception threshold), `F1@70ms`, `CMLt`, `AMLt`, `UpbeatGap` ($AMLt - CMLt$), Phase Bias, Phase Jitter, and CPU time per frame.
  - Supports pre-cached `.npz` float32 audio arrays in `assets/musics/mp3_files/librosa/` to bypass slow Windows MP3 decoding.
- **[`benchmarks/engine/episode_slicer.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/benchmarks/engine/episode_slicer.py)**:
  - Slices 5–10s anomaly windows into structured JSON (`failure_episodes.json`) for AI agents:
    - `PHASE_INVERSION_UPBEAT` (180° offbeat traps).
    - `GHOST_BEAT_BURST` (hallucinating beats during silence instead of coasting).
    - `HIGH_PHASE_JITTER` (unstable phase snapping).
- **[`benchmarks/run_benchmark.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/benchmarks/run_benchmark.py)**: CLI runner with formatted terminal scorecard.
- **[`benchmarks/compare_runs.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/benchmarks/compare_runs.py)**: Delta comparator between baseline and candidate runs.

### C. Visual Diagnostics Suite
- **[`benchmarks/plot_diagnostics.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/benchmarks/plot_diagnostics.py)**:
  - Multi-panel visual generator rendering:
    1. Audio Waveform with True Beats (green solid lines) vs Model Beats (magenta dashed lines).
    2. Spectral Flux (ODF) spikes.
    3. Continuous Flywheel Phase $\phi(t) \in [0, 1)$ sawtooth ramp.
    4. Estimated BPM over time with shaded Failure Episode highlight zones.
  - Outputs high-res figures to `experiments/plots/` (e.g. `synthetic_step_tempo_diagnostic.png`, `Palladium_diagnostic.png`).

### D. Experiment Ledger & Leaderboard
- **[`experiments/LEADERBOARD.md`](file:///c:/Users/Users/Desktop/vialactée/vialactee/experiments/LEADERBOARD.md)**: Persistent markdown table tracking Git commit, model name, F1@50ms, CMLt, AMLt, Jitter, and latency.
- **[`experiments/runs/`](file:///c:/Users/Users/Desktop/vialactée/vialactee/experiments/runs/)**: Versioned run folders containing `manifest.json`, `scorecard.json`, `failure_episodes.json`, and `telemetry.npz`.

---

## 3. Exact State of Ground Truth (Tiers 1, 2, 3)

The ground truth hierarchy is strictly separated into 3 tiers:

### Tier 1: Synthetic "Clean Room" Tracks (Active & Verified)
- **Location:** `benchmarks/ground_truth/synthetic_cache/` (8 WAVs + 8 `.beats.txt`)
- **Origin:** Generated from scratch by `benchmarks/ground_truth/synthetic/generator.py`.
- **Nature:** 100% mathematical certainty. Beat timestamps are known down to 0.0001s.
- **Scenarios covered:**
  - `synthetic_click_120bpm`, `synthetic_click_85bpm`, `synthetic_click_140bpm` (constant metronomes).
  - `synthetic_step_tempo` (instant jump 120 $\to$ 140 BPM).
  - `synthetic_breakdown_dropout` (16 bars drums $\to$ 8 bars silence $\to$ drums return).
  - `synthetic_tempo_drift_accel` (continuous linear ramp 100 $\to$ 130 BPM over 30s).
  - `synthetic_syncopated_reggae` (kicks on downbeats, loud hats on offbeats).
  - `synthetic_polyrhythm_3_against_2` (triplets against quarter notes).

### Tier 2: Neural Deep Learning Ground Truth (Active & Verified Across User Library)
- **Location:** `benchmarks/ground_truth/neural/` (contains `.beats.txt`, `.downbeats.txt`, and `.meta.json`)
- **Generator:** `benchmarks/ground_truth/extract_neural_reference.py`
- **Engine:** **BeatNet 1.1.1** (Heydari et al., ISMIR 2021) — 1D/2D CRNN acoustic model + Dynamic Bayesian Network (DBN) inference.
- **Windows / No-MSVC Acceleration:**
  - Standard `madmom` fails on Windows without MSVC C++. We patched `madmom-0.16.1` using an AST-validated transpiler to convert Cython (`hmm.pyx`, `comb_filters.pyx`, `beats_crf.pyx`) into pure Python, accelerating the Viterbi search loop via `@numba.jit(nopython=True, fastmath=True)`.
  - Installed official binary wheels for `pyaudio`.
  - Offline inference runs in ~3-12s per full track on CPU.
- **Nature:**
  - **No rigid periodic grid**: Captures real human microtiming, swing, tempo drift, downbeats (measure starts: e.g. 4/4 vs 3/4 time signatures), and expressive variations.
  - Generates `.downbeats.txt` tracking bar boundaries (e.g. 304 beats / 101 downbeats on 3/4 meter *Chanson pour l'auvergnat*).
- **Benchmarking Real-World Traps:**
  - Exposed genuine tracking failure episodes in `AudioAnalyzer`, such as 180° upbeat phase locking on Queen's *Another One Bites The Dust* (Upbeat Gap: 0.21) and ghost beats during quiet sections.

### Tier 3: Standard Academic Datasets (Ballroom Benchmark Fully Integrated)
- **Location:** `benchmarks/ground_truth/academic/loader.py` and `benchmarks/ground_truth/academic/data/ballroom/`
- **Origin:** University Pompeu Fabra (MTG) & CPJKU ground-truth annotations (Krebs, Böck et al.) via `mirdata`.
- **Dataset Chosen:** **Ballroom** (698 tracks, 8 ballroom dance styles: Cha-cha-cha, Jive, Quickstep, Rumba, Samba, Tango, Viennese Waltz, Slow Waltz).
- **Status:**
  - All 698 track beat annotations and metadata index downloaded into local cache.
  - Sample exported references in `benchmarks/ground_truth/academic/ballroom/`.
  - To download full audio archive (~1.35GB audio WAVs):
    `python -m benchmarks.ground_truth.academic.loader --dataset ballroom --download-audio`

---

## 4. Key Algorithmic Fixes in `AudioAnalyzer.py`

Benchmark failure slicing revealed three critical flaws that were resolved:

1. **Double-Trigger Chatter Bug:**
   - *Cause:* Phase soft-snap was snapping phase backwards across the $0.0$ boundary into $[0.85, 1.0)$ immediately following a beat, causing `_advance_flywheel` to fire a duplicate beat on the very next frame (16.6ms apart).
   - *Fix:*
     - Added **Backward Wrap Clamp** in `_run_oracle_sweep`: if $\phi < 0.25$, phase adjustment cannot wrap backwards across 0.
     - Added **Refractory Period Lockout** in `_advance_flywheel`: beats cannot fire within $T_{\min} = \max(0.18\text{s}, 0.40 \times 60/\text{BPM})$.
2. **Breakdown Dropout Hallucination:**
   - *Cause:* `rolling_flux_baseline` decayed toward zero during silence, allowing tiny background hiss to pass the ratio test and mark beats as `is_real_beat = True`.
   - *Fix:* Changed condition so transient energy must exceed BOTH the baseline ratio AND the absolute energy floor (`real_beat_energy_floor = 5.0`). The metronome continues freewheeling on inertia (`is_beat = True`), but kick flash flags are silenced (`is_real_beat = False`, `is_dropped_beat = True`).
3. **Simulation Latency Alignment:**
   - *Cause:* Production chandelier uses `fakeDelay = 5.0s` so the listener buffers audio for 5 seconds to look into the future. In headless simulation, the audio file is fed directly. Having `fakeDelay = 5.0` caused the analyzer to back-project phase by 5 seconds, causing phase shifts on all non-120 BPM tempos (e.g. 140 BPM shifted by 0.66 beats $\to$ 0% F1).
   - *Fix:* Set `"fakeDelay": 0.0` in `evaluator.py` for simulation mode.

---

## 5. Performance Scorecard

### Synthetic Benchmark Suite (`--suite synthetic`)

| Metric | Baseline | Fixed AudioAnalyzer | Delta |
| :--- | :---: | :---: | :---: |
| **Macro F1@50ms** | 63.2% | **92.0%** | **+28.8%** 🚀 |
| **Macro CMLt** | 69.5% | **91.6%** | **+22.1%** 🚀 |
| **Macro AMLt** | 81.6% | **91.6%** | **+10.0%** |
| **Mean Phase Jitter** | 40.3ms | **17.6ms** | **-56% reduction** |
| **Upbeat Gap ($AMLt - CMLt$)** | 0.12 | **0.00** | **Eliminated 180° Inversion** |
| **Failure Episodes** | 11 | **1** | Only step-tempo jitter remaining |
| **CPU Time per Frame** | 1.86ms | **1.90ms** | $<3\text{ms}$ on Raspberry Pi |

---

## 6. Environment & Platform Constraints

- **OS:** Windows 10/11. Shell: PowerShell.
- **Python:** Python 3.10.11 (`python`).
- **Terminal Encoding:** Windows default console is `cp1252`. All benchmark scripts and visualizers **must** include:
  ```python
  if hasattr(sys.stdout, "reconfigure"):
      sys.stdout.reconfigure(encoding="utf-8", errors="replace")
  ```
- **C++ Compilers:** No MSVC C++ build tools installed. **Do NOT attempt to pip install `madmom` from source** (it will fail C++ compilation). Use pure Python / NumPy / SciPy / Numba / `mir_eval` / `mirdata`.
- **Audio Loading Speed:** Decoding MP3s via `librosa`/`torchaudio` on Windows can take 20s. Always prefer using the pre-cached `.npz` arrays in `assets/musics/mp3_files/librosa/` (loads in 0.05s).

---

## 7. Immediate Next Steps / Decision Fork for Incoming Agent

The user previously asked about the ground truth data. Here are the immediate options to discuss with the user:

1. **Option A: Download Tier 3 Academic MIR Dataset (Recommended for literature benchmarks)**
   - Run `python -m benchmarks.ground_truth.academic.loader --dataset ballroom --download`.
   - Run benchmark on Ballroom tracks to measure against published international algorithms.
2. **Option B: Develop Next-Gen Experimental Models (`experiments/models/`)**
   - Create alternative tracking architectures (e.g. Multi-band Onset Weighting, Kalman Filter Phase Tracker, Dual-Band Judge).
   - Evaluate against synthetic and natural suites using `python -m benchmarks.run_benchmark --model <Name> --save-run`.
   - Use `python -m benchmarks.compare_runs` to verify improvement over the 92.0% baseline.
3. **Option C: Acoustic / Live Track Non-Quantized Ground Truth**
   - For tracks with human tempo drift (*Bohemian Rhapsody*, live concerts), create a tool or human annotation protocol to mark non-quantized beats.
