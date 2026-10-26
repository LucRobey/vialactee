# [2026-10-26] Entity Architecture & Trust-Rated Contracts (v4)

> **Date:** 2026-10-26  
> **Session ID:** `28baedce-8bca-4a3e-8959-30d81448d9f9`  
> **Agent / Model:** Antigravity  
> **Primary Goal:** Extract the 10-file DSP & Music Context room from `core/` into `music/` with a single `music/api.py` door, consolidate trust-rated contracts under `docs/contracts/`, and enforce signal parity and mode trust-tier compliance via AST governance tests.  
> **Status:** COMPLETED  
> **Commits:** `95f1473`, `6f330ee`, `4a53c10`  
> **Skills Used:** `vialactee-project`, `vialactee-dsp-engine`, `vialactee-mode-creator`, `vialactee-research-manager`, `vialactee-researcher`  
> **Skill Friction:** `.agents/skills/` contained several legacy `file:///c:/Users/Users/Desktop/vialactée/vialactee/...` links and a broken link to `docs/axioms/AXIOM-01_FRAME_BUDGET.md` which failed `test_skills_governance.py`; fixed in place by converting to relative paths.

---

## 1. Context & Motivation

* `core/` previously combined runtime orchestration (`Mode_master.py`, `Segment.py`, `TransitionBridge.py`, `CommandRouter.py`, `AppConfigStore.py`, `Webapp_instruction_logger.py`) with all 10 DSP and musical context modules (`Listener.py`, `AudioIngestion.py`, `BaseAudioAnalyzer.py`, `AudioAnalyzer.py`, `MultiBandOnsetAudioAnalyzer.py`, `DyadicMetricalAudioAnalyzer.py`, `comb_kernels.py`, `StructuralNoveltyDetector.py`, `RhythmConfig.py`, `MusicalContextEngine.py`).
* Visual modes and downstream sectors lacked an explicit, machine-enforced trust contract distinguishing rock-solid physical DSP signals (🟢 HIGH), beat-flywheel signals requiring confidence gating (🟡 MEDIUM), and structural/macro scene heuristics (🟠 LOW).
* This session executed the 3-phase *Entity Architecture & Trust-Rated Contracts Plan (v4)* to establish `music/` as a self-contained room with a single public door (`music/api.py`), centralize contracts under `docs/contracts/`, and add AST-based governance tests.

---

## 2. Changes Made

### Phase 1 — Extract `music/`, Migrate Imports, Fix Links & Isolation Tests
* **[MOVE / MODIFY]** Moved 10 files via `git mv` from `core/` to [`music/`](file:///c:/Users/lucro/Desktop/vialactee/music/):
  * [`music/AudioIngestion.py`](file:///c:/Users/lucro/Desktop/vialactee/music/AudioIngestion.py), [`music/BaseAudioAnalyzer.py`](file:///c:/Users/lucro/Desktop/vialactee/music/BaseAudioAnalyzer.py), [`music/AudioAnalyzer.py`](file:///c:/Users/lucro/Desktop/vialactee/music/AudioAnalyzer.py), [`music/MultiBandOnsetAudioAnalyzer.py`](file:///c:/Users/lucro/Desktop/vialactee/music/MultiBandOnsetAudioAnalyzer.py), [`music/DyadicMetricalAudioAnalyzer.py`](file:///c:/Users/lucro/Desktop/vialactee/music/DyadicMetricalAudioAnalyzer.py), [`music/comb_kernels.py`](file:///c:/Users/lucro/Desktop/vialactee/music/comb_kernels.py), [`music/StructuralNoveltyDetector.py`](file:///c:/Users/lucro/Desktop/vialactee/music/StructuralNoveltyDetector.py), [`music/RhythmConfig.py`](file:///c:/Users/lucro/Desktop/vialactee/music/RhythmConfig.py), [`music/MusicalContextEngine.py`](file:///c:/Users/lucro/Desktop/vialactee/music/MusicalContextEngine.py), [`music/Listener.py`](file:///c:/Users/lucro/Desktop/vialactee/music/Listener.py).
* **[NEW]** [`music/__init__.py`](file:///c:/Users/lucro/Desktop/vialactee/music/__init__.py) and [`music/api.py`](file:///c:/Users/lucro/Desktop/vialactee/music/api.py):
  * Created the single public door for the `music/` room exporting `Listener`, `ANALYZER_REGISTRY`, `DEFAULT_ANALYZER_MODEL`, `resolve_analyzer_class`, `MusicalScene`, `MusicalContextEngine`, `ListenerProtocol`, `MusicalContextProtocol`, and the disjoint trust sets (`LISTENER_HIGH_TRUST`, `LISTENER_MEDIUM_TRUST`, `LISTENER_LOW_TRUST`, `LISTENER_CONFIG_TRUST`, `LISTENER_INTERNAL_ATTRS`, `CONTEXT_HIGH_TRUST`, `CONTEXT_MEDIUM_TRUST`, `CONTEXT_LOW_TRUST`, `CONTEXT_INTERNAL_ATTRS`).
* **[MODIFY]** Production callers migrated exclusively to `music.api`:
  * [`Main.py`](file:///c:/Users/lucro/Desktop/vialactee/Main.py), [`core/Mode_master.py`](file:///c:/Users/lucro/Desktop/vialactee/core/Mode_master.py), [`modes/Shining_stars_mode.py`](file:///c:/Users/lucro/Desktop/vialactee/modes/Shining_stars_mode.py).
* **[MODIFY]** Updated imports across `tools/`, `scripts/`, `tests/` (32 test files + `assertLogs` logger names in [`tests/test_analyzer_contract_compliance.py`](file:///c:/Users/lucro/Desktop/vialactee/tests/test_analyzer_contract_compliance.py)), `research/`, `scratch/`, and `archive/*.py`.
* **[NEW / MODIFY]** Room READMEs and Markdown references:
  * Created [`music/README.md`](file:///c:/Users/lucro/Desktop/vialactee/music/README.md) and slimmed [`core/README.md`](file:///c:/Users/lucro/Desktop/vialactee/core/README.md) to reflect the 6 remaining orchestrator files.
  * Updated path references across markdown files in `.agents/skills/`, `.agents/docs/`, `docs/`, and `research/`.
* **[NEW / MODIFY]** Governance tests:
  * Created [`tests/governance/test_music_isolation.py`](file:///c:/Users/lucro/Desktop/vialactee/tests/governance/test_music_isolation.py) enforcing `music/` independence, `music/api.py` door usage by production rooms, and zero remnants of the 10 moved files in `core/`.
  * Updated [`tests/governance/test_axiom_07_code_governance.py`](file:///c:/Users/lucro/Desktop/vialactee/tests/governance/test_axiom_07_code_governance.py), [`tests/test_code_governance.py`](file:///c:/Users/lucro/Desktop/vialactee/tests/test_code_governance.py), [`tests/governance/test_axiom_09_platform_invariance.py`](file:///c:/Users/lucro/Desktop/vialactee/tests/governance/test_axiom_09_platform_invariance.py), and [`tests/governance/test_skills_governance.py`](file:///c:/Users/lucro/Desktop/vialactee/tests/governance/test_skills_governance.py).

### Phase 2 — Trust-Rated Contracts (`docs/contracts/` & `modes/MODE_RULES.md`)
* **[NEW]** [`docs/contracts/README.md`](file:///c:/Users/lucro/Desktop/vialactee/docs/contracts/README.md): Index of the 4 inter-room contracts and the 3-tier trust system (🟢 HIGH, 🟡 MEDIUM, 🟠 LOW).
* **[NEW]** [`docs/contracts/music_analyzer_contract.md`](file:///c:/Users/lucro/Desktop/vialactee/docs/contracts/music_analyzer_contract.md): Exhaustive trust-rated signal reference covering all 42 `Listener` properties + 6 internal attributes, all 31 `MusicalContextEngine` properties + 19 internal attributes, Part A input/output doors, and the `BaseAudioAnalyzer` 4-step subclass lifecycle.
* **[NEW]** [`docs/contracts/mood_contract.md`](file:///c:/Users/lucro/Desktop/vialactee/docs/contracts/mood_contract.md) and [`docs/contracts/transition_contract.md`](file:///c:/Users/lucro/Desktop/vialactee/docs/contracts/transition_contract.md): Upgraded with explicit trust badges on every input and output signal.
* **[NEW / MODIFY]** Pointer stubs in [`docs/reference/mood_contract.md`](file:///c:/Users/lucro/Desktop/vialactee/docs/reference/mood_contract.md), [`docs/reference/transition_contract.md`](file:///c:/Users/lucro/Desktop/vialactee/docs/reference/transition_contract.md), and [`docs/reference/audio_analyzer_contract.md`](file:///c:/Users/lucro/Desktop/vialactee/docs/reference/audio_analyzer_contract.md).
* **[MODIFY]** [`modes/MODE_RULES.md`](file:///c:/Users/lucro/Desktop/vialactee/modes/MODE_RULES.md): Added **Part A: Mode Sector Contract** defining the incoming doors, Rule A (🟠 LOW forbidden in concrete modes), Rule B (🟡 MEDIUM must be confidence-gated), and the sanctioned gated helpers in `Mode.py`.

### Phase 3 — Enforcement & Mode Trust Compliance
* **[MODIFY]** [`modes/Synesthesia_mode.py`](file:///c:/Users/lucro/Desktop/vialactee/modes/Synesthesia_mode.py): Removed `ctx.is_structural_cut` access so concrete modes obey Rule A without grandfathered exceptions.
* **[MODIFY]** [`modes/Chromatic_chaser_mode.py`](file:///c:/Users/lucro/Desktop/vialactee/modes/Chromatic_chaser_mode.py): Gated `bpm_factor` with `self.rhythm_lock` (`1.0 + self.rhythm_lock * ((bpm / 120.0) - 1.0)`) so `bpm` smoothly falls back to `1.0` when `rhythm_lock == 0.0` (Rule B compliance).
* **[MODIFY]** [`tests/governance/test_docs_parity.py`](file:///c:/Users/lucro/Desktop/vialactee/tests/governance/test_docs_parity.py): Added `test_music_contract_parity` and `test_modes_respect_trust_tiers` (inspecting `ast.Attribute`, `ast.Name`, and `getattr`/`hasattr` `ast.Call` string literal arguments, with empty `low_trust_grandfathered` and `medium_trust_grandfathered` ratchet sets).

---

## 3. Verification & Testing

* **Command**: `.\.venv\Scripts\python.exe -m pytest -q tests/governance/`
  * **Result**: `37 passed` (includes all 5 tests in `test_skills_governance.py`, 5 tests in `test_music_isolation.py`, and 5 tests in `test_docs_parity.py`).
* **Command**: `.\.venv\Scripts\python.exe -m pytest -q --ignore=tests/test_benchmark_engine.py`
  * **Result**: `384 passed, 10 failed, 93 subtests passed` (the 10 failures are pre-existing: 7 async tests due to missing `pytest-asyncio` plugin in `.venv` and 3 pre-existing transition handshake tests in `test_transition_bridge.py` and `test_families_and_handshake.py`).
* **Command**: `research.benchmarks.run_benchmark.load_model_class` check across all 10 benchmark models (`baseline`, `dyadic`, `phase1_floating`, `phase2_competitor`, `exp1_groove`, `exp2_variance`, `exp3_bounce`, `exp4_inertia`, `exp5_sigmoid`, `exp6_consensus`)
  * **Result**: All 10 models imported and instantiated cleanly.

---

## 4. Architecture Decisions & Trade-offs

* **Single Door (`music/api.py`) for Production, Direct Imports Allowed for Tests & Research**: Production sectors (`Main.py`, `core/`, `modes/`, `mood/`, `transitions/`, `hardware/`, `connectors/`, `config/`, `utils/`) are strictly enforced by `test_music_isolation.py` to import only from `music.api`, while `tests/`, `research/`, `tools/`, and `scripts/` may import internal `music.*` modules directly for unit testing and DSP benchmarking.
* **Zero Grandfathered Mode Exceptions**: Fixing `Synesthesia_mode.py` (removing `is_structural_cut`) and `Chromatic_chaser_mode.py` (blending `bpm_factor` with `self.rhythm_lock`) allowed both `low_trust_grandfathered` and `medium_trust_grandfathered` in `test_modes_respect_trust_tiers` to start at `frozenset()`.

---

## 5. Pitfalls & Lessons Learned

* **`unittest.assertLogs` Logger Names**: Moving `core/Listener.py` and `core/BaseAudioAnalyzer.py` to `music/` changed `logging.getLogger(__name__)` from `core.Listener` to `music.Listener`; `tests/test_analyzer_contract_compliance.py` required updating its `assertLogs` logger targets accordingly.
* **Exact Attribute Backtick Matching in `music_analyzer_contract.md`**: `test_music_contract_parity` checks for `` `{attr}` `` in `docs/contracts/music_analyzer_contract.md`, so method names in internal attribute tables should be formatted as `` `reset` `` (with ``Method (`reset()`)`` in the kind column) rather than `` `reset()` ``.
* **Indirect `getattr(listener, "<signal>")` Lookups in Modes**: Several modes (`Metronome_mode`, `Extending_waves_mode`, `Beat_runner_mode`, `Impact_shockwave_mode`) read `beat_phase`, `beat_count`, or `is_beat` via `getattr(self.listener, "beat_phase", 0.0)` and assign to differently named local variables (`phase`, `count`). Inspecting `getattr`/`hasattr` `ast.Call` string constant arguments in `_extract_mode_signal_identifiers` ensures AST governance catches both direct attribute access and `getattr()` lookups without touching docstrings or comments.

---

## 6. Open Items & Next Steps

* [ ] Install `pytest-asyncio` (or `anyio`), `pyyaml`, and `mir_eval` into `.venv` so async and benchmark tests run without CLI `--ignore` flags.
* [ ] Reconcile the 3 pre-existing `mode_handshake` test assertions in `tests/test_transition_bridge.py` and `tests/transitions/test_families_and_handshake.py`.
