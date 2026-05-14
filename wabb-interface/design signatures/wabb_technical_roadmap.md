# Wabb-Interface: Technical Roadmap & Backend Changes

This document tracks the backend and system-level capabilities the Web Interface (Wabb-Interface) relies on. Items below are flagged as **implemented**, **partial**, or **future** based on the current React + Python state.

## 📡 1. Core Bridge & State Management
*To establish a high-frequency data pipeline between the Python backend and the web client.*

*   **Bi-Directional WebSockets (implemented):** `connectors/Connector.py` exposes aiohttp `/ws` on port `8080`. The browser sends page/action instructions and receives backend state snapshots.
*   **JSON State Schema (implemented):** `Mode_master.get_state_snapshot()` builds the `mode_master_state` payload. Highlights:
    *   Active modes and directions per segment, plus blocked / target-mode / in-transition flags.
    *   Global luminosity, sensibility, and **auto-transition time** (`autoTransitionTime`, in seconds).
    *   Active playlist, active/queued configuration, selected transition, transition lock, and transition progress.
    *   `availableModes` catalog plus per-mode descriptors (`modeSettingsCatalog`) and the effective `modeSettings` for the active configuration.
    *   Nested `system` block (telemetry + action capabilities, see §5).
*   **Pending State Manager (future):** Backend-side "Staged Transitions" that batch changes across many segments until the UI flushes them with an `EXECUTE` command. The frontend already keeps per-segment pending edits client-side; the multi-segment staging API is not yet implemented.

---

## 🎛️ 2. Deep Parameter Injection & Modifiers
*To expose mathematical control over the running animations directly to the operator.*

*   **Mode-Specific Parameter Introspection (implemented):** Each `Mode` subclass declares its settings; `Mode_master` ships the descriptors through `modeSettingsCatalog`. The UI renders `switch`, `slider`, and `list` controls dynamically for every loaded mode that declares settings.
*   **Auto-Transition Engine (partial):** `mode_master_state` exposes `autoTransitionTime` and the Live Deck slider sends `set_auto_transition_time` so Mode_master can rotate the active configuration on its own schedule. Per-transition style randomization and music-aware safe windows still depend on `Transition_Director.py` behavior.
*   **Global Speed Multiplier (future):** A single override variable in `Mode_master.py` that scales `delta_time` for every mode (e.g., `0.5x`, `1x`, `2x`) is not yet wired up.
*   **Global Modifiers / Glitter Mask (future):** A global overlay function applied on top of the calculated frame before hardware push is still planned.

---

## 🗺️ 3. Segment Routing & Topology
*To control how data flows to specific physical areas of the stage.*

*   **Topology tab (implemented):** `components/pages/TopologyEditor.tsx` is rendered from `App.tsx` with `allowedModes={['LIVE']}`. It mirrors `mode_master_state`, sends `select_segment_mode` and `toggle_segment_direction` for runtime changes (no `POST` in LIVE), and uses client-side pending merges so ~30 Hz snapshots do not flicker overrides. `Mode_master` applies saved presets with shallow-copied `modes` / `way` on `activ_configuration` so live swaps stay isolated from the in-memory playlist store. See `wabb-interface/design rules/topology.md`.
*   **Configurator tab (implemented):** Same `TopologyEditor` component rendered with `allowedModes={['MODIFY', 'BUILD']}` and `syncPlaylistsFromModeMaster=false`. Persists presets only from MODIFY/BUILD via `POST /api/configurations`, then notifies `Mode_master` with `modify_configuration` or `build_configuration`.
*   **Live Topology Editor (future):** Allow the UI to push updated X/Y coordinates for segments back to the Pi, overwriting the spatial mapping used by the transition architecture on the fly.
*   **Segment Locking & Mode Configurations (future):** Lock specific segments to their current mode, immune to Auto-DJ / Global Transitions / random drops. Save the locked/unlocked combination as a "Global Mode Configuration" preset.
*   **Segment Masking/Muting (future):** Mathematical logic to selectively black out segments without changing their underlying mode state.
*   **Virtual Grouping (future):** Arbitrary clusters defined via the UI so commands can target groups (e.g., "Left Wing").

---

## 🤖 4. Show Automation & Presets
*To reduce cognitive load for the operator during a live show.*

*   **Snapshot Save/Load (implemented):** Playlist/configuration snapshots flow through `data/configurations.json` and `/api/configurations`. Vite serves the endpoint in development; `Connector.py` serves it in Python-backed operation and reloads `Mode_master` after writes. Configurations carry per-mode `modeSettings`.
*   **Auto-Transition Engine (partial):** See §2 — the Live Deck slider drives the interval in seconds. Per-style randomization, music-drop awareness, and a UI knob for the sweep duration are still planned.
*   **The Director's Override / Drop Action (implemented):** The Live Deck DROP button emits a `manual_drop` instruction handled by `Mode_master` to force a music-drop style override.
*   **Dynamic Palette Injection (future):** An endpoint to receive a new primary/secondary color pair and blend it into running generative modes.

---

## ⚙️ 5. Telemetry, Hardware & External Integrations
*For system stability, safety, and physical control.*

*   **Live Telemetry Stream (implemented):** `mode_master_state.system` carries Pi CPU temperature, RAM and disk usage, Python loop FPS / health, simulation vs hardware mode, ESP32 reachability, Bluetooth phone status, microphone state, audio stream state / health, last sample age, dynamic latency, uptime, hostname / platform, and the connected web-client count. The System tab and Live Deck telemetry strip subscribe to this stream.
*   **Remote Process Management (implemented):** `restart_python_loop` and `restart_raspberry_pi` instructions are dispatched from the System tab and gated by the `system.actions` capability flags supplied by Python. The UI also surfaces the most recent action feedback.
*   **Master Power Limiter (future):** Mathematical ceiling on RGB values applied just before hardware output (in `HardwareFactory` or `Mode_master`) to protect the power supply.
*   **Web MIDI Support (future):** WebSocket hooks designed to map to the browser's Web MIDI API for physical controllers (e.g., a Launchpad) to trigger UI events and macros.
