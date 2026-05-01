# 🌌 Vialactée

Welcome to the **Vialactée** project!

Vialactée is an asynchronous Python orchestration server designed to run on a Raspberry Pi and control a 1,304-LED music-reactive chandelier. It listens to live audio in real-time, performs deep algorithmic analysis (beat detection, frequency extraction, structural event detection), and drives the physical LED arrays using mathematically precise visual modes.

It features a non-causal audio lookahead buffer, seamless asynchronous orchestration, and an interactive Web Interface for real-time control.

## 📂 Project Structure

Here is a breakdown of the core directories in this project:

- **`core/`**: The brain of the project. Contains the algorithmic engines, asynchronous managers, the Listener (audio DSP), and the Transition Director.
- **`config/`**: JSON files and managers detailing the hardware geometry and global settings.
- **`connectors/`**: The external communication handlers. This includes the TCP/WebSocket server that talks to the web interface, as well as microphone stream capture tools.
- **`hardware/`**: Hardware abstractions. Allows switching seamlessly between testing on a PC (with Pygame simulated LEDs) and running on the real Raspberry Pi (with WS2812b NeoPixels).
- **`modes/`**: The visual behavior library. Each file here defines a unique lighting animation pattern powered by numpy matrix math.
- **`wabb-interface/`**: A React-based web application serving as the remote controller for the user to change playlists, transition modes, or tweak settings on the fly.
- **`.agents/`**: Core context, architectural rules, and technical specifications designed for AI agents working on the codebase.

*(Please refer to the `README.md` inside each specific folder to learn more about how they work in detail).*
