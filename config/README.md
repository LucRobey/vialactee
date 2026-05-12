# Configuration (`/config/`)

This directory acts as the central registry for the chandelier's static and dynamic settings.

## Key Components:

- **`segments.json`**: Defines the physical hardware geometry and 2D coordinate mapping. It includes strip ordering, LED counts, orientation (`horizontal` or `vertical`), and geometry vectors (`start`, `step`) used by spatial transitions.
- **`app_config.json`**: Contains global application variables (like network ports, audio thresholds, and persisted Live Deck `luminosity` / `sensibility`) that can be tweaked without modifying code.

### `app_config.json` Schema

| Key | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `startServer` | Boolean | `false` | If true, launches the aiohttp connector on port 8080. |
| `startWebApp` | Boolean | `true` | If true, launches the Vite React frontend on port 5173. |
| `useMicrophone` | Boolean | `true` | If true, `Local_Microphone` actively listens to the system default input device. |
| `HARDWARE_MODE` | String | `"auto"` | `"auto"`, `"rpi"`, or `"simulation"`. Determines if visualizer relies on physical ESP32 UDP networking or the Pygame visualizer. |
| `printTimeOfCalculation` | Boolean | `false` | Enables timing logs for execution loops. |
| `printModesDetails` | Boolean | `true` | Enables logs from visual modes (overridden by `modesToPrintDetails`). |
| `printMicrophoneDetails` | Boolean | `false` | Enables logs from `Local_Microphone`. |
| `printAppDetails` | Boolean | `false` | Enables core application logs. |
| `printAsservmentDetails` | Boolean | `false` | Enables logs for mathematical asservment logic. |
| `printConfigurationLoads` | Boolean | `false` | Enables logs when configuration files are read. |
| `printConfigChanges` | Boolean | `false` | Enables logs when visual configurations transition. |
| `modesToPrintDetails` | Array of Strings | `["PSG"]` | List of mode names to isolate for detailed print logs. |

- **`Configuration_manager.py`**: A utility script to load and inject these JSON configurations into the Python architecture safely.

Saved playlists and visual configurations live in `data/configurations.json`, not in `/config`. Both `Mode_master` and the Wabb web app load that file as the source of truth. The web app accesses it through `/api/configurations`, so playlist and configuration names must not be duplicated or hardcoded in React. Runtime mode or direction overrides from the Topology tab in **LIVE** do not change this file; they only affect the active `Segment` objects until the next configuration apply or reload.

## How it works:
When the program starts, the configuration manager parses the JSON files. The `segments.json` geometry is used by `Segment.py` to correctly map the 1D NeoPixel array into a 2D logical workspace, ensuring the visual algorithms display correctly on the physical chandelier. `AudioIngestion` initializes Live Deck luminosity and sensibility from `app_config.json`, and `Mode_master` persists slider changes back to that file. `Mode_master.load_configurations()` separately reads `data/configurations.json` for playlist rotation and saved segment mode/direction assignments.
