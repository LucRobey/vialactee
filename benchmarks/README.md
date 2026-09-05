# Vialactée Benchmark & Evaluation Suite (`/benchmarks/`)

The `benchmarks/` directory houses the immutable evaluation harness for beat tracking, rhythm analysis, and structural event detection. It provides a permanent, reproducible ground truth hierarchy and standardized scorecard metrics across all model iterations.

---

## Architecture Overview

```
benchmarks/
├── ground_truth/
│   ├── synthetic/
│   │   └── generator.py            ← Tier 1: 8 exact mathematical clean-room stress tests
│   ├── synthetic_cache/            ← Generated WAV audio and .beats.txt ground truth
│   ├── natural/                    ← Tier 2: 28 Studio-Quantized .beats.txt references
│   ├── build_quantized_reference.py← Derives sub-ms downbeat alignment from verified BPMs
│   └── academic/
│       └── loader.py               ← Tier 3: mirdata integration (Ballroom, Beatles)
├── engine/
│   ├── evaluator.py                ← 60 FPS headless simulation & mir_eval scorecard
│   └── episode_slicer.py           ← AI semantic failure episode extraction
├── run_benchmark.py                ← CLI runner with terminal scorecard output
├── compare_runs.py                 ← Delta comparison tool between baseline & candidate
└── plot_diagnostics.py             ← 4-tier visual diagnostic inspection plot generator
```

---

## The 3-Tier Source of Truth Hierarchy

To ensure evaluations are mathematically sound, ground truth is structured into three tiers:

### Tier 1: Synthetic "Clean Room" Tracks (`benchmarks/ground_truth/synthetic_cache/`)
Synthesized audio waveforms with exact millisecond mathematical timestamps:
1. `synthetic_click_120bpm`: Constant 120.0 BPM 4/4 metronome kick.
2. `synthetic_click_85bpm`: Slow 85.0 BPM ballad/hip-hop tempo.
3. `synthetic_click_140bpm`: Fast 140.0 BPM techno/EDM tempo.
4. `synthetic_step_tempo`: Instantaneous tempo step 120 $\to$ 140 BPM (measures re-lock latency).
5. `synthetic_breakdown_dropout`: 16 bars drums $\to$ 8 bars silence $\to$ drums return (measures coasting).
6. `synthetic_tempo_drift_accel`: Continuous linear ramp 100 $\to$ 130 BPM over 30s (measures drummer drift).
7. `synthetic_syncopated_reggae`: Kicks on downbeats, loud hats on offbeats (upbeat resistance).
8. `synthetic_polyrhythm_3_against_2`: 3-against-2 cross-rhythms (sub-harmonic trap resistance).

*Regenerate synthetic tracks:*
```bash
python -m benchmarks.ground_truth.synthetic.generator
```

### Tier 2: Studio-Quantized References (`benchmarks/ground_truth/natural/`)
For studio-recorded music with quartz-crystal tempos (from `assets/musics/mp3_files/bpm_database.json`):
* Evaluates cross-correlation $S(t_0) = \sum \text{onset}(t_0 + n \cdot T)$ at 1ms resolution to determine the exact downbeat offset $t_0^*$.
* Generates periodic grids $t_n = t_0^* + n \cdot (60/\text{BPM})$.
* Contains 28 verified references (e.g. *Palladium*, *Another One Bites The Dust*, *Pumped Up Kicks*, *Stayin' Alive*, *Boogie Wonderland*).

*Regenerate quantized references:*
```bash
python -m benchmarks.ground_truth.build_quantized_reference
```

### Tier 3: Academic MIR Datasets (`benchmarks/ground_truth/academic/`)
* Standard international benchmarks (e.g., Ballroom, Beatles) loaded via `mirdata`.
* Use `loader.py` to inspect or download datasets:
```bash
python -m benchmarks.ground_truth.academic.loader --dataset ballroom --download
```

---

## Standardized Evaluation Metrics

Evaluated using the `mir_eval` library:
* **F1@50ms**: Harmonic mean of precision and recall within a tight 50ms tolerance window (human visual synchronization perception limit for LEDs).
* **F1@70ms**: Standard MIREX beat tracking tolerance window.
* **CMLt (Correct Metric Level Total)**: Proportion of track tracked correctly at the exact metric tempo and phase.
* **AMLt (Any Metric Level Total)**: Proportion of track tracked at acceptable metric levels (double-time, half-time, or offbeat).
* **Upbeat Gap ($AMLt - CMLt$)**: Measures phase inversion (when the tracker locks 180° out of phase on upbeats).
* **Phase Bias**: Mean timing offset $\mu_{\Delta t}$ in milliseconds (positive = lagging, negative = rushing).
* **Phase Jitter**: Timing standard deviation $\sigma_{\Delta t}$ in milliseconds (measures flywheel instability).
* **CPU Time (ms/frame)**: Execution time per frame (must remain $<16.6\text{ms}$ for 60 FPS real-time execution).

---

## CLI Usage

### Running a Benchmark
```bash
# Run on all synthetic tracks and save experiment
python -m benchmarks.run_benchmark --suite synthetic --save-run --name my_experiment

# Run on natural songs
python -m benchmarks.run_benchmark --suite natural --limit 5

# Run a specific experimental model
python -m benchmarks.run_benchmark --model MyNewModel --suite synthetic
```

### Comparing Two Runs
```bash
python -m benchmarks.compare_runs experiments/runs/RUN_BASELINE experiments/runs/RUN_CANDIDATE
```

### Generating Visual Diagnostics
```bash
# Generate visual diagnostic plot for a track
python -m benchmarks.plot_diagnostics --track synthetic_step_tempo

# Generate diagnostic plot focused on a specific time window
python -m benchmarks.plot_diagnostics --track Palladium --tmin 0.0 --tmax 15.0
```
Outputs high-resolution 4-panel figures into `experiments/plots/`.

---

## AI Agent Pattern Mining (`failure_episodes.json`)

When `--save-run` is invoked, `benchmarks/engine/episode_slicer.py` scans frame telemetry and slices 5–10s anomaly windows into `experiments/runs/<RUN_ID>/failure_episodes.json`:
* `PHASE_INVERSION_UPBEAT`: Consecutive runs where beats are shifted by 50% of the period.
* `GHOST_BEAT_BURST`: Runs where `is_real_beat = True` during sustained dropouts or silence.
* `HIGH_PHASE_JITTER`: Periods where timing standard deviation exceeds 25ms.

AI agents read this JSON directly to pinpoint algorithmic failure modes without human intervention.
