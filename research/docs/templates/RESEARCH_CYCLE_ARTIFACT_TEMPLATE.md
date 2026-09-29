# 🧪 Research Cycle Log: Cycle [NUMBER] - [TOPIC]

**Date:** [YYYY-MM-DD]  
**Investigator:** Autonomous Rhythm Data Scientist & Audio DSP Engineer  
**Target Model:** `research/experiments/models/[CandidateModel].py`  
**Model Card:** `research/docs/models/[CandidateModel].md`  
**Baseline Run:** `research/experiments/runs/[BASELINE_RUN_ID]`  

---

## 1. Orientation & Literature Review

### Past Dead Ends & Baseline Scorecard
- **Baseline Macro F1@50ms:** [X.X%] | **CMLt:** [X.X%] | **AMLt:** [X.X%] | **Upbeat Gap:** [X.XX]
- **Key Failure Episodes Inspected:**
  - `[EPISODE_ID]`: [Track] ([t_start]s - [t_end]s) - [Failure Type] - [Notes]

### Musical Style & Taxonomy Analysis
- Identified failure correlations from `music_catalog.json`:
  - [e.g. Disco/Funk tracks suffering from 180° upbeat traps on high-frequency hi-hats]

---

## 2. Scientific Hypothesis & Approved Plan

### Implementation Plan & User Approval
- **Implementation Plan Artifact:** [`implementation_plan.md`](file:///C:/Users/Users/.gemini/antigravity/brain/[CONVERSATION_ID]/implementation_plan.md)
- **Approval Status:** Approved by User on [DATE/TIME]

### Problem Statement
[Describe why the current AudioAnalyzer logic fails mathematically or rhythmically.]

### Proposed DSP / Mathematical Formulation
[Detail equations, Mel band weighting, phase damping, or threshold modifications.]
$$\text{e.g. } \phi_{\text{new}} = \dots$$

### Expected Quantitative Impact
- Target F1 delta: $\ge +0.0\%$ on synthetic, $+X.X\%$ on real-world.
- Upbeat Gap reduction: $< 0.10$.

---

## 3. Candidate Architecture & Implementation

### Code Changes
- **Model File:** `research/experiments/models/[CandidateModel].py`
- **Subclassed from:** `BaseAudioAnalyzer` (or `AudioAnalyzer`)

### Real-Time Embedded & Memory Compliance Check
- [x] **Zero Dynamic Heap Allocation:** All state buffers pre-allocated in `__init__()`.
- [x] **Pure Vectorization:** All per-frame calculations use NumPy vectorized operations.
- [x] **RPi 4/5 CPU Frame Budget:** Average latency $\le 3.0\text{ms}$ per frame at 60 FPS.

---

## 4. Clean-Room Synthetic Verification (`--suite synthetic`)

```bash
python -m research.benchmarks.run_benchmark --model [CandidateModel] --suite synthetic --save-run --name cycle[N]_synth
```

| Track Name | Baseline F1@50ms | Candidate F1@50ms | Delta | Status |
| :--- | :---: | :---: | :---: | :---: |
| synthetic_click_120bpm | 99.2% | [X.X%] | [+0.0%] | Pass |
| synthetic_click_140bpm | 97.8% | [X.X%] | [+0.0%] | Pass |
| synthetic_click_85bpm | 94.1% | [X.X%] | [+0.0%] | Pass |
| synthetic_step_tempo | 59.0% | [X.X%] | [+0.0%] | Pass |
| synthetic_breakdown_dropout | 92.8% | [X.X%] | [+0.0%] | Pass |
| synthetic_tempo_drift_accel | 95.7% | [X.X%] | [+0.0%] | Pass |
| synthetic_syncopated_reggae | 98.3% | [X.X%] | [+0.0%] | Pass |
| synthetic_polyrhythm_3_against_2 | 99.2% | [X.X%] | [+0.0%] | Pass |
| **Synthetic Macro Average** | **92.0%** | **[X.X%]** | **[+X.X%]** | **[PASS / FAIL]** |

---

## 5. Real-World Benchmark Results (`--suite neural-core`)

```bash
python -m research.benchmarks.run_benchmark --model [CandidateModel] --suite neural-core --save-run --name cycle[N]_candidate
```

### Macro Metrics
- **Candidate F1@50ms:** [X.X%] ($\Delta$ [+/-X.X%])
- **CMLt:** [X.X%] ($\Delta$ [+/-X.X%])
- **AMLt:** [X.X%] ($\Delta$ [+/-X.X%])
- **Upbeat Gap:** [X.XX] ($\Delta$ [+/-X.XX])
- **Avg Phase Jitter:** [X.Xms] ($\Delta$ [+/-X.Xms])
- **CPU Time / Frame:** [X.XXms]

### Genre Performance Breakdown
| Genre | Tracks | Baseline F1 | Candidate F1 | Delta |
| :--- | :---: | :---: | :---: | :---: |
| Chanson Française / Acoustic | 1 | [X.X%] | [X.X%] | [+/-X.X%] |
| Classic / Hard Rock | 2 | [X.X%] | [X.X%] | [+/-X.X%] |
| Disco / Funk | 3 | [X.X%] | [X.X%] | [+/-X.X%] |
| Electronic / Synthwave | 1 | [X.X%] | [X.X%] | [+/-X.X%] |
| Pop / Pop-Rock | 1 | [X.X%] | [X.X%] | [+/-X.X%] |
| Soul / R&B | 1 | [X.X%] | [X.X%] | [+/-X.X%] |

---

## 6. Diagnostic & Ablation Studies (if applicable)

```bash
python -m research.benchmarks.diagnose_track --track "[TrackName]" --baseline AudioAnalyzer --candidate [CandidateModel]
python -m research.benchmarks.run_ablation --track "[TrackName]" --models AudioAnalyzer,[CandidateModel]
```

[Document findings from single-track analysis, spectral distributions, and component isolation.]

---

## 7. Decision & Historical Rationale

- **Final Verdict:** `[PROMOTED TO PRODUCTION / REJECTED (DEAD END)]`
- **Root Cause Analysis:**
  [Detailed musical and DSP explanation of why the candidate succeeded or failed.]
- **Lessons Learned for Future Research Cycles:**
  1. [Lesson 1]
  2. [Lesson 2]
- **Persistent Log Updated:**
  - [x] Appended to `research/experiments/RESEARCH_HISTORY.md`
  - [x] Updated `research/experiments/LEADERBOARD.md` (if promoted or benchmarked)
