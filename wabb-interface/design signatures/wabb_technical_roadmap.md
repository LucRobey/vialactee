# Wabb-Interface: Technical Roadmap & Backend Changes

This document outlines the technical changes, backend modifications, and new capabilities required to build the upcoming Web Interface (Wabb-Interface). It focuses purely on functional and system-level features, deferring visual UI/UX design until implementation.

## 📡 1. Core Bridge & State Management
*To establish a high-frequency data pipeline between the Python backend and the web client.*

*   **Bi-Directional WebSockets:** Implemented through `connectors/Connector.py` using aiohttp `/ws` on port `8080`. The browser sends page/action instructions and receives backend state snapshots.
*   **JSON State Schema:** Implemented as `mode_master_state`, built by `Mode_master.get_state_snapshot()`. It currently includes:
    *   Active modes and directions per segment.
    *   Global luminosity and sensibility.
    *   Active playlist, active/queued configuration, selected transition, transition lock, and transition progress.
    *   Segment blocked/transition status.
*   **The "Pending" State Manager:** Implement backend logic to hold "Staged Transitions" (batch changes across multiple segments) in memory until the UI explicitly sends an `EXECUTE` command to flush them to the LEDs simultaneously.

---

## 🎛️ 2. Deep Parameter Injection & Modifiers
*To expose mathematical control over the running animations directly to the operator.*

*   **Mode-Specific Parameter Introspection:** Modify the mode classes (e.g., `Rainbow_mode`, `Pulsar_mode`) to expose their internal global variables (like `ball_size`, `tail_length`, `color_density`). The UI will dynamically read these and generate sliders to tweak them live.
*   **Global Speed Multiplier:** Implement an override variable in `Mode_master.py` that scales `delta_time` or the internal logic timers of all modes (e.g., `0.5x`, `1x`, `2x`).
*   **Global Modifiers (The Glitter Mask):** Implement a global overlay function. This applies effects (like random white twinkling) on top of the calculated frame *after* the base mode computes, but *before* the frame is pushed to hardware.

---

## 🗺️ 3. Segment Routing & Topology
*To control how data flows to specific physical areas of the stage.*

*   **Live Topology Editor:** Allow the UI to push updated X/Y coordinates for segments back to the Pi. This overwrites the spatial mapping used by the `transition_architecture` on the fly, allowing for physical stage layout changes.
*   **Segment Locking & Mode Configurations:** 
    *   Build logic to "Lock" specific segments to their currently assigned mode.
    *   Locked segments become immune to the Auto-DJ, Global Transitions, or randomized drops.
    *   Allow the UI to save this specific combination of locked/unlocked segments and their running modes as a "Global Mode Configuration" preset.
*   **Segment Masking/Muting:** Build mathematical logic to selectively intercept and blackout specific segments, effectively muting them without changing their underlying mode state.
*   **Virtual Grouping:** Create a system to define arbitrary groups of segments (e.g., "Left Wing") via the UI so commands can be targeted to clusters.

---

## 🤖 4. Show Automation & Presets
*To reduce cognitive load for the operator during a live show.*

*   **Snapshot Save/Load:** Implemented for playlist/configuration snapshots through `data/configurations.json` and `/api/configurations`. Vite serves the endpoint in development; `Connector.py` serves it in Python-backed operation and reloads `Mode_master` after writes.
*   **Auto-Transition Engine & Timing:** Implement a backend toggle that automatically selects and executes a random, safe transition.
    *   Triggered every *X* minutes or *Y* song drops.
    *   Must allow the UI to configure both the interval between transitions *and* the duration/speed of the transition sweep itself.
*   **The Director's Override (Drop Action):** Wire a specific command that temporarily suspends the current state, forces a hardcoded macro (like max-brightness white strobe), and triggers a massive global transition exactly when the button is released.
*   **Dynamic Palette Injection:** Implement an endpoint to receive a new primary/secondary color pair and seamlessly blend it into the running generative modes.

---

## ⚙️ 5. Telemetry, Hardware & External Integrations
*For system stability, safety, and physical control.*

*   **Live Telemetry Stream:** Extract Raspberry Pi CPU temperature, RAM usage, and main loop FPS. Broadcast this continuously over the WebSocket for the UI to monitor thermal throttling.
*   **Remote Process Management:** Create secure endpoints to remotely restart the main Python script or reboot the Raspberry Pi hardware directly from the web interface.
*   **Master Power Limiter:** Implement a mathematical ceiling on RGB values just before hardware output (in `HardwareFactory` or `Mode_master`) to prevent overdrawing the power supply.
*   **Web MIDI Support:** Expose WebSocket hooks specifically designed to map to the browser's Web MIDI API, allowing physical MIDI controllers (like a Launchpad) to trigger UI events and macros natively.
