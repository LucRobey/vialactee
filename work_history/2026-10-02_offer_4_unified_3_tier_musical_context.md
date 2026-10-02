# [2026-10-02] Offer 4: Unified 3-Tier Musical Context Engine

> **Date:** 2026-10-02  
> **Session ID:** `1a5f01df-62c6-4153-bc5d-c4e67c82677a`  
> **Agent / Model:** Antigravity (Google DeepMind)  
> **Primary Goal:** Implement Offer 4 (The Unified 3-Tier Musical Context) in `core/MusicalContextEngine.py` replacing the legacy 6 regimes with 3 orthogonal layers (Tier 1: Continuous Dynamic Kinetics, Tier 2: 4 Macro Scenes `MusicalScene`, Tier 3: Micro Physical Badges), full backward compatibility, updated developer studios, and zero-allocation AXIOM-01/02/07 compliance.  
> **Status:** COMPLETED  

---

## 1. Context & Motivation

* **User Request:**
  Upgrade the musical context system to Offer 4: The Unified 3-Tier Musical Context.
* **Why this was needed:**
  The legacy 6 regimes (`DEEP_AMBIENT`, `FLOATING_PULSE`, `THE_POCKET`, `CHAOTIC_FILL`, `PRE_DROP_BUILDUP`, `STRUCTURAL_CHANGE`) mixed macroscopic acoustic states (chill vs groove), microscopic musical expressions (in pocket vs chaotic syncopation), and transient transition events (pre-drop buildup, structural changes) into a single discrete enum. This forced visual modes to handle complex edge cases and caused chattering when music hovered near boundary conditions.
* **The Solution (Offer 4 Architecture):**
  1. **Tier 1 (Continuous Dynamic Kinetics):** Smooth scalar fields in $[0.0, 1.0]$ (`energy`, `tension`, `drop_progress`, `spectral_tilt`, `vertical_center`, `salience_gradient`, `power_gradient`).
  2. **Tier 2 (4 Macro Scenes):** Broad structural scenes (`MusicalScene`: `CHILL`, `GROOVE`, `BUILDUP`, `DROP_IMPACT`) with 1.0s minimum dwell between `CHILL` and `GROOVE`, 1.5s lock on `DROP_IMPACT`, and 0.5s smooth crossfade blending.
  3. **Tier 3 (Micro Physical Badges):** High-precision boolean flags (`is_locked`, `is_syncopated`, `is_real_beat`, `is_silent`, `is_drop_impact`, `is_drop_imminent`, `is_structural_cut`).
  4. **Transparent Backward Compatibility:** `MusicalRegime = MusicalScene`, enum alias mapping, legacy property getters, and bidirectional equality support.

---

## 2. Changes Made

### 1. Core Musical Context Engine
* **[MODIFY]** [`core/MusicalContextEngine.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/MusicalContextEngine.py):
  * **Tier 2 Macro Scenes (`MusicalScene(str, Enum)`):**
    * Canonical values: `CHILL = "CHILL"`, `GROOVE = "GROOVE"`, `BUILDUP = "BUILDUP"`, `DROP_IMPACT = "DROP_IMPACT"`.
    * Implemented `__eq__` and `_missing_` to bidirectionally match legacy regime strings (`"THE_POCKET" == MusicalScene.GROOVE`, `"DEEP_AMBIENT" == MusicalScene.CHILL`, etc.).
    * State machine with Schmitt trigger hysteresis ($P$, $S$, $T$) and minimum dwell times (1.0s for `CHILL` $\leftrightarrow$ `GROOVE`; 1.5s dwell lock in `DROP_IMPACT`).
    * Smooth cosine crossfade (`scene_blend` progressing $0.0 \to 1.0$ over 0.5s).
  * **Tier 1 Continuous Kinetics:**
    * `energy`: Fused acoustic/rhythmic driver $\in [0.0, 1.0]$.
    * `tension`: Anticipation curve peaking at 1.0 on drop landing $\in [0.0, 1.0]$.
    * `drop_progress`: Buildup progression curve peaking at 1.0 on impact frame $\in [0.0, 1.0]$.
    * `spectral_tilt`: Bass vs treble tilt in $[-1.0, 1.0]$.
    * `vertical_center`: Spectral center of gravity in $[0.0, 1.0]$.
    * `salience_gradient` & `power_gradient`: Differential lookahead gradients.
  * **Tier 3 Micro Physical Badges:**
    * `is_locked`: High rhythmic stability ($T \ge 0.50$ with release $< 0.35$).
    * `is_syncopated`: Rhythmic complexity/off-beat energy ($S \ge 0.45 \land T < 0.35$).
    * `is_real_beat`: Audio beat tag validated by acoustic power ($P \ge 0.20$).
    * `is_silent`: Acoustic floor detected ($P < 0.05$ with exit at $P \ge 0.08$).
    * `is_drop_impact`: 1-frame shockwave pulse on landing.
    * `is_drop_imminent`: Buildup countdown $\le 0.40$s.
    * `is_structural_cut`: 1.2s dwell triggered by song or verse/chorus transitions.
  * **Backward Compatibility Facade:**
    * `MusicalRegime = MusicalScene` alias.
    * Properties: `current_regime`, `previous_regime`, `regime_blend`, `regime_dwell_time`, `is_ambient`, `is_rhythmic`, `is_in_pocket`, `is_buildup`, `is_structural_change`.
    * Pre-allocated `telemetry` dictionary updated in-place without heap churn.
  * **Governance Compliance:**
    * Strictly **477 physical lines** ($\le 500$ line cap, AXIOM-07).
    * Zero dynamic allocations in steady-state `update()` (AXIOM-02).
    * Execution time $\le 0.033$ ms per frame (budget $\le 0.15$ ms, AXIOM-01).

### 2. Core Audio Listener
* **[MODIFY]** [`core/Listener.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/Listener.py):
  * Cleanly imports and re-exports `MusicalScene` alongside `MusicalRegime`.
  * Preserved all safe audio feature getters and telemetry delegation.
  * Maintained strictly at **419 physical lines** ($\le 500$ line cap, AXIOM-07).

### 3. Developer Studios Visualization Tools
* **[MODIFY]** [`tools/mode_studio.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/tools/mode_studio.py):
  * Updated `SCENE_COLORS`, `SCENE_BG_COLORS`, and `SCENE_ICONS` (`≋ CHILL`, `● GROOVE`, `▲ BUILDUP`, `💥 DROP IMPACT`).
  * Card 2 upgraded to display:
    * Primary macro scene badge with color coding and icon.
    * Scene transition blend bar ($0.0 \to 1.0$) when crossfading.
    * Tier 3 micro physical badge pills: `[LOCKED]`, `[SYNCOPATED]`, `[SILENT]`, `[IMMINENT]`, `[IMPACT]`.
  * Phase plane grid updated for 4-scene space.
* **[MODIFY]** [`tools/music_studio.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/tools/music_studio.py):
  * Updated scene color palette, icons, and phase plane mapping.
  * Added Tier 3 physical badge pills to top HUD header.

### 4. Unit & Regression Tests
* **[MODIFY]** [`tests/test_musical_context_engine.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/tests/test_musical_context_engine.py):
  * Completely updated test suite with 20 unit tests:
    * Tier 1 continuous kinetics calculations and edge clamping.
    * Tier 2 macro scene state machine, Schmitt hysteresis, 1.0s dwell time, and 1.5s `DROP_IMPACT` dwell lock.
    * Tier 3 micro badge evaluations (`is_locked`, `is_syncopated`, `is_real_beat`, `is_silent`, `is_drop_impact`, `is_drop_imminent`, `is_structural_cut`).
    * Full backward compatibility (`current_regime`, `is_in_pocket`, enum equality with legacy strings).
    * AXIOM-01 frame budget verification ($0.033$ ms $\le 0.15$ ms).
    * AXIOM-02 zero dynamic heap allocation in steady-state `update()` via `tracemalloc`.

### 5. Architectural Documentation
* **[MODIFY]** [`docs/architecture/musical_context_engine.md`](file:///c:/Users/Users/Desktop/vialactée/vialactee/docs/architecture/musical_context_engine.md):
  * Comprehensive documentation of the 3-Tier Musical Context architecture, mathematical formulas, state machine transition diagrams, mode authoring guidelines, and backward compatibility layer.
* **[MODIFY]** [`docs/reference/audio_analyzer_contract.md`](file:///c:/Users/Users/Desktop/vialactée/vialactee/docs/reference/audio_analyzer_contract.md):
  * Updated Group E contract table with all Tier 1, Tier 2, and Tier 3 properties on `self.listener.context`.

---

## 3. Verification & Testing

* **Pytest Suite (`python -m pytest`)**:
  * **Result**: **150 passed, 5 deselected in 12.57s (100% pass rate)**.
* **Unittest Discover (`python -m unittest discover -s tests`)**:
  * **Result**: **125 tests passed in 11.181s (100% pass rate)**.
* **Governance Test Suite (`python -m unittest discover -s tests/governance`)**:
  * **Result**: **18 tests passed in 0.447s (100% pass rate)**:
    * `test_axiom_01_frame_budget.py`: PASSED (0.033 ms $\le 0.15$ ms).
    * `test_axiom_02_zero_allocation.py`: PASSED (0 dynamic allocations in steady state).
    * `test_axiom_03_geometry.py`: PASSED.
    * `test_axiom_04_network_limits.py`: PASSED.
    * `test_axiom_07_code_governance.py`: PASSED (`MusicalContextEngine.py`: 477 lines, `Listener.py`: 419 lines, both $\le 500$).
    * `test_axiom_09_platform_invariance.py`: PASSED.
    * `test_docs_parity.py`: PASSED.
* **Targeted Context Engine Suite (`python -m unittest tests/test_musical_context_engine.py`)**:
  * **Result**: **20 tests passed in 0.044s (100% pass rate)**.

---

## 4. Architecture Decisions & Trade-offs

1. **Orthogonal 3-Tier Separation**:
   * *Rationale:* Decoupling macro ambient vs groove states from micro stylistic badges (locked, syncopated) and continuous modulation kinetics allows visual modes to modulate brightness and speed smoothly while using badges for discrete punchy visual events.
2. **Zero-Allocation Hot Path Enum Comparison**:
   * *Trade-off:* Overriding `__eq__` on Enum instances enables transparent backward compatibility with legacy strings like `"THE_POCKET"`. However, executing `self.scene == MusicalScene.GROOVE` inside `update()` calls `__eq__` which creates string tuples.
   * *Resolution:* Used identity operators (`is` and `is not`) for all internal state machine comparisons, and hoisted alias mappings into module-level `frozenset` objects. Steady-state heap allocation is strictly 0 bytes.
3. **1.5s Dwell Lock in `DROP_IMPACT`**:
   * *Rationale:* On a drop impact, visual modes need sustained visual payoff. Locking the scene in `DROP_IMPACT` for 1.5s prevents immediate chattering back into `CHILL` or `GROOVE`, before gracefully crossfading to `GROOVE` (or `CHILL` if power $P < 0.20$).
4. **1.0s Minimum Dwell Between `CHILL` and `GROOVE`**:
   * *Rationale:* Prevents flickering when musical passages feature ambiguous rhythmic energy or sparse percussion.

---

## 5. Pitfalls & Lessons Learned

* **Python Tuple Unpacking Allocates Heap Memory (AXIOM-02)**:
  * In Python, syntax like `a, b, c, d = t, p, p_live, nov` compiles to a `BUILD_TUPLE` instruction that allocates a 72-byte heap tuple every single frame. Direct scalar assignment (`a = t\nb = p\n...`) completely eliminates this allocation.
* **Warmup Requirements for Tracemalloc in Unit Tests**:
  * Because transition crossfades (`scene_blend`) update state during scene changes, testing for zero steady-state allocation requires stepping the engine past the 1.0s dwell window before sampling tracemalloc snapshots.
* **Post-Silence Drop Surge Tracking**:
  * In tracks with a pre-drop silence cut, the audio drops to silence before exploding. Tracking `_buildup_saw_silence` ensures the drop impact triggers only after the acoustic surge arrives ($P \ge 0.50$ or $S \ge 0.45$).

---

## 6. Open Items & Next Steps

* [ ] Integrate Tier 3 micro badges (`is_locked`, `is_syncopated`, `is_real_beat`) in visual animation modes (e.g. `Metronome_mode.py`, `Dual_nature_mode.py`, `Hyper_strobe_mode.py`).
* [ ] Expose Tier 2 `MusicalScene` and Tier 3 micro badge pills to the React web interface (`wabb-interface`).
