# Physical Matrix Coordinates

This document outlines the real physical coordinates of the LED segments based on the project's global spatial matrix (`Mode_Globaux/Matrix_data.py`).

## Overview
The LED matrix is defined on a theoretical grid of **432 columns (X)** by **246 rows (Y)**. 
- The origin `(0, 0)` is located at the top-left corner.
- `Horizontal` segments extend from left to right.
- `Vertical` segments extend from top to bottom.

## Segment Layout Table

| Strip | Segment Name | Orientation | Length (LEDs) | X Range (Columns) | Y Range (Rows) |
| :---: | :--- | :--- | :---: | :--- | :--- |
| **0** | `segment_v4` | Vertical | 173 | 431 | 32 to 204 |
| **0** | `segment_h32` | Horizontal | 48 | 383 to 430 | 85 |
| **0** | `segment_h31` | Horizontal | 48 | 383 to 430 | 171 |
| **0** | `segment_h30` | Horizontal | 47 | 383 to 429 | 1 |
| **0** | `segment_v3` | Vertical | 173 | 383 | 73 to 245 |
| **0** | `segment_h20` | Horizontal | 91 | 292 to 382 | 16 |
| **0** | `segment_h00` | Horizontal | 205 | 0 to 204 | 16 |
| **1** | `segment_v2` | Vertical | 173 | 292 | 73 to 245 |
| **1** | `segment_h11` | Horizontal | 87 | 205 to 291 | 73 |
| **1** | `segment_h10` | Horizontal | 86 | 205 to 290 | 189 |
| **1** | `segment_v1` | Vertical | 173 | 205 | 16 to 188 * |

> **\*Note on V1:** The global matrix data tracks logical structural `1`s from row 1 to 188, but the actual wired physical hardware segment consists of 173 LEDs effectively spanning row 16 to 188 (to align symmetrically with `segment_v2` and horizontal connections).

## Pygame Simulator Mapping
To render this layout accurately on a screen without overlap, the `hardware/Fake_leds.py` visualizer scales and shifts these coordinates using the following formula:
- **Scale factor**: `2` pixels per LED
- **Padding offset**: `100` pixels

**Formulas:**
- `Visualizer X = 100 + (Matrix Col * 2)`
- `Visualizer Y = 100 + (Matrix Row * 2)`
