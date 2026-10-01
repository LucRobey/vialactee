# Physical Matrix Coordinates & Channel Mapping

> **Location:** `docs/reference/coordinates_matrix.md` (Tier 1 Canonical Specification)  
> **Enforcing Axioms:** [AXIOM-03: Physical Chandelier Geometry & Vertical Invariant](../axioms/AXIOM-03_HARDWARE_GEOMETRY.md)

This document specifies the exact physical coordinates, 2D matrix projections, and hardware channel assignments for all LED segments on the Vialactée chandelier.

---

## 1. Physical Grid Overview

The global chandelier layout is mapped onto a 2D coordinate space spanning **432 columns (X)** by **246 rows (Y)**:
- **Origin `(0, 0)`:** Top-left corner of the spatial bounding box.
- **Horizontal Segments:** Step horizontally from left to right (`step.x = 1, step.y = 0`).
- **Vertical Segments:** Strictly adhere to the **Vertical Invariant (AXIOM-03)**: physically wired from **bottom to top** (`"vertical_up"`, `step.x = 0, step.y = -1`).

---

## 2. Full Profile (`config/segments_full.json`) — 1,304 LEDs

Total Physical LEDs: **1,304 WS2812B LEDs** across 11 segments and 2 hardware channels.

| Channel Key | Port | Pin | Segment Name | Orientation | Length (LEDs) | X Range (Columns) | Y Range (Rows) |
|:---:|:---:|:---:|:---|:---|:---:|:---|:---|
| `segs_1` | 9001 | GPIO 21 | `segment_v4` | Vertical (`vertical_up`) | 173 | 431 | 32 to 204 |
| `segs_1` | 9001 | GPIO 21 | `segment_h32` | Horizontal | 48 | 383 to 430 | 85 |
| `segs_1` | 9001 | GPIO 21 | `segment_h31` | Horizontal | 48 | 383 to 430 | 171 |
| `segs_1` | 9001 | GPIO 21 | `segment_h30` | Horizontal | 47 | 383 to 429 | 1 |
| `segs_1` | 9001 | GPIO 21 | `segment_v3` | Vertical (`vertical_up`) | 173 | 383 | 73 to 245 |
| `segs_1` | 9001 | GPIO 21 | `segment_h20` | Horizontal | 91 | 292 to 382 | 16 |
| `segs_1` | 9001 | GPIO 21 | `segment_h00` | Horizontal | 205 | 0 to 204 | 16 |
| **Total Channel 1** | | | | | **785** | | |
| `segs_2` | 9002 | GPIO 18 | `segment_v2` | Vertical (`vertical_up`) | 173 | 292 | 73 to 245 |
| `segs_2` | 9002 | GPIO 18 | `segment_h11` | Horizontal | 87 | 205 to 291 | 73 |
| `segs_2` | 9002 | GPIO 18 | `segment_h10` | Horizontal | 86 | 205 to 290 | 189 |
| `segs_2` | 9002 | GPIO 18 | `segment_v1` | Vertical (`vertical_up`) | 173 | 205 | 16 to 188 |
| **Total Channel 2** | | | | | **519** | | |
| **Total Chandelier** | | | | | **1,304** | | |

---

## 3. Small Profile (`config/segments_small.json`) — 249 LEDs

Total Physical LEDs: **249 WS2812B LEDs** across 3 segments and 1 hardware channel.

| Channel Key | Port | Pin | Segment Name | Orientation | Length (LEDs) |
|:---:|:---:|:---:|:---|:---|:---:|
| `segs_1` | 9001 | GPIO 21 | `s1` | Vertical (`vertical_up`) | 49 |
| `segs_1` | 9001 | GPIO 21 | `s2` | Vertical (`vertical_up`) | 108 |
| `segs_1` | 9001 | GPIO 21 | `s3` | Vertical (`vertical_up`) | 92 |
| **Total Chandelier** | | | | | **249** |

---

## 4. Pygame Visualizer Geometry Calculation

The graphical simulator (`hardware/Fake_leds.py`) reconstructs segment positions dynamically from the active segment JSON:
- **Scale Factor:** 2 pixels per physical LED.
- **Canvas Offset:** 100 pixels padding.

### Formulae:
- **Horizontal Strips:**
  $$\text{Pixel}_X = 100 + 2 \times X_{\text{col}} + 2 \times i, \quad \text{Pixel}_Y = 100 + 2 \times Y_{\text{row}}$$
- **Vertical Strips (`vertical_up`):**
  $$\text{Pixel}_X = 100 + 2 \times X_{\text{col}}, \quad \text{Pixel}_Y = 100 + 2 \times Y_{\text{start}} - 2 \times i$$
  (Where $i \in [0, \text{length}-1]$, guaranteeing that index 0 is at the bottom and index increases upwards).
