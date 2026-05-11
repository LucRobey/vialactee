# Connectors (`/connectors/`)

The `connectors` directory manages all external Data In (Audio) and Data Out (Network Commands).

## Key Components:

- **`Connector.py`**: A WebSocket server (`/ws` on port `8080`) that listens for JSON instructions from the `wabb-interface` React app (`src/utils/controlBridge.ts`). It validates instruction payloads, logs them, and acknowledges receipt.
- **`Local_Microphone.py`**: Wraps the Python `sounddevice` library. It maintains a continuous sliding buffer of analog audio input and asynchronously pushes raw PCM data arrays directly into the `Listener` engine (which routes it to `AudioIngestion` for actual DSP math).

## How it works:
These modules run concurrently in async tasks. The `Local_Microphone` strictly acts as an I/O push-stream (performing no math), feeding raw audio to the math engine. Meanwhile, `Connector` accepts WebSocket instructions and validates the new control payload shape:

```json
{
  "page": "live_deck | topology | auto_dj | system",
  "action": "string_action_name",
  "payload": {},
  "timestamp": 1715430000000
}
```

`Connector.py` no longer uses the legacy colon-separated command parser. It now expects JSON instructions only and responds with:

- `{"ok": true, "received": "<action>"}`
- `{"ok": false, "error": "invalid_instruction_json"}` when payload parsing fails.
