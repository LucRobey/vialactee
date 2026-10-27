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

## 2. Audio Loopback & ALSA Configuration

### USB Sound Card / Microphone Setup
1. List available ALSA devices:
   ```bash
   arecord -l
   aplay -l
   ```
2. Configure `audio_preset` in `config/app_config.json`:
   - `"mic"`: Real-time room microphone (`fakeDelay: 0.0`).
   - `"aux"`: External line-in through 3.5mm / USB capture with 5.0s lookahead delay (`fakeDelay: 5.0`).
   - `"custom"`: Explicit `input_device_id` and `output_device_id`.

---

## 3. Direct GPIO NeoPixel Wiring (`HARDWARE_MODE: "rpi"`)

When driving strips directly from the Raspberry Pi GPIO pins (requires `sudo` for DMA `/dev/mem` access):
- **Channel 1 (785 LEDs):** `GPIO 21` (Physical Pin 40 — PCM_DOUT, conflict-free with onboard audio).
- **Channel 2 (519 LEDs):** `GPIO 18` (Physical Pin 12 — PWM0).
- **Level Shifting:** Use a 74AHCT125 level shifter to step 3.3V logic up to 5.0V WS2812B data level, with a 330 $\Omega$ series resistor on each data line and common ground (`GND`) shared between the Pi and 5V power supplies.

---

## 4. Wireless ESP32 UDP Receiver (`HARDWARE_MODE: "esp32"`)

In production, the Raspberry Pi or PC streams chunked UDP pixel frames over Wi-Fi to an ESP32 running [`hardware/esp32_firmware/`](../../hardware/esp32_firmware/).

### 4.1 Firmware Directory Structure

```text
hardware/esp32_firmware/
├── esp32_udp_neopixel.ino        # Master configurable firmware (#define PROFILE_FULL)
├── esp32_udp_neopixel_full.ino   # Ready-to-flash 2-Channel Full Chandelier firmware (1,304 LEDs)
├── esp32_udp_neopixel_small.ino  # Ready-to-flash 1-Channel Small Testing firmware (249 LEDs)
└── secrets.h.example             # Template for Wi-Fi credentials (copy to secrets.h)
```

### 4.2 Profile Comparison (`FULL` vs `SMALL`)

Matches `"hardware_profile"` in [`config/app_config.json`](../../config/app_config.json):

| Feature | **FULL Profile** (`"full"`) | **SMALL Profile** (`"small"`) |
| :--- | :--- | :--- |
| **Sketch File** | `esp32_udp_neopixel_full.ino` | `esp32_udp_neopixel_small.ino` |
| **Active Channels** | **2 Channels** (Dual UDP Listeners) | **1 Channel** (Single UDP Listener) |
| **Total LEDs** | **1,304 LEDs** | **249 LEDs** |
| **Channel 1** | **785 LEDs** on **UDP Port `9001`** $\rightarrow$ **GPIO 4** | **249 LEDs** on **UDP Port `9001`** $\rightarrow$ **GPIO 4** |
| **Channel 2** | **519 LEDs** on **UDP Port `9002`** $\rightarrow$ **GPIO 5** | *Disabled* |

### 4.3 On-Board Status LED (`GPIO 2` Blue LED)

- **Rapid Blinking (`200ms` interval):** Searching for and connecting to Wi-Fi.
- **Solid ON:** Connected to Wi-Fi and actively listening for UDP packets on port `9001` (and `9002` in `FULL` mode).
- **Brief Flicker OFF:** Indicates Wi-Fi drop; auto-reconnection is triggered automatically.

### 4.4 Hardware Wiring & Pinout (ESP32)

| ESP32 Pin | Label on Board | Connects To | Purpose |
| :--- | :--- | :--- | :--- |
| **GPIO 4** | `D4` | **Strip 1 Data In (`DIN`)** | Primary LED Strip Data (Channel 1 — Port `9001`) |
| **GPIO 5** | `D5` | **Strip 2 Data In (`DIN`)** | Secondary LED Strip Data (Channel 2 — Port `9002`, `FULL` profile only) |
| **GND** | `GND` | **LED Strip `GND` / Power Supply `-V`** | **CRITICAL:** Common Ground Reference |
| **VIN / 5V** | `VIN` or `5V` | **5V Power Supply `+V`** *(Optional)* | Powers the ESP32 if not powered via USB |

> **Electrical Safeguards:**
> 1. **Common Ground (`GND`):** Always connect `GND` of the ESP32 to the negative (`GND` / `-V`) terminal of the 5V LED power supply. Without a common ground, the LEDs will glitch violently.
> 2. **Data Line Resistor:** Place a **$330\,\Omega$ to $470\,\Omega$ resistor** in series between `GPIO 4` / `GPIO 5` and the strip `DIN` pads to prevent voltage ringing.
> 3. **Power Filtering Capacitor:** Connect a **$1000\,\mu\text{F}$ electrolytic capacitor** ($\ge 6.3\text{V}$, ideally $16\text{V}$) across `+5V` and `GND` where power enters the strips.
> 4. **Never power LEDs through the ESP32:** Feed high-amperage 5V power directly from the external PSU to the strips (with power injection every ~150–250 LEDs).

### 4.5 Flashing the ESP32

1. Install **Arduino IDE 2.x**, add the Espressif ESP32 board manager URL (`https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`), and install the **esp32** board package and **FastLED** library.
2. Copy `hardware/esp32_firmware/secrets.h.example` to `hardware/esp32_firmware/secrets.h` (git-ignored) and set `WIFI_SSID` and `WIFI_PASSWORD`.
3. Open `esp32_udp_neopixel_full.ino` (or `esp32_udp_neopixel_small.ino`), select **ESP32 Dev Module** (`115200` baud), and click **Upload**.
4. Open the Serial Monitor (`115200` baud) to read the ESP32's assigned IP address and set `"esp32_ip"` in `config/app_config.json`.
