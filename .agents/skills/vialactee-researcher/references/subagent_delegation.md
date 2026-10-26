# Researcher Reference: Lean Subagent Delegation & Red-Teaming

> Loaded on demand from [`SKILL.md`](../SKILL.md).

## 5. Lean Subagent Delegation & Adversarial Red-Teaming

To prevent token exhaustion, latency bloat, and fragile multi-tier nesting, autonomous research follows a **Lean 2-Tier Subagent Model**:
- **Direct Execution by Lead Researcher:** The Lead Researcher executes all fast CLI commands directly via bash/PowerShell ([`diagnose_track.py`](../../../../research/benchmarks/diagnose_track.py), [`run_ablation.py`](../../../../research/benchmarks/run_ablation.py), and [`compare_runs.py`](../../../../research/benchmarks/compare_runs.py)). Do NOT spawn sub-subagents merely to run a single CLI command!
- **Targeted Subagent Delegation:** Spawning subagents (`invoke_subagent`) is reserved for high-leverage cognitive tasks:

### 5.1 High-Value Subagent Delegation Patterns

1. **Adversarial Red-Team Gatekeeper (`research` or `self` subagent):**
   - **Mandate:** Audit the mathematical proposal and code implementation for physical edge cases before heavy benchmarks are run.
   - **Checklist:**
     - Phase wrap discontinuities near $\phi = 0.0$ and $\phi = 2\pi$.
     - Division by zero or NaN during quiet song intros / breakdowns.
     - 180° upbeat traps on syncopated funk/disco tracks.
     - Memory profiling: verifies that `update()` executes with zero dynamic heap allocations.
   - **Prompt Example:**
     > *"Red-team the proposed Costas-loop model in `research/experiments/models/CostasAudioAnalyzer.py`. Specifically audit the phase discriminator for boundary discontinuities when phase wraps around 2*pi, check for potential NaN propagation during silent intros, and confirm that all state buffers are pre-allocated in __init__(). Return a prioritized bullet list of risks and concrete safeguards."*

2. **Mathematical Prototyper (`self` subagent):**
   - **Task:** Test a new difference equation, pole-zero stability, or BLAS vectorization scheme in an isolated scratch script before authoring a full model class.
   - **Prompt Example:**
     > *"Test the numerical stability and per-frame CPU latency of a vectorized 16-oscillator Kuramoto network on synthetic 120bpm audio in `<appDataDir>/brain/<conversation-id>/scratch/kuramoto_test.py`. Verify that it executes in <= 0.5ms on 1000 frames with zero dynamic array allocations. Return only CPU timing, stability confirmation, and the vectorized NumPy function snippet."*

### 5.2 Subagent Execution Rules for the Lead Researcher
- **Clear & Bounded Briefs:** Provide the subagent with explicit inputs, mathematical constraints, and required outputs.
- **Strictly No Polling:** Do NOT call `schedule` or `manage_subagents` in a loop. End your turn; the system automatically delivers a high-priority reactive wakeup when the subagent completes.
- **Log to Living Artifact:** Synthesize discoveries and embed them directly into `<appDataDir>\brain\<conversation-id>/research_log.md`.
