# AXIOM-08: Scientific Clean-Room Zero-Regression Gate

**Tier:** Tier 0 (Untouchable Golden Axiom)  
**Status:** Inviolable Law  
**Enforcement:** `research/benchmarks/`, `research/LEADERBOARD.md`  

---

## 1. Specification

1. **Clean-Room Benchmark Immutability:**
   Ground truth audio tracks, beat annotation files (`.beats.txt`), and scoring algorithms residing in `research/benchmarks/ground_truth/` are **immutable reference assets**.
   - No engineer, researcher, or AI agent may edit, trim, or adjust ground truth annotations to make a candidate rhythm algorithm score higher.
2. **Production Promotion Gate:**
   No candidate beat tracking model or DSP enhancement may be promoted from `research/experiments/` into `core/` unless it passes the strict two-factor gate:
   - **Zero F1 Regression:** Achieves $\Delta \text{F1@50ms} \ge 0.0\%$ and $\Delta \text{F1@70ms} \ge 0.0\%$ compared to the current production baseline across the synthetic test suite.
   - **Real-Time Frame Budget:** Average per-frame computation time remains $\le \mathbf{3.0\text{ ms}}$ on ARM Cortex-A72 ($< 1.0\text{ ms}$ on desktop x86_64).
3. **Experiment Registry Mandate:**
   Every experimental candidate tested must be permanently logged in `research/LEADERBOARD.md` with:
   - Candidate model name and git commit hash.
   - Evaluation metrics: `F1@50ms`, `F1@70ms`, `CMLt`, `AMLt`, Phase Jitter (ms), Avg Frame Compute (ms).
   - Mathematical innovation summary and pass/fail verdict.

---

## 2. Evaluation Metrics Definition

- **F1@50ms:** Harmonic mean of precision and recall for beat detections within $\pm 50.0\text{ ms}$ of ground truth.
- **CMLt (Correct Metrical Level with Continuity):** Percentage of track tracked at the correct tempo octave with continuous phase alignment.
- **AMLt (Any Metrical Level with Continuity):** Tracks tempo octave multiples (half-time / double-time allowed).
- **Phase Jitter:** Standard deviation of beat timing error against true clicks.

---

## 3. Violation Conditions

- Modifying reference ground truth `.beats.txt` annotations.
- Promoting an algorithm that improves tempo accuracy at the expense of exceeding the 3.0 ms per-frame compute cap.
- Replacing the production model without logging complete benchmark results in the experiment registry.
