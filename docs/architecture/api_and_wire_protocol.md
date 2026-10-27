# API, WebSocket & UDP Wire Protocol Specification

> **Location:** `docs/architecture/api_and_wire_protocol.md` (Tier 1 Canonical Specification)  
> **Source Files:** [`connectors/Connector.py`](../../connectors/Connector.py), [`connectors/Local_Microphone.py`](../../connectors/Local_Microphone.py), [`core/CommandRouter.py`](../../core/CommandRouter.py), [`hardware/Udp_Sender.py`](../../hardware/Udp_Sender.py)  
> **Enforcing Axiom:** [AXIOM-04: Network Transport Protocols](../axioms/AXIOM-04_NETWORK_PROTOCOLS.md)

---

## 1. Connectors Layer Overview (`connectors/`)

The `connectors/` package bridges the external world (HTTP/WebSocket clients and physical audio capture devices) to the internal orchestration engine:
- **[`connectors/Connector.py`](../../connectors/Connector.py):** Asynchronous `aiohttp` web server listening on `0.0.0.0:8080`. Exposes the `/api/topology` REST endpoint, manages full-duplex `/ws` WebSocket client connections, serves the compiled `wabb-interface/dist` static bundle, and throttles outbound state broadcasts to $\le 10\text{ Hz}$ (`0.1s` minimum interval) off the 30 FPS render hot path.
- **[`connectors/Local_Microphone.py`](../../connectors/Local_Microphone.py):** Real-time audio I/O bridge built on `sounddevice`. Captures PCM frames at 44,100 Hz (`blocksize=512`), routes audio into `Listener.ingest_audio_frame()`, and (when `fakeDelay > 0.0` in presets `"spotify"`, `"spotify_aux"`, or `"aux"`) buffers raw PCM in a circular ring buffer to play delayed audio out to the physical speakers in exact alignment with the 5.0-second visual lookahead window.

---

## 2. HTTP REST Endpoints (`Connector.py`)

### `GET /api/topology`
Returns the unified segment geometry and UI grid layout from `config/segments_full.json` or `config/segments_small.json` (governed by **AXIOM-03**).
- **Response (`200 OK`, `application/json`):**
  ```json
  {
    "segments": [
      {
        "name": "v1",
        "length": 133,
        "orientation": "vertical",
        "start": {"x": 15, "y": 310},
        "step": {"x": 0, "y": -1},
        "ui": {"id": "v1", "col": 2, "row": 2, "w": 1, "h": 6, "color": "#FF3B30"}
      }
    ],
    "cables": [
      {"from": "c1", "to": "v1", "cp1": {"x": 0, "y": 0}, "cp2": {"x": 0, "y": 0}}
    ]
  }
  ```

---

## 3. WebSocket Full-Duplex Protocol (`/ws`)

### A. Outbound Server-to-Client (`state_update`)
Throttled to $\le 10\text{ Hz}$ (or event-driven on user interaction):
```json
{
  "type": "state_update",
  "hardwareProfile": "full",
  "activeMood": "Cyberpunk",
  "availableMoods": [
    {"name": "Cyberpunk", "description": "...", "colors": ["rgb(0, 240, 255)", "..."]}
  ],
  "availableModes": ["Rainbow", "Bary Rainbow", "..."],
  "segments": {
    "v1": {"mode": "Rainbow", "direction": "UP", "isLocked": false}
  },
  "luminosity": 50,
  "sensibility": 50,
  "autoTransitionTime": 80,
  "isLocked": false,
  "isInTransition": false,
  "modeSettingsCatalog": {},
  "modeSettingsValues": {},
  "capabilities": {
    "canRestartPython": true,
    "canRebootRaspberryPi": false
  }
}
```

### B. Inbound Client-to-Server Commands (`CommandRouter.py`)
All commands arrive as JSON objects with an `"action"` string, and receive an acknowledgement packet:
```json
{
  "type": "instruction_ack",
  "status": "ok",
  "action": "set_luminosity"
}
```

| Action | Parameters | Description |
| :--- | :--- | :--- |
| `select_mood` | `{"mood": "Cyberpunk"}` | Switches active mood palette (`2.5s` cosine crossfade). |
| `go_to_next_configuration` | `{}` | Triggers immediate beat-aligned global transition (`request_next`). |
| `lock_current_configuration` | `{"locked": true}` | Freezes/unfreezes automatic transitions. |
| `manual_drop` | `{}` | Triggers immediate high-energy drop transition (`request_drop`). |
| `select_segment_mode` | `{"segment": "v1", "mode": "Rainbow"}` | Overrides mode on a specific segment (`1.2s` fade). |
| `toggle_segment_direction` | `{"segment": "v1"}` | Toggles segment animation direction (`UP` / `DOWN`). |
| `set_luminosity` | `{"value": 80}` | Sets master brightness (`1..100`) and persists to `app_config.json`. |
| `set_sensibility` | `{"value": 60}` | Sets audio sensitivity (`1..100`) and persists to `app_config.json`. |
| `set_auto_transition_time` | `{"value": 90}` | Sets auto-transition interval (`5..300` s) and persists to `app_config.json`. |
| `set_mode_setting` | `{"mode": "Rainbow", "key": "speed", "value": 1.5}` | Updates live mode parameter across segments and persists to `mode_settings`. |
| `restart_python_loop` | `{}` | Gracefully restarts the Python orchestrator process. |
| `restart_raspberry_pi` | `{}` | Executes `sudo reboot` (only when `onRaspberry == True`). |

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
