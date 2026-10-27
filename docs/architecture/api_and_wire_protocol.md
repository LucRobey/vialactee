# API, WebSocket & UDP Wire Protocol Specification

> **Location:** `docs/architecture/api_and_wire_protocol.md` (Tier 1 Canonical Specification)  
> **Source Files:** [`connectors/Connector.py`](../../connectors/Connector.py), [`connectors/Local_Microphone.py`](../../connectors/Local_Microphone.py), [`connectors/System_status.py`](../../connectors/System_status.py), [`core/CommandRouter.py`](../../core/CommandRouter.py), [`hardware/Udp_Sender.py`](../../hardware/Udp_Sender.py)  
> **Enforcing Axiom:** [AXIOM-04: Network Transport Protocols](../axioms/AXIOM-04_NETWORK_PROTOCOLS.md)

---

## 1. Connectors Layer Overview (`connectors/`)

The `connectors/` package bridges external HTTP/WebSocket clients and physical audio capture devices to the internal orchestration engine:
- **[`connectors/Connector.py`](../../connectors/Connector.py):** Asynchronous `aiohttp` web server listening on `0.0.0.0:8080`. Exposes REST endpoints (`/`, `/health`, `/api/topology`, `/api/topology/reset`), manages full-duplex `/ws` WebSocket client connections, serves the compiled `wabb-interface/dist` static bundle, and throttles outbound state broadcasts to $\le 10\text{ Hz}$ (`0.1s` minimum interval) off the 30 FPS render hot path.
- **[`connectors/Local_Microphone.py`](../../connectors/Local_Microphone.py):** Real-time audio I/O bridge built on `sounddevice`. Captures PCM frames at 44,100 Hz (`blocksize=512`), routes audio into `Listener.process_raw_audio()`, and (when `fakeDelay > 0.0` in presets `"spotify"`, `"spotify_aux"`, or `"aux"`) buffers raw PCM in a circular ring buffer to play delayed audio out to the physical speakers in exact alignment with the 5.0-second visual lookahead window.
- **[`connectors/System_status.py`](../../connectors/System_status.py):** Lightweight network connectivity checker (`check_internet_connection()`).

---

## 2. HTTP REST Endpoints (`Connector.py`)

| Method | Path | Description |
| :---: | :--- | :--- |
| `GET` | `/` | Serves `wabb-interface/dist/index.html` (or a status JSON fallback if the frontend bundle is not built). |
| `GET` | `/health` | Health probe returning `{"ok": true}`. |
| `GET` | `/api/topology` | Returns the active hardware topology JSON (`config/segments_full.json` or `config/segments_small.json`). |
| `POST` | `/api/topology` | Validates (`segs_1`, `cables`) and persists updated 2D simulator coordinates (`start`, `step`) and cable geometry (`cables`) to the active topology JSON file. |
| `POST` | `/api/topology/reset` | Restores `start`, `step`, and `cables` from the corresponding `.default.json` backup (`segments_full.default.json` or `segments_small.default.json`). |

### Topology Schema (`GET /api/topology`)
Governed by **AXIOM-03 (Unified Topology Source of Truth)**:
```json
{
  "segs_1": [
    {
      "name": "Segment v4",
      "size": 173,
      "way": "UP",
      "orientation": "vertical",
      "start": { "x": 160, "y": 546 },
      "step": { "x": 0, "y": -2 },
      "ui": { "id": "v4", "col": 2, "row": 2, "w": 1, "h": 6, "color": "#FF3B30" }
    }
  ],
  "segs_2": [ ... ],
  "cables": [
    {
      "id": "cable-0",
      "start": { "x": 160, "y": 202 },
      "end": { "x": 200, "y": 220 },
      "cp1": { "x": 160, "y": 180 },
      "cp2": { "x": 200, "y": 180 }
    }
  ]
}
```

---

## 3. WebSocket Full-Duplex Protocol (`/ws`)

### A. Outbound Server-to-Client (`mode_master_state`)
Broadcast automatically upon connection, immediately after any state-mutating command, and periodically during runtime (throttled to $\le 10\text{ Hz}$ during transitions via `self._last_state_broadcast_time`, `1.0 Hz` heartbeat on steady state per AXIOM-04):
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
      {
        "id": "v1",
        "name": "Segment v1",
        "mode": "Rainbow",
        "direction": "UP",
        "blocked": false,
        "targetMode": null,
        "inTransition": false
      }
    ],
    "modeSettingsCatalog": [
      {
        "mode": "Rainbow",
        "label": "Rainbow",
        "settings": [
          {
            "key": "smoothRatio",
            "label": "Smoothing",
            "control": "slider",
            "valueType": "number",
            "min": 0.0,
            "max": 1.0,
            "step": 0.05,
            "default": 0.5,
            "attr": "smooth_ratio"
          }
        ]
      }
    ],
    "modeSettings": {
      "Rainbow": { "smoothRatio": 0.5, "intensityBase": 0.1, "intensityMultiplier": 0.9 }
    },
    "system": {
      "connectedClients": 1,
      "fps": 30.0
    }
  }
}
```

### B. Inbound Client-to-Server Commands (`CommandRouter.py`)
The React frontend (`wabb-interface/src/utils/controlBridge.ts`) sends JSON instructions over `/ws`:
```json
{
  "page": "topology",
  "action": "select_segment_mode",
  "payload": {
    "segmentId": "v1",
    "mode": "Rainbow"
  },
  "timestamp": 1711800000000
}
```

Every inbound command receives a synchronous JSON acknowledgment on the same WebSocket connection:
```json
{
  "ok": true,
  "received": "select_segment_mode",
  "result": {
    "applied": true
  }
}
```

| `page` | `action` | `payload` Schema | Target Handler (`core/CommandRouter.py`) & Effect |
| :--- | :--- | :--- | :--- |
| `live_deck` | `set_luminosity` | `{ "value": <0..100> }` | Sets `mm.listener.luminosite = value / 100.0` and persists `"luminosity"` to `config/app_config.json`. |
| `live_deck` | `set_sensibility` | `{ "value": <0..100> }` | Sets `mm.listener.sensi = value / 100.0` and persists `"sensibility"` to `config/app_config.json`. |
| `live_deck` | `set_auto_transition_time` | `{ "value": <int >= 1> }` | Calls `mm.transitions.set_auto_interval(value)` and persists `"auto_transition_time"` to `config/app_config.json`. |
| `live_deck` | `select_mood` | `{ "palette": "<name>" }` *(or `"mood"`)* | Calls `mm.mood.request_palette(palette)` to start a cosine palette crossfade. |
| `live_deck` | `select_transition` | `{ ... }` | **Retired** (still accepted; always replies `{"applied": false, "reason": "transition_selection_retired"}`). |
| `live_deck` | `go_to_next_configuration` | `{}` | Calls `mm.transitions.request_next()` to trigger the next DNA transition. |
| `live_deck` | `manual_drop` | `{}` | Calls `mm.transitions.request_drop()` to trigger an immediate drop transition. |
| `live_deck` | `lock_current_configuration` | `{ "locked": <bool> }` | Calls `mm.transitions.set_locked(bool(locked))` to freeze or unfreeze automatic transitions. |
| `topology` | `select_segment_mode` | `{ "segmentId": "<id>", "mode": "<name>" }` | Calls `segment.execute_mode_swap(mode_name)` and `mm._push_installation()`. |
| `topology` | `toggle_segment_direction` | `{ "segmentId": "<id>", "direction": "UP"\|"DOWN" }` | Calls `segment.change_way(direction)` to invert strip rendering direction. |
| `mode_settings` | `set_mode_setting` | `{ "mode": "<name>", "key": "<key>", "value": <val> }` | Validates via `Mode.normalize_setting_value()`, applies across segments (`mm._apply_active_mode_settings()`), and persists `"mode_settings"` to `config/app_config.json`. |
| `system` | `restart_python_loop` | `{}` | Schedules `mm._restart_python_process_task()` (`close_properly()` + `os.execv()`). |
| `system` | `restart_raspberry_pi` | `{}` | Schedules `mm._restart_raspberry_pi_task()` (`sudo reboot` on Linux Raspberry Pi systems). |

---

## 4. UDP LED Wire Protocol (`Udp_Sender.py`)

Governed by **AXIOM-04 (UDP Chunk Size $\le 1,202\text{ B}$)**.
- **Ports:** `9001` (Channel 1, 785 LEDs), `9002` (Channel 2, 519 LEDs). Sideband simulator metadata uses port `9003` and simulator transition control uses port `9004` (see [`docs/architecture/hardware_abstraction.md`](./hardware_abstraction.md)).
- **Binary Packet Layout:**
  ```
  +------------------------+-----------------------------------------+
  | Bytes 0..1 (uint16 LE) | Bytes 2..N (uint8 RGB triplets)         |
  | start_index            | [R0, G0, B0, R1, G1, B1, ...]           |
  +------------------------+-----------------------------------------+
  ```
- **Chunking:** Maximum `400` LEDs per UDP datagram ($2 + 400 \times 3 = 1,202\text{ bytes}$), ensuring zero IP fragmentation on standard 1,500-byte Ethernet/Wi-Fi MTU links.
