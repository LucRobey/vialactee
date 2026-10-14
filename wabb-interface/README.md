# Wabb Interface (Web Controller)

This directory contains the React + Vite frontend application for Vialactée.

It serves as the official remote control for the chandelier. We pivoted to this web interface (away from the legacy native Android App) to provide universal access across devices without requiring app store installations.

## Structure and Workflow

- **React Framework**: Built using React, TypeScript, and Vite for lightning-fast HMR and compilation.
- **Network Layer**: Communicates with the backend over HTTP and WebSockets (handled by `Connector.py` in the `connectors/` folder).
- **Dynamic Topology Source**: Chandelier segments and cable wiring are loaded dynamically from `GET /api/topology` (`src/utils/topologyStore.ts`), which reads the active profile's segment file (`config/segments_full.json` or `config/segments_small.json`). Segment positions on the Lego grid (`col`, `row`, `w`, `h`, `color`) and Bezier connection `cables` are unified in the backend config.
- **Interface Capabilities**: Provides sliders, toggles, lists, and visual feedback so the user can select mood palettes, trigger transitions, force per-segment mode and direction changes, tune per-mode settings, and observe real-time system and hardware profile metrics.

## Tabs (`App.tsx`)

The interface exposes four tabs:

| Tab | Component | Purpose |
|---|---|---|
| **Live Deck** | `components/pages/LiveDeck.tsx` | Performance dashboard: telemetry strip, three vertical sliders (luminosity / sensibility / auto-transition time), GO transition button, HOLD/LIVE switch, manual DROP, and Mood Palette bricks. |
| **Topology** | `components/pages/TopologyEditor.tsx` | Live spatial map of the chandelier with per-segment mode and direction inspector. Segment layout and cables load dynamically from `/api/topology`. |
| **Mode Settings** | `components/pages/ModeSettings.tsx` | Dynamic per-mode tuning driven by `modeSettingsCatalog`; emits `set_mode_setting`. |
| **System** | `components/pages/SystemSetup.tsx` | Live telemetry, active hardware profile display (`FULL`: 2 Channels · 11 Segments, or `SMALL`: 1 Channel · 3 Segments), and dangerous actions (`restart_python_loop`, `restart_raspberry_pi`) gated by backend capability flags. |

## Dynamic Topology API (`/api/topology`)

Handled by `src/utils/topologyStore.ts` via `loadTopology()`:
- `GET /api/topology` returns `{ "segments": RawSegmentDefinition[], "cables": TopologyCable[] }`.
- `normalizeTopologySegments()` converts backend segment definitions into UI `TopologySegment` objects, applying grid offsets (`MAP_OFFSET_C`, `MAP_OFFSET_R`).
- When the backend switches `hardwareProfile`, `TopologyEditor` dynamically re-fetches the topology layout.

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

The same WebSocket also receives `mode_master_state` messages from Python. These snapshots hydrate Live Deck, Topology, Mode Settings, and System with:
- `hardwareProfile`: Current active profile (`"full"` or `"small"`). Triggers reactive reload of topology when changed.
- `transitionLocked`, `transitionState`, `transitionProgress`, `selectedTransition`.
- `activeMood`, `availableMoods`.
- Sliders: `luminosity`, `sensibility`, `autoTransitionTime`.
- Catalogs: `availableModes`, `modeSettingsCatalog`, effective `modeSettings`.
- Segments: active `mode`, `direction`, `blocked`, `targetMode`, and `inTransition` per segment.
- `system`: telemetry block (hardware mode, profile, temperatures, FPS, resource usage).

The frontend sends instructions including:

- **Live Deck (`page: "live_deck"`)**: `select_mood`, `select_transition`, `go_to_next_configuration`, `lock_current_configuration`, `manual_drop`, `set_luminosity`, `set_sensibility`, `set_auto_transition_time`.
- **Topology (`page: "topology"`)**: `select_segment_mode`, `toggle_segment_direction`.
- **Mode Settings (`page: "mode_settings"`)**: `set_mode_setting` messages that update per-mode `mode_settings` in `config/app_config.json` and immediately apply them to every live segment instance using that mode.
- **System (`page: "system"`)**: `restart_python_loop` and `restart_raspberry_pi`, both confirmed in the UI and gated by `system.actions.*.available`.

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
