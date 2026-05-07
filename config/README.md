# Configuration (`/config/`)

This directory acts as the central registry for the chandelier's static and dynamic settings.

## Key Components:

- **`segments.json`**: Defines the physical hardware geometry and 2D coordinate mapping. It includes strip ordering, LED counts, orientation (`horizontal` or `vertical`), and geometry vectors (`start`, `step`) used by spatial transitions.
- **`app_config.json`**: Contains global application variables (like maximum brightness, network ports, or audio thresholds) that can be tweaked without modifying code.
- **`Configuration_manager.py`**: A utility script to load and inject these JSON configurations into the Python architecture safely.

## How it works:
When the program starts, the configuration manager parses the JSON files. The `segments.json` geometry is used by `Segment.py` to correctly map the 1D NeoPixel array into a 2D logical workspace, ensuring the visual algorithms display correctly on the physical chandelier.
