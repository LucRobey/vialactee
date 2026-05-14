# Wabb Interface (Web Controller)

This directory contains the React + Vite frontend application for Vialactée.

It serves as the official remote control for the chandelier. We pivoted to this web interface (away from the legacy native Android App) to provide universal access across devices without requiring app store installations.

## Structure and Workflow

- **React Framework**: Built using React, TypeScript, and Vite for lightning-fast HMR and compilation.
- **Network Layer**: Communicates with the Raspberry Pi's backend over HTTP and WebSockets (handled by `Connector.py` in the `connectors/` folder).
- **Configuration Source**: Playlists and configurations are loaded from `data/configurations.json` through `/api/configurations`. Do not hardcode playlist names or configuration names in React components.
- **Interface Capabilities**: Provides sliders, toggles, lists, and visual feedback so the user can manipulate playlist rotation, force mode changes, tune per-mode settings, and observe the system's real-time performance metrics.

## Tabs (`App.tsx`)

The interface exposes five tabs, all currently implemented:

| Tab | Component | Purpose |
|---|---|---|
| **Live Deck** | `components/pages/LiveDeck.tsx` | Performance dashboard: telemetry strip, three vertical sliders (luminosity / sensibility / auto-transition time), Next Configuration & Next Transition queue, baton-pass button, HOLD/LIVE switch, manual DROP, eight preset bricks. |
| **Topology** | `components/pages/TopologyEditor.tsx` rendered with `allowedModes={['LIVE']}` | LIVE spatial map of the chandelier with per-segment inspector. No preset authoring panels are visible here. |
| **Configurator** | `components/pages/Configurator.tsx` (reuses the same `TopologyEditor`) | Preset authoring: MODIFY / BUILD over `POST /api/configurations` plus the configuration & playlist inspector panels. |
| **Mode Settings** | `components/pages/ModeSettings.tsx` | Dynamic per-mode tuning driven by `modeSettingsCatalog`; emits `set_mode_setting`. |
| **System** | `components/pages/SystemSetup.tsx` | Live telemetry + dangerous actions (`restart_python_loop`, `restart_raspberry_pi`) gated by backend capability flags. |

## Configuration JSON

The shared helper `src/utils/configurationStore.ts` is the frontend boundary for reading and writing `data/configurations.json`.

- `GET /api/configurations` returns `{ "playlists": string[], "configurations": Record<string, Configuration[]> }`.
- `POST /api/configurations` persists the same shape back to disk.
- During Vite development, `vite.config.ts` serves this API.
- During Python-backed operation, `connectors/Connector.py` serves the same API and asks `Mode_master` to reload the saved playlists/configurations.
- `loadConfigurationStore()` uses the HTTP endpoint (Live Deck / Topology). `loadConfigurationFileStore()` resolves the file via Vite's `?raw` import — used by the Configurator to avoid racing live snapshots.

## WebSocket Control And State

The app emits control instructions from the UI to the backend bridge through a shared WebSocket sender in `src/utils/controlBridge.ts`.

- Default WebSocket URL: `ws://<host>:8080/ws` (or `wss://` on HTTPS).
- Optional override via env var: `VITE_WABB_WS_URL`.
- Instruction shape sent by the frontend:

```json
{
  "page": "live_deck | topology | mode_settings | system",
  "action": "string_action_name",
  "payload": {},
  "timestamp": 1715430000000
}
```

The same WebSocket also receives `mode_master_state` messages from Python. These snapshots hydrate Live Deck, Topology, Configurator, Mode Settings, and System with the current active playlist, active/queued configuration, transition lock, luminosity, sensibility, **auto-transition time**, the backend-provided `availableModes` catalog, each segment's active mode/direction, the mode-settings catalog, the current effective per-mode values for the active configuration, and the live `system` telemetry block.

**Topology `LIVE`:** segment mode/direction changes are sent as instructions only (no `POST /api/configurations`). The UI merges snapshots with short-lived pending values so rapid broadcasts do not undo a click before Python applies it.
**Configurator `MODIFY` / `BUILD`:** saving writes through `POST /api/configurations` and issues `modify_configuration` or `build_configuration`.

> The Configurator tab dispatches its instructions on the same `topology` page; the backend distinguishes intent via the `set_editor_mode` action and the persistence-related actions.

The frontend sends instructions including:

- **Live Deck (`page: "live_deck"`)**: `select_configuration`, `select_transition`, `go_to_next_configuration`, `lock_current_configuration`, `manual_drop`, `select_playlist`, `set_luminosity`, `set_sensibility`, `set_auto_transition_time`.
- **Topology / Configurator (`page: "topology"`)**: `select_segment`, `select_segment_mode`, `toggle_segment_direction`, `set_editor_mode` (`LIVE` / `MODIFY` / `BUILD`), `select_playlist_slot`, `select_configuration`, `modify_configuration`, `build_configuration`. Persisted saves are only triggered outside `LIVE`.
- **Mode Settings (`page: "mode_settings"`)**: `set_mode_setting` messages that update the active configuration's per-mode `modeSettings` and immediately apply them to every live segment instance using that mode.
- **System (`page: "system"`)**: `restart_python_loop` and `restart_raspberry_pi`, both confirmed in the UI and gated by `system.actions.*.available`. The `system` snapshot includes hardware mode, CPU temp, RAM and disk usage, loop FPS/health, ESP32 reachability, Bluetooth phone status, microphone state, audio stream health, last sample age, dynamic latency, uptime, hostname/platform, connected web-client count, and `lastAction` feedback for the dangerous controls.

## Development

The interface auto-launches when you run `Main.py` (if `startWebApp` is `true` in `config/app_config.json`).

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
