# Experiment Ledger & Model Registry (`/experiments/`)

The `experiments/` directory is the persistent research ledger for Vialactée. It tracks all historical algorithm runs, preserves immutable scorecard results, archives telemetry tensors for AI analysis, and hosts the automated leaderboard.

---

## Directory Structure

```
experiments/
├── LEADERBOARD.md                   ← Markdown scoreboard auto-updated on each benchmark run
├── models/                          ← Sandbox for candidate models inheriting BaseAudioAnalyzer
├── plots/                           ← Rendered visual diagnostic plots (.png)
└── runs/                            ← Versioned historical experiment packages
    └── RUN_<TIMESTAMP>_<MODEL>_<NAME>/
        ├── manifest.json            ← Git commit, model metadata, run arguments, macro summary
        ├── scorecard.json           ← Full per-track standardized MIR metrics
        ├── failure_episodes.json    ← Sliced 5-10s failure moments formatted for AI pattern mining
        └── telemetry.npz            ← Compressed frame-by-frame telemetry tensors
```

---

## Experiment Run Artifacts

Each `--save-run` execution creates an immutable directory inside `experiments/runs/` containing:

1. **`manifest.json`**:
   Metadata snapshot including execution timestamp, Git commit hash, model class name, benchmark suite, and macro average metrics (F1@50ms, CMLt, Jitter, CPU time).
2. **`scorecard.json`**:
   Full dictionary containing per-track evaluations (`f1_50ms`, `f1_70ms`, `cmlt`, `amlt`, `upbeat_gap`, `mean_phase_bias_ms`, `phase_jitter_ms`, `avg_frame_time_ms`).
3. **`failure_episodes.json`**:
   Structured JSON list of detected failure intervals (`PHASE_INVERSION_UPBEAT`, `GHOST_BEAT_BURST`, `HIGH_PHASE_JITTER`) with exact start/end timestamps, duration, and diagnostic summaries.
4. **`telemetry.npz`**:
   Compressed NumPy archives containing time series of `bpm`, `beat_phase`, `confidence`, `custom_flux`, and beat flags for every frame.

---

## How to Introduce a New Experimental Model

1. Create a new file in `experiments/models/` (e.g. `experiments/models/dual_judge_tracker.py`).
2. Subclass `BaseAudioAnalyzer` from `core.BaseAudioAnalyzer`:
   ```python
   from core.BaseAudioAnalyzer import BaseAudioAnalyzer
   from typing import Dict, Any

   class DualJudgeTracker(BaseAudioAnalyzer):
       def reset(self) -> None:
           ...
       def update(self, current_time: float, dt: float, fps_ratio: float) -> None:
           ...
       def capture_frame_telemetry(self) -> Dict[str, Any]:
           ...
   ```
3. Evaluate the model against the benchmark:
   ```bash
   python -m benchmarks.run_benchmark --model DualJudgeTracker --suite synthetic --save-run --name my_first_attempt
   ```
4. Compare against the baseline:
   ```bash
   python -m benchmarks.compare_runs experiments/runs/RUN_BASELINE experiments/runs/RUN_MY_ATTEMPT
   ```
5. If the candidate achieves a higher score without regressions, propose integrating the logic into `core/AudioAnalyzer.py`.
