# System Architecture Overview

> **Location:** `docs/architecture/system_overview.md` (Tier 1 Canonical Specification)  
> **Enforcing Axioms:** [AXIOM-01](../axioms/AXIOM-01_FRAME_BUDGET.md), [AXIOM-02](../axioms/AXIOM-02_ZERO_ALLOCATION.md), [AXIOM-07](../axioms/AXIOM-07_CODE_GOVERNANCE.md), [AXIOM-09](../axioms/AXIOM-09_PLATFORM_AGNOSTIC_DSP.md)

Vialactée is an asynchronous, real-time Python orchestration server and audio-visual DSP engine designed to run on a Raspberry Pi 4B (and desktop simulation environments) to drive an interactive, mathematically mapped LED chandelier (1,304 WS2812B LEDs across 11 spatial segments).

---

## 1. Top-Level Execution Pipeline

```mermaid
graph TD
    %% External Inputs
    subgraph Inputs [External Audio & UI]
        Wabb["Wabb-Interface (React + Vite Web App)"]
        RoomAudio["Live Audio (Microphone / Spotify Loopback)"]
    end

    %% Network & Audio Ingestion Layer
    subgraph Connectors [Connectors Layer]
        Conn["Connector (aiohttp REST / WebSocket :8080)"]
        Mic["Local_Microphone (PortAudio PCM Stream)"]
    end

    Wabb -->|WebSocket Instructions / Presets| Conn
    Conn -->|State Snapshots (<= 10Hz)| Wabb
    RoomAudio --> Mic

    %% Core Processing Engine
    subgraph Core [Core Orchestration Engine]
        ListenerFacade["Listener (Facade & 5.0s Lookahead Queue)"]
        AudioIngest["AudioIngestion (Dual-Res Mel: 8 & 32 Bands)"]
        AudioAnalyz["MultiBandOnsetAudioAnalyzer (32-Band Onset Engine)"]
        ModeMaster["Mode_master (Central Orchestrator)"]
        TransDir["Transition_Director (State Machine)"]
    end

    Mic -->|Raw PCM Push| ListenerFacade
    Conn -->|Commands & Overrides| ModeMaster
    ModeMaster -->|State Dirty & Active Presets| Conn
    ListenerFacade -->|PCM Chunks| AudioIngest
    AudioIngest -->|32-Band Mel Energies| AudioAnalyz
    AudioIngest -->|8-Band Smoothed FFT & Power| ListenerFacade
    ListenerFacade -->|Delayed FFT & Beat Context| ModeMaster
    AudioAnalyz -->|BPM, Phase & Transients| ModeMaster
    AudioAnalyz -->|Structural Changes & Drops| TransDir
    TransDir -->|Commands Mode Transitions| ModeMaster

    %% Visual Rendering Layer
    subgraph Visuals [Visual Animation Pipeline]
        Mode["Mode Subclasses (22 Active Modes)"]
        Seg["Segment (Logical LED Strip)"]
        TransEng["Transition_Engine (Spatial Blends)"]
    end

    ModeMaster -->|Update Ticks (30 FPS)| Seg
    Seg -->|Queries Transition State| TransDir
    Seg -->|Renders Mode Animation| Mode
    Mode -->|Mutates RGB Buffer| Seg
    Seg -->|Applies Spatial Masks| TransEng
    Seg -->|Flushes Frame Arrays| HwFac

    %% Hardware Output Layer
    subgraph Hardware [Hardware Abstraction]
        HwFac["HardwareFactory (Channel Allocator)"]
        UDP["Udp_Sender (UDP Port 9001/9002)"]
        FakeESP["Fake_ESP32 Subprocess -> Fake_leds (Pygame Window)"]
        PhysESP["Physical ESP32 Microcontroller"]
        Rpi["Rpi_NeoPixels (Direct GPIO SPI Fallback)"]
    end

    HwFac -->|Simulation Mode| UDP
    HwFac -->|ESP32 Network Mode| UDP
    HwFac -->|Raspberry Pi GPIO Mode| Rpi
    UDP -->|UDP 127.0.0.1:9001/9002| FakeESP
    UDP -->|UDP 192.168.0.26:9001/9002| PhysESP
```

---

## 2. Real-Time Async Execution Model

1. **The 30.0 FPS Visual Loop:**
   - Managed in `Mode_master.update()`.
   - Budget: 33.33 ms frame period, $\le 20.0\text{ ms}$ compute cap on Pi 4B (AXIOM-01).
   - Hot-path operations are zero-allocation NumPy slice assignments (AXIOM-02).
2. **The 60.0 Hz Audio Onset Sampling:**
   - Audio feature extraction in `core/MultiBandOnsetAudioAnalyzer.py` samples at 60 Hz to ensure precise onset detection.
   - Lookahead buffer maintains a continuous 5.0-second delay queue, back-projecting beat phase to speaker time $T_{\text{speaker}}$ (AXIOM-05).
3. **Decoupled Telemetry:**
   - `Connector.on_frame_tick()` executes in 0.0 ms when no clients are connected.
   - When clients are active, updates broadcast on state mutations (`mode_master._state_dirty`), transition edges, or a 1.0 Hz background heartbeat (AXIOM-04).
