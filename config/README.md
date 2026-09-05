# Configuration (`/config/`)

This directory acts as the central registry for the chandelier's static and dynamic settings.

## Key Components:

- **`segments_full.json` & `segments_small.json`**: Unified single source of truth defining both physical hardware geometry AND Web App UI layout for each hardware profile:
  - **Hardware Geometry**: Physical strip ordering (`order`), LED counts (`size`), physical orientation (`horizontal` or `vertical`), and 2D spatial coordinate mapping vectors (`start`, `step`) used by spatial transitions.
  - **Web App UI Layout**: Studio grid rendering metadata (`id`, `ui`: `col`, `row`, `w`, `h`, `color`) for the interactive Wabb Topology board.
  - **Cables Array**: Top-level `cables` array defining Bezier connection curves (`start`, `end`, `cp1`, `cp2`) rendered in the Wabb Topology view.
- **`app_config.json`**: Contains global application variables (network ports, hardware profile selection, audio thresholds, and persisted Live Deck `luminosity` / `sensibility`).
- **`Configuration_manager.py`**: Dynamic configuration resolution utility and spatial coordinate builder:
  - `resolve_segments_file_path(infos=None)`: Resolves the active segment layout (`segments_small.json` for `small`, `segments_full.json` for `full`).
  - `resolve_configurations_file_path(infos=None)`: Resolves the active playlist/mode configuration file (`data/configurations_small.json` for `small`, `data/configurations_full.json` for `full`).
  - `Configurations_manager`: Class that loads segment definitions and provides `get_segment_coordinates(segment_name)` to generate 2D coordinate arrays `[[x, y], ...]` for spatial transition algorithms.

### `app_config.json` Schema

| Key | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `hardware_profile` | String | `"full"` | Active profile: `"full"` (11 segments, 2 channels, 1,304 LEDs) or `"small"` (3 segments, 1 channel, 249 LEDs). Determines which segment and configuration store files are loaded. |
| `HARDWARE_MODE` | String | `"auto"` | Hardware driver selection: `"auto"`, `"simulation"`, `"esp32"`, or `"rpi"`. |
| `startServer` | Boolean | `false` | If true, starts the aiohttp WebSocket and REST API server on port 8080. |
| `useMicrophone` | Boolean | `true` | If true, enables audio ingestion from the system default microphone or input loopback. |
| `audio_preset` | String | `"spotify"` | Automatic audio routing preset: `"spotify"` (Spotify in via Virtual Cable, 5s delay, PC speakers out), `"spotify_aux"` (Spotify in via Virtual Cable, 5s delay, AUX jack out), `"aux"` (external Line-in/jack in, 5s delay, PC speakers out), `"mic"` (ambient room mic, 5s delay), or `"custom"` (uses explicit `input_device_id`, `output_device_id`, and `fakeDelay`). |
| `esp32_ip` | String | `"192.168.0.26"` | Target ESP32 controller IP address when using UDP network streaming. |
| `log_level` | String | `"INFO"` | Standard library logger verbosity (`"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"`). |
| `luminosity` | Integer | `50` | Master brightness scale percentage (0–100), persisted across sessions. |
| `sensibility` | Integer | `50` | Audio gain sensitivity scale percentage (1–100), persisted across sessions. |
| `auto_transition_time` | Integer | `80` | Automatic timer duration (seconds) before transitioning between configuration playlist presets. |
| `show_music_analyser_panel` | Boolean | `true` | If true, renders the live audio analysis HUD overlay in the visualizer window. |
| `printCpuFpsInfo` | Boolean | `true` | If true, periodically logs loop execution FPS, component timings, and performance metrics to stdout. |
| `profiler` | Object | `{...}` | Granular profiler tuning: `format` (`"compact"`, `"dashboard"`, `"alerts_only"`), `interval_seconds` (default `5.0`), `target_fps` (default `30`), `alert_threshold_ms` (default `35.0`), `track_slowest_mode` (default `true`). |

## Hardware Profiles (`full` vs `small`)

| Profile | Channel Count | Total Segments | Total LEDs | Segment File | Configuration Store |
|---|---|---|---|---|---|
| **`full`** | 2 channels (`segs_1`, `segs_2`) | 11 segments (`v1`–`v4`, `h00`, `h10`, `h11`, `h20`, `h30`–`h32`) | 1,304 LEDs | `config/segments_full.json` | `data/configurations_full.json` |
| **`small`** | 1 channel (`segs_1`) | 3 segments (`s1`, `s2`, `s3`) | 249 LEDs | `config/segments_small.json` | `data/configurations_small.json` |

## How it works:
When the program starts, `Configuration_manager.resolve_segments_file_path()` and `resolve_configurations_file_path()` determine which files to load based on `hardware_profile` in `app_config.json`. 

The segment definitions map the 1D NeoPixel arrays into a 2D logical workspace for `Segment.py` and provide layout metadata for the Wabb Web App over `GET /api/topology`. `AudioIngestion` initializes Live Deck luminosity and sensibility from `app_config.json`, and `Mode_master` persists slider changes back to that file. `Mode_master.load_configurations()` reads the resolved configuration JSON (`data/configurations_full.json` or `data/configurations_small.json`) for playlist rotation and saved segment mode/direction assignments.

