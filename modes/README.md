# Visual Modes (`/modes/`)

The `modes` directory contains the creative visual algorithms for the chandelier. Each file is an animation subclass.

## Key Components:

- **`Mode.py`**: The base class for all visual effects. It provides shared utility functions, vectorized numpy matrix operations (`self.rgb_list`), decay smoothing (`self.smooth_segment_vectorized`), and enforces the execution contract with `Mode_master`.
- **Active Modes**: Registered in [`config/modes.json`](file:///c:/Users/Users/Desktop/vialact%C3%A9e/vialactee/config/modes.json) (15 modes mounted at runtime and switchable from the web interface).
- **Dormant / Experimental Modes**: Implemented modes in `modes/` that are unmounted from `config/modes.json` (e.g., `Extending_waves_mode.py`, `Magnetic_ball_mode.py`, `Power_bar_mode.py`, `Static_wave_mode.py`, `Alcool_randomer.py`).

---

## The Architecture Contract

### 1. `run()` vs `update()`
All mode subclasses must override `run()`, **not** `update()`.
*   `Mode.update()` is a final method on the base class that automatically handles performance profiling, listener synchronization, and boilerplate updates. It internally calls `self.run()`.
*   Overriding `update()` inside a mode subclass breaks the performance profiling pipeline.

### 2. The `rgb_list` Array
The visual canvas for a segment is managed natively as a 2D numpy matrix: `self.rgb_list` (shape: `[number_of_leds, 3]`). 
Modes operate by slicing and mutating this matrix directly, taking advantage of C-level vectorization to compute thousands of LEDs without Python loops.

### 3. The `infos` Payload & Mode Settings Schema
Variables controlling visual behavior (speeds, color palettes, thresholds, physical constraints) are passed through `self.infos` rather than hardcoded. `self.infos` is populated by merging `app_config.json` with dynamic `modeSettings` injected from active segment configurations.

Modes can declare interactive controls for the Web UI by implementing `get_settings_schema() -> List[Dict[str, Any]]`:

```python
def get_settings_schema(self):
    return [
        {
            "id": "chaser_speed",
            "label": "Chaser Speed",
            "type": "slider",
            "min": 0.5,
            "max": 10.0,
            "step": 0.1,
            "default": 2.0
        }
    ]
```

### 4. Mode Parameters Reference Table

| Mode File | Key in `infos` | Type | Default | Description |
|---|---|---|---|---|
| `Chromatic_chaser_mode.py` | `chaser_speed` | float | `2.0` | Movement speed of the chaser head |
| | `chaser_fade_ratio` | float | `0.05` | Exponential decay rate of the laser trail |
| | `chaser_bounce_enabled` | bool | `True` | Rebound off segment boundaries |
| `Hyper_strobe_mode.py` | `strobe_flux_threshold` | float | `0.7` | Spectral flux required to fire strobe |
| | `strobe_decay_ratio` | float | `0.3` | Speed of fade to black after flash |
| | `strobe_listen_band` | int | `1` | FFT band monitored for kick transients |
| `Metronome_mode.py` | `metronome_brightness` | float | `1.0` | Master brightness multiplier |
| | `metronome_alternate_sub_beats` | bool | `True` | Alternate white (downbeat) and blue (sub-beat) |
| | `metronome_accent_color` | str | `"blue"` | Sub-beat accent color |
| `Matrix_rain_mode.py` | `rain_flux_threshold` | float | `0.5` | Threshold to spawn new raindrops |
| | `rain_fade_ratio` | float | `0.15` | Drop trail persistence |
| | `rain_listen_band` | int | `-1` | Frequency band triggering drops (-1 = treble) |
| `Plasma_fire_mode.py` | `fire_fade_ratio` | float | `0.3` | Flame decay rate |
| | `fire_height_multiplier` | float | `1.2` | Power-to-height scaling ratio |
| `Rainbow_mode.py` | `rainbow_smooth_ratio` | float | `0.5` | Smoothing ratio for band brightness |
| | `rainbow_intensity_base` | float | `0.1` | Baseline ambient brightness |
| | `rainbow_intensity_mult` | float | `0.9` | Dynamic audio reactive brightness scale |
| `Shining_stars_mode.py` | `stars_sub_segment_size`| int | `15` | Spatial bin size for star spawning |
| | `stars_iteration_wait` | int | `30` | Cool-down frames between star spawns |
| `Synesthesia_mode.py` | `synesthesia_fade_ratio`| float | `0.2` | Color transition smoothing |
| | `synesthesia_brightness`| float | `1.0` | Output brightness multiplier |
| `Alcool_randomer.py` *(dormant)* | `shot_base_speed` | float | `nb_leds / 40` | Initial launch speed |
| | `shot_max_speed` | float | `4 * base` | Terminal cruising velocity |
| | `shot_fade_ratio` | float | `0.4` | Trail decay rate |

---

## Mode Registration Workflow

To add a new mode to the live system:
1. Create `modes/Your_new_mode.py` inheriting from `modes.Mode.Mode`.
2. Implement `__init__(...)`, `run()`, and optionally `get_settings_schema()`.
3. Register the mode in [`config/modes.json`](file:///c:/Users/Users/Desktop/vialact%C3%A9e/vialactee/config/modes.json):
   ```json
   {
     "name": "Your Mode Name",
     "module": "Your_new_mode",
     "class": "Your_new_mode"
   }
   ```
4. `Mode_master` automatically discovers, dynamically imports, and instantiates registered modes across segments.
