# Vialactée Project Overview & AI Guidelines

Welcome to the **Vialactée** project! If you are an AI agent working on this codebase, **this is your primary entrypoint.** Read this file completely before taking any action.

Vialactée is an asynchronous Python orchestration server designed to run on a Raspberry Pi and control a 1,304-LED music-reactive chandelier. It listens to live audio in real-time, performs deep algorithmic analysis (beat detection, frequency extraction, structural event detection), and drives the physical LED arrays using mathematically precise visual modes.

It features a non-causal audio lookahead buffer, seamless asynchronous orchestration, and an interactive Web Interface for real-time control.

---

## 1. Architecture Flow

```mermaid
graph TD
    %% External Inputs
    subgraph Inputs [External Data and Interfaces]
        Wabb["Wabb-Interface (React Web App)"]
        RoomAudio["Live Audio"]
    end

    %% Network and Audio Ingestion
    subgraph Connectors [Connectors]
        Conn["Connector (HTTP/WS Server)"]
        Mic["Local_Microphone (Raw PCM Push)"]
    end

    Wabb -->|User Commands / Config JSON API| Conn
    Conn -->|Mode Master State Snapshots| Wabb
    RoomAudio --> Mic

    %% Core Processing Engine
    subgraph Core [Core Engine]
        Config["Configuration_manager"]
        ListenerFacade["Listener (Facade & 5s Delay Buffer)"]
        AudioIngest["AudioIngestion (Dual-Res Mel Filterbanks: 8/32 Bands)"]
        AudioAnalyz["MultiBandOnsetAudioAnalyzer (Production 32-Band Onset Engine)<br/><i>Fallback: AudioAnalyzer (Legacy Single-ODF)</i>"]
        ModeMaster["Mode_master (Orchestrator)"]
        TransDir["Transition_Director"]
    end

    Mic -->|Raw PCM Push| ListenerFacade
    Conn -->|Overrides / Requests| ModeMaster
    ModeMaster -->|Active playlist/config/segments| Conn
    ListenerFacade -->|Routes Audio| AudioIngest
    AudioIngest -->|32-Band Mel Energies| AudioAnalyz
    AudioIngest -->|8-Band Smoothed FFT / Power| ListenerFacade
    ListenerFacade -->|Delayed Smoothed 8-Band FFT / Power| ModeMaster
    AudioAnalyz -->|BPM / Phase| ModeMaster
    AudioAnalyz -->|Structural Music Drops| TransDir
    TransDir -->|Commands Configuration Changes| ModeMaster

    %% Animation and Visuals
    subgraph Visuals [Visual Algorithms]
        Mode["Mode Base Class (Rainbow, etc)"]
        Seg["Segment (Logical LED Strip)"]
    end

    Config -->|Loads app_config.json| ModeMaster
    Config -->|Resolves segments config (full/small)| ModeMaster
    Config -->|Resolves segments config (full/small)| TransDir

    ModeMaster -->|Calls segment update| Seg
    Seg -->|Queries State and Progress| TransDir
    Seg -->|Executes mode update| Mode
    Mode -->|Mutates RGB buffer| Seg
    Seg -->|Flushes to Global LED Array| HwFac

    %% Hardware Output Layer
    subgraph Hardware [Hardware Abstraction]
        HwFac["HardwareFactory (Dynamic Channels)"]
        UDP["Udp_Sender (Network UDP Packets)"]
        FakeESP["Fake_ESP32 Subprocess -> Fake_leds (Pygame Window)"]
        PhysESP["Physical ESP32 Chandelier Controller"]
        Rpi["Rpi_NeoPixels (Legacy Raspberry Pi GPIO)"]
    end

    ModeMaster -->|Flushes Frame Array| HwFac
    HwFac -->|Simulation / Auto on PC| UDP
    HwFac -->|Physical ESP32 Network| UDP
    HwFac -->|Direct Pi GPIO Fallback| Rpi
    UDP -->|UDP 127.0.0.1:9001/9002| FakeESP
    UDP -->|UDP 192.168.0.26:9001/9002| PhysESP
```

---

## 2. General Project Structure

Here is a breakdown of the core directories in this project:

- **`/core`**: The brain of the project. Contains the algorithmic engines, asynchronous managers, the Audio Pipeline (`AudioIngestion`, `MultiBandOnsetAudioAnalyzer`, `comb_kernels`, `AudioAnalyzer`, `StructuralNoveltyDetector`, `RhythmConfig`, and the `Listener` facade), `BeatGridQuantizer`, `Webapp_instruction_logger`, and `Transition_Director`.
- **`/modes`**: The visual behavior library. Each file here defines a unique lighting animation pattern powered by numpy matrix math.
- **`/config`**: JSON files and managers detailing hardware profiles (`hardware_profile`: `"full"` vs `"small"` in `app_config.json`), unified physical geometry + Web App UI layout (`segments_full.json`, `segments_small.json`), and dynamic path resolution (`Configuration_manager.py`).
- **`/connectors`**: External communication handlers: `Connector.py` (HTTP/WebSocket server on port 8080 exposing `/ws`, `/api/topology`, and `/api/configurations`) and `Local_Microphone.py` (analog audio push stream).
- **`/hardware`**: Hardware abstractions. Dynamically provisions channels via `HardwareFactory._get_channel_specs()`, streaming UDP frames via `Udp_Sender` to either `Fake_ESP32` (Pygame visualizer) or physical ESP32 controllers, with `Rpi_NeoPixels` as a legacy direct GPIO fallback.
- **`/wabb-interface`**: A React-based web application serving as the remote controller. Loads segment layout dynamically from `/api/topology`, and playlists/configurations from the active profile via `/api/configurations`.
- **`/research`**: The offline MIR laboratory. Houses immutable evaluation benchmark suites (`run_benchmark.py`, synthetic stress tests, BeatNet neural references, Ballroom academic dataset) and the iterative experiment ledger (`LEADERBOARD.md`, candidate models in `research/experiments/models/`). Kept strictly separate from the live embedded Raspberry Pi runtime.
- **`/.agents`**: Core context, constitution, and specialized skills (`.agents/skills/`) for AI agents working on the codebase.
- **`/work_history`**: Permanent chronological audit trail and memory ledger where agents and developers log sessions using `TEMPLATE.md` to prevent agent amnesia. Master index is kept in `work_history/README.md`.
- **`/docs`**: Canonical system documentation root organized under the 5-Tier Authority Matrix. Contains Golden Axioms (`docs/axioms/`), Architecture Specs (`docs/architecture/`), Reference Catalogs (`docs/reference/`), and Operations Manuals (`docs/manuals/`).

---

## 3. The 9 Golden Axioms (Tier 0 Core)

All code and architecture changes must strictly obey the [9 Untouchable Golden Axioms](docs/axioms/README.md):
- [AXIOM-01: Real-Time Frame Budget (30 FPS / 20ms compute)](docs/axioms/AXIOM-01_FRAME_BUDGET.md)
- [AXIOM-02: Zero Dynamic Heap Allocations in Render Loop](docs/axioms/AXIOM-02_ZERO_ALLOCATION.md)
- [AXIOM-03: Physical Chandelier Geometry & Vertical Invariant](docs/axioms/AXIOM-03_HARDWARE_GEOMETRY.md)
- [AXIOM-04: Network Protocols & UDP MTU Bounds (<= 1202 B)](docs/axioms/AXIOM-04_NETWORK_PROTOCOLS.md)
- [AXIOM-05: Predictive Lookahead & Speaker Back-Projection (< 50ms sync)](docs/axioms/AXIOM-05_LOOKAHEAD_SYNC.md)
- [AXIOM-06: Perceptual Invariance & Real-Beat Gating](docs/axioms/AXIOM-06_PERCEPTUAL_RHYTHM.md)
- [AXIOM-07: Code Governance & The 500-Line Ratchet](docs/axioms/AXIOM-07_CODE_GOVERNANCE.md)
- [AXIOM-08: Scientific Clean-Room Zero-Regression Gate](docs/axioms/AXIOM-08_RESEARCH_REGRESSION.md)
- [AXIOM-09: Scoped DSP Math & Processing Invariance](docs/axioms/AXIOM-09_PLATFORM_AGNOSTIC_DSP.md)

---

## 4. Task-Based Navigation Map

Do not guess how the architecture works. Depending on the task you have been given, **you must read the corresponding files** before writing code:

- **If you are modifying or creating a Visual Mode (LED animation):**
  - 👉 Read [`docs/manuals/mode_authoring_guide.md`](docs/manuals/mode_authoring_guide.md), [`docs/reference/modes_catalog.md`](docs/reference/modes_catalog.md), `modes/README.md`, and `modes/MODE_RULES.md`. Review an existing mode to understand the `render()` loop and numpy matrix structure.
- **If you are working on Audio Ingestion or DSP Math:**
  - 👉 Read [`docs/architecture/audio_pipeline.md`](docs/architecture/audio_pipeline.md). Understand the Mel filterbanks, Chromagram extraction, and the non-causal 5-second ring buffer.
- **If you are working on Beat Detection or Rhythm Tracking:**
  - 👉 Read [`docs/architecture/rhythm_engine.md`](docs/architecture/rhythm_engine.md) and [`docs/axioms/AXIOM-05_LOOKAHEAD_SYNC.md`](docs/axioms/AXIOM-05_LOOKAHEAD_SYNC.md). Understand the Anticipation Flywheel ("Oracle") and $T_{\text{speaker}}$ back-projection before touching DSP code.
- **If you are working on Music Events (Drops, Verse/Chorus detection):**
  - 👉 Read [`docs/architecture/structural_novelty.md`](docs/architecture/structural_novelty.md).
- **If you are working on Transitions between modes:**
  - 👉 Read [`docs/architecture/transition_director.md`](docs/architecture/transition_director.md) and [`core/Transition_Engine.py`](core/Transition_Engine.py).
- **If you are touching Hardware, Network, or Output Drivers:**
  - 👉 Read [`docs/architecture/hardware_abstraction.md`](docs/architecture/hardware_abstraction.md) and [`docs/axioms/AXIOM-04_NETWORK_PROTOCOLS.md`](docs/axioms/AXIOM-04_NETWORK_PROTOCOLS.md).
- **If you are modifying Web App playlists, configurations, Mode Settings, Live Deck, or Topology state:**
  - 👉 Read [`docs/architecture/api_and_wire_protocol.md`](docs/architecture/api_and_wire_protocol.md), [`docs/reference/configuration_schemas.md`](docs/reference/configuration_schemas.md), and `wabb-interface/README.md`.
- **If you are deploying or configuring the Raspberry Pi 4:**
  - 👉 Read [`docs/manuals/raspberry_pi_deployment.md`](docs/manuals/raspberry_pi_deployment.md).

---

## 5. Rules of Engagement (Pre & Post Task)

### 🛑 BEFORE Doing a Task:
1. **Consult Golden Axioms:** Ensure your planned design does not violate any of the 9 Golden Axioms.
2. **Locate the Context:** Find the relevant specification from the navigation map above and read it.
3. **Check Configuration:** Never hardcode paths, pins, or IPs. Check `config/app_config.json` to see if a variable already exists. Resolve paths dynamically via `config/Configuration_manager.py`.
4. **Verify Dependencies:** Understand that this project runs on both Windows (Pygame simulator) and Raspberry Pi (NeoPixels / ESP32). Ensure imports preserve the `HardwareFactory.py` abstraction.

### ✅ AFTER Doing a Task:
1. **Self-Correction & Linting:**
   - Did you use blocking synchronous code (`time.sleep`)? If so, remove it and use `asyncio.sleep` or delta-time math.
   - Are your calculations frame-independent (using `fps_ratio`)?
   - Did your changes stay within the 500-line code governance cap (`AXIOM-07`)?
2. **Update Documentation:** If you changed an algorithm, API, or configuration schema, **you must update the corresponding specification in `docs/`**.
3. **Simulator Check:** If possible, confirm that the code executes properly under the `Fake_leds` Pygame simulator.
4. **Fast Governance Tests:** Run `python -m pytest tests/test_code_governance.py` to confirm code health.
5. **Mandatory Work History Logging:** Every engineering or research session that modifies code or project configuration **must create or update a dated entry in `work_history/`** following [`work_history/TEMPLATE.md`](work_history/TEMPLATE.md) and add it to the chronological table in [`work_history/README.md`](work_history/README.md).

