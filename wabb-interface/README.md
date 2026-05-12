# Wabb Interface (Web Controller)

This directory contains the React + Vite frontend application for Vialactée. 

It serves as the official remote control for the chandelier. We pivoted to this web interface (away from the legacy native Android App) to provide universal access across devices without requiring app store installations.

## Structure and Workflow:

- **React Framework**: Built using React, TypeScript, and Vite for lightning-fast HMR and compilation.
- **Network Layer**: Communicates with the Raspberry Pi's backend over HTTP and WebSockets (handled by `Connector.py` in the `connectors/` folder).
- **Configuration Source**: Playlists and configurations are loaded from `data/configurations.json` through `/api/configurations`. Do not hardcode playlist names or configuration names in React components.
- **Interface Capabilities**: Provides sliders, toggles, lists, and visual feedback so the user can manipulate playlist rotation, force mode changes, tune per-mode settings, and observe the system's real-time performance metrics.

## Configuration JSON

The shared helper `src/utils/configurationStore.ts` is the frontend boundary for reading and writing `data/configurations.json`.

- `GET /api/configurations` returns `{ "playlists": string[], "configurations": Record<string, Configuration[]> }`.
- `POST /api/configurations` persists the same shape back to disk.
- During Vite development, `vite.config.ts` serves this API.
- During Python-backed operation, `connectors/Connector.py` serves the same API and asks `Mode_master` to reload the saved playlists/configurations.

## WebSocket Control And State

The app emits control instructions from the UI to the backend bridge through a shared WebSocket sender in `src/utils/controlBridge.ts`.

- Default WebSocket URL: `ws://<host>:8080/ws` (or `wss://` on HTTPS)
- Optional override via env var: `VITE_WABB_WS_URL`
- Instruction shape sent by the frontend:

```json
{
  "page": "live_deck | topology | mode_settings | system",
  "action": "string_action_name",
  "payload": {},
  "timestamp": 1715430000000
}
```

The same WebSocket also receives `mode_master_state` messages from Python. These snapshots hydrate Live Deck, Topology, Mode Settings, and System with the current active playlist, active/queued configuration, transition lock, luminosity, sensibility, each segment's active mode/direction, the mode-settings catalog, the current effective per-mode values for the active configuration, and the live `system` telemetry block.

**Topology `LIVE`:** segment mode/direction changes are sent as instructions only (no `POST /api/configurations`). The UI merges snapshots with short-lived pending values so rapid broadcasts do not undo a click before Python applies it. **Topology `MODIFY` / `BUILD`:** saving writes through `POST /api/configurations` and issues `modify_configuration` or `build_configuration`.

The frontend sends instructions including:

- **Live Deck**: configuration selection, transition selection, next configuration trigger, lock current configuration, manual drop, playlist buttons, luminosity slider, sensibility slider.
- **Topology**: segment selection, segment mode and direction changes (`select_segment_mode`, `toggle_segment_direction`), editor mode (`LIVE` / `MODIFY` / `BUILD`), configuration and playlist actions where enabled by mode, persisted saves only outside `LIVE`.
- **Mode Settings**: generic `set_mode_setting` messages that update the active configuration's per-mode `modeSettings` and immediately apply them to every live segment instance using that mode.
- **System**: live host telemetry plus restart python loop / restart raspberry pi controls. The `system` snapshot now includes hardware mode, CPU temp, RAM and disk usage, loop FPS/health, ESP32 reachability, Bluetooth phone status when detectable, audio stream health, uptime, connected web-client count, and action capability / feedback fields for the dangerous controls.

## Development:
The interface now auto-launches when you run `Main.py` (if `startWebApp` is `true` in `config/app_config.json`).

To run the interface manually:
```bash
npm install
npm run dev
```

If you want to disable auto-launch, set:
```json
{
  "startWebApp": false
}
```
