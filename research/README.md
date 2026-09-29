# Vialactée R&D Laboratory (`/research/`)

Welcome to the **Vialactée R&D Laboratory**. This directory houses all offline Music Information Retrieval (MIR) research, immutable benchmarking harnesses, ground-truth datasets, candidate models, and historical experiment ledgers.

---

## Architecture & Boundary

Vialactée is divided into two distinct domains:
1. **Live Embedded Runtime** (`/core`, `/modes`, `/hardware`, `/connectors`, `/config`):
   - Real-time execution at 60 FPS on Raspberry Pi or PC simulator.
   - Zero dependencies on heavy offline MIR packages (e.g. `mirdata`, `mir_eval`, `BeatNet`).
2. **Offline Research Laboratory** (`/research`):
   - Scientific evaluation, deterministic stress-testing, and automated experiment tracking.
   - Never deployed to the Raspberry Pi (can be safely excluded via `--exclude research/`).

---

## Directory Structure

```
research/
├── benchmarks/                      # Immutable Evaluation Harness & Ground Truth
│   ├── engine/                      # Standalone evaluation & failure episode slicer
│   │   ├── evaluator.py             # 60 FPS simulation runner, mir_eval & salience metrics
│   │   └── episode_slicer.py        # Anomaly window extraction for AI pattern mining
│   ├── ground_truth/                # Standardized evaluation data (3-tier hierarchy)
│   │   ├── synthetic/               # Algorithmic stress tracks (generator.py)
│   │   ├── synthetic_cache/         # Generated synthetic WAVs and .beats.txt
│   │   ├── neural/                  # BeatNet reference (.beats.txt, .downbeats.txt, .salience.npz)
│   │   ├── extract_beat_salience.py # Ground truth Beat Importance extractor (.salience.npz)
│   │   └── academic/                # mirdata loaders & annotations (Ballroom, etc.)
│   ├── run_benchmark.py             # Main CLI benchmark runner (F1@50ms, F1_Salient, TrustCal)
│   ├── plot_beat_salience.py        # Beat Importance & Rhythmic Salience Visualizer
│   ├── plot_diagnostics.py          # High-resolution 4-tier visual diagnostic plotter
│   ├── compare_runs.py              # Statistical run diffing & regression detector
│   ├── source_of_truth.md           # Guide on ground truth hierarchy & enrichment
│   └── README.md                    # Benchmark suite documentation
│
└── experiments/                     # Historical Ledger & Candidate Model Registry
    ├── LEADERBOARD.md               # Auto-updated scoreboard tracking all runs
    ├── models/                      # Candidate experimental model classes
    ├── plots/                       # Diagnostic inspection figures (.png)
    ├── salience_plots/              # Beat Importance visual dashboards (.png)
    ├── runs/                        # Versioned experiment snapshots (scorecard, telemetry)
    └── README.md                    # Experiment ledger & model authoring documentation
```

---

## Quickstart Commands

All commands are executed from the **repository root**:

### 1. Run Benchmarks
```powershell
# Run deterministic synthetic benchmark
python -m research.benchmarks.run_benchmark --suite synthetic

# Run benchmark and record experiment to ledger & LEADERBOARD.md
python -m research.benchmarks.run_benchmark --suite synthetic --save-run --name my_experiment

# Run academic Ballroom benchmark
python -m research.benchmarks.run_benchmark --suite academic --limit 10
```

### 2. Compare Experiment Runs
```powershell
python -m research.benchmarks.compare_runs research/experiments/runs/<RUN_A> research/experiments/runs/<RUN_B>
```

### 3. Visual Diagnostic Inspection
```powershell
# Render 4-panel diagnostic plot with failure episode highlights
python -m research.benchmarks.plot_diagnostics --track synthetic_step_tempo
python -m research.benchmarks.plot_diagnostics --track "Palladium"
```

### 4. Beat Importance & Rhythmic Salience Ground Truth
```powershell
# Plot continuous Beat Importance curve & priority zones for any track
python -m research.benchmarks.plot_beat_salience --track "Sweet Child O' Mine" --tmin 0 --tmax 60

# Compare with live model bpm_trust / confidence
python -m research.benchmarks.plot_beat_salience --track "Sweet Child O' Mine" --tmin 0 --tmax 60 --model CostasLoopAudioAnalyzer

# Extract/update .salience.npz ground truth for neural-core tracks
python -m research.benchmarks.ground_truth.extract_beat_salience --core-only
```

### 5. Manage Datasets
```powershell
# Check Ballroom dataset status
python -m research.benchmarks.ground_truth.academic.loader --dataset ballroom --status

# Extract neural references for new tracks
python -m research.benchmarks.ground_truth.extract_neural_reference --limit 5
```
