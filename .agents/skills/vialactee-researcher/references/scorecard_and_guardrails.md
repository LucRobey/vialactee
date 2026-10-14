# Researcher Reference: Scorecard Schema, Exit Codes & Windows Command Safety

> Loaded on demand from [`SKILL.md`](../SKILL.md).

- **Windows / PowerShell Command Safety:**
  - **Never use multi-statement inline `python -c "..."` commands** in PowerShell. Nested single/double quotes, f-strings, and semicolons get stripped by PowerShell, causing `SyntaxError: unterminated string literal` or `NameError: name 'np' is not defined`.
  - Instead, write a clean Python script to `<appDataDir>\brain\<conversation-id>/scratch/<name>.py` using `write_to_file`, and run it with `python <path>`.
  - Always ensure UTF-8 output encoding in Python scripts (`import sys; sys.stdout.reconfigure(encoding='utf-8')`) to avoid `UnicodeEncodeError: 'charmap'` with mathematical/Greek characters (`≤`, `Δ`, `•`).
  - Prefer using existing CLI tools (`run_benchmark`, `diagnose_track`, `run_ablation`) over writing ad-hoc scratch scripts.
- **Scorecard Dictionary Schema:** When reading programmatically from `scorecard.json` or evaluation results, use these exact canonical keys:
  - `f1_50ms` (float, e.g. 0.920 for 92.0%)
  - `f1_70ms` (float)
  - `f1_salient_50ms` (float, Rhythmic Salience-Weighted F1: weights precision and recall by beat importance ground truth)
  - `cmlt` (float, Correct Metric Level Total)
  - `amlt` (float, Any Metric Level Total)
  - `upbeat_gap` (float, $AMLt - CMLt$; $>0.10$ indicates 180° upbeat locking)
  - `mean_phase_bias_ms` (float, ms phase offset)
  - `phase_jitter_ms` (float, ms phase standard deviation)
  - `bpm_trust_calibration` (float, Pearson correlation between model's live `confidence_score` and ground truth salience curve $S(t)$)
  - `avg_frame_time_ms` (float, CPU latency per frame)
  - `crashed` (bool, true if simulation threw an exception)
- **Benchmark Exit Codes:**
  - `compare_runs.py` exits with code **0** when candidate is improved or neutral.
  - It exits with code **1** when a regression is detected ($\Delta \text{F1} < -0.5\%$). This is a **domain signal** (regression detected), NOT an execution crash or tool error! You can also pass `--allow-regression` to force exit code 0.
