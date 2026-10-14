# Researcher Reference: Executive Reporting Format (Mandatory)

> Loaded on demand from [`SKILL.md`](../SKILL.md). Baseline numbers in the table are placeholders; take current baselines from `research/experiments/LEADERBOARD.md`.

## 6. Executive Reporting Format (Mandatory)

Never end a research cycle with a rambling wall of text that buries the bottom line. The user should never have to ask *"so what's the conclusion?"*.
Every final response concluding a research cycle MUST start with this structured Executive Summary:

```markdown
# 🧬 Research Cycle XXX Executive Report: [Candidate Model Name]

**Investigator:** Autonomous Lead Rhythm Data Scientist & Audio DSP Engineer  
**Target Domain:** High-Energy Electro, Techno, Synthwave, Classic Rock & Pop  
**Candidate Model:** [`research/experiments/models/<Model>.py`](...)  
**Living Experiment Log:** [`research_log.md`](...)  

---

## 1. Executive Summary & Verdict

| Metric | Official Baseline | Candidate Model | Net Delta ($\Delta$) | Status |
| :--- | :---: | :---: | :---: | :---: |
| **Synthetic Suite F1@50ms** | 92.0% | XX.X% | +X.X% | **PASS / FAIL** |
| **Synthetic Suite CMLt** | 91.6% | XX.X% | +X.X% | **GAIN / REGRESSION** |
| **Real-World Macro F1@50ms** | 41.1% | XX.X% | +X.X% | **GAIN / REGRESSION** |
| **Real-World Macro CMLt** | 36.5% | XX.X% | +X.X% | **GAIN / REGRESSION** |
| **Pop / Pop-Rock F1@50ms** | 28.7% | XX.X% | +X.X% | **GAIN / REGRESSION** |
| **Classic / Hard Rock F1@50ms** | 60.8% | XX.X% | +X.X% | **GAIN / REGRESSION** |
| **Per-Frame CPU Latency** | 2.44 ms | X.XX ms | -XX% | **PASS (<= 3.0ms)** |
| **Heap Allocations in `update()`** | 0 bytes | 0 bytes | 0 | **VERIFIED** |

### Decision: `[PROMOTION RECOMMENDED / REJECTED (ZERO-REGRESSION INVARIANT)]`
[Brief 2-3 sentence bottom line explaining the decision]

---

## 2. Genre & Key Track Breakthroughs
- **[Genre 1]:** [Highlight specific track gains, e.g. Pumped Up Kicks +13.5%]
- **[Genre 2]:** [Highlight specific track continuity or jitter improvements]

## 3. Root-Cause Analysis of Any Regressed Tracks
- **[Track Name]:** [Explicit mathematical diagnosis of why it regressed]

## 4. Architectural Directive for the Next Cycle
- [Clear, actionable mathematical formulation or experiment for Cycle N+1]
```
