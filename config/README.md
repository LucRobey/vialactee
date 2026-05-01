# Configuration (`/config/`)

This directory acts as the central registry for the chandelier's static and dynamic settings.

## Key Components:

- **`segments.json`**: Defines the physical hardware geometry. It lists how many LEDs are in each strip, their topological order, and their physical orientation (`horizontal` or `vertical`).
- **`app_config.json`**: Contains global application variables (like maximum brightness, network ports, or audio thresholds) that can be tweaked without modifying code.
- **`Configuration_manager.py`**: A utility script to load and inject these JSON configurations into the Python architecture safely.

## How it works:
When the program starts, the configuration manager parses the JSON files. The `segments.json` geometry is used by `Segment.py` to correctly map the 1D NeoPixel array into a 2D logical workspace, ensuring the visual algorithms display correctly on the physical chandelier.
