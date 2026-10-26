# Entity Architecture & Sector Contracts

This directory is the **single source of truth** for the sealed sector contracts of the Vialactée interactive LED chandelier. Each contract is also the only place where its sector's own outputs get a trust rating (see §3).

---

## 1. Sealed Entity Map

| Entity / Sector | Package | Front Door (`api.py`) | Canonical Contract | Governance Test |
| :--- | :--- | :--- | :--- | :--- |
| **Music Analyzer & DSP** | [`music/`](../../music/) | [`music/api.py`](../../music/api.py) | [`music_analyzer_contract.md`](music_analyzer_contract.md) | [`tests/governance/test_music_isolation.py`](../../tests/governance/test_music_isolation.py) & [`tests/governance/test_docs_parity.py`](../../tests/governance/test_docs_parity.py) |
| **Mood & Palettes** | [`mood/`](../../mood/) | [`mood/api.py`](../../mood/api.py) | [`mood_contract.md`](mood_contract.md) | [`tests/governance/test_mood_isolation.py`](../../tests/governance/test_mood_isolation.py) |
| **Transitions & Choreography** | [`transitions/`](../../transitions/) | [`transitions/api.py`](../../transitions/api.py) | [`transition_contract.md`](transition_contract.md) | [`tests/governance/test_transition_isolation.py`](../../tests/governance/test_transition_isolation.py) |
| **Visual Modes** | [`modes/`](../../modes/) | [`modes/Mode.py`](../../modes/Mode.py) | [`modes/MODE_RULES.md`](../../modes/MODE_RULES.md) (Part A) | *(no dedicated test; guidance only)* |
| **Core Orchestrator** | [`core/`](../../core/) | `Mode_master`, `Segment`, `TransitionBridge`, `CommandRouter`, `AppConfigStore` | [`core/README.md`](../../core/README.md) | [`tests/governance/test_axiom_07_code_governance.py`](../../tests/governance/test_axiom_07_code_governance.py) |
| **Hardware & Simulators** | [`hardware/`](../../hardware/) | `HardwareFactory.create_hardware(infos)` | [`docs/reference/coordinates_matrix.md`](../reference/coordinates_matrix.md) & [`docs/manuals/raspberry_pi_deployment.md`](../manuals/raspberry_pi_deployment.md) | [`tests/governance/test_axiom_03_geometry.py`](../../tests/governance/test_axiom_03_geometry.py) |
| **Async Connectors & Web UI** | [`connectors/`](../../connectors/) | `Connector`, `Local_Microphone`, `Local_AudioFile` | [`docs/architecture/api_and_wire_protocol.md`](../architecture/api_and_wire_protocol.md) | [`tests/governance/test_axiom_04_network_limits.py`](../../tests/governance/test_axiom_04_network_limits.py) |

---

## 2. One-Frame Dataflow (30 FPS Render Loop, 60 Hz DSP Clock)

```mermaid
flowchart LR
    MIC["Audio Input\n(Mic / AudioFile)"] -->|"PCM chunks"| ING["music/\nAudioIngestion + Analyzer + Context"]
    ING -->|"T_speaker ring buffer\n(music.api.Listener)"| MM["core/\nMode_master + TransitionBridge"]
    MM -->|"update(dt, scene)"| MOOD["mood/\nMoodService (mood.api)"]
    MOOD -->|"🟢 colors() (4,3) int32\n🟢 modifiers() (4,) float32"| MODE["modes/\nMode base class & 21 modes"]
    ING -->|"physical FFT & power\nrhythm gated by rhythm_lock"| MODE
    MM -->|"update(dt, MusicSnapshot)"| TRANS["transitions/\nTransitionService (transitions.api)"]
    TRANS -->|"TransitionOrders +\nin-place blend()"| SEG["core/\nSegment dual buffers"]
    MODE -->|"render(buffer)"| SEG
    SEG -->|"RGB frames"| HW["hardware/\nNeoPixels / UDP / Pygame"]
```

1. **Audio Ingestion & Lookahead Alignment (`music/`):** Raw PCM audio enters `Listener.process_raw_audio()`. `Listener.update()` advances the 5-second lookahead rhythm analyzer (`DyadicMetricalAudioAnalyzer` by default), writes spectral/novelty/rhythm frames into a zero-allocation circular ring buffer, pops speaker-aligned (`T_speaker`) features, and updates `listener.context` (`MusicalContextEngine`).
2. **Hardware Show (`hardware/`):** `Mode_master.update()` flushes the previous frame's RGB buffers to physical LEDs or the simulator.
3. **Mode Rendering (`modes/` & `core/Segment.py`):** Each `Segment` renders its active mode (and outgoing mode during `TRANSITION_DUAL`) into pre-allocated buffers and blends them in place via `TransitionService.blend()`.
4. **Mood Shock Absorber (`mood/`):** `TransitionBridge.build_music_snapshot(listener)` freezes the current frame's music state. `mood.update(dt, music.scene)` debounces (`0.30 s`) and cosine-crossfades (`2.5 s`) the `scene` heuristic into 🟢 `mood.modifiers()` (`[pace, sharpness, trail, accent_mix]`) and (`4.0 s` dwell, `3.0 s` crossfade) `mood.colors()`.
5. **Transition Scheduling (`transitions/`):** `transitions.update(dt, music)` advances cooldowns and lookahead countdowns, returning `TransitionOrders` on the frame a transition fires.

---

## 3. Signal Trust (Guidance)

Not all signals leaving `music/` have the same reliability. Trust is **engineering guidance** for people and AI agents writing or reviewing consumers. It is not a runtime type, not encoded in Python, and not enforced by a test.

**Single-source rule:** only the sector that *produces* a signal states our trust in it, in its own `*_contract.md`.

| Producer | Where trust is stated |
| :--- | :--- |
| `music/` (`Listener`, `listener.context`) | [`music_analyzer_contract.md`](music_analyzer_contract.md) (§2, §3), the only place with per-signal ratings |
| `mood/` (`colors()`, `modifiers()`, `get_status()`) | [`mood_contract.md`](mood_contract.md) |
| `transitions/` (`TransitionOrders`, `blend()`, `get_status()`) | [`transition_contract.md`](transition_contract.md) |

Consumer contracts link to the producer instead of repeating ratings. To change a signal's trust, edit only its row in the producer's contract.

| Tier | Meaning | General Handling Guidance |
| :--- | :--- | :--- |
| **🟢 HIGH** *(physical / pre-gated)* | Direct spectral measurement, or a signal already debounced and smoothed inside its own sealed room | Safe to drive brightness, spatial extent, or colour directly every frame without extra gating |
| **🟡 MEDIUM** *(confidence-gated)* | Tempo/phase flywheel estimate or rhythm badge that can drift on beatless intros, breakdowns, or complex polyrhythms | Gate or blend by confidence (`rhythm_lock`, `beat_trust`, `rhythm_salience`, `is_locked`, `beat_confidence`, or `Mode.beat_pulse()`), with a continuous fallback when confidence is `0.0` |
| **🟠 LOW** *(heuristic / predictive / uncalibrated)* | Macro scene classification, novelty, lookahead boundary prediction, or uncalibrated pitch bins prone to false positives and jitter | Avoid reading directly in concrete modes and avoid hard branches, velocity flips, or 1.5 s whiteouts. Absorb behind debounce/dwell (`mood/`), security cooldowns (`transitions/`), or sanctioned `Mode.py` envelope helpers (`self.drop_hit`, `self.drop_decay`) |
| **⚙️ CONFIG** *(user / hardware setting)* | User-configured scalar or static filterbank dimension forwarded through `Listener` | Safe to read as configuration parameters |

---

## 4. Automated Enforcement Summary

1. **Package Isolation (`test_{music,mood,transition}_isolation.py`):**
   * Nothing inside `music/`, `mood/`, or `transitions/` imports project code outside its own package.
   * Production code outside each room imports only `<room>.api`.
2. **Contract Drift Parity (`TestDocsParity.test_music_contract_parity`):**
   * Instantiates `Listener({"useMicrophone": False})` and verifies that every public attribute on `Listener` and `listener.context` appears as `` `name` `` in [`music_analyzer_contract.md`](music_analyzer_contract.md). It checks documentation completeness only, not trust tiers.
