# Wabb Interface (Web Controller)

This directory contains the React + Vite frontend application for Vialactée. 

It serves as the official remote control for the chandelier. We pivoted to this web interface (away from the legacy native Android App) to provide universal access across devices without requiring app store installations.

## Structure and Workflow:

- **React Framework**: Built using React, TypeScript, and Vite for lightning-fast HMR and compilation.
- **Network Layer**: Communicates with the Raspberry Pi's backend over TCP/WebSockets (handled by `Connector.py` in the `connectors/` folder).
- **Interface Capabilities**: Provides sliders, toggle buttons, and visual feedback for the user to manipulate playlist rotation, override colors, force mode changes, and observe the system's real-time performance metrics.

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
