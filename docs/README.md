# 🌌 Vialactée Documentation Master Portal

Welcome to the central documentation knowledge base for the **Vialactée** music-reactive chandelier project.

All documentation in this repository is strictly organized into a **5-Tier Authority Hierarchy**, establishing clear mutability boundaries, source-of-truth definitions, and automated verification rules.

---

## 🏛️ The 5-Tier Document Authority Matrix

| Tier | Category | Filesystem Location | Authority & RFC Policy | Automated Enforcement |
|:---:|:---|:---|:---|:---|
| **Tier 0** | **Untouchable Golden Axioms** | [`docs/axioms/`](./axioms/README.md) | **Immutable Core.** Governs physical, mathematical, and architectural laws. Barred from autonomous AI modification. Changes require Human Architectural RFC. | CI governance tests in `tests/governance/` |
| **Tier 1** | **Canonical Specifications** | [`docs/architecture/`](./architecture/system_overview.md), [`docs/reference/`](./reference/modes_catalog.md) | **Authoritative System Truth.** Public APIs, hardware geometry, and configuration schemas. Updated concurrently with code changes. | Parity & schema linters |
| **Tier 2** | **Operational Manuals** | [`docs/manuals/`](./manuals/mode_authoring_guide.md) | **Engineering & Deployment Guides.** Practical step-by-step guides for developers, operators, and agents. | Pointer validation & manual review |
| **Tier 3** | **Living Memory & Skills** | [`.agents/skills/`](../.agents/skills/), [`work_history/`](../work_history/README.md) | **Continuous Agent Memory.** Session audit logs, procedural skills, and experimental ledgers updated every session to eliminate amnesia. | Session log format linting |
| **Tier 4** | **Exploratory & Archives** | [`docs/archive/`](./archive/), [`archive/playground/`](../archive/playground/) | **Historical / Sandbox.** Prospective concepts, deprecation logs, and legacy research spikes. Never cited as system truth. | Prominent archive disclaimer banners |

---

## 📚 Documentation Directory Map

### 1. [Tier 0: Golden Axioms (`docs/axioms/`)](./axioms/README.md)
The 9 inviolable foundational principles governing real-time execution, memory bounds, network limits, and math invariance:
- [AXIOM-01: Real-Time Frame Budget & Execution Pacing](./axioms/AXIOM-01_FRAME_BUDGET.md)
- [AXIOM-02: Zero Dynamic Heap Allocations in Render Hot Path](./axioms/AXIOM-02_ZERO_ALLOCATION.md)
- [AXIOM-03: Physical Chandelier Geometry & The Vertical Invariant](./axioms/AXIOM-03_HARDWARE_GEOMETRY.md)
- [AXIOM-04: Network Transport Protocols & UDP MTU Bounds](./axioms/AXIOM-04_NETWORK_PROTOCOLS.md)
- [AXIOM-05: Predictive Lookahead & Speaker Back-Projection](./axioms/AXIOM-05_LOOKAHEAD_SYNC.md)
- [AXIOM-06: Perceptual Invariance & Real-Beat Gating](./axioms/AXIOM-06_PERCEPTUAL_RHYTHM.md)
- [AXIOM-07: Code Governance & The 500-Line Ratchet](./axioms/AXIOM-07_CODE_GOVERNANCE.md)
- [AXIOM-08: Scientific Clean-Room Zero-Regression Gate](./axioms/AXIOM-08_RESEARCH_REGRESSION.md)
- [AXIOM-09: Scoped DSP Math & Processing Invariance](./axioms/AXIOM-09_PLATFORM_AGNOSTIC_DSP.md)

### 2. [Tier 1: Architecture Specifications (`docs/architecture/`)](./architecture/system_overview.md)
Authoritative blueprints for each architectural domain:
- [System Overview & Execution Flow](./architecture/system_overview.md)
- [Audio Ingestion & Feature Pipeline](./architecture/audio_pipeline.md)
- [Rhythm Tracking & Anticipation Flywheel ("Oracle")](./architecture/rhythm_engine.md)
- [Structural Novelty & Drop Detection](./architecture/structural_novelty.md)
- [Transition Director & Spatial Engine](./architecture/transition_director.md)
- [Hardware Abstraction & Dynamic Profiles](./architecture/hardware_abstraction.md)
- [API, WebSocket & Wire Protocol](./architecture/api_and_wire_protocol.md)

### 3. [Tier 1: Reference Specifications (`docs/reference/`)](./reference/modes_catalog.md)
Comprehensive catalogs and schemas:
- [Configuration Schemas & Parameter Master](./reference/configuration_schemas.md)
- [Modes Visual Catalog (22 Active Modes)](./reference/modes_catalog.md)
- [Coordinates Matrix & Channel Mapping](./reference/coordinates_matrix.md)

### 4. [Tier 2: Manuals & Operations (`docs/manuals/`)](./manuals/mode_authoring_guide.md)
Operational how-to guides:
- [Mode Authoring Guide (Vectorization, Base Class, Schemas)](./manuals/mode_authoring_guide.md)
- [Raspberry Pi 4 Deployment & Service Management](./manuals/raspberry_pi_deployment.md)
- [Developer Tools & Simulators Guide](./manuals/developer_tools.md)
- [Web Interface Operator Manual](./manuals/web_interface_manual.md)

### 5. [Tier 4: Concept Archive (`docs/archive/`)](./archive/)
Prospective research concepts and historical review archives:
- [Prospective Transitions Concepts](./archive/prospective_transitions.md)
- [Prospective Music Events Concepts](./archive/prospective_music_events.md)
- [Legacy Research Spikes & Notebooks Archive](../archive/playground/)
