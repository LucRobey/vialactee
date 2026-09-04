# Hardware Mapping & Coordinate Reference

Vialactée supports two hardware profiles configured via `"hardware_profile"` in `config/app_config.json`:
- **`full` (Default)**: 1,304 addressable WS2812B LEDs mapped across 11 logical structural segments over 2 hardware channels.
- **`small`**: 249 addressable WS2812B LEDs mapped across 3 structural segments over 1 hardware channel.

Segment definitions are unified in `config/segments_full.json` and `config/segments_small.json`, containing both physical 2D matrix coordinates (`start`, `step`, `size`, `order`, `orientation`) and Web App UI layout parameters (`id`, `ui`: `col`, `row`, `w`, `h`, `color`), along with top-level `cables` Bezier splines.

---

## 1. Physical Segment Tables

### Profile: `full` (`config/segments_full.json`)

#### Channel 1 (`segs_1` · 785 LEDs · Port 9001 · Pin D21)

| Segment Name | ID | Size (LEDs) | Orientation | Wiring Direction | UI Placement (Col, Row, W, H) | Color |
|---|---|---|---|---|---|---|
| `Segment v4` | `v4` | 173 | `"vertical"` | **Bottom-to-Top** (`step.y: -1`) | `col: 43, row: 1, w: 2, h: 18` | `#3264ff` |
| `Segment h32`| `h32` | 48 | `"horizontal"` | Left-to-Right (`step.x: 1`) | `col: 38, row: -3, w: 6, h: 2` | `#ff3232` |
| `Segment h31`| `h31` | 48 | `"horizontal"` | Left-to-Right (`step.x: 1`) | `col: 38, row: 7, w: 6, h: 2` | `#ff00ff` |
| `Segment h30`| `h30` | 47 | `"horizontal"` | Left-to-Right (`step.x: 1`) | `col: 38, row: 16, w: 6, h: 2` | `#969696` |
| `Segment v3` | `v3` | 173 | `"vertical"` | **Bottom-to-Top** (`step.y: -1`) | `col: 38, row: -1, w: 2, h: 18` | `#00ffff` |
| `Segment h20`| `h20` | 91 | `"horizontal"` | Left-to-Right (`step.x: 1`) | `col: 29, row: 4, w: 10, h: 2` | `#96ff96` |
| `Segment h00`| `h00` | 205 | `"horizontal"` | Left-to-Right (`step.x: 1`) | `col: 0, row: -1, w: 22, h: 2` | `#0000ff` |

#### Channel 2 (`segs_2` · 519 LEDs · Port 9002 · Pin D18)

| Segment Name | ID | Size (LEDs) | Orientation | Wiring Direction | UI Placement (Col, Row, W, H) | Color |
|---|---|---|---|---|---|---|
| `Segment v2` | `v2` | 173 | `"vertical"` | **Bottom-to-Top** (`step.y: -1`) | `col: 29, row: 4, w: 2, h: 18` | `#00ff00` |
| `Segment h11`| `h11` | 87 | `"horizontal"` | Left-to-Right (`step.x: 1`) | `col: 21, row: 2, w: 9, h: 2` | `#ff9664` |
| `Segment h10`| `h10` | 86 | `"horizontal"` | Left-to-Right (`step.x: 1`) | `col: 21, row: 16, w: 9, h: 2` | `#9632c8` |
| `Segment v1` | `v1` | 173 | `"vertical"` | **Bottom-to-Top** (`step.y: -1`) | `col: 21, row: -1, w: 2, h: 18` | `#ffff00` |

**Full Profile Total:** **1,304 LEDs** across 11 segments.

---

### Profile: `small` (`config/segments_small.json`)

#### Channel 1 (`segs_1` · 249 LEDs · Port 9001 · Pin D21)

| Segment Name | ID | Size (LEDs) | Order | Orientation | Wiring Direction | UI Placement (Col, Row, W, H) | Color |
|---|---|---|---|---|---|---|---|
| `Segment s2` | `s2` | 108 | 0 | `"vertical"` | Center | `col: 23, row: 1, w: 2, h: 18` | `#ff3232` |
| `Segment s1` | `s1` | 49 | 1 | `"vertical"` | Left | `col: 11, row: 5, w: 2, h: 10` | `#3264ff` |
| `Segment s3` | `s3` | 92 | 2 | `"vertical"` | Right | `col: 35, row: 2, w: 2, h: 16` | `#00ff00` |

**Small Profile Total:** **249 LEDs** across 3 segments.

---

## 2. Inverted Vertical Orientation Rule

> [!IMPORTANT]
> All physical vertical LED strips (`v1`–`v4`, `s1`, `s3`) are physically wired from **bottom to top**.
> - In `hardware/Fake_leds.py`, vertical segment drawing loops must use `"vertical_up"`.
> - Their `start_y` corresponds geometrically to their **bottom-most physical coordinate**.
> - The upward step is negative: `y -= 2`.

---

## 3. Hardware Abstraction Drivers

* **`hardware/HardwareFactory.py`**: Reads active segment JSON via `_get_channel_specs(infos)` to dynamically determine channel count and strip sizes, returning a tuple of hardware instances.
* **`hardware/Fake_leds.py`**: PyGame physical simulation for Windows / macOS local testing. Dynamically configures layout via `_load_visualizer_segments_def()` based on active profile. Runs strictly in the main thread.
* **`hardware/Fake_ESP32.py`**: Standalone background script that binds UDP sockets dynamically to all active channel ports (9001, 9002) and metadata port (9003).
* **`hardware/Udp_Sender.py`**: Wi-Fi UDP streaming packetizer for real ESP32 or simulation `Fake_ESP32`.
* **`hardware/Rpi_NeoPixels.py`**: Direct GPIO DMA driver on Raspberry Pi (via `rpi_ws281x`), instantiated per active channel.

