# API, WebSocket & UDP Wire Protocol Specification

> **Location:** `docs/architecture/api_and_wire_protocol.md` (Tier 1 Canonical Specification)  
> **Source Files:** [`connectors/Connector.py`](../../connectors/Connector.py), [`connectors/Local_Microphone.py`](../../connectors/Local_Microphone.py), [`connectors/System_status.py`](../../connectors/System_status.py), [`core/CommandRouter.py`](../../core/CommandRouter.py), [`hardware/Udp_Sender.py`](../../hardware/Udp_Sender.py)  
> **Enforcing Axiom:** [AXIOM-04: Network Transport Protocols](../axioms/AXIOM-04_NETWORK_PROTOCOLS.md)

---

## 1. Connectors Layer Overview (`connectors/`)

The `connectors/` package bridges external HTTP/WebSocket clients and physical audio capture devices to the internal orchestration engine:
- **[`connectors/Connector.py`](../../connectors/Connector.py):** Asynchronous `aiohttp` web server listening on `0.0.0.0:8080`. Exposes REST endpoints (`/`, `/health`, `/api/topology`, `/api/topology/reset`), manages full-duplex `/ws` WebSocket client connections, serves the compiled `wabb-interface/dist` static bundle, and throttles outbound state broadcasts to $\le 10\text{ Hz}$ (`0.1s` minimum interval) off the 30 FPS render hot path.
- **[`connectors/Local_Microphone.py`](../../connectors/Local_Microphone.py):** Real-time audio I/O bridge built on `sounddevice`. Captures PCM frames at 44,100 Hz (`blocksize=512`), routes audio into `Listener.ingest_audio_frame()`, and (when `fakeDelay > 0.0` in presets `"spotify"`, `"spotify_aux"`, or `"aux"`) buffers raw PCM in a circular ring buffer to play delayed audio out to the physical speakers in exact alignment with the 5.0-second visual lookahead window.
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
Broadcast automatically upon connection, immediately after any state-mutating command, and periodically during runtime (throttled to $\le 10\text{ Hz}$ via `self._last_state_broadcast_time`):
```json
{
  "type": "mode_master_state",
  "payload": {
    "hardwareProfile": "full",
    "activeMood": "Cyberpunk",
    "availableMoods": [
      {
        "name": "Cyberpunk",
        "description": "Neon cyan, hot magenta, and electric violet",
        "colors": ["rgb(0, 240, 255)", "rgb(255, 0, 128)", "..."]
      }
    ],
    "availableModes": ["Rainbow", "Bary Rainbow", "..."],
    "segments": [
      {
        "id": "v4",
        "name": "Segment v4",
        "channel": 1,
        "size": 173,
        "way": "UP",
        "orientation": "vertical",
        "mode": "Rainbow"
      }
    ],
    "luminosity": 50,
    "sensibility": 50,
    "autoTransitionTime": 80,
    "isLocked": false,
    "isInTransition": false,
    "modeSettingsCatalog": {
      "Rainbow": [
        { "key": "rainbow_steps_number", "label": "Rainbow Steps", "type": "int", "min": 10, "max": 600, "step": 10, "default": 255 }
      ]
    },
    "modeSettingsValues": {
      "Rainbow": { "rainbow_steps_number": 255 }
    },
    "capabilities": {
      "canRestartPython": true,
      "canRebootRaspberryPi": false
    }
  }
}
```

### B. Inbound Client-to-Server Commands (`CommandRouter.py`)
The React frontend (`wabb-interface/src/utils/controlBridge.ts`) sends JSON instructions over `/ws`:
```json
{
  "page": "configurator",
  "action": "select_segment_mode",
  "payload": {
    "segmentId": "v4",
    "mode": "Hyper Strobe"
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
    "ok": true,
    "action": "select_segment_mode",
    "segmentId": "v4",
    "mode": "Hyper Strobe"
  }
}
```

| `action` | `payload` Schema | Target Handler & Effect |
| :--- | :--- | :--- |
| `select_mood` | `{ "mood": "<string>" }` | `Mode_master.select_mood(mood)` — initiates a `2.5s` cosine palette crossfade via `MoodService`. |
| `go_to_next_configuration` | `{}` | `Mode_master.go_to_next_configuration()` — sets `request_next` on `TransitionService`. |
| `lock_current_configuration` | `{ "locked": <bool> }` | `Mode_master.set_lock_state(locked)` — freezes or unfreezes automatic transitions. |
| `manual_drop` | `{}` | `Mode_master.trigger_manual_drop()` — sets `request_drop` on `TransitionService` (`0.15s` flash cut). |
| `select_segment_mode` | `{ "segmentId": "<id>", "mode": "<name>" }` | `Mode_master.select_segment_mode(segment_id, mode)` — starts a `1.2s` fade on the target segment. |
| `toggle_segment_direction` | `{ "segmentId": "<id>", "direction"?: "UP"\|"DOWN" }` | `Mode_master.toggle_segment_direction(segment_id, direction)` — flips segment index reversal. |
| `set_luminosity` | `{ "value": <1..100> }` | `Mode_master.set_luminosity(value)` — updates `infos["luminosity"]` and persists to `config/app_config.json`. |
| `set_sensibility` | `{ "value": <1..100> }` | `Mode_master.set_sensibility(value)` — updates `infos["sensibility"]` and persists to `config/app_config.json`. |
| `set_auto_transition_time` | `{ "value": <5..300> }` | `Mode_master.set_auto_transition_time(value)` — updates `TransitionService` timer and persists to `config/app_config.json`. |
| `set_mode_setting` | `{ "mode": "<name>", "key": "<key>", "value": <num\|bool> }` | `Mode_master.set_mode_setting(mode, key, value)` — validates against `get_settings_schema()`, applies live across segments, and persists to `config/app_config.json`. |
| `restart_python_loop` | `{}` | `Mode_master.restart_python_loop()` — calls `close_properly()` and `os.execv()` after `150ms`. |
| `restart_raspberry_pi` | `{}` | `Mode_master.restart_raspberry_pi()` — executes `sudo reboot` (only when `infos["onRaspberry"] == True`). |

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
