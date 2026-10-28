# AXIOM-07: Code Governance & The 500-Line Ratchet

**Tier:** Tier 0 (Untouchable Golden Axiom)  
**Status:** Inviolable Law  
**Enforcement:** `tests/governance/test_axiom_07_code_governance.py` (and legacy `tests/test_code_governance.py`)  

---

## 1. Specification

1. **500-Line Production File Cap:**
   No new or modified production file in `core/`, `music/`, `hardware/`, `modes/`, `config/`, `connectors/`, `transitions/`, `mood/`, `utils/`, or `Main.py` may exceed **500 physical lines of code**.
2. **The Grandfathered Ratchet:**
   Two legacy music files exceed 500 lines due to complex historical algorithmic consolidation. These files are subject to a **strict one-way ratchet**: they may shrink, but they may **never expand**:
   - `music/AudioAnalyzer.py`: Maximum **598 lines**
   - `music/MultiBandOnsetAudioAnalyzer.py`: Maximum **621 lines**
   *(Note: `core/Mode_master.py` was refactored below the 500-line cap and retired from the grandfathered ratchet.)*
3. **Ratchet Lowering Mandate:**
   When refactoring or reclaiming lines in any grandfathered file, the ratchet ceiling in the governance test must be lowered to lock in the savings permanently.
4. **Fast Headless CI Governance SLA:**
   Automated governance, parity, and static AST verification tests in `tests/governance/` must execute headlessly (with `SDL_VIDEODRIVER=dummy` and without heavy DSP synthesis) in $\le \mathbf{0.5\text{ s}}$ total runtime.
5. **Heavy Benchmark Marker Scoping:**
   MIR evaluation benchmarks that synthesize audio files or process multi-second WAV audio belong strictly to `research/benchmarks/` and must be marked with `@pytest.mark.benchmark` so they are excluded from standard fast test runs.

---

## 2. Grandfathered Ratchet Ledger

| Grandfathered File | Historical Line Count | Ratchet Limit | Current Headroom |
|:---|:---|:---|:---|
| `music/AudioAnalyzer.py` | 598 | 598 | 0 lines |
| `music/MultiBandOnsetAudioAnalyzer.py` | 621 | 621 | 0 lines |

---

## 3. Violation Conditions

- Any production Python file outside the grandfathered table exceeding 500 lines.
- Any grandfathered file expanding beyond its recorded ratchet limit.
- Governance tests taking $> 0.5\text{ s}$ to execute.
- Altering the ratchet thresholds upward to accommodate messy code additions.
