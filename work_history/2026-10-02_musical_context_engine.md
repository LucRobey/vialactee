# [2026-10-02] Musical Context Engine & Canonical Musical Regimes

> **Date:** 2026-10-02  
> **Session ID:** `9ecf745a-5381-4c7a-b13c-3c82527d48bb`  
> **Agent / Model:** Antigravity (Gemini 3.8 Flash High)  
> **Primary Goal:** Implement `core/MusicalContextEngine.py` to classify real-time audio into 6 canonical musical regimes, add delayed `beat_trust` to `core/Listener.py`, enforce anti-flicker Schmitt hysteresis and crossfading, document architecture and contracts, and verify 100% test pass rate with zero heap allocations.  
> **Status:** COMPLETED  

---

## 1. Context & Motivation

* **User Request:**
  1. *How to integrate rhythmic salience and beat trust in our system? How should each mode react?*
  2. *Should we have a class in addition to the audio analyzer (like a moodFeeler or musical context engine) that, with all data coming out of the audio analyzer, decides the state we are in (calm music, hard bpm, drop incoming, music changing, etc.)? That would allow each mode to not have its own duplicate ad-hoc logic, but define its behavior across all possible states.*
  3. *How will we document this next addition?*
* **Core Problem:**
  1. **Mode Logic Duplication & Inconsistency:** Prior to this engine, modes implemented ad-hoc threshold logic (`confidence < 0.4`), causing conflicting reactions and visual discordance during song transitions.
  2. **Boundary Chattering / Epilepsy Risk:** Continuous DSP metrics naturally fluctuate frame-to-frame. Without Schmitt trigger hysteresis and minimum dwell time locks, modes near boundaries could flicker at 60 FPS.
  3. **Timing Desync in Beat Confidence:** Pearson correlation was evaluated on the incoming lookahead buffer ($T_{\text{lookahead}} = T_{\text{speaker}} + 5.0\text{s}$). Consuming `beat_confidence` directly led speaker playback by ~5 seconds.
  4. **Anticipation Underutilization:** The 5-second lookahead stream was not systematically leveraged to prepare visual drop buildups.

---

## 2. Changes Made

### 1. Architectural Specification & Documentation
* **[NEW]** [`docs/architecture/musical_context_engine.md`](file:///c:/Users/Users/Desktop/vialactée/vialactee/docs/architecture/musical_context_engine.md):
  * Complete Tier 1 specification detailing pipeline placement, the 2x2 $S \times T$ matrix, Schmitt trigger deadbands, 1.0s minimum dwell times, lookahead salience gradient $\Delta R \ge +0.40$ pre-drop countdown, and smooth crossfade interpolation (`regime_blend`).
* **[MODIFY]** [`docs/reference/audio_analyzer_contract.md`](file:///c:/Users/Users/Desktop/vialactée/vialactee/docs/reference/audio_analyzer_contract.md):
  * Added `beat_trust` and `live_beat_trust` to Group A.
  * Added `salience_gradient` ($\Delta R$).
  * Added **Group E: Musical Context & Regimes (High-Level Classification Engine)** detailing all properties of `self.listener.context`.
  * Added **Pattern 4: Declarative Musical Regime Handling** demonstrating declarative mode authoring.
* **[MODIFY]** [`modes/MODE_RULES.md`](file:///c:/Users/Users/Desktop/vialactée/vialactee/modes/MODE_RULES.md) & [`docs/manuals/mode_authoring_guide.md`](file:///c:/Users/Users/Desktop/vialactée/vialactee/docs/manuals/mode_authoring_guide.md):
  * Codified the 6 canonical musical regimes as the primary state abstraction for visual modes.
  * Documented how modes should branch on `self.listener.context.current_regime` and interpolate transitions with `regime_blend`.
* **[MODIFY]** Agent skills in `.agents/skills/`:
  * Updated `vialactee-dsp-engine`, `vialactee-mode-creator`, and `vialactee-project` to document `MusicalContextEngine` and `self.listener.context`.

### 2. Core Engine Implementation
* **[NEW]** [`core/MusicalContextEngine.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/MusicalContextEngine.py):
  * `MusicalRegime(str, Enum)` with 6 canonical regimes:
    * `DEEP_AMBIENT`: Low Salience ($S < 0.35$), Low Trust ($T < 0.35$).
    * `FLOATING_PULSE`: Low Salience ($S < 0.35$), High Trust ($T \ge 0.50$).
    * `THE_POCKET`: High Salience ($S \ge 0.45$), High Trust ($T \ge 0.50$).
    * `CHAOTIC_FILL`: High Salience ($S \ge 0.45$), Low Trust ($T < 0.35$).
    * `PRE_DROP_BUILDUP`: Salience gradient $\Delta R = R_{\text{live}} - R_{\text{speaker}} \ge +0.40$. Arms and decrements `drop_countdown`. Protected by `pre_drop_cooldown`.
    * `STRUCTURAL_CHANGE`: Immediate priority on `is_song_change` or `is_verse_chorus_change`. Dwells for `structural_dwell_time` (1.2s).
  * **Schmitt Trigger Hysteresis**: Dual thresholds prevent chatter:
    * $S$: high threshold 0.45, low threshold 0.35 (deadband $[0.35, 0.45]$).
    * $T$: high threshold 0.50, low threshold 0.35 (deadband $[0.35, 0.50]$).
  * **Minimum Dwell Time ($\tau_{\text{dwell}} \ge 1.0\text{s}$)**: Prevents rapid steady-state toggling.
  * **Smooth Crossfade Progress (`regime_blend` $\in [0.0, 1.0]$)**: Ramps over 0.5s from $0.0 \to 1.0$.
  * **AXIOM-01 & AXIOM-02 Compliant**: Execution time $\le 0.01\text{ms}$ (budget $\le 0.15\text{ms}$), 0 dynamic heap allocations in hot path.
  * Line count: 278 lines (AXIOM-07 cap $\le 500$).

### 3. Listener Facade & Delay Buffering
* **[MODIFY]** [`core/Listener.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/Listener.py):
  * Pre-allocated `_ring_beat_trust` circular delay buffer (`np.zeros(capacity)`).
  * Ingests `confidence_score` at $T_{\text{lookahead}}$ and outputs `beat_trust` synchronized to speaker playback ($T_{\text{speaker}}$).
  * Exposes `self.listener.context` pointing to `MusicalContextEngine(self)`.
  * Calls `self.context.update(self.dt)` on every frame tick.
  * Line count: 408 lines (strictly under 500-line cap).
* **[MODIFY]** [`core/BaseAudioAnalyzer.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/BaseAudioAnalyzer.py):
  * Added contractual fallback properties `beat_trust` and `live_beat_trust`.

---

## 3. Verification & Testing

* **Full Pytest Suite**:
  * **Command**: `python -m pytest`
  * **Result**: **142 passed, 5 deselected in 10.58s (100% pass rate)**.
* **Heavy MIR Benchmarks**:
  * **Command**: `python -m pytest -m benchmark`
  * **Result**: **5 passed in 10.12s**.
* **Governance & Axiom Compliance**:
  * `test_axiom_01_frame_budget.py`: PASSED (Engine runtime $\approx 0.005\text{ms} \ll 0.15\text{ms}$).
  * `test_axiom_02_zero_allocation.py`: PASSED (**0 heap bytes / 0 objects allocated** in hot update path).
  * `test_axiom_07_code_governance.py`: PASSED (`MusicalContextEngine.py`: 278 lines, `Listener.py`: 408 lines, all $\le 500$).
  * `test_docs_parity.py` & `test_docs_parity_and_bugs.py`: PASSED.
* **Unit Tests for MusicalContextEngine (`tests/test_musical_context_engine.py`)**:
  * All 4 steady-state matrix quadrants verified.
  * Schmitt trigger deadband hysteresis verified.
  * Minimum dwell time locking verified.
  * Pre-drop buildup trigger, countdown decrement, and drop transition verified.
  * Structural change priority override and dwell verified.
  * Regime blend ramp verified ($0.0 \to 1.0$).
  * Edge cases (NaN inputs, out-of-bounds inputs, negative dt, zero dt) verified.

---

## 4. Architecture Decisions & Trade-offs

1. **Centralized Semantic Context vs Per-Mode Logic**: Giving modes raw DSP signals created diverging interpretations and jitter bugs. Moving regime classification to `MusicalContextEngine` allows modes to be purely declarative while ensuring visual cohesion across all 1,304 LEDs.
2. **Delayed `beat_trust` via Ring Buffer**: Preserving `beat_confidence` as an unbuffered lookahead metric for anticipation while introducing delayed `beat_trust` at $T_{\text{speaker}}$ resolved the 5-second timing lead without breaking backward compatibility for code expecting lookahead.
3. **Schmitt Trigger + Minimum Dwell Time vs Moving Average**: Simple moving averages introduce phase lag (sluggishness). Dual-threshold Schmitt triggers combined with minimum dwell time provide instantaneous entry into states without chattering on noisy signals.

---

## 5. Pitfalls, Reviewer Findings & Fixes

* **Pre-Drop Buildup Re-trigger Loop**: When simulating pre-drop countdown in synthetic tests, if delayed speaker salience never rose after countdown expiry, the engine could immediately re-trigger `PRE_DROP_BUILDUP` on the next frame. Adding `pre_drop_cooldown` (3.0s) and ensuring exit conditions handle both landed drops and aborted build-ups eliminated re-trigger chatter.
* **Chaotic Drop Arrival Exit Bug (FIXED)**: In the initial implementation, line 160 checked `if self._drop_countdown <= 0.0 or (self._is_salience_high and self._is_trust_high):`, requiring high beat trust to exit `PRE_DROP_BUILDUP`. If a drop arrived with high salience ($S \ge 0.45$) but low trust ($T < 0.35$, i.e. `CHAOTIC_FILL`), the engine remained trapped in tension buildup for up to 5 seconds while the drop was already blasting through the speakers. Fixed to exit whenever speaker salience breaches high threshold (`self._is_salience_high`), immediately transitioning to the appropriate active steady target.
* **Structural Change Re-Trigger Reset (FIXED)**: If a new discrete macro structural change (`is_verse_chorus_change` or `is_song_change`) occurred while already in `STRUCTURAL_CHANGE`, `_switch_regime` previously ignored it due to `new_regime == current_regime`. Fixed to reset `regime_dwell_time = 0.0` and `regime_blend = 0.0` so the new section gets its full visual animation duration.
* **String Assignment Crash in `get_state_snapshot()` (FIXED)**: Directly assigning a string or passing a string to `_switch_regime` raised `AttributeError: 'str' object has no attribute 'value'` in `get_state_snapshot()`. Coerced all inputs to `MusicalRegime` enums and added safe attribute fallbacks.
* **Missing Power & Spectral Novelty Ingestion (FIXED)**: Added ingestion of `asserved_total_power` and `asserved_novelty` into `core/MusicalContextEngine.py`, exposed `.power` and `.novelty` properties, and included them in telemetry snapshots.
* **Listener Config & Polymorphism Parity (FIXED)**: Passed `infos.get("musical_context") or infos.get("context_engine")` to `MusicalContextEngine`, and used `getattr(self.analyzer, 'live_beat_trust', ...)` for clean analyzer subclass polymorphism.

---

## 6. Open Items & Next Steps

1. **Migrate Visual Modes to `self.listener.context`**:
   * Update existing modes (e.g. `Metronome_mode.py`, `Dual_nature_mode.py`, `Hyper_strobe_mode.py`) to declare behavior across the 6 regimes instead of hardcoded threshold checks.
2. **Webapp / Connector Telemetry**:
   * Expose `self.listener.context.get_state_snapshot()` over `/ws` and the React web interface so users can see the active musical regime and drop countdown in real time.
