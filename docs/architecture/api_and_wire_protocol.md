# API & WebSocket Wire Protocol

> **Location:** `docs/architecture/api_and_wire_protocol.md` (Tier 1 Canonical Specification)  
> **Source Files:** [`connectors/Connector.py`](../../connectors/Connector.py), [`core/CommandRouter.py`](../../core/CommandRouter.py), [`wabb-interface/`](../../wabb-interface/)  
> **Enforcing Axioms:** [AXIOM-02](../axioms/AXIOM-02_ZERO_ALLOCATION.md), [AXIOM-04](../axioms/AXIOM-04_NETWORK_PROTOCOLS.md)

---

## 1. REST Endpoints (`0.0.0.0:8080`)

Implemented via `aiohttp` in `connectors/Connector.py`:

| Method | Endpoint | Description | Response Schema |
|:---:|:---|:---|:---|
| `GET` | `/` | Serves compiled React web app (`wabb-interface/dist/index.html`) | HTML |
| `GET` | `/api/configurations` | Returns all playlists and presets from active profile store | JSON object containing `playlists`, `configurations`, `blockedPlaylists` |
| `POST` | `/api/configurations` | Overwrites presets in the active configuration JSON | `{"status": "saved"}` |
| `GET` | `/api/topology` | Returns physical segment coordinates, lengths, orientations, and cables | `{"segments": [...], "cables": [...]}` |
| `GET` | `/ws` | Upgrades connection to WebSocket for live bidirectional control | WebSocket protocol |

---

## 2. WebSocket Protocol (`/ws`)

### A. Server-to-Client Telemetry (`mode_master_state`)
Broadcasts state snapshots to active browser clients.
- **Throttling (AXIOM-04):** Throttled to $\le 10\text{ Hz}$ during transitions, 1.0 Hz heartbeat on steady state.
- **Payload Schema:**
```json
{
  "type": "mode_master_state",
  "payload": {
    "current_playlist": "Cosmic",
    "current_configuration": "Supernova",
    "active_modes": { "v1": "Rainbow", "h00": "Hyper Strobe" },
    "is_in_transition": false,
    "transition_progress": 0.0,
    "luminosity": 50,
    "sensibility": 50,
    "bpm": 124.0,
    "beat_confidence": 0.88,
    "is_beat": true,
    "is_real_beat": true
  }
}
```

### B. Client-to-Server Instructions (`controlBridge`)
```json
{
  "page": "topology",
  "action": "select_segment_mode",
  "payload": {
    "segmentId": "v1",
    "mode": "Rainbow"
  }
}
```
Supported Actions by Page:
- **`live_deck`**:
  - `set_luminosity`: Sets master LED brightness percentage ($0\text{--}100$). Payload: `{"value": 80}`.
  - `set_sensibility`: Sets audio gain sensitivity ($1\text{--}100$). Payload: `{"value": 65}`.
  - `set_auto_transition_time`: Sets configuration rotation interval (seconds). Payload: `{"value": 30}`.
  - `select_transition`: Sets active transition preset. Payload: `{"transition": "CUT" | "CROSSFADE" | "FADE IN/OUT"}`.
  - `select_configuration`: Queues configuration by name. Payload: `{"configuration": "name"}`.
  - `select_playlist`: Activates single playlist and switches. Payload: `{"playlist": "name"}`.
  - `go_to_next_configuration`: Triggers immediate transition to next configuration. Payload: `{"transition": ..., "configuration": ...}`.
  - `manual_drop`: Triggers structural drop event or queued configuration transition.
  - `lock_current_configuration`: Locks or unlocks automatic configuration rotation. Payload: `{"locked": true|false}`.
- **`topology`**:
  - `select_segment_mode`: Sets active mode on a logical strip. Payload: `{"segmentId": "v1", "mode": "Rainbow"}`.
  - `toggle_segment_direction`: Inverts strip rendering direction. Payload: `{"segmentId": "v1", "direction": "UP" | "DOWN"}`.
  - `select_playlist_slot`: Selects single active playlist from topology view.
  - `select_configuration`: Activates configuration with transition.
- **`mode_settings`**:
  - `set_mode_setting`: Live tunes dynamic mode parameter. Payload: `{"mode": "mode_name", "key": "setting_key", "value": val}`.
