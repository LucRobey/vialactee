# 🌌 Vialactée Master Documentation Portal

Welcome to the central documentation repository for **Vialactée** — the real-time audio-reactive LED chandelier orchestration system and DSP rhythm laboratory.

All documentation in this repository is governed by a strict **5-Tier Documentation Authority Matrix**. If any lower-tier document, comment, or external note contradicts a higher-tier document, the **higher tier always wins**.

---

## 🏛️ The 5-Tier Document Authority Matrix

| Tier | Category | Filesystem Location | Authority & RFC Policy | Automated Enforcement |
| :---: | :--- | :--- | :--- | :--- |
| **Tier 0** | **Untouchable Golden Axioms** | [`docs/axioms/`](./axioms/README.md) | **Immutable Core.** Governs physical, mathematical, and architectural laws. Barred from autonomous AI modification. Changes require Human Architectural RFC. | CI governance tests in `tests/governance/` |
| **Tier 1** | **Canonical Specifications & Contracts** | [`docs/contracts/`](./contracts/README.md), [`docs/architecture/`](./architecture/system_overview.md), [`docs/reference/`](./reference/modes_catalog.md) | **Authoritative System Truth.** Sealed sector contracts, public APIs, hardware geometry, and configuration schemas. Updated concurrently with code changes. | Parity, isolation & schema linters |
| **Tier 2** | **Operational Manuals** | [`docs/manuals/`](./manuals/mode_authoring_guide.md) | **Engineering & Deployment Guides.** Practical step-by-step guides for developers, operators, and agents. | Link & path resolution checks |
| **Tier 3** | **Living Memory & Skills** | [`.agents/skills/`](../.agents/skills/), [`work_history/`](../work_history/README.md) | **Continuous Agent Memory.** Session audit logs, procedural skills, and experimental ledgers updated every session to eliminate amnesia. | Skill governance & session log linting |
| **Tier 4** | **Ideas Scratchpad & Archives** | [`docs/ideas/`](./ideas/README.md), [`docs/archive/`](./archive/), [`archive/playground/`](../archive/playground/) | **Historical / Sandbox.** Prospective concepts, user scratchpads, and legacy snapshots. Never cited as system truth. | Prominent non-authoritative banners |

---

## 🧭 Task-Based Navigation Map (Where to Go Depending on Your Task)

| If you are working on... | Read First (Contract / Spec) | Operational Manual / Skill |
| :--- | :--- | :--- |
| **Visual Lighting Modes (`modes/`)** | [`docs/contracts/mode_contract.md`](./contracts/mode_contract.md)<br/>[`docs/reference/modes_catalog.md`](./reference/modes_catalog.md) | [`docs/manuals/mode_authoring_guide.md`](./manuals/mode_authoring_guide.md)<br/>[`.agents/skills/vialactee-mode-creator/SKILL.md`](../.agents/skills/vialactee-mode-creator/SKILL.md) |
| **Audio DSP, Beat Tracking & Musical Context (`music/`)** | [`docs/contracts/music_analyzer_contract.md`](./contracts/music_analyzer_contract.md)<br/>[`docs/architecture/audio_pipeline.md`](./architecture/audio_pipeline.md)<br/>[`docs/architecture/rhythm_engine.md`](./architecture/rhythm_engine.md)<br/>[`docs/architecture/musical_context_engine.md`](./architecture/musical_context_engine.md) | [`docs/manuals/developer_tools.md`](./manuals/developer_tools.md)<br/>[`.agents/skills/vialactee-dsp-engine/SKILL.md`](../.agents/skills/vialactee-dsp-engine/SKILL.md) |
| **Spatial Transitions (`transitions/`)** | [`docs/contracts/transition_contract.md`](./contracts/transition_contract.md)<br/>[`docs/architecture/core_orchestrator.md`](./architecture/core_orchestrator.md) | [`docs/architecture/system_overview.md`](./architecture/system_overview.md) |
| **Mood Palettes & Scene Crossfades (`mood/`)** | [`docs/contracts/mood_contract.md`](./contracts/mood_contract.md) | [`docs/architecture/musical_context_engine.md`](./architecture/musical_context_engine.md) |
| **Core Orchestrator & Segment Loop (`core/`)** | [`docs/architecture/core_orchestrator.md`](./architecture/core_orchestrator.md)<br/>[`docs/architecture/system_overview.md`](./architecture/system_overview.md) | [`docs/reference/configuration_schemas.md`](./reference/configuration_schemas.md) |
| **Web Remote Interface (`wabb-interface/` & `connectors/`)** | [`docs/architecture/api_and_wire_protocol.md`](./architecture/api_and_wire_protocol.md) | [`docs/manuals/web_interface_manual.md`](./manuals/web_interface_manual.md)<br/>[`docs/manuals/web_ui_design_system.md`](./manuals/web_ui_design_system.md) |
| **Hardware, ESP32 UDP & Raspberry Pi (`hardware/`)** | [`docs/architecture/hardware_abstraction.md`](./architecture/hardware_abstraction.md)<br/>[`docs/reference/coordinates_matrix.md`](./reference/coordinates_matrix.md) | [`docs/manuals/raspberry_pi_deployment.md`](./manuals/raspberry_pi_deployment.md) |
| **MIR Rhythm Research (`research/`)** | [`docs/axioms/AXIOM-08_RESEARCH_REGRESSION.md`](./axioms/AXIOM-08_RESEARCH_REGRESSION.md)<br/>[`research/README.md`](../research/README.md) | [`.agents/skills/vialactee-researcher/SKILL.md`](../.agents/skills/vialactee-researcher/SKILL.md)<br/>[`.agents/skills/vialactee-research-manager/SKILL.md`](../.agents/skills/vialactee-research-manager/SKILL.md) |

---

## 🏛️ Tier 0: The 9 Golden Axioms (`docs/axioms/`)
*Inviolable architectural and mathematical laws enforced by automated CI governance tests (`tests/governance/`). Never violate or weaken an Axiom.*

- **[`docs/axioms/README.md`](./axioms/README.md)** — Master Index of the 9 Golden Axioms
  1. **[`AXIOM-01_FRAME_BUDGET.md`](./axioms/AXIOM-01_FRAME_BUDGET.md)** — 30 FPS Visual Loop ($\le 20.0\text{ ms}$ budget) & 60 Hz Audio Sampling
  2. **[`AXIOM-02_ZERO_ALLOCATION.md`](./axioms/AXIOM-02_ZERO_ALLOCATION.md)** — Zero Dynamic Heap Allocations in Hot Path & Decoupled Telemetry
  3. **[`AXIOM-03_HARDWARE_GEOMETRY.md`](./axioms/AXIOM-03_HARDWARE_GEOMETRY.md)** — Physical Chandelier Geometry & Vertical Bottom-Up Invariant
  4. **[`AXIOM-04_NETWORK_PROTOCOLS.md`](./axioms/AXIOM-04_NETWORK_PROTOCOLS.md)** — UDP Packet MTU Safety ($\le 1,202\text{ B}$) & WebSocket Throttling ($\le 10\text{ Hz}$)
  5. **[`AXIOM-05_LOOKAHEAD_SYNC.md`](./axioms/AXIOM-05_LOOKAHEAD_SYNC.md)** — 5.0s Lookahead Buffer & Speaker Cone Back-Projection ($< 50\text{ ms}$)
  6. **[`AXIOM-06_PERCEPTUAL_RHYTHM.md`](./axioms/AXIOM-06_PERCEPTUAL_RHYTHM.md)** — Perceptual Invariance, Graceful Confidence Decay & `is_real_beat` Strobe Gating
  7. **[`AXIOM-07_CODE_GOVERNANCE.md`](./axioms/AXIOM-07_CODE_GOVERNANCE.md)** — 500-Line Module Cap, Monotonic Ratchet & Automated Test Enforcement
  8. **[`AXIOM-08_RESEARCH_REGRESSION.md`](./axioms/AXIOM-08_RESEARCH_REGRESSION.md)** — Clean-Room Evaluation & Zero-Regression Gate
  9. **[`AXIOM-09_PLATFORM_AGNOSTIC_DSP.md`](./axioms/AXIOM-09_PLATFORM_AGNOSTIC_DSP.md)** — Scoped DSP Mathematical Invariance Across OS & Input Sources

---

## 🔒 Tier 1A: Sealed Sector Contracts (`docs/contracts/`)
*The front-door specifications for each sealed sector of the codebase, including per-signal reliability/trust ratings (`HIGH` / `MEDIUM` / `LOW`).*

- **[`docs/contracts/README.md`](./contracts/README.md)** — Overview of the 4 Sealed Sectors (`music/`, `mood/`, `transitions/`, `modes/`)
- **[`music_analyzer_contract.md`](./contracts/music_analyzer_contract.md)** — `music.api` Front Door, Listener Signals, `MusicalContext` & Signal Trust Ratings
- **[`mood_contract.md`](./contracts/mood_contract.md)** — `mood.api` Front Door, Curated Palettes, `2.5s` Cosine Crossfade & `MoodModifiers`
- **[`transition_contract.md`](./contracts/transition_contract.md)** — `transitions.api` Front Door, 23 Transition Techniques & Cooperative Mode Handshake
- **[`mode_contract.md`](./contracts/mode_contract.md)** — `modes/` Sector Contract, Input/Output Doors, Signal Trust Handling & Perceptual Laws

---

## 📐 Tier 1B: Canonical Architecture & Reference Specifications (`docs/architecture/` & `docs/reference/`)
*Authoritative technical specifications reflecting the current production implementation.*

### System Architecture (`docs/architecture/`)
- **[`system_overview.md`](./architecture/system_overview.md)** — High-Level Dataflow, Dual-Loop Concurrency Model & Module Map
- **[`core_orchestrator.md`](./architecture/core_orchestrator.md)** — `Mode_master`, `Segment` Dual-Buffer Lifecycle, `TransitionBridge`, `CommandRouter` & `AppConfigStore`
- **[`audio_pipeline.md`](./architecture/audio_pipeline.md)** — Audio Ingestion, Dual-Resolution Mel Filterbanks (8 & 32 Bands), 12-Tone Chromagram & 5.0s Delay Queue
- **[`rhythm_engine.md`](./architecture/rhythm_engine.md)** — Multi-Band Onset Engine, Dyadic Metrical Hierarchy, Anticipation Flywheel ("Oracle") & Structural Novelty
- **[`structural_novelty.md`](./architecture/structural_novelty.md)** — Short-Term vs Long-Term Memory (STM/LTM) Novelty, Verse/Chorus Boundaries & Song-Cut Detection
- **[`musical_context_engine.md`](./architecture/musical_context_engine.md)** — 3-Tier Visual Conductor (`MusicalContextEngine`): Continuous Kinetics, 4 Macro Scenes & Micro Badges
- **[`hardware_abstraction.md`](./architecture/hardware_abstraction.md)** — Hardware Factory, Driver Selection (`auto`, `simulation`, `esp32`, `rpi`), UDP Ports `9001`–`9004` & Profiles
- **[`api_and_wire_protocol.md`](./architecture/api_and_wire_protocol.md)** — HTTP REST Endpoints, Full-Duplex WebSocket Schema & Binary UDP Pixel Framing

### Reference Catalogs (`docs/reference/`)
- **[`modes_catalog.md`](./reference/modes_catalog.md)** — Complete Visual & Behavioral Catalog of All 21 Active Mounted Modes & Settings Schemas
- **[`configuration_schemas.md`](./reference/configuration_schemas.md)** — Master Reference for `app_config.json`, `modes.json`, `segments_*.json` & Audio Presets
- **[`coordinates_matrix.md`](./reference/coordinates_matrix.md)** — Exact 2D Spatial Coordinate Grid & Segment Wiring Lookup Tables

---

## 🛠️ Tier 2: Operational Manuals (`docs/manuals/`)
*Step-by-step guides for developers, operators, and hardware deployment.*

- **[`mode_authoring_guide.md`](./manuals/mode_authoring_guide.md)** — How to Write, Vectorize, Configure & Register a New Visual Mode
- **[`raspberry_pi_deployment.md`](./manuals/raspberry_pi_deployment.md)** — Raspberry Pi Provisioning, ALSA Loopback, GPIO DMA & ESP32 Firmware Flashing
- **[`developer_tools.md`](./manuals/developer_tools.md)** — Using `Fake_leds.py`, `tools/mode_studio.py`, `tools/music_studio.py` & `run_benchmark.py`
- **[`web_interface_manual.md`](./manuals/web_interface_manual.md)** — Operating & Connecting to the React `wabb-interface` (Live Deck, Topology, Mode Settings, System)
- **[`web_ui_design_system.md`](./manuals/web_ui_design_system.md)** — Tactile Lego Design System, `LEGO_MATH` 30px Stud Grid, `<FitBoard>` & Component Architecture

---

## 🤖 Tier 3: AI Agent Governance & Skills (`.agents/` & `work_history/`)
*Operational routing and domain-specific instructions for autonomous coding and research agents.*

- **[`.agents/AGENT.md`](../.agents/AGENT.md)** — Master Agent Entry Point & Verification Checklist
- **[`.agents/CONSTITUTION.md`](../.agents/CONSTITUTION.md)** — Agent Constitutional Summary (Mirroring Tier 0 Axioms)
- **[`.agents/skills/`](../.agents/skills/)** — Domain-Specific Skills (`vialactee-project`, `vialactee-dsp-engine`, `vialactee-mode-creator`, `vialactee-researcher`, `vialactee-research-manager`)
- **[`work_history/README.md`](../work_history/README.md)** — Chronological Engineering Session Ledger

---

## 💡 Tier 4: Ideas Scratchpad & Historical Archive (`docs/ideas/` & `docs/archive/`)
*Non-authoritative future brainstorming and retired historical records. Do **not** treat Tier 4 files as current system truth.*

- **[`docs/ideas/README.md`](./ideas/README.md)** — Ideas Hub Index:
  - **[`docs/ideas/IDEAS.md`](./ideas/IDEAS.md)** — Personal Next-Session Scratchpad
  - **[`docs/ideas/transition_potential_ideas.md`](./ideas/transition_potential_ideas.md)** — Prospective Transition Concepts
  - **[`docs/ideas/music_events_potential_ideas.md`](./ideas/music_events_potential_ideas.md)** — Prospective Music Event Concepts
- **[`docs/archive/AGENT_HANDOFF_2026-09-05.md`](./archive/AGENT_HANDOFF_2026-09-05.md)** — Archived September 2026 Handoff Snapshot
