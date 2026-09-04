# Hardware Abstraction (`/hardware/`)

The `hardware` directory provides an interface layer between the Python code and the physical light-emitting hardware. 

## Key Components:

- **`HardwareInterface.py`**: The abstract base class defining what a hardware controller must be able to do (e.g., `set_pixel()`, `show()`, array operations).
- **`HardwareFactory.py`**: A factory pattern script that detects the environment and returns the appropriate hardware class. In simulation mode, it automatically launches the `Fake_ESP32` process in the background.
- **`Udp_Sender.py`**: The primary data driver. Instead of blocking the Python event loop with hardware processing, it serializes the computed RGB arrays and broadcasts them as high-speed UDP packets over the network (ports 9001/9002). It also streams segment metadata and live `AudioAnalyzer` telemetry over sideband port 9003.
- **`Fake_ESP32.py`**: The development receiver. A standalone Python script that mimics the physical ESP32. It listens on local UDP ports for incoming RGB packets (9001, 9002) and metadata packets (9003), passing them to the Pygame visualizer.
- **`Fake_leds.py`**: Contains `FakeLedsVisualizer`, which draws a Pygame window that perfectly simulates the physical dimensions and segment layout of the chandelier. When `show_music_analyser_panel` is enabled, it renders a real-time cyberpunk HUD overlay in the bottom-left corner with live BPM, flywheel phase, confidence, onset events, and structural novelty.

### Legacy / Deprecated Components:

- **`Rpi_NeoPixels.py`**: (Legacy/Alternative) Direct GPIO driver using `rpi_ws281x`. Eclipsed by the UDP/ESP32 architecture.

## How it works:
When `Mode_master` finishes computing the colors for a frame, it passes the RGB array to the active Hardware instance (usually `Udp_Sender`). The sender blasts the data over UDP. 

If `HARDWARE_MODE` is `"simulation"`, `HardwareFactory` spawns the `Fake_ESP32` subprocess which receives these local UDP packets and renders them on a PC screen. This perfectly simulates the Raspberry Pi -> Wi-Fi -> ESP32 architecture on a single machine, decoupling the visual rendering from the main `asyncio` audio-processing loop. Live audio analyzer state is streamed on sideband port `9003` to power the in-simulator HUD without stalling the main loop.

> [!NOTE]
> [See ../.agents/docs/hardware_pipeline.md for the full system diagram]