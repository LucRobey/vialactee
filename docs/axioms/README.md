# The 9 Untouchable Golden Axioms of Vialactée (Tier 0)

This directory defines the **Tier 0 Untouchable Golden Axioms** of the Vialactée system. These axioms represent the foundational physical, temporal, mathematical, and architectural laws governing the entire repository.

---

## 🏛️ Axiom Governance & RFC Procedure

1. **Immutable Core**:
   These axioms are **barred from autonomous AI modification**. An AI agent may never relax, weaken, bypass, or delete an axiom or its corresponding verification test.
2. **Human Architectural RFC Required**:
   Modifications to any axiom require a formal Human Architectural Request for Comments (RFC) signed and approved by the project lead.
3. **Automated Enforcement**:
   Every axiom is backed by automated tests located in `tests/governance/`. CI pipelines strictly reject any commit that violates these invariants.

---

## 📋 Master Axiom Index

| Axiom ID | Title | Summary Invariant | Primary Enforcement |
|:---|:---|:---|:---|
| [**AXIOM-01**](./AXIOM-01_FRAME_BUDGET.md) | Real-Time Frame Budget & Pacing | 30.0 FPS target, $\le 20.0\text{ ms}$ total compute budget, 60 Hz ODF feature extraction | `tests/governance/test_axiom_01_frame_budget.py` |
| [**AXIOM-02**](./AXIOM-02_ZERO_ALLOCATION.md) | Zero Dynamic Heap Allocations | 0 heap allocations in render loop & PortAudio callback; decoupled WS telemetry | `tests/governance/test_axiom_02_zero_allocation.py` |
| [**AXIOM-03**](./AXIOM-03_HARDWARE_GEOMETRY.md) | Physical Geometry & Vertical Invariant | Single source of truth in `segments_*.json`; vertical strips wired bottom-up | `tests/governance/test_axiom_03_geometry.py` |
| [**AXIOM-04**](./AXIOM-04_NETWORK_PROTOCOLS.md) | Network Transport & UDP MTU Bounds | UDP chunks $\le 1,202\text{ B}$ (MTU safe); telemetry rate-limited to $\le 10\text{ Hz}$ | `tests/governance/test_axiom_04_network_limits.py` |
| [**AXIOM-05**](./AXIOM-05_LOOKAHEAD_SYNC.md) | Predictive Lookahead & Speaker Sync | Speaker cone back-projection ($T_{\text{speaker}}$) with $< 50\text{ ms}$ AV synchronization | `tests/test_audio_pipeline.py` |
| [**AXIOM-06**](./AXIOM-06_PERCEPTUAL_RHYTHM.md) | Perceptual Invariance & Real-Beat Gating | Graceful decay on low confidence; strobe & hard transitions gated by `is_real_beat` | `tests/test_modes_rhythm.py` |
| [**AXIOM-07**](./AXIOM-07_CODE_GOVERNANCE.md) | Code Governance & The 500-Line Ratchet | 500-line hard cap, strict ratchet on grandfathered files, fast headless tests | `tests/governance/test_axiom_07_code_governance.py` |
| [**AXIOM-08**](./AXIOM-08_RESEARCH_REGRESSION.md) | Scientific Clean-Room Zero Regression | Immutable benchmark ground truth; zero regression gate ($\Delta \text{F1@50ms} \ge 0.0\%$) | `research/benchmarks/` |
| [**AXIOM-09**](./AXIOM-09_PLATFORM_AGNOSTIC_DSP.md) | Scoped DSP Math & Invariance | Pure math in `core/` and `modes/`; zero OS/hardware branching outside `hardware/` | `tests/governance/test_axiom_09_platform_invariance.py` |
