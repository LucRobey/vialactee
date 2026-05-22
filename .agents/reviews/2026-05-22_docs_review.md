# Vialactée — Docs Review — 2026-05-22

> **Type:** Documentation Audit
> **Axes:** Human Understanding · Agent Effectiveness · Maintainability
> **Scope:** All project `.md` files + inline Python comments
> **Reviewer:** Antigravity (AI Pair Programming Assistant)
> **Previous review:** [.agents/reviews/2026-05-12_docs_review.md](file:///c:/Users/Users/Desktop/vialact%C3%A9e/vialactee/.agents/reviews/2026-05-12_docs_review.md)
> **Resolved since last review:**
> - Deleted `.agents/PLAN.md` to prevent stale implementation plan traps (replaced by past-tense `hardware_pipeline.md`).
> - Removed duplicate hardware pipeline Mermaid diagram from `hardware/README.md` and added a clean link pointing to `.agents/docs/hardware_pipeline.md`.
> - Reconciled `evaluate_context()` with `update(current_time)` in `core/README.md` class diagrams and step-by-step loop descriptions.
> - Added inline label explaining that `leds.show()` flushes the previous frame in `core/precisions/mode_master.md` flowchart.
> - Integrated geometry mapping/loading into the initialization phase flowchart of `core/precisions/transition_director.md`.
> - Clarified that `force_mode` and `execute_mode_swap` trigger instant segment-level overrides in `core/precisions/segment.md`.
> - Moved legacy WS2812B direct GPIO driver (`Rpi_NeoPixels.py`) to a dedicated "Legacy / Deprecated Components" section in `hardware/README.md`.
> - Updated `AGENT.md` hardware listings to include all 5 core driver files, extracted the dense DSP pipeline into a clean markdown table, and replaced relative dates with absolute definitions.
> - Fixed vague directory links and added hardware routing targets inside `.agents/docs/00_AGENT_NAVIGATION.md`.
> - Added compatibility columns (Horizontal vs Vertical vs Both) and moved unimplemented modes (`Bary_rainbow_mode`, `Chromatic_chaser_mode`) to a "Planned Modes" section in `modes/modes_description.md`.
> - Fixed duplicate headings and Python-comment artifacts (`# ===`) in `.agents/docs/music_events_architecture.md`.
> - Added a web application implementation status table to `wabb-interface/design signatures/webapp_architecture.md`.
> - Clarified the "Design Signatures" terminology in `wabb-interface/design signatures/signature_design.md`.
> - Documented the full `app_config.json` keys, defaults, and descriptions schema in `config/README.md`.
> - Removed the stale 22KB `vialactee_review.md` audit report from the project root.

---

## Executive Summary

| Layer | Overall Score | Critical Issues |
|---|---|---|
| Human Understanding | **9.1 / 10** | Unexplained "Strip 0" vs "Strip 1" columns in coordinates table; minor incomplete sentences and stale conditional links in project overview. |
| Agent Effectiveness | **8.6 / 10** | Sweep intervals (0.2s vs 0.4s) and template weights mismatches in the Rhythm Tracker architecture; updates-per-second mismatch in the BPM Trust documentation. |
| Maintainability | **9.1 / 10** | `vocals_present` documented as active via Harmonic Product Spectrum (HPS) but hardcoded to `False` in code; `modes/README.md` lacks a unified `infos` settings reference table. |

---

## 1. Human Understanding

### 1.1 `project_overview.md` — Score: 9/10

**Strengths:**
- Excellent Mermaid flowchart mapping external interfaces, connectors, core engine files, visuals, and hardware layers.
- Clear pre-task and post-task Rules of Engagement (detailing delta-time requirements and simulator checks).
- Direct task-based routing targets.

**Issues:**

| Severity | Location | Problem | Fix |
|---|---|---|---|
| 🟢 Low | Line 104 | Stale conditional phrase: "read `modes/README.md` (if it exists)". The file is standard and exists. | Change to "read `modes/README.md`". |
| 🟢 Low | Line 138 | Incomplete sentence: "If you made temporary python files, remember to delete them or to put them." | Complete to: "...or move them to `playground/`." |

---

### 1.2 `core/README.md` — Score: 9.5/10

**Strengths:**
- Thorough class diagram showing accurate methods (`update(current_time)`) and properties (`is_in_standby`, `activ_configuration`).
- Loop steps correctly map to real async code update patterns.

**Issues:** None.

---

### 1.3 `core/precisions/mode_master.md` — Score: 9.5/10

**Strengths:**
- Flowchart clearly shows that `leds.show()` flushes the previous frame.
- Replaced stale `data/configurations.json` file paths.

**Issues:** None.

---

### 1.4 `core/precisions/transition_director.md` — Score: 9.5/10

**Strengths:**
- Flowchart includes geometry loading.
- Clean state transition logic matches Python code behavior.

**Issues:** None.

---

### 1.5 `core/precisions/segment.md` — Score: 9.5/10

**Strengths:**
- The dual-buffer state machine (`rgb_list` and `dual_rgb_list`) is beautifully visual.
- Cleared up segment configuration loading paths.

**Issues:** None.

---

### 1.6 `hardware/README.md` — Score: 9.5/10

**Strengths:**
- Correctly links to `hardware_pipeline.md` instead of duplicating diagrams.
- Legacy driver separated cleanly.

**Issues:** None.

---

### 1.7 `.agents/coordinates.md` — Score: 7.5/10

**Strengths:**
- Highly practical coordinate ranges table for physical installation debugging.
- Scales and offsets for the Pygame simulation are mathematically documented.

**Issues:**

| Severity | Location | Problem | Fix |
|---|---|---|---|
| 🟡 Medium | Column 1 ("Strip") | Segments are split between Strip 0 and Strip 1, but there is no explanation of what this means. | Add a brief note explaining that Strip 0 and 1 represent two physical output lines from the controllers. |

---

## 2. Agent Effectiveness

### 2.1 `.agents/AGENT.md` — Score: 8.5/10

**Strengths:**
- Upgrades list is extremely comprehensive.
- Replaced relative time indicators with absolute definitions.
- The `DSP Engine Overview` table is easy to parse.

**Issues:**

| Severity | Location | Problem | Fix |
|---|---|---|---|
| 🟢 Low | Recent Upgrades | Duplicate bullet #5 ("Decluttered Root...") and skips bullet #6 (which was moved to the DSP table). | Correct the bullet list numbering. |
| 🟡 Medium | Architecture Overview | `AudioIngestion.py` and `AudioAnalyzer.py` are missing from the `core/` folder description bullet. | Add them to the list of core components. |

---

### 2.2 `.agents/docs/00_AGENT_NAVIGATION.md` — Score: 9.5/10

**Strengths:**
- Specific, actionable instructions (e.g., dynamic imports, 20s cooldowns, profiling context managers).
- Accurate navigation links pointing directly to configurations and connectors.

**Issues:** None.

---

### 2.3 `.agents/docs/hardware_pipeline.md` — Score: 9.5/10

**Strengths:**
- Renamed from `PLAN.md` and updated from future tense to past tense to reflect current reality.
- Detailed routing from smartphone (Bluetooth) through ALSA to the speakers and ESP32.

**Issues:** None.

---

### 2.4 `.agents/docs/rhythm_tracker_architecture.md` — Score: 7/10

**Strengths:**
- Great explanation of the Coarse Autocorrelation Flywheel and localized sweeps.
- Flowchart matches components.

**Issues:**

| Severity | Location | Problem | Fix |
|---|---|---|---|
| 🟡 Medium | Section 3 | Text states that the continuous phase sweep runs "every 0.4 seconds", but code (`AudioAnalyzer.py:437`) runs it "every 0.2 seconds". | Change text to "every 0.2 seconds". |
| 🟡 Medium | Section 3 | Template weights listed (Main: 1.5, Sub: 0.6, Sub-Sub: 0.0) differ from code implementations (1.0, 0.6, 0.3 in `cycle_template`). | Reconcile the weights text with the actual code values. |

---

### 2.5 `.agents/docs/bpm_trust_architecture.md` — Score: 8/10

**Strengths:**
- Exceptional layout tracing spectral flux up to biased auto-correlation and long-term trust.

**Issues:**

| Severity | Location | Problem | Fix |
|---|---|---|---|
| 🟡 Medium | Section 5 | Text states that the loop samples trust "every 2 seconds (120 frames)" representing 60 FPS. Code sweeps and updates trust every 0.2 seconds using `0.9 ** fps_ratio` dynamic decay. | Reconcile the update rate and decay math with the production code. |

---

### 2.6 `.agents/skills/vialactee-project/SKILL.md` — Score: 9/10

**Strengths:**
- The single most critical onboarding document for agents. Enforces vectorized rendering rules and dynamic environment checks.

**Issues:**

| Severity | Location | Problem | Fix |
|---|---|---|---|
| 🟢 Low | Rule 2 | One massive 270-word paragraph detailing the mathematical models without formatting. | Break into subheadings or a small table. |

---

## 3. Maintainability

### 3.1 `modes/modes_description.md` — Score: 9.5/10

**Strengths:**
- Symmetrical layout descriptions are excellent.
- Added orientation matrix (Horizontal vs Vertical vs Both) and segregated planned modes.

**Issues:** None.

---

### 3.2 `modes/README.md` — Score: 8/10

**Strengths:**
- Explains the `run()` override contract.
- Details NumPy C-level vectorization expectations on `rgb_list`.

**Issues:**

| Severity | Location | Problem | Fix |
|---|---|---|---|
| 🟡 Medium | Document body | Lacks a configuration reference table mapping custom `infos.get()` settings to specific modes (e.g., `smoothRatio` for Rainbow). | Add a configuration reference section. |

---

### 3.3 `music_events_architecture.md` — Score: 8.5/10

**Strengths:**
- Renumbered headings and fixed raw python comments.
- Dynamic thresholding envelopes (LM/GM) are mathematically outlined.

**Issues:**

| Severity | Location | Problem | Fix |
|---|---|---|---|
| 🟡 Medium | Section 5 (API table) | `listener.vocals_present` is listed as utilizing Harmonic Product Spectrum (HPS), but in `AudioAnalyzer.py`, `vocals_present` is hardcoded to `False` (stub). | Mark the entry as `[PLANNED]` to flag the stub state. |

---

### 3.4 `wabb-interface/` design docs — Score: 9.5/10

**Strengths:**
- `webapp_architecture.md` contains a clear implementation status table showing all 5 pages implemented.
- `signature_design.md` clearly defines what "Design Signatures" means.

**Issues:** None.

---

### 3.5 `config/README.md` — Score: 9.5/10

**Strengths:**
- Contains a comprehensive configuration schema table for `app_config.json`.

**Issues:** None.

---

## 4. Python Inline Comments — Quick Assessment

### `Main.py`
- **Quality:** High. Clean descriptions of platform checks (Windows taskkills vs POSIX signals), configuration setups, and thread pools.
- **Issues:** Missing a module-level docstring at the top of the file explaining that it is the central async execution orchestrator.

### `AudioAnalyzer.py`
- **Quality:** Exceptional math comments. Fully explains the comb filters, logarithmic ODF compression, and the PLL.
- **Issues:** The `vocals_present = False` stub lacks an inline comment explaining that HPS vocal isolation is planned but currently unimplemented.

---

## 5. Priority Action Plan

### 🔴 CRITICAL (Fix immediately — creates agent errors or contradictions)

1. **Rhythm Tracker Sweep Mismatch:** Update `.agents/docs/rhythm_tracker_architecture.md` to reflect the actual 0.2s localized sweep frequency instead of 0.4s.
2. **Rhythm Tracker Weights Mismatch:** Reconcile template weights in `.agents/docs/rhythm_tracker_architecture.md` with the actual `AudioAnalyzer.py` implementations (1.0, 0.6, 0.3 for cycle_template, and complex continuous sweep math).
3. **BPM Trust Update Mismatch:** Fix the 2-second (120 frames) update rate description in `.agents/docs/bpm_trust_architecture.md` to match the actual 0.2s sweep update and `0.9 ** fps_ratio` dynamic decay.
4. **vocals_present HPS Stub Mismatch:** Mark `vocals_present` in `.agents/docs/music_events_architecture.md` API table as `[PLANNED]` and add a comment in `AudioAnalyzer.py` explaining it is currently stubbed to `False`.

### 🟡 HIGH (Fix before next agent session)

5. **Add strip hardware mapping explanation:** Update `.agents/coordinates.md` to explain what "Strip 0" vs "Strip 1" means (e.g., dual physical output lines).
6. **Correct AGENT.md upgrades numbering & listings:** Fix duplicate bullet 5 and skip of bullet 6 in `.agents/AGENT.md`, and add `AudioIngestion.py` and `AudioAnalyzer.py` to the core component overview list.
7. **Create modes config reference table:** Expand `modes/README.md` to include a reference table mapping `infos.get()` variables to their respective modes.

### 🟢 MEDIUM (Nice to have)

8. **Format SKILL.md Rule 2:** Break down the massive 270-word paragraph in `.agents/skills/vialactee-project/SKILL.md` (Rule 2) into subheadings or a table.
9. **Remove stale modes readme link in project overview:** Clean up the conditional `modes/README.md (if it exists)` reference in `project_overview.md` (since it is standard) and fix the incomplete sentence on line 138.
10. **Module docstrings:** Add descriptive module-level docstrings at the top of `Main.py` and `AudioAnalyzer.py`.
11. **Transition Architecture Duplicate Heading:** Fix the duplicate "## 3." headings in `.agents/docs/transition_architecture.md` (renumbering the second to 4).

---

## 6. Documentation Debt Heatmap

| Area | Debt Level | Primary Risk |
|---|---|---|
| **Rhythm & BPM Tracking docs** | 🟡 MEDIUM | Sweep rates, weights, and update frequencies differ from production code, leading to agent mathematical assumptions. |
| **Audio Event analysis docs** | 🟡 MEDIUM | `vocals_present` is documented as active via HPS, but is hardcoded to `False`, misleading devs on features. |
| **Mode system docs** | 🟡 MEDIUM | `modes/README.md` lacks a unified `infos` settings reference table. |
| **Project Structure / Overview** | 🟢 LOW | Minor cleanup (stale parenthetical link, incomplete sentence). |
| **Core Orchestration / Transitions** | 🟢 LOW | Exceptionally high synchronization between documentation, state diagrams, and production code. Duplicate "## 3." heading is minor. |
| **Hardware & UI Integration docs** | 🟢 LOW | Complete parity. Duplicate diagrams resolved; all 5 web app pages fully documented and matched to source code. |
