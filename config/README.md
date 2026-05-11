# Configuration (`/config/`)

This directory acts as the central registry for the chandelier's static and dynamic settings.

## Key Components:

- **`segments.json`**: Defines the physical hardware geometry and 2D coordinate mapping. It includes strip ordering, LED counts, orientation (`horizontal` or `vertical`), and geometry vectors (`start`, `step`) used by spatial transitions.
- **`app_config.json`**: Contains global application variables (like network ports, audio thresholds, and persisted Live Deck `luminosity` / `sensibility`) that can be tweaked without modifying code.
- **`Configuration_manager.py`**: A utility script to load and inject these JSON configurations into the Python architecture safely.

Saved playlists and visual configurations live in `data/configurations.json`, not in `/config`. Both `Mode_master` and the Wabb web app load that file as the source of truth. The web app accesses it through `/api/configurations`, so playlist and configuration names must not be duplicated or hardcoded in React.

## How it works:
When the program starts, the configuration manager parses the JSON files. The `segments.json` geometry is used by `Segment.py` to correctly map the 1D NeoPixel array into a 2D logical workspace, ensuring the visual algorithms display correctly on the physical chandelier. `AudioIngestion` initializes Live Deck luminosity and sensibility from `app_config.json`, and `Mode_master` persists slider changes back to that file. `Mode_master.load_configurations()` separately reads `data/configurations.json` for playlist rotation and saved segment mode/direction assignments.
