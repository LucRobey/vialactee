# Vialactée ESP32 Firmware

This directory contains the ESP32 micro-controller firmware for streaming addressable WS2812B NeoPixel frames over high-speed Wi-Fi UDP.

The ESP32 acts as a pure, lightweight rasterizer. All complex spatial transitions, segment layouts, orientations, beat-tracking, and audio analysis are executed upstream on the Raspberry Pi / PC host (`Mode_master` and `Segment.py`) and sent as raw RGB UDP packets.

---

## 1. Profiles & Folder Structure

```
hardware/esp32_firmware/
├── ESP32_small/
│   ├── ESP32_small.ino        # Firmware for "hardware_profile": "small" (249 LEDs)
│   ├── secrets.h              # Wi-Fi credentials (not tracked in Git)
│   └── secrets.h.example      # Example credentials template
├── ESP32_full/
│   ├── ESP32_full.ino         # Firmware for "hardware_profile": "full" (1,304 LEDs)
│   ├── secrets.h              # Wi-Fi credentials (not tracked in Git)
│   └── secrets.h.example      # Example credentials template
└── README.md                  # This documentation
```

### Profile Comparison

| Setting | `ESP32_small` | `ESP32_full` |
|---|---|---|
| **Target Profile** | `hardware_profile == "small"` | `hardware_profile == "full"` |
| **Total LEDs** | **249** LEDs | **1,304** LEDs |
| **Channels / Strips** | **1 strip** (`PIN_STRIP_1 = GPIO 2`) | **2 strips** (`GPIO 2` and `GPIO 4`) |
| **Channel 1 LEDs** | 249 LEDs | 785 LEDs |
| **Channel 2 LEDs** | None (unused) | 519 LEDs |
| **UDP Listening Ports** | Port `9001` only | Ports `9001` (Strip 1) and `9002` (Strip 2) |
| **Segments Covered** | `s1` (49), `s2` (108), `s3` (92) | `v1`–`v4`, `h00`, `h10`, `h11`, `h20`, `h30`–`h32` |

---

## 2. Hardware Diagnostics & LED Status Colors

Both sketches include an immediate visual diagnostic indicator to identify system and network states at a glance:

| LED Color | State | Meaning |
|---|---|---|
| 🔴 **Solid RED** | `STATE_DISCONNECTED` | ESP32 is **not connected to Wi-Fi** (during initial boot or if Wi-Fi disconnected). Automatic background reconnection is active. |
| 🟢 **Solid GREEN** | `STATE_WAITING` | ESP32 is **connected to Wi-Fi** and ready, waiting for UDP packets from the Python host (or if the stream paused/stopped for > 1 second). |
| ⚡ **Live Animations** | `STATE_STREAMING` | Actively receiving UDP packets from Python and displaying live audio-reactive light frames. |

---

## 3. Wi-Fi Configuration (`secrets.h`)

Before flashing either firmware, ensure `secrets.h` contains your local Wi-Fi SSID and password:

```cpp
#pragma once

const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
```

A template is provided as `secrets.h.example`.

---

## 4. Hardware Wiring & Pinout

### Profile: `ESP32_small` (249 LEDs)
- **Data Pin**: Connect ESP32 **GPIO 2** to the Data IN of the LED strip (recommended: 330Ω–470Ω series resistor).
- **Ground**: Connect ESP32 **GND** to the 5V power supply **GND** and the LED strip **GND** (common ground is mandatory).
- **Power**: 5V external power supply (~3A minimum for 249 WS2812B LEDs). Do **not** power the strip directly from the ESP32 5V/VIN pin.

### Profile: `ESP32_full` (1,304 LEDs)
- **Channel 1 Data Pin**: Connect ESP32 **GPIO 2** to Strip 1 Data IN (785 LEDs).
- **Channel 2 Data Pin**: Connect ESP32 **GPIO 4** to Strip 2 Data IN (519 LEDs).
- **Power**: 5V external power supply (15A–20A recommended, with power injection every 250–300 LEDs).

---

## 5. How to Compile & Flash

### Option A: Arduino IDE
1. Install the **esp32** board package in Arduino IDE (`Boards Manager` -> search `esp32` by Espressif).
2. Install the required libraries via `Library Manager`:
   - `FastLED` (by Daniel Garcia)
   - `AsyncUDP` (included with the ESP32 core)
3. Open `hardware/esp32_firmware/ESP32_small/ESP32_small.ino` (or `ESP32_full/ESP32_full.ino`).
4. Select your board (e.g. **ESP32 Dev Module** or **DOIT ESP32 DEVKIT V1**).
5. Select the correct COM port and click **Upload**.
6. Open the **Serial Monitor** at **115200 baud** to see the assigned IP address upon Wi-Fi connection.
7. Enter this IP address in `config/app_config.json`:
   ```json
   {
       "hardware_profile": "small",
       "esp32_ip": "192.168.0.XX"
   }
   ```
