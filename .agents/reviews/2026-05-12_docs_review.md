# Vialactée Documentation Review
*Axes: Human Understanding · Agent Effectiveness · Maintainability*
*Scope: 29 project .md files + inline Python comments in Main.py*

---

## Executive Summary

| Layer | Overall Score | Critical Issues |
|---|---|---|
| Human Understanding | **6.2 / 10** | Contradictions between `core/README.md` and `core/precisions/transition_director.md`; incomplete sentences; confusing strip table in `coordinates.md` |
| Agent Effectiveness | **7.1 / 10** | `PLAN.md` uses future tense for implemented features; `AGENT.md` hardware section is stale; missing `AudioAnalyzer.py` architecture doc |
| Maintainability | **5.4 / 10** | `hardware/README.md` fully duplicates `PLAN.md` diagram; `modes_description.md` lists 2 phantom modes; no `app_config.json` schema doc; `vialactee_review.md` has no clear ownership |

---

## 1. Human Understanding

### 1.1 `project_overview.md` — Score: **8/10**

**Strengths:**
- The Mermaid architecture diagram is genuinely excellent — correctly shows all data flows from `Local_Microphone` through the delay queue to `ModeMaster`
- The "Task-Based Navigation Map" (Section 3) is a best-practice pattern: task-first routing
- The BEFORE/AFTER "Rules of Engagement" are clear and actionable

**Issues:**

| Severity | Line | Problem | Fix |
|---|---|---|---|
| 🟡 Medium | `HwFac` node in `Visuals` subgraph | `HardwareFactory` is grouped inside the `Visuals` subgraph but it's part of the `Hardware` subgraph. The diagram is structurally misleading. | Move `HwFac` node to the `Hardware` subgraph where it belongs |
| 🟡 Medium | "read `modes/README.md` (if it exists)" | Undermines trust — the file either exists or it doesn't | Remove the conditional; it exists and should be referenced unconditionally |
| 🔴 Low | "remember to delete them or to put them" (Section 4) | Incomplete sentence — "put them" where? | Fix to: "remember to delete them or move them to `playground/`" |
| 🟡 Medium | Section 3 has no entry for "If you are working on the Web Interface" | A developer touching `wabb-interface/` has no navigation target | Add: "👉 Read `wabb-interface/README.md` and the `design rules/` docs" |

---

### 1.2 `core/README.md` — Score: **6.5/10**

**Strengths:**
- The classDiagram shows class members and ownership relationships clearly
- The 4-step execution loop explanation is well ordered

**Issues:**

| Severity | Location | Problem | Fix |
|---|---|---|---|
| 🔴 High | `Transition_Director` class in classDiagram | Shows `evaluate_context(current_time, next_change_time) : tuple[str, dict]` as the key method, but `core/precisions/transition_director.md` shows the main method is `update()`. **Direct contradiction.** | Reconcile. If `evaluate_context` is called by Mode_master and `update()` is internal, document both with their different roles |
| 🔴 High | classDiagram — `is_in_standby: bool` | This field is shown on `Transition_Director` but the state machine in `transition_director.md` defines two states: `PASSATION` and `TRANSITION_DUAL`. `is_in_standby` maps to neither. | Verify actual field names in `Transition_Director.py` and update classDiagram to match |
| 🟡 Medium | Step 2 in execution loop | "Mode_master immediately asks the Transition_Director what to do by passing the time state: `transition_director.evaluate_context(current_time, next_change_time)`" — but the `mode_master.md` flowchart shows `transition_director.update(current_time)` is the call made in the loop | One of these is wrong. Must verify against actual code and fix whichever doc is stale |

---

### 1.3 `core/precisions/mode_master.md` — Score: **7.5/10**

**Strengths:**
- Three separate Mermaid charts (init, main loop, external inputs) is the right split — avoids an unreadably dense single diagram
- The shuffle bag explanation is one of the clearest sections in the entire project

**Issues:**

| Severity | Location | Problem | Fix |
|---|---|---|---|
| 🟡 Medium | Main loop flowchart | Shows `2. leds.show()` as step 2, BEFORE segment rendering. The explanation says this "flushes the **previous frame's** buffer" which is correct but non-obvious and confusing without explanation in the diagram itself | Add a tooltip or inline label: "Flushes previous frame" on the leds.show() node |
| 🟡 Medium | Section 2.1 | "Reads `data/configurations.json`" — but `AGENT.md` says config is in `config/`. Neither `AGENT.md` nor `config/README.md` mention `data/`. **Path mismatch.** | Verify actual path of configurations.json and fix both docs |

---

### 1.4 `core/precisions/transition_director.md` — Score: **6/10**

**Strengths:**
- The state machine diagram (`PASSATION` ↔ `TRANSITION_DUAL`) is precise and unambiguous

**Issues:**

| Severity | Location | Problem | Fix |
|---|---|---|---|
| 🟡 Medium | Section 3.3 | "currently default to an 'explosion' effect for testing" — flagged as a draft/placeholder | Update to reflect the actual implemented default, or remove "for testing" language |
| 🟡 Medium | Section 3.1 | "Geometry Mapping: On startup, it parses `config/segments.json` to map out which segments are vertical vs horizontal" — this is not mentioned at all in the flowchart, which starts directly at `CheckState` | Add geometry loading to the init phase of the flowchart |

---

### 1.5 `core/precisions/segment.md` — Score: **7/10**

**Strengths:**
- The dual-buffer state machine (`rgb_list` / `dual_rgb_list`) is the clearest explanation of a complex mechanism in the entire project
- O(1) lookup explanation for the modes dictionary is a nice touch

**Issues:**

| Severity | Location | Problem | Fix |
|---|---|---|---|
| 🟡 Medium | Section 2.1 | "the segment reads `modes.json`" — but `config/README.md` mentions no `modes.json`, only `segments.json` and `app_config.json`. What is `modes.json`? | Clarify: is it `data/modes.json`, `config/modes.json`, or a different file? |
| 🟡 Medium | Flowchart | `force_mode / execute_mode_swap` is shown as a path but never explained — when is it used vs `change_mode`? | Add brief text: "`force_mode()` is called for instant segment-level mode changes (e.g., external network commands), bypassing the transition system" |

---

### 1.6 `hardware/README.md` — Score: **5/10**

**Strengths:**
- The component listing correctly identifies the evolved architecture (UDP_Sender, Fake_ESP32)

**Issues:**

| Severity | Location | Problem | Fix |
|---|---|---|---|
| 🔴 High | The Mermaid diagram (entire second half of file) | **100% duplicate** of the diagram in `.agents/PLAN.md`. Two docs should never share the same exact diagram — when one is updated, the other goes stale | Delete the diagram from `hardware/README.md`. Add a link: "See `.agents/PLAN.md` for the full hardware pipeline diagram." |
| 🟡 Medium | Key Components list | `Rpi_NeoPixels.py` described as "(Legacy/Alternative) Direct GPIO driver using `rpi_ws281x`. Eclipsed by the UDP/ESP32 architecture." — but it's still listed as a Key Component. If it's eclipsed, either remove it from the list or move to a "Legacy" subsection | Move to a "Legacy / Deprecated" subsection |

---

### 1.7 `.agents/coordinates.md` — Score: **6/10**

**Strengths:**
- Providing a clean coordinate table is essential and well-placed in `.agents/`
- The Pygame formula (`Visualizer X = 100 + (Matrix Col * 2)`) is exactly what an agent needs

**Issues:**

| Severity | Location | Problem | Fix |
|---|---|---|---|
| 🔴 High | Strip column in the table | All 11 segments show Strip "0" EXCEPT the last 4 which show Strip "1" — this appears to be a data error since the intro says "mapped sequentially". Also, `segment_v4` through `segment_h00` are Strip 0, then `segment_v2` through `segment_v1` suddenly are Strip 1 mid-table | Verify against actual hardware wiring and correct — or explain what "Strip 0" vs "Strip 1" means (two separate physical LED strips wired to different controller GPIO pins) |
| 🟡 Medium | V1 footnote | "align symmetrically with segment_v2 and horizontal connections" — the reason is explained but not where the 15 "missing" LEDs physically go (they're not wired? They're at the bottom below row 16?) | Clarify: "The first 15 LEDs (physical rows 1-15) of the wired strip are not used due to physical installation constraints" |

---

## 2. Agent Effectiveness

### 2.1 `.agents/AGENT.md` — Score: **6.5/10**

**Strengths:**
- The 14 "Recent Upgrades" bullets are a genuinely effective technique for briefing agents on non-obvious architectural decisions they'd otherwise miss
- Hardware section clearly specifies the LED count (1,304) and grouping (11 segments) — precise and unambiguous

**Issues:**

| Severity | Location | Problem | Fix |
|---|---|---|---|
| 🔴 High | Hardware section: "currently houses `Fake_leds.py`" | `hardware/` now contains `HardwareFactory.py`, `Udp_Sender.py`, `Fake_ESP32.py`, `Fake_leds.py`, `Rpi_NeoPixels.py` — listing only `Fake_leds.py` is dangerously incomplete. An agent asked to add hardware code would be blind to the factory pattern | Update the hardware bullet to list all 5 files |
| 🔴 High | Upgrade #6 bullet (261 words) | Describes the entire DSP pipeline in ONE bullet. This is the most critical piece of context but is completely buried and impossible to parse. An agent reading quickly will skip it. | Extract upgrade #6 into its own `## DSP Engine Overview` section with a table |
| 🟡 Medium | No mention of `AudioAnalyzer.py` as a distinct class | `AGENT.md` mentions `AudioIngestion.py` and `Listener.py` but not `AudioAnalyzer.py` — which is its own class with distinct BPM trust / song-change logic | Add `AudioAnalyzer.py` to the Architecture Overview with its role |
| 🟡 Medium | Upgrades section uses relative dates ("As of April 2026") | When reading this in the future, "April 2026" is non-contextual. Is the code from that date already current? | Replace "As of April 2026" with "Current Architecture State" or link to a changelog |

---

### 2.2 `.agents/docs/00_AGENT_NAVIGATION.md` — Score: **8/10**

**Strengths:**
- The 6-point "Agent Instructions Formatter" at the bottom is the single most effective section in the entire `.agents/` directory — concrete, specific, and action-preventing
- Task-based routing by documentation type is excellent

**Issues:**

| Severity | Location | Problem | Fix |
|---|---|---|---|
| 🟡 Medium | Rule #6: `with self.profiler.measure("feature_name"):` | Refers to `self.profiler` but there is no documentation of what this profiler is, where it lives, or how to access it | Add: "The profiler is accessible via `self.profiler` on the `Mode_master` instance, initialized in `__init__`" |
| 🟡 Medium | Section 3 links to `wabb-interface/` directory rather than a specific doc | "Explore this directory to understand..." is vague — a directory is not a navigation target | Link to `wabb-interface/README.md` specifically |
| 🟢 Low | No section for: "If you are working on Hardware Abstraction" | Missing routing for agents touching `hardware/` | Add routing: "👉 Read `hardware/README.md` for the factory pattern and UDP pipeline" |

---

### 2.3 `.agents/PLAN.md` — Score: **4/10**

**Strengths:**
- Phase 3 calibration notes (ALSA config, latency hardcoding) are genuinely useful reference info

**Critical Issue (🔴 High):** 
The document is titled "Implementation Plan" and uses future tense throughout:
- *"Local_Microphone.py...must be upgraded to a duplex stream"*
- *"we need to modify the internal Python engine"*
- *"The processing must happen instantly"*

But based on `AGENT.md` Upgrades #14, the 5-second lookahead is **already implemented**. This creates a severe agent trap: an agent reading `PLAN.md` will believe these features need to be built, potentially **duplicating or breaking existing implementations**.

**Fix:** Either:
1. Rename to `PLAN_implemented.md` and convert all future-tense to past-tense with a header: "STATUS: IMPLEMENTED as of April 2026" — OR
2. Delete the file entirely and incorporate its content into `AGENT.md` under "Architecture Decisions"

---

### 2.4 `.agents/docs/rhythm_tracker_architecture.md` — Score: **8/10**

**Strengths:**
- The Mermaid diagram maps exactly to the 4-step component description — rare alignment of diagram and text
- The deprecated magnetic snapper footnote with `*(Previously...)*` is correct practice — keeps context while signaling obsolescence

**Issues:**

| Severity | Location | Problem | Fix |
|---|---|---|---|
| 🟡 Medium | "every 0.4 seconds" and "0.1 BPM resolution" | Are these hardcoded constants or configurable? An agent needs to know which file to touch to change them | Add: "(hardcoded in `AudioAnalyzer.py` at `SWEEP_INTERVAL = 0.4`)" or equivalent |
| 🟡 Medium | Template weights: `Main Beat: 1.5, Sub-Beat: 0.6, Off-beat: -0.2` | Not linked to any config variable. If these change in code, the doc becomes wrong | Add location: "(see `PHASE_TEMPLATE` constant in `AudioAnalyzer.py`)" |

---

### 2.5 `.agents/docs/bpm_trust_architecture.md` — Score: **9/10**

This is the best-written doc in the entire project.

**Strengths:**
- The 6-step bottom-up explanation perfectly mirrors the Mermaid flow from top to bottom
- The "High Trust" / "Low Trust" intuition section is excellent agent-friendly framing
- The gatekeeper section explains the exact math: `binary_trust < (LTM * 0.6)` → permits hard reset

**Only Issue:**
| Severity | Location | Problem | Fix |
|---|---|---|---|
| 🟢 Low | "samples `binary_trust` every 2 seconds (120 frames)" | This implies 60 FPS but the rest of the project targets 30 FPS. "120 frames at 30FPS = 4 seconds" | Verify actual sampling interval and fix the parenthetical |

---

### 2.6 `.agents/skills/vialactee-project/SKILL.md` — Score: **9/10**

The strongest agent-facing document. Every rule is precise, actionable, and non-generic.

**Strengths:**
- Rule 1 (PyGame threading) has exact conditional logic: `if onRaspberry: loop.run_in_executor else: call synchronously`
- Rule 3 (LED orientation) explicitly lists ALL THREE variants with their exact string values: `"horizontal"`, `"vertical"`, `"vertical_up"`
- The anti-pattern rules in Rule 6 are the most effective in the project: "Do not iterate over `led_index` with Python `for` loops"

**Only Issue:**
| Severity | Location | Problem | Fix |
|---|---|---|---|
| 🟡 Medium | Rule 2 paragraph (~270 words in one block) | One massive paragraph with no internal structure | Break into a short table: `| Component | Method | Notes |` |

---

## 3. Maintainability

### 3.1 `modes/modes_description.md` — Score: **5.5/10**

**Strengths:**
- Rich visual descriptions are genuinely useful for understanding mode intent

**Issues:**

| Severity | Location | Problem | Fix |
|---|---|---|---|
| 🔴 High | `Bary_rainbow_mode` and `Chromatic_chaser_mode` listed | Neither of these appears in the `.py` file list scanned from `modes/`. They may be aspirational or renamed. | Verify against actual `.py` files. If not implemented, move to a "Planned Modes" section. If renamed, update the doc |
| 🔴 High | No orientation column | Zero documentation of which modes work on `horizontal` vs `vertical` segments — this is critical given the orientation-based segment system | Add an orientation compatibility note to each mode: "Works on: Both / Horizontal only / Vertical only" |
| 🔴 High | No `infos` parameter table | Zero documentation of which `infos.get()` config keys each mode reads | Either add inline to each mode description, or create a separate `modes/config_reference.md` |
| 🟡 Medium | No link from `modes/README.md` to `modes_description.md` | These two files in the same directory serve complementary purposes but aren't cross-referenced | Add link in `modes/README.md`: "See `modes_description.md` for visual descriptions of each mode" |

---

### 3.2 `modes/README.md` — Score: **4/10**

At 851 bytes covering a system with 19 modes, NumPy vectorization requirements, and a strict `run()` override contract, this file is critically underdeveloped.

**Missing (critical):**
- No mention of the `run()` vs `update()` distinction (yet SKILL.md calls this out as a key trap)
- No explanation of how `infos` dict is passed to modes
- No explanation of the `rgb_list` 2D numpy array structure that modes must write into
- No mention of the `smooth_segment_vectorized()` utility method

**Fix:** This file should be expanded to at minimum 200 lines. The SKILL.md content in sections 6 is the source — extract it here.

---

### 3.3 `music_events_architecture.md` — Score: **6/10**

**Strengths:**
- The Mermaid diagram correctly models the `STM → LTM → Novelty → Envelopes → Events` pipeline
- The API table at the end is the right pattern for developer integration

**Issues:**

| Severity | Location | Problem | Fix |
|---|---|---|---|
| 🔴 High | Section D: Acoustic Breakdown | Written as: `    # === D. The Acoustic Breakdown ===` | This is a Python comment artifact — the raw `#` is inside a code block with 8 leading spaces, likely copy-pasted from code. Format it as a proper markdown section: `### D. The Acoustic Breakdown` |
| 🔴 High | Two `## 3.` headings | The document has "## 3. The Pre-Cog Architecture" and then "## 3. The Architecture Diagram" (mis-numbered) | Renumber to 3 and 4 respectively |
| 🟡 Medium | `listener.vocals_present` in API table | Listed as a real property but is described as "Harmonic Product Spectrum isolates singing" — there is no other documentation of HPS being implemented | Mark as `[PLANNED]` or verify it's implemented |

---

### 3.4 `wabb-interface/` design docs — Score: **5/10**

**Structural Problem:** There are two separate directories with no explained relationship:
- `design rules/` — contains `lego_ui_developer_blueprint.md`, `live_deck.md`, `topology.md`
- `design signatures/` — contains `signature_design.md`, `webapp_architecture.md`, `wabb_technical_roadmap.md`

The naming "design signatures" is non-standard and opaque. It appears "signatures" = "specifications" or "design specs" but this is never explained anywhere.

**Implementation Reality Gap:** `webapp_architecture.md` describes 5 complete pages (Live Deck, Stage Architect, Topology Editor, Auto-DJ Tuning, System & Setup). The actual web app at `localhost:5173` may only implement 1-2 of these. Without a status column, an agent building a new page cannot tell which pages are:
- Fully implemented
- Partially implemented  
- Purely aspirational

**Fix:** Add a status table at the top of `webapp_architecture.md`:
```
| Page | Status |
|---|---|
| Live Deck | Implemented |
| Stage Architect | In Progress |
| Topology Editor | Planned |
...
```

---

### 3.5 `config/README.md` — Score: **5/10**

Critical gap: `app_config.json` is described as containing "global application variables (like maximum brightness, network ports, or audio thresholds)" but **zero actual keys are documented**.

The actual default keys (from `Main.py`) are:
```
startServer, useMicrophone, HARDWARE_MODE, printTimeOfCalculation, 
printModesDetails, printMicrophoneDetails, printAppDetails, 
printAsservmentDetails, printConfigurationLoads, printConfigChanges, 
modesToPrintDetails
```

**Fix:** Add a schema table to `config/README.md`:
```
| Key | Type | Default | Description |
|---|---|---|---|
| startServer | bool | false | Enables TCP port 12345. Set false during local dev to avoid socket collisions |
| HARDWARE_MODE | string | "auto" | "auto", "rpi", or "simulation" |
...
```

---

### 3.6 `vialactee_review.md` (root, 22,986 bytes) — Score: **4/10**

**Problem:** This 23KB file sits in the project root alongside `project_overview.md`. It is likely an audit report generated by a previous AI conversation session. Its presence creates a confusion risk:
- New developers might mistake it for documentation
- Its root-level placement makes it appear authoritative
- At 22KB, it is larger than most actual documentation files

**Fix:**
1. Move to `.agents/docs/archive/` or `playground/`  
2. Add a header: `# REVIEW ARTIFACT — Generated [date] — Not active documentation`

---

### 3.7 `hardware/README.md` + `.agents/PLAN.md` — Duplication Risk: **Critical**

The entire Mermaid hardware pipeline diagram exists verbatim in both files. This is the highest-priority duplication in the project.

**Risk:** When the architecture changes (e.g., switching from Bluetooth to direct Aux input), the diagram will be updated in one file and forgotten in the other, creating contradictory documentation.

**Fix:** Single source of truth. Keep the diagram in `.agents/PLAN.md` (rename to `hardware_pipeline.md`). Have `hardware/README.md` contain: `[See .agents/docs/hardware_pipeline.md for the full system diagram]`.

---

## 4. Python Inline Comments — Quick Assessment

**`Main.py`** — Well-commented for its complexity. Key observations:
- Line 102: `# 'auto', 'rpi', or 'simulation'` — inline schema hint is exactly right and should be duplicated to `config/README.md`
- Line 127: `# Python 3.10 compatible task cancellation (since you're not on 3.11+)` — excellent context
- Lines 139-147: Comments on the graceful shutdown pattern are precise and necessary
- **Missing:** No module-level docstring explaining what `Main.py` is the entrypoint for, which `project_overview.md` recommends agents read first

---

## 5. Priority Action Plan

### 🔴 CRITICAL (Fix immediately — creates agent errors or contradictions)

1. **Resolve `evaluate_context()` vs `update()` contradiction** between `core/README.md` and `core/precisions/transition_director.md` — verify against actual code
2. **Retitle or tombstone `.agents/PLAN.md`** — current future-tense language will cause agents to re-implement already-built features
3. **Delete duplicate hardware Mermaid diagram** from `hardware/README.md`
4. **Fix Acoustic Breakdown Python-comment artifact** in `music_events_architecture.md` (raw `# ===` code formatting)
5. **Document `app_config.json` schema** in `config/README.md` — the schema is only recoverable from `Main.py` default config block

### 🟡 HIGH (Fix before next agent session)

6. **Add orientation compatibility** to `modes/modes_description.md` (horizontal vs vertical per mode)
7. **Expand `modes/README.md`** — add `run()` vs `update()` distinction, `infos` injection pattern, `rgb_list` structure
8. **Fix double `## 3.` heading** in `music_events_architecture.md`
9. **Correct AGENT.md hardware section** — `hardware/` has 5 files, not just `Fake_leds.py`
10. **Add `HARDWARE_MODE` entry** and Transition_Director routing to `00_AGENT_NAVIGATION.md`

### 🟢 MEDIUM (Nice to have)

11. Add status column to `wabb-interface/webapp_architecture.md` (implemented vs planned pages)
12. Move `vialactee_review.md` out of root into `.agents/archive/` with a status header
13. Add `bpm_trust_architecture.md` reference to `00_AGENT_NAVIGATION.md` — it's not listed at all
14. Clarify the `data/configurations.json` vs `config/configurations.json` path in `mode_master.md`
15. Add a "design signatures" explanation header to that subdirectory

---

## 6. Documentation Debt Heatmap

| Area | Debt Level | Primary Risk |
|---|---|---|
| `hardware/` architecture docs | 🔴 HIGH | Diagram duplication will diverge |
| Mode system docs | 🔴 HIGH | Phantom modes, no orientation/config docs |
| `PLAN.md` staleness | 🔴 HIGH | Will cause agents to re-implement live features |
| `app_config.json` schema | 🔴 HIGH | Only recoverable from Main.py source |
| `core/` class diagram consistency | 🟡 MEDIUM | `evaluate_context` vs `update` contradiction |
| `wabb-interface` implementation status | 🟡 MEDIUM | Design docs describe aspirational pages as real |
| DSP constants documentation | 🟡 MEDIUM | Template weights and sweep intervals unlinkable to code |
| `vialactee_review.md` root placement | 🟡 MEDIUM | Confuses new contributors about source of truth |
