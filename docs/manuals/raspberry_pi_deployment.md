# Raspberry Pi & ESP32 Deployment Manual

> **Location:** `docs/manuals/raspberry_pi_deployment.md` (Tier 2 Operational Manual)  
> **Target Hardware:** Raspberry Pi 4B (4GB/8GB) + ESP32 DevKit V1 + WS2812B / NeoPixel Strips  
> **Firmware Directory:** [`hardware/esp32_firmware/`](../../hardware/esp32_firmware/)  
> **Enforcing Axioms:** [AXIOM-01](../axioms/AXIOM-01_FRAME_BUDGET.md), [AXIOM-03](../axioms/AXIOM-03_HARDWARE_GEOMETRY.md), [AXIOM-04](../axioms/AXIOM-04_NETWORK_PROTOCOLS.md)

---

## 1. Automated Provisioning (`setup-raspberry-pi.sh`)

To deploy Vialactée on a fresh Raspberry Pi OS (Bookworm / Bullseye 64-bit):

```bash
chmod +x setup-raspberry-pi.sh
./setup-raspberry-pi.sh
```

This script:
1. Installs system audio & compilation packages (`portaudio19-dev`, `libatlas-base-dev`, `python3-venv`, `nodejs`, `npm`).
2. Clones/updates the repository in `~/vialactee`.
3. Builds the Python `.venv` and installs `requirements.txt`.
4. Builds `wabb-interface` npm dependencies and creates `~/vialactee/run-vialactee.sh`.

---

## 2. Audio Loopback, Bluetooth A2DP Sink & ALSA Configuration

### A. USB Sound Card / Microphone Setup
1. List available ALSA devices:
   ```bash
   arecord -l
   aplay -l
   ```
2. Configure `audio_preset` in `config/app_config.json`:
   - `"mic"`: Real-time room microphone (`fakeDelay: 0.0`).
   - `"aux"`: External line-in through 3.5mm / USB capture with 5.0s lookahead delay (`fakeDelay: 5.0`).
   - `"custom"`: Explicit `input_device_id` and `output_device_id`.

### B. Bluetooth A2DP Sink (Smartphone Streaming)
To stream music directly from a smartphone to the Raspberry Pi:
1. Install `bluez-alsa` or `pulseaudio-module-bluetooth`:
   ```bash
   sudo apt-get install -y bluez-tools pulseaudio-module-bluetooth
   ```
2. Pair smartphone via `bluetoothctl`.
3. In `config/app_config.json`, configure:
   ```json
   {
     "audio_preset": "spotify_aux",
     "HARDWARE_MODE": "esp32",
     "hardware_profile": "full",
     "esp32_ip": "192.168.1.41"
   }
   ```

---

## 3. Systemd Service Deployment (`vialactee.service`)

To run Vialactée automatically at system boot as an unprivileged service:

1. Create `/etc/systemd/system/vialactee.service`:
   ```ini
   [Unit]
   Description=Vialactee LED Chandelier Orchestrator
   After=network.target sound.target

   [Service]
   Type=simple
   User=pi
   WorkingDirectory=/home/pi/vialactee
   ExecStart=/home/pi/vialactee/.venv/bin/python Main.py
   Restart=on-failure
   RestartSec=5s
   Environment=PYTHONUNBUFFERED=1
   Environment=SDL_VIDEODRIVER=dummy

   [Install]
   WantedBy=multi-user.target
   ```
2. Enable and start:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable vialactee.service
   sudo systemctl start vialactee.service
   ```
3. Check logs:
   ```bash
   journalctl -u vialactee.service -f
   ```

---

## 4. Direct GPIO NeoPixel Wiring (`HARDWARE_MODE: "rpi"`)

When driving strips directly from the Raspberry Pi GPIO pins (requires `sudo` for DMA `/dev/mem` access):
- **Channel 1 (785 LEDs):** `GPIO 21` (Physical Pin 40 — PCM_DOUT, conflict-free with onboard audio).
- **Channel 2 (519 LEDs):** `GPIO 18` (Physical Pin 12 — PWM0).
- **Level Shifting:** Use a 74AHCT125 level shifter to step 3.3V logic up to 5.0V WS2812B data level, with a 330 $\Omega$ series resistor on each data line and common ground (`GND`) shared between the Pi and 5V power supplies.

---

## 5. Wireless ESP32 UDP Receiver (`HARDWARE_MODE: "esp32"`)

In production, the Raspberry Pi or PC streams chunked UDP pixel frames over Wi-Fi to an ESP32 running [`hardware/esp32_firmware/`](../../hardware/esp32_firmware/).

### 5.1 Firmware Directory Structure

```text
hardware/esp32_firmware/
├── ESP32_full/
│   ├── ESP32_full.ino        # 2-Channel Full Chandelier firmware (1,304 LEDs)
│   ├── secrets.h             # Local Wi-Fi credentials
│   └── secrets.h.example     # Template for Wi-Fi credentials
├── ESP32_small/
│   ├── ESP32_small.ino       # 1-Channel Small Profile firmware (249 LEDs)
│   ├── secrets.h             # Local Wi-Fi credentials
│   └── secrets.h.example     # Template for Wi-Fi credentials
└── ESP32_test/
    └── ESP32_test.ino        # Standalone hardware test sketch (no Wi-Fi/UDP)
```

### 5.2 Profile Comparison (`FULL` vs `SMALL`)

Matches `"hardware_profile"` in [`config/app_config.json`](../../config/app_config.json):

| Feature | **FULL Profile** (`"full"`) | **SMALL Profile** (`"small"`) |
| :--- | :--- | :--- |
| **Sketch File** | `ESP32_full/ESP32_full.ino` | `ESP32_small/ESP32_small.ino` |
| **Active Channels** | **2 Channels** (Dual UDP Listeners) | **1 Channel** (Single UDP Listener) |
| **Total LEDs** | **1,304 LEDs** | **249 LEDs** |
| **Channel 1** | **785 LEDs** on **UDP Port `9001`** $\rightarrow$ **GPIO 21** (`D21`) | **249 LEDs** on **UDP Port `9001`** $\rightarrow$ **GPIO 21** (`D21`) |
| **Channel 2** | **519 LEDs** on **UDP Port `9002`** $\rightarrow$ **GPIO 18** (`D18`) | *Disabled* |

### 5.3 Visual Strip Status Diagnostics

- **Solid RED (`STATE_DISCONNECTED`):** Searching for and connecting to Wi-Fi (or Wi-Fi dropped; auto-reconnection is active).
- **Solid GREEN (`STATE_WAITING`):** Connected to Wi-Fi and ready, waiting for UDP packets on port `9001` (and `9002` in `FULL` mode), or stream idle for $> 1\text{ s}$.
- **Live Animations (`STATE_STREAMING`):** Actively receiving UDP frames from Python.

### 5.4 Hardware Wiring & Pinout (ESP32)

| ESP32 Pin | Label on Board | Connects To | Purpose |
| :--- | :--- | :--- | :--- |
| **GPIO 21** | `D21` | **Strip 1 Data In (`DIN`)** | Primary LED Strip Data (Channel 1 — Port `9001`) |
| **GPIO 18** | `D18` | **Strip 2 Data In (`DIN`)** | Secondary LED Strip Data (Channel 2 — Port `9002`, `FULL` profile only) |
| **GND** | `GND` | **LED Strip `GND` / Power Supply `-V`** | **CRITICAL:** Common Ground Reference |
| **VIN / 5V** | `VIN` or `5V` | **5V Power Supply `+V`** *(Optional)* | Powers the ESP32 if not powered via USB |

> **Electrical Safeguards:**
> 1. **Common Ground (`GND`):** Always connect `GND` of the ESP32 to the negative (`GND` / `-V`) terminal of the 5V LED power supply. Without a common ground, the LEDs will glitch violently.
> 2. **Data Line Resistor:** Place a **$330\,\Omega$ to $470\,\Omega$ resistor** in series between `GPIO 21` / `GPIO 18` and the strip `DIN` pads to prevent voltage ringing.
> 3. **Power Filtering Capacitor:** Connect a **$1000\,\mu\text{F}$ electrolytic capacitor** ($\ge 6.3\text{V}$, ideally $16\text{V}$) across `+5V` and `GND` where power enters the strips.
> 4. **Never power LEDs through the ESP32:** Feed high-amperage 5V power directly from the external PSU to the strips (with power injection every ~150–250 LEDs).

### 5.5 Flashing the ESP32

1. Install **Arduino IDE 2.x**, add the Espressif ESP32 board manager URL (`https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`), and install the **esp32** board package and **FastLED** library.
2. Verify `secrets.h` inside `ESP32_full/` or `ESP32_small/` has your Wi-Fi `ssid` and `password`.
3. Open `ESP32_full/ESP32_full.ino` (or `ESP32_small/ESP32_small.ino`), select **ESP32 Dev Module** (`115200` baud), and click **Upload**.
4. Open the Serial Monitor (`115200` baud) to read the ESP32's assigned IP address and set `"esp32_ip"` in `config/app_config.json`.
