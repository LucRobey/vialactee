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
    "hardwareProfile": "full",
    "selectedTransition": "DYNAMIC",
    "transitionLocked": false,
    "transitionState": "PASSATION",
    "transitionProgress": 0.0,
    "luminosity": 50,
    "sensibility": 50,
    "autoTransitionTime": 20,
    "availableModes": ["Rainbow", "Hyper Strobe"],
    "activeMood": "Cyberpunk",
    "availableMoods": ["Cyberpunk", "Solar Ember"],
    "segments": [
      { "id": "v1", "name": "Segment v1", "mode": "Rainbow", "direction": "UP", "blocked": false, "targetMode": null, "inTransition": false }
    ],
    "modeSettingsCatalog": [...],
    "modeSettings": { "Rainbow": { "smoothRatio": 0.5 } },
    "system": { "...": "..." }
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
  - `set_auto_transition_time`: Sets automatic transition interval (seconds). Payload: `{"value": 30}`.
  - `select_mood`: Selects active mood palette. Payload: `{"palette": "Cyberpunk"}`.
  - `select_transition`: **Retired** (still accepted; always replies `{"applied": false, "reason": "transition_selection_retired"}`).
  - `go_to_next_configuration`: Triggers next DNA transition via `transitions.request_next()`.
  - `manual_drop`: Triggers immediate drop transition via `transitions.request_drop()`.
  - `lock_current_configuration`: Locks or unlocks automatic transitions. Payload: `{"locked": true|false}`.
- **`topology`**:
  - `select_segment_mode`: Sets active mode on a logical strip. Payload: `{"segmentId": "v1", "mode": "Rainbow"}`.
  - `toggle_segment_direction`: Inverts strip rendering direction. Payload: `{"segmentId": "v1", "direction": "UP" | "DOWN"}`.
- **`mode_settings`**:
  - `set_mode_setting`: Live tunes dynamic mode parameter and persists to `config/app_config.json`. Payload: `{"mode": "mode_name", "key": "setting_key", "value": val}`.
- **`system`**:
  - `restart_python_loop`: Triggers a controlled restart of the Python process.
  - `restart_raspberry_pi`: Triggers host reboot on Linux Raspberry Pi systems.
