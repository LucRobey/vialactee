# Connectors (`/connectors/`)

The `connectors` directory manages all external Data In (Audio) and Data Out (Network Commands).

## Key Components:

- **`Connector.py`**: A TCP/WebSocket server that listens for commands from the `wabb-interface` (React app). It processes remote control inputs (like "change color", "change mode", or "turn off").
- **`Local_Microphone.py`**: Wraps the Python `sounddevice` library. It maintains a continuous sliding buffer of analog audio input and asynchronously pushes raw PCM data arrays directly into the `Listener` engine (which routes it to `AudioIngestion` for actual DSP math).

## How it works:
These modules run concurrently in their own threads or async loops. The `Local_Microphone` strictly acts as an I/O push-stream (performing no math), feeding raw audio to the math engine. Meanwhile, the `Connector` listens asynchronously for state-change requests from the user's phone or computer and alters global variables in the orchestration loop.
