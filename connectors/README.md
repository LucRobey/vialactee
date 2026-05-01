# Connectors (`/connectors/`)

The `connectors` directory manages all external Data In (Audio) and Data Out (Network Commands).

## Key Components:

- **`Connector.py`**: A TCP/WebSocket server that listens for commands from the `wabb-interface` (React app). It processes remote control inputs (like "change color", "change mode", or "turn off").
- **`Local_Microphone.py`**: Wraps the Python `sounddevice` library. It maintains a continuous 4096-sample sliding buffer of analog audio input, piping raw PCM data into the `Listener` engine for DSP analysis.
- **`ESP32_Microphone.py`**: A network-based microphone handler (typically used if an ESP32 is broadcasting UDP audio packets instead of a direct line-in).

## How it works:
These modules run concurrently in their own threads or async loops. The `Local_Microphone` pushes audio data to the math engine, while the `Connector` listens asynchronously for state-change requests from the user's phone or computer and alters global variables in the orchestration loop.
