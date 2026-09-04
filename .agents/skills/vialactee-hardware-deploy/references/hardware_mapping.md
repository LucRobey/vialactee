# Hardware Mapping & Coordinate Reference

The Vialactée chandelier consists of **1,304 addressable WS2812B LEDs** mapped across 11 logical structural segments.

---

## 1. Physical Segment Table

| Segment Name | Type | LED Count | Wiring Orientation | Simulator Behavior |
|---|---|---|---|---|
| `Segment v4` | Vertical Strip | 173 | **Bottom-to-Top** | `"vertical_up"`: `y -= 2` (start_y is bottom-most) |
| `Segment h32`| Horizontal Ring | 48 | Left-to-Right | `"horizontal"`: `x += 2` |
| `Segment h31`| Horizontal Ring | 48 | Left-to-Right | `"horizontal"`: `x += 2` |
| `Segment h30`| Horizontal Ring | 47 | Left-to-Right | `"horizontal"`: `x += 2` |
| `Segment v3` | Vertical Strip | 173 | **Bottom-to-Top** | `"vertical_up"`: `y -= 2` |
| `Segment h21`| Horizontal Ring | 48 | Left-to-Right | `"horizontal"`: `x += 2` |
| `Segment h20`| Horizontal Ring | 48 | Left-to-Right | `"horizontal"`: `x += 2` |
| `Segment v2` | Vertical Strip | 173 | **Bottom-to-Top** | `"vertical_up"`: `y -= 2` |
| `Segment h10`| Horizontal Ring | 48 | Left-to-Right | `"horizontal"`: `x += 2` |
| `Segment v1` | Vertical Strip | 173 | **Bottom-to-Top** | `"vertical_up"`: `y -= 2` |
| `Segment c`  | Center Ring | 325 | Circular | Custom ring coordinates |
| **Total** | | **1,304** | | |

---

## 2. Inverted Vertical Orientation Rule

> [!IMPORTANT]
> All physical vertical LED strips (`v1`, `v2`, `v3`, `v4`) are physically wired from **bottom to top**.
> - In `hardware/Fake_leds.py`, vertical segment drawing loops must use `"vertical_up"`.
> - Their `start_y` corresponds geometrically to their **bottom-most physical coordinate**.
> - The upward step is negative: `y -= 2`.

---

## 3. Hardware Abstraction Drivers

* **`hardware/Fake_leds.py`**: PyGame 1300x1000 physical simulation for Windows / macOS local testing. Runs strictly in the main thread.
* **`hardware/Rpi_NeoPixels.py`**: Direct GPIO DMA driver on Raspberry Pi (via `rpi_ws281x`).
* **`hardware/Udp_Sender.py`**: Wi-Fi UDP streaming packetizer for ESP32 receiver modules.
* **`hardware/HardwareFactory.py`**: Factory that selects the appropriate driver based on `infos["onRaspberry"]` and config flags.
