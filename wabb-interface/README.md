# Wabb Interface (Web Controller)

This directory contains the React + Vite frontend application for Vialactée. 

It serves as the official remote control for the chandelier. We pivoted to this web interface (away from the legacy native Android App) to provide universal access across devices without requiring app store installations.

## Structure and Workflow:

- **React Framework**: Built using React, TypeScript, and Vite for lightning-fast HMR and compilation.
- **Network Layer**: Communicates with the Raspberry Pi's backend over TCP/WebSockets (handled by `Connector.py` in the `connectors/` folder).
- **Interface Capabilities**: Provides sliders, toggle buttons, and visual feedback for the user to manipulate playlist rotation, override colors, force mode changes, and observe the system's real-time performance metrics.

## Outgoing Control Instructions

The app now emits control instructions from the UI to the backend bridge through a shared WebSocket sender in `src/utils/controlBridge.ts`.

- Default WebSocket URL: `ws://<host>:8765/ws` (or `wss://` on HTTPS)
- Optional override via env var: `VITE_WABB_WS_URL`
- Message shape sent by the frontend:

```json
{
  "page": "live_deck | topology | auto_dj | system",
  "action": "string_action_name",
  "payload": {},
  "timestamp": 1715430000000
}
```

The frontend currently sends only instructions (no receive handling yet), including:

- **Live Deck**: configuration selection, transition selection, next configuration trigger, lock current configuration, manual drop, playlist buttons, luminosity slider, sensibility slider.
- **Topology**: segment selection, segment mode selection, segment direction toggle, editor mode switch (LIVE/MODIFY/BUILD), configuration selection, save/build actions, playlist previous/next cycle.
- **Auto-DJ**: rainbow color intensity, pulsar tail length, trigger interval, sweep duration.
- **System**: restart python loop, restart raspberry pi.

## Development:
The interface now auto-launches when you run `Main.py` (if `startWebApp` is `true` in `config/app_config.json`).

To run the interface manually:
```bash
npm install
npm run dev
```

If you want to disable auto-launch, set:
```json
{
  "startWebApp": false
}
```
