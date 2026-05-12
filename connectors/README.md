# Connectors (`/connectors/`)

The `connectors` directory manages all external Data In (Audio) and Data Out (Network Commands).

## Key Components:

- **`Connector.py`**: An aiohttp server on port `8080` that exposes `/ws` for bidirectional web app state/control and `/api/configurations` for persisted playlist/configuration JSON. It validates instruction payloads, logs them, acknowledges receipt, and broadcasts `Mode_master` state snapshots back to connected clients.
- **`Local_Microphone.py`**: Wraps the Python `sounddevice` library. It maintains a continuous sliding buffer of analog audio input and asynchronously pushes raw PCM data arrays directly into the `Listener` engine (which routes it to `AudioIngestion` for actual DSP math).

## How it works:
These modules run concurrently in async tasks. The `Local_Microphone` strictly acts as an I/O push-stream (performing no math), feeding raw audio to the math engine. Meanwhile, `Connector` accepts WebSocket instructions and validates the control payload shape:

```json
{
  "page": "live_deck | topology | mode_settings | system",
  "action": "string_action_name",
  "payload": {},
  "timestamp": 1715430000000
}
```

`Connector.py` no longer uses the legacy colon-separated command parser. It now expects JSON instructions only and responds with:

- `{"ok": true, "received": "<action>", "result": {...}}`
- `{"ok": false, "error": "invalid_instruction_json"}` when payload parsing fails.

It also pushes live snapshots to every connected web client:

```json
{
  "type": "mode_master_state",
  "payload": {
    "activePlaylist": "Luc",
    "activeConfiguration": "luc1",
    "queuedConfiguration": "luc-3",
    "modeSettings": {
      "Rainbow": { "smoothRatio": 0.5 }
    },
    "segments": [
      { "id": "v4", "name": "Segment v4", "mode": "Rainbow", "direction": "UP" }
    ]
  }
}
```

The `mode_master_state` payload now also includes a nested `system` block for the System page. It carries host/runtime telemetry such as resolved hardware mode, simulation state, CPU temperature when available, RAM and disk usage, loop FPS/health, microphone state, best-effort ESP32 reachability, Bluetooth phone status when detectable, connected web-client count, and the capability / last-feedback fields for the dangerous system actions.

## Configuration API

`GET /api/configurations` reads `data/configurations.json`.
`POST /api/configurations` validates and writes the same JSON shape:

```json
{
  "playlists": ["Luc"],
  "configurations": {
    "Luc": [
      {
        "name": "luc1",
        "modes": { "Segment v4": "Rainbow" },
        "way": { "Segment v4": "UP" },
        "modeSettings": {
          "Rainbow": { "smoothRatio": 0.5 }
        }
      }
    ]
  }
}
```

After a successful save, `Connector` calls `Mode_master.load_configurations()` and broadcasts a fresh state snapshot. The React app should never hardcode playlist or configuration names.

Topology **live** segment mode/direction changes are WebSocket instructions handled inside `Mode_master.process_instruction()`; they are not written by `POST /api/configurations`. Only explicit saves from the Topology editor’s `MODIFY` / `BUILD` flow update the JSON file.

Mode Settings uses the same `/ws` channel with a generic `set_mode_setting` action. `Mode_master` validates the requested mode/key/value, applies it to every live instance of that mode across all segments, persists the active configuration's `modeSettings`, and broadcasts the updated `mode_master_state`.

System actions also use `/ws`. `restart_python_loop` now requests a controlled restart through `Main.py` so the controller relaunches inside the same terminal/session, while `restart_raspberry_pi` is only exposed on Linux Raspberry hosts with a reboot command available. Their latest feedback is folded back into the `system` snapshot so the UI can explain why an action is pending, unavailable, or failed.
