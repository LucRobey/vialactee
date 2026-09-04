# Web Connector Protocol & State Reference

The web control bridge connects the React UI (`wabb-interface/`) to the Python core (`connectors/Connector.py`) using REST for configuration persistence and WebSockets for real-time state synchronization.

---

## 1. REST API Endpoints

### `GET /api/configurations`
* **Purpose**: Retrieves all saved configurations and playlists from `data/configurations.json`.
* **Response**:
  ```json
  {
    "configurations": {
      "default": {
        "modes": { "v1": "Rainbow", "v2": "Bary_rainbow", ... },
        "way": { "v1": "up", "v2": "down", ... }
      }
    }
  }
  ```

### `POST /api/configurations`
* **Purpose**: Saves or updates configurations in `data/configurations.json`.
* **Behavior**: Sanitizes input, writes to disk, invokes `mode_master.load_configurations()`, and forces a WebSocket state broadcast to all connected clients.

---

## 2. WebSocket Protocol (`/ws`)

### State Broadcast (`mode_master_state`)
Sent automatically upon client connection and whenever state changes:
```json
{
  "type": "mode_master_state",
  "payload": {
    "activ_configuration": "default",
    "configurations": { ... },
    "current_modes": { "v1": "Rainbow", "v2": "Bary_rainbow" },
    "current_ways": { "v1": "up", "v2": "down" },
    "luminosite": 1.0,
    "sensi": 1.0,
    "available_modes": ["Rainbow", "Bary_rainbow", "Metronome", ...]
  }
}
```

### Client Action Messages
Clients send control frames with standard envelope:
```json
{
  "page": "topology" | "live_deck" | "settings",
  "action": "action_name",
  "payload": { ... },
  "timestamp": 1725219500000
}
```

Common Actions:
* `select_segment_mode`: `{"segment": "v1", "mode": "Rainbow"}` (Live temporary mode change)
* `toggle_segment_direction`: `{"segment": "v1"}` (Toggles direction `up`/`down`)
* `set_configuration`: `{"name": "party_night"}` (Switches active playlist/configuration)
* `set_luminosity`: `{"value": 0.8}`
* `set_sensitivity`: `{"value": 1.2}`
* `apply_mode_settings`: `{"mode": "Rainbow", "settings": {"speed": 2.0}}`

---

## 3. Architecture Rules: LIVE vs PERSIST
1. **LIVE (Temporary swaps)**: Interactive mode switches from the Live Deck send WebSocket actions (`select_segment_mode`). `Mode_master` modifies its active runtime copies without mutating the saved `data/configurations.json` configuration store.
2. **PERSIST (Saving to Disk)**: Saving a playlist or layout permanently is done strictly via `POST /api/configurations`.
