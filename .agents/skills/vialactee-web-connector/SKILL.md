---
name: vialactee-web-connector
description: Protocols, REST endpoints, WebSocket message contracts, and state synchronization rules for the web interface and remote control connector (connectors/Connector.py and wabb-interface/).
---

# Vialactée Web Connector & UI Skill

Use this skill whenever you are modifying the web remote control interface, WebSocket event handling, or configuration persistence layers in `connectors/Connector.py`, `wabb-interface/`, or `data/configurations.json`.

## Core Guidelines & Invariants

### 1. Local Development Port Conflicts
* In local simulator testing on Windows, `Main.py` provides `startServer: False` in `infos` to prevent port `8080` socket collisions on successive restarts.
* When testing web interface features, explicitly set `startServer: True`.

### 2. State Synchronization Model
* **Single Source of Truth**: The Python `Mode_master` engine holds the authoritative runtime state.
* Whenever configurations or modes change, `Connector.broadcast_state_if_changed()` broadcasts `mode_master_state` to all connected React clients.
* React components should bind their UI elements reactively to the latest `mode_master_state` payload.

### 3. LIVE Swaps vs Persistence Separation
* **LIVE Swaps**: Changing a mode or toggling a direction in real-time must send WebSocket actions (`select_segment_mode` / `toggle_segment_direction`). `Mode_master` modifies its runtime copies (`modes`/`way`) without mutating the loaded configuration definitions on disk.
* **PERSIST**: Saving a playlist or layout permanently is done strictly via `POST /api/configurations`. Do not write arbitrary JSON mutations outside this endpoint.

### 4. Protocol Reference
* Consult [api_protocol.md](./references/api_protocol.md) for endpoint specifications, payload shapes, and action names.
