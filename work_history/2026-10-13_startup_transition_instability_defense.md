# [2026-10-13] Startup Transition Instability Multi-Layer Defense

> **Date:** 2026-10-13  
> **Session ID:** `4130cdeb-017d-4c49-84b6-860557afe545`  
> **Agent / Model:** Antigravity (Gemini 3.8 Flash)  
> **Primary Goal:** Eliminate rapid erratic mode changes and blackout explosion transitions during the initial 1 to 3 seconds of startup across all audio sources.  
> **Status:** COMPLETED  

---

## 1. Context & Motivation

When launching `Main.py`, the chandelier lighting experienced intense mode swapping during the first 1 to 3 seconds. The empirical trace from `vialactee.log` showed 2 consecutive song-change transitions, 1 structural-change transition, and 1 pre-drop buildup explosion blackout fired in rapid succession upon track playback initiation:

```text
  INFO - [Local_AudioFile]    - Playing 'Palladium.mp3' with 5.0s predictive lookahead...
  INFO - [Transition_Director]- (TD) Song change boundary arrived at speakers -> triggering transition
  INFO - [Transition_Director]- (TD) Song change boundary arrived at speakers -> triggering transition
  INFO - [Transition_Director]- (TD) Structural change boundary arrived at speakers -> triggering transition
  INFO - [Transition_Director]- (TD) Pre-drop lookahead detected! Scheduling buildup duration=2.06s...
```

Root-cause analysis confirmed a multi-stage startup transient cascade across `StructuralNoveltyDetector` (cold-start STM vs LTM adaptation spike), `Local_AudioFile.prime_analyzer()` (300-frame pre-roll ring buffer contamination), `Transition_Director` (unshielded initial frame triggers), and `LocalTransitionManager` (zero-phase downbeat fallthrough on uninitialized flywheel).

---

## 2. Changes Made

### Layer 1: Structural Novelty Warmup & Dynamic Cooldown Anchoring
* **MODIFY** [`core/StructuralNoveltyDetector.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/StructuralNoveltyDetector.py):
  * Added `self.warmup_frames_total = 60` and `self._warmup_frames_remaining` (1.0 second at 60 FPS). During warmup, STM and LTM memory envelopes adapt normally, but novelty-driven triggers (`is_verse_chorus_change` and `is_song_change`) are suppressed.
  * Added dynamic first-frame anchoring: `self.last_structural_change_time = current_time` is set on frame 0 to respect both real-time epoch timestamps and synthetic benchmark time domains ($t=0.0$).
  * Added complete `reset()` method to restore memory filters, cooldowns, and warmup state.
* **MODIFY** [`core/RhythmConfig.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/RhythmConfig.py):
  * Added `structural_warmup_frames: int = 60` to centralized configuration.

### Layer 2: Audio File Pre-Roll Ring Buffer Sanitization & Context Synchronization
* **MODIFY** [`connectors/Local_AudioFile.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/connectors/Local_AudioFile.py):
  * In `prime_analyzer()`, after simulating 300 frames and spacing out ring timestamps, explicitly zeroed out event arrays and delayed trigger flags:
    * `_ring_is_song_change.fill(False)`
    * `_ring_is_verse_chorus_change.fill(False)`
    * `_ring_asserved_novelty.fill(0.0)`
    * `_ring_combined_novelty.fill(0.0)`
    * `_delayed_is_song_change = False`
    * `_delayed_is_verse_chorus_change = False`
    * `_delayed_asserved_novelty = 0.0`
    * `_delayed_combined_novelty = 0.0`
  * Called `self.listener.context.reset()` at the end of `prime_analyzer()` to reset `MusicalContextEngine` state (scene, dwell timer, drop countdown) so playback starts from a clean baseline.

### Layer 3 & 4: Transition Director Startup Grace Period & App Config Parity
* **MODIFY** [`transitions/director.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/transitions/director.py):
  * Initialized `cooldown_remaining` from `infos.get("startup_grace_period", 0.0)` so live apps enforce a stable 3.0s startup window while unit test fixtures default safely to 0.0.
* **MODIFY** [`config/app_config.json`](file:///c:/Users/Users/Desktop/vialactée/vialactee/config/app_config.json):
  * Added `"startup_grace_period": 3.0`.
* **MODIFY** [`docs/reference/configuration_schemas.md`](file:///c:/Users/Users/Desktop/vialactée/vialactee/docs/reference/configuration_schemas.md):
  * Documented `startup_grace_period` in the master configuration table to preserve `test_docs_parity.py` governance.

### Layer 5: Downbeat Quantization Trust Gate
* **MODIFY** [`transitions/manager.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/transitions/manager.py):
  * In `LocalTransitionManager.update()`, gated `phase < 0.05` downbeat checks with `beat_trust >= 0.20`:
    ```python
    is_beat_trustworthy = _safe_float(getattr(self.listener, "beat_trust", 0.0), 0.0) >= 0.20
    downbeat_hit = (phase < 0.05 and is_beat_trustworthy) or is_beat
    ```
  * Prevents cold-start uninitialized phase `0.0` from trivially firing on frame 0 before rhythmic lock is achieved.

### End-to-End Regression Test
* **MODIFY** [`tests/test_local_audio_file.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/tests/test_local_audio_file.py):
  * Added `test_startup_transition_stability_and_ring_buffer_cleanliness()`: primes audio file lookahead, verifies 100% clean ring buffer triggers, simulates 180 frames (3.0s) of speaker playback, and asserts that 0 transitions fire during the startup grace window.

---

## 3. Verification & Testing

* **Local Audio File & Startup Stability Suite:**
  `python -m unittest tests/test_local_audio_file.py`
  * **Result**: Ran 8 tests in 10.188s, **OK** (100% pass including new startup stability test).
* **Transitions Sector Suite:**
  `python -m unittest discover -s tests/transitions`
  * **Result**: Ran 88 tests in 0.572s, **OK**.
* **Governance & Documentation Parity Suite:**
  `python -m unittest discover -s tests/governance`
  * **Result**: Ran 21 tests in 2.999s, **OK** (AXIOM-01, AXIOM-02, AXIOM-07 500-line cap, docs parity verified).
* **Comprehensive Multi-Domain Regression Suite:**
  `python -m unittest tests/test_oracle_analyzer.py tests/test_score_structural_predictions.py tests/transitions/test_transition_director.py tests/transitions/test_api_contracts.py tests/governance/test_axiom_07_code_governance.py tests/governance/test_docs_parity.py tests/test_musical_context_engine.py`
  * **Result**: Ran 98 tests in 4.284s, **OK**.

---

## 4. Architecture Decisions & Trade-offs

* **First-Frame Dynamic Anchoring vs. Hardcoded `time.time()`:** Seeding cooldowns in `__init__` with `time.time()` breaks offline benchmarks and unit tests running in synthetic virtual time ($t \ge 0.0$). Anchoring on frame 0 dynamically adapts to any clock domain without skew.
* **Preserving Silence Drop Mechanics in `test_silence_detection`:** Restricting warmup suppression to novelty triggers (`asserved_novelty` and `combined_novelty`) allows continuous silence accumulation tests to pass without artificial threshold inflation.
* **Separation of Concerns for Lookahead Buildup:** Instead of altering the core math of `MusicalContextEngine` (which would break silence-cut EDM drop handling in `test_buildup_silence_cut_drop_handling` and risk violating AXIOM-07 500-line cap), startup stabilization was cleanly handled via `Transition_Director` startup grace period and `prime_analyzer` context reset.

---

## 5. Pitfalls & Lessons Learned

* `test_docs_parity.py` enforces that every single key in `config/app_config.json` must be documented in `docs/reference/configuration_schemas.md`. Adding a new configuration key without updating the schema reference immediately breaks CI.
* `test_cooldown_security_blocks_automatic_triggers_for_5_seconds` in `test_transition_director.py` expects that during normal post-transition cooldown, boundary events *are* armed to fire upon cooldown expiration. Thus, startup grace period was decoupled from trigger latching.

---

## 6. Open Items & Next Steps

* All 5 layers implemented and verified with zero regressions across 98 unit tests. Ready for live visual verification with Pygame simulator and physical hardware.
