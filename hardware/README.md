# Hardware Abstraction (`/hardware/`)

The `hardware` directory provides an interface layer between the Python code and the physical light-emitting hardware. 

## Key Components:

- **`HardwareInterface.py`**: The abstract base class defining what a hardware controller must be able to do (e.g., `set_pixel()`, `show()`, array operations).
- **`HardwareFactory.py`**: Dynamic hardware instantiator:
  - Dynamically reads the active segment configuration via `_get_channel_specs(infos)` to determine channel count, LED lengths per channel, ports (`9000 + idx`), and pins (`D21` for ch 1, `D18` for ch 2).
  - Returns a tuple of hardware controller instances (e.g. `(leds1,)` for `small` profile or `(leds1, leds2)` for `full` profile) passed to `Mode_master`.
  - In simulation mode, automatically spawns `Fake_ESP32.py` as a background process.
- **`Udp_Sender.py`**: The primary data driver. Serializes computed RGB arrays and broadcasts them as high-speed UDP packets over the network (e.g. ports 9001 and 9002). It also streams segment metadata and live `AudioAnalyzer` telemetry over sideband port 9003.
- **`Fake_ESP32.py`**: The development receiver. A standalone background script that mimics the physical ESP32. It calls `_get_channel_specs()` to bind UDP listener sockets dynamically for all active channels (e.g., 9001 for ch 1, 9002 for ch 2) and metadata (9003), routing RGB frames to `Fake_leds.py`.
- **`Fake_leds.py`**: Contains `FakeLedsVisualizer`, which renders the chandelier in a `1300 x 900` Pygame window. It dynamically reconstructs its display geometry via `_load_visualizer_segments_def()` directly from the active segment JSON file (`segments_full.json` or `segments_small.json`), establishing a single source of truth:
  - **`full` profile**: Renders the 11-segment 2-channel chandelier layout (1,304 LEDs).
  - **`small` profile**: Renders the 3-segment 1-channel layout (249 LEDs: `s1` vertical, `s2` vertical, `s3` vertical).
  - When `show_music_analyser_panel` is enabled, renders the real-time cyberpunk HUD overlay with live BPM, flywheel phase, onset events, and structural novelty.

### Legacy Raspberry Pi Direct GPIO:

- **`Rpi_NeoPixels.py`**: Legacy direct GPIO driver using `adafruit-circuitpython-neopixel` and `adafruit-blinka` on Raspberry Pi hosts, dynamically instantiated per channel with assigned GPIO pins (`D21`, `D18`). Note that production deployments use the networked ESP32 architecture over UDP to avoid Linux DMA/PWM audio contention.

## UDP Network Protocol Specifications

The communication between `Udp_Sender.py` and the receiver (`Fake_ESP32.py` or physical ESP32 firmware) follows strict network packet standards:

### 1. Pixel Data Streams (Ports 9001, 9002)
- **Header**: 2-byte little-endian unsigned short (`<H`) representing the starting pixel index for the packet payload.
- **Payload**: Raw contiguous RGB bytes (`np.uint8`, 3 bytes per pixel).
- **MTU Chunking**: Packets are chunked to a maximum of `400` LEDs (1,200 bytes payload + 2 bytes header = 1,202 bytes), fitting safely within standard 1,472-byte UDP MTU limits without IP fragmentation.
  - Full Profile Channel 1 (785 LEDs): Packet 0 (LEDs 0–399, 1,202 B), Packet 1 (LEDs 400–784, 1,157 B).
  - Full Profile Channel 2 (519 LEDs): Packet 0 (LEDs 0–399, 1,202 B), Packet 1 (LEDs 400–518, 359 B).
  - Small Profile Channel 1 (249 LEDs): Packet 0 (LEDs 0–248, 749 B).

### 2. Sideband Telemetry & Metadata (Port 9003)
UTF-8 encoded JSON packets sent to power the Pygame simulator HUD without stalling the pixel loops:
- `analyzer_state`: Broadcasts `bpm`, `phase`, `flywheel_status`, `confidence`, `is_beat`, `beat_tag`, `is_song_change`, `is_verse_chorus_change`, `novelty`, `power`, and `silence_frames`.
- `segment_mode`: Broadcasts segment active and target transition modes (`name`, `mode`, `target`).

## How it works:
When `Mode_master` finishes computing the colors for a frame, it passes each channel's RGB array to its respective hardware driver instance (e.g., `Udp_Sender` or `Rpi_NeoPixels`).

If `HARDWARE_MODE` is `"simulation"`, `HardwareFactory` spawns the `Fake_ESP32` subprocess which receives local UDP packets across all active channels and renders them in Pygame. This perfectly simulates the Raspberry Pi -> Wi-Fi -> ESP32 architecture on a single machine, decoupling visual rendering from the main `asyncio` audio-processing loop. Live audio analyzer state is streamed on sideband port `9003` to power the in-simulator HUD without stalling the main loop.

> [!NOTE]
> [See ../.agents/docs/hardware_pipeline.md for the full system diagram]