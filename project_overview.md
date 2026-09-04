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
        AudioIngest["AudioIngestion (FFT Math & Smoothers)"]
        AudioAnalyz["AudioAnalyzer (DSP and Rhythm Lookahead)"]
        ModeMaster["Mode_master (Orchestrator)"]
        TransDir["Transition_Director"]
    end

    Mic -->|Raw PCM Push| ListenerFacade
    Conn -->|Overrides / Requests| ModeMaster
    ModeMaster -->|Active playlist/config/segments| Conn
    ListenerFacade -->|Routes Audio| AudioIngest
    AudioIngest -->|Raw Values| AudioAnalyz
    AudioIngest -->|Raw FFT / Power| ListenerFacade
    ListenerFacade -->|Delayed Smoothed FFT / Power| ModeMaster
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

- **`/core`**: The brain of the project. Contains the algorithmic engines, asynchronous managers, the Audio Pipeline (`AudioIngestion`, `AudioAnalyzer`, `StructuralNoveltyDetector`, `RhythmConfig`, and the `Listener` facade), `BeatGridQuantizer`, `Webapp_instruction_logger`, and `Transition_Director`.
- **`/modes`**: The visual behavior library. Each file here defines a unique lighting animation pattern powered by numpy matrix math.
- **`/config`**: JSON files and managers detailing hardware profiles (`hardware_profile`: `"full"` vs `"small"` in `app_config.json`), unified physical geometry + Web App UI layout (`segments_full.json`, `segments_small.json`), and dynamic path resolution (`Configuration_manager.py`).
- **`/connectors`**: External communication handlers: `Connector.py` (HTTP/WebSocket server on port 8080 exposing `/ws`, `/api/topology`, and `/api/configurations`) and `Local_Microphone.py` (analog audio push stream).
- **`/hardware`**: Hardware abstractions. Dynamically provisions channels via `HardwareFactory._get_channel_specs()`, streaming UDP frames via `Udp_Sender` to either `Fake_ESP32` (Pygame visualizer) or physical ESP32 controllers, with `Rpi_NeoPixels` as a legacy direct GPIO fallback.
- **`/wabb-interface`**: A React-based web application serving as the remote controller. Loads segment layout dynamically from `/api/topology`, and playlists/configurations from the active profile via `/api/configurations`.
- **`/.agents`**: Core context, architectural rules, and technical specifications designed for AI agents working on the codebase.

---

## 3. Task-Based Navigation Map

Do not guess how the architecture works. Depending on the task you have been given, **you must read the corresponding files** before writing code:

- **If you are modifying or creating a Visual Mode (LED animation):**

  - 👉 Read `modes/README.md` and `modes/modes_description.md`, and review an existing mode to understand the `run()` loop and numpy matrix structure.
- **If you are working on Beat Detection or Rhythm Tracking:**

  - 👉 Read `.agents/docs/rhythm_tracker_architecture.md` and `.agents/docs/bpm_trust_architecture.md`. Understand the Anticipation Flywheel ("Oracle") before touching DSP code.
- **If you are working on Music Events (Drops, Verse/Chorus detection):**

  - 👉 Read `.agents/docs/music_events_architecture.md` (and companion `.agents/docs/music_events_architecture_potential_ideas.md`).
- **If you are working on Transitions between modes:**

  - 👉 Read `.agents/docs/transition_architecture.md` (and companion `.agents/docs/transition_architecture_potential_ideas.md`).
- **If you are touching the Main Orchestrator or Async loops:**

  - 👉 Read `.agents/AGENT.md` to understand our `asyncio` constraints and frame-independent math requirements.
- **If you are modifying Web App playlists, configurations, Mode Settings, Live Deck, or Topology state:**

  - 👉 Read `wabb-interface/README.md`, `wabb-interface/design rules/topology.md`, `connectors/README.md`, and `core/precisions/mode_master.md`. The active configuration store (`data/configurations_full.json` or `data/configurations_small.json`) is the source of truth for presets, and `GET /api/topology` provides dynamic segment geometry and cables. Preserve the `/ws` state snapshot flow (`hardwareProfile`, `mode_master_state`). Topology **LIVE** uses instructions for runtime segment mode/direction only; persisting presets uses `POST /api/configurations` from **MODIFY** or **BUILD** only. Per-mode tuning belongs to configuration-scoped `modeSettings` and flows through `Mode_master` over `/ws`.

---

## 4. Rules of Engagement (Pre & Post Task)

### 🛑 BEFORE Doing a Task:

1. **Locate the Context:** Find the relevant `.md` file from the navigation map above and read it.
2. **Check Configuration:** Never hardcode paths, pins, or IPs. Check `config/app_config.json` to see if a variable already exists.
3. **Verify Dependencies:** Understand that this project must run on both Windows (Pygame simulator) and Raspberry Pi (NeoPixels / ESP32). Ensure your imports do not break the `HardwareFactory.py` abstraction.

### ✅ AFTER Doing a Task:

1. **Self-Correction & Linting:**
   - Did you use blocking synchronous code (`time.sleep`)? If so, remove it and use `asyncio.sleep` or delta-time math.
   - Are your calculations frame-independent (using `fps_ratio`)?
2. **Update Documentation:** If you changed how a core algorithm works, added a new feature, or changed a configuration schema, **you must update the relevant `.md` file in `.agents/docs/`**.
3. **Simulator Check:** If possible, confirm that the code will execute properly under the `Fake_leds` Pygame simulator.
4. If you made temporary python files, remember to delete them or move them to the `playground/` directory.
