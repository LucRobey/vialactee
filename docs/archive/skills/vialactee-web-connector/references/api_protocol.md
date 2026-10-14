# Web Connector Protocol & State Reference

The web control bridge connects the React UI (`wabb-interface/`) to the Python core (`connectors/Connector.py`) using REST for configuration persistence and WebSockets for real-time state synchronization.

---

## 1. REST API Endpoints

### `GET /api/topology`
* **Purpose**: Retrieves all defined segments (with both hardware coordinates and UI layout parameters) and cable splines for the active profile (`config/segments_full.json` or `config/segments_small.json`).
* **Response**:
  ```json
  {
    "segments": [
      {
        "id": "v4",
        "name": "Segment v4",
        "size": 173,
        "order": 0,
        "orientation": "vertical",
        "start": { "x": 0, "y": 204 },
        "step": { "x": 0, "y": -1 },
        "ui": { "col": 43, "row": 1, "w": 2, "h": 18, "color": "#3264ff" }
      }
    ],
    "cables": [
      { "start": [2.5, 3], "end": [2.5, 6.5], "cp1": [1, 3], "cp2": [1, 6.5] }
    ]
  }
  ```

### `GET /api/configurations`
* **Purpose**: Retrieves playlists and configurations from the active profile's configuration file (`data/configurations_full.json` or `data/configurations_small.json`).
* **Response**:
  ```json
  {
    "playlists": ["Default"],
    "configurations": {
      "Default": [
        {
          "name": "Rainbow Triad",
          "modes": { "Segment s1": "Rainbow", "Segment s2": "Shining Stars", "Segment s3": "Rainbow" },
          "way": { "Segment s1": "UP", "Segment s2": "UP", "Segment s3": "UP" },
          "modeSettings": {}
        }
      ]
    }
  }
  ```

### `POST /api/configurations`
* **Purpose**: Saves or updates configurations in the active profile's configuration file.
* **Behavior**: Sanitizes input, writes to disk, invokes `mode_master.load_configurations()`, and forces a WebSocket state broadcast to all connected clients.

---

## 2. WebSocket Protocol (`/ws`)

### State Broadcast (`mode_master_state`)
Sent automatically upon client connection and whenever state changes:
```json
{
  "type": "mode_master_state",
  "payload": {
    "hardwareProfile": "full",
    "activePlaylist": "Default",
    "enabledPlaylists": ["Default"],
    "activeConfiguration": "Rainbow Triad",
    "queuedConfiguration": "Pulse",
    "selectedTransition": "Dual Crossfade",
    "transitionLocked": false,
    "transitionState": "idle",
    "transitionProgress": 0.0,
    "luminosity": 50,
    "sensibility": 50,
    "autoTransitionTime": 80,
    "playlists": ["Default"],
    "availableModes": ["Rainbow", "Shining Stars"],
    "segments": [
      {
        "id": "v4",
        "name": "Segment v4",
        "mode": "Rainbow",
        "direction": "UP",
        "blocked": false,
        "targetMode": "Rainbow",
        "inTransition": false
      }
    ],
    "modeSettingsCatalog": [...],
    "modeSettings": {
      "Rainbow": { "rainbow_smooth_ratio": 0.5 }
    },
    "system": { ... }
  }
}
```

### Client Action Messages
Clients send control frames with a standard envelope:
```json
{
  "page": "live_deck" | "topology" | "mode_settings" | "system",
  "action": "action_name",
  "payload": { ... },
  "timestamp": 1725219500000
}
```

#### Page `live_deck`
* `set_luminosity`: `{"value": 50}` — Master brightness scale (0–100 integer percentage).
* `set_sensibility`: `{"value": 50}` — Audio gain sensitivity scale (1–100 integer percentage).
* `set_auto_transition_time`: `{"value": 80}` — Automatic playlist rotation duration in seconds.
* `select_transition`: `{"transition": "fade_in_out"}` — Sets transition effect for subsequent configuration changes.
* `select_configuration`: `{"configuration": "Config Name"}` — Stages a configuration for next transition.
* `select_playlist`: `{"playlist": "Playlist Name"}` — Isolates active playlist and triggers random switch.
* `go_to_next_configuration`: `{"configuration": "...", "transition": "..."}` — Forces immediate transition.
* `manual_drop`: `{}` — Triggers immediate transition to queued configuration.
* `lock_current_configuration`: `{"locked": true}` — Freezes/unfreezes automatic playlist rotation.

#### Page `topology`
* `select_segment_mode`: `{"segmentId": "v4", "mode": "Rainbow"}` — Immediate live mode swap on target segment.
* `toggle_segment_direction`: `{"segmentId": "v4", "direction": "UP"}` — Direction must be `"UP"` or `"DOWN"`.
* `select_playlist_slot`: `{"playlist": "Default"}` — Selects active playlist slot in topology view.
* `select_configuration`: `{"playlist": "Default", "configuration": "Rainbow Triad"}` — Direct configuration switch.
* `build_configuration`: `{}` — Notifies `Mode_master` that new presets were persisted via `POST /api/configurations`.
* `modify_configuration`: `{}` — Notifies `Mode_master` that presets were updated.

#### Page `mode_settings`
* `set_mode_setting`: `{"mode": "Rainbow", "key": "rainbow_smooth_ratio", "value": 0.5}` — Sets and persists a specific setting descriptor.

#### Page `system`
* `restart_python_loop`: `{}` — Queues graceful process exit and systemd restart of the Python core.
* `restart_raspberry_pi`: `{}` — Queues system reboot command on Linux host.

---

## 3. Architecture Rules: LIVE vs PERSIST
1. **LIVE (Temporary swaps)**: Interactive mode switches from the Live Deck or Topology send WebSocket actions (`select_segment_mode`, `toggle_segment_direction`). `Mode_master` modifies its active runtime copies without mutating the saved configuration files.
2. **PERSIST (Saving to Disk)**: Saving a playlist or layout permanently is done strictly via `POST /api/configurations`, which writes to `data/configurations_full.json` or `data/configurations_small.json`.
