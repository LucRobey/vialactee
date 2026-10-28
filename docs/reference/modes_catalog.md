# Modes Visual Catalog (All 13 Active Modes)

> **Location:** `docs/reference/modes_catalog.md` (Tier 1 Canonical Specification)  
> **Registry:** [`config/modes.json`](../../config/modes.json) (13 mounted active modes)  
> **Source Directory:** [`modes/`](../../modes/)  
> **Sector Contract:** [`docs/contracts/mode_contract.md`](../contracts/mode_contract.md)

This catalog provides the canonical visual description, orientation support, lead/secondary choreographic drivers (Law 7), behavioral characteristics, and live-tunable parameter schemas for all 13 active mounted modes in Vialactée.

---

## 1. Active Mounted Modes Table

| # | Mode Name | Python Class | Orientation | Lead | Secondary | Visual Description & Dynamics |
|:---:|:---|:---|:---:|:---:|:---:|:---|
| 1 | **Rainbow** | [`Rainbow_mode`](../../modes/Rainbow_mode.py) | Omnidirectional | `spectrum` | `none` | Continuous smooth rainbow spectrum covering the strip. Brightness and saturation of frequency regions pulse dynamically with respective FFT bands. |
| 2 | **Bary Rainbow** | [`Bary_rainbow_mode`](../../modes/Bary_rainbow_mode.py) | Both / Horizontal | `spectrum` | `beat` | Symmetrical rainbow gradient mirrored outward from the segment center. Center hue is driven by `ctx.vertical_center` and gentle continuous drift (`mood_pace`), while brightness and saturation pulse with `ctx.energy` and `self.beat_pulse()`. |
| 3 | **Middle Bar** | [`Middle_bar_mode`](../../modes/Middle_bar_mode.py) | Horizontal | `beat` | `spectrum` | Solid colored bar growing symmetrically outward from the exact center. Width expands/contracts in proportion to beat envelope and bass FFT band energy. |
| 4 | **Shining Stars** | [`Shining_stars_mode`](../../modes/Shining_stars_mode.py) | Omnidirectional | `transient` | `spectrum` | Ambient dark canvas where individual LEDs twinkle and flash into existence at random positions when frequency bands peak, matching their color to the triggering band. |
| 5 | **Proportion Rainbow** | [`Proportion_rainbow_mode`](../../modes/Proportion_rainbow_mode.py) | Omnidirectional | `spectrum` | `none` | Full rainbow gradient spanning the strip where the width of each color slice expands or contracts based on proportional FFT band energy distribution. |
| 6 | **Opposite Sides** | [`Opposite_sides_mode`](../../modes/Opposite_sides_mode.py) | Horizontal | `spectrum` | `transient` | Dual complementary mood-colored bars advancing toward a central equilibrium gradient zone. Balance center shifts with `ctx.spectral_tilt` (plus gentle sway when rhythm lock is low), and bar depths scale with `ctx.energy` and `self.beat_pulse()`. |
| 7 | **Hyper Strobe** | [`Hyper_strobe_mode`](../../modes/Hyper_strobe_mode.py) | Omnidirectional | `transient` | `none` | Kinetic strobe and pulse gated on verified acoustic beats (`ctx.is_real_beat` with `beat_trust > 0.4`), `self.drop_hit`, or spectral flux peaks (`band_flux`), flashing `highlight_color` blended with `mood_colors[2]`. Smoothly crossfades to an acoustic breathing glow when `rhythm_lock` is low. |
| 8 | **Chromatic Chaser** | [`Chromatic_chaser_mode`](../../modes/Chromatic_chaser_mode.py) | Horizontal / Both | `beat` | `level` | Concentrated laser head sweeping across the strip (with optional edge bounce) leaving an exponential decay trail (`mood_trail`). Speed synchronizes to `listener.bpm` (gated by `rhythm_lock`), `ctx.tension`, and `mood_pace`; head color blends `mood_colors` by `ctx.vertical_center` and `mood_accent`. |
| 9 | **Metronome** | [`Metronome_mode`](../../modes/Metronome_mode.py) | Omnidirectional | `beat` | `none` | Pulses rhythmically with the Anticipation Flywheel (`beat_phase`, `beat_count`) when confident (`rhythm_lock`), alternating between `highlight_color` on downbeats and `mood_colors[2]` / configurable accent color on sub-beats, and smoothly crossfading into acoustic breathing when beat tracking is lost. |
| 10 | **Coloured Middle Wave** | [`Coloured_middle_wave_mode`](../../modes/Coloured_middle_wave_mode.py) | Horizontal | `spectrum` | `beat` | Strip divided symmetrically into frequency bands. Center represents bass (red/orange), edges treble (blue/purple). Sections pulse outward with band volumes. |
| 11 | **Impact Shockwave** | [`Impact_shockwave_mode`](../../modes/Impact_shockwave_mode.py) | Horizontal / Both | `transient` | `level` | Center-outward expanding ripple waves whose speed scales to BPM. Spawns kinetic shockwaves on verified acoustic hits (`is_real_beat`); suppresses flashes on ghost beats. |
| 12 | **Power Bar** | [`Power_bar_mode`](../../modes/Power_bar_mode.py) | Vertical | `level` | `beat` | Classic audio VU peak meter. Solid colored column rises vertically with instantaneous power. Persistent peak-hold white dot floats at maximum crest and descends under gravity. |
| 13 | **Extending Waves** | [`Extending_waves_mode`](../../modes/Extending_waves_mode.py) | Horizontal | `level` | `beat` | On each detected beat, a new colored wavefront injects at strip center and travels outward towards both edges like ripples in water. Wave speed and luminosity scale with audio power. |

---

## 2. Live Web UI Configurable Settings (`get_settings_schema()`)

Six modes override `Mode.get_settings_schema()` to expose live-tunable parameters to the Web UI (`ModeSettings.tsx`) and `tools/mode_studio.py` (persisted under `mode_settings` in `config/app_config.json`):

| Mode | Schema Key (`key`) | Attribute (`attr`) | `infos` Startup Key | Label | Control | Default | Range / Options |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Rainbow** ([`Rainbow_mode`](../../modes/Rainbow_mode.py)) | `smoothRatio` | `smooth_ratio` | `rainbow_smooth_ratio` | Smoothing | `slider` | `0.5` | `0.0 .. 1.0` (step `0.05`) |
| | `intensityBase` | `intensity_base` | `rainbow_intensity_base` | Base Intensity | `slider` | `0.1` | `0.0 .. 1.0` (step `0.05`) |
| | `intensityMultiplier` | `intensity_mult` | `rainbow_intensity_mult` | Intensity Boost | `slider` | `0.9` | `0.0 .. 2.0` (step `0.05`) |
| **Shining Stars** ([`Shining_stars_mode`](../../modes/Shining_stars_mode.py)) | `threshold` | `threshold` | `stars_threshold` | Activation Threshold | `slider` | `10.0` | `1.0 .. 100.0` (step `1.0`) |
| | `fade_ratio` | `fade_ratio` | `stars_fade_ratio` | Star Fade Speed | `slider` | `0.1` | `0.02 .. 0.5` (step `0.02`) |
| | `sub_segment_size` | `sub_segment_size` | `stars_sub_segment_size` | Constellation Spacing | `slider` | `40` | `5 .. 100` (step `5`, integer) |
| **Hyper Strobe** ([`Hyper_strobe_mode`](../../modes/Hyper_strobe_mode.py)) | `fluxThreshold` | `flux_threshold` | `strobe_flux_threshold` | Trigger Threshold | `slider` | `0.7` | `0.0 .. 1.0` (step `0.05`) |
| | `decayRatio` | `decay_ratio` | `strobe_decay_ratio` | Decay | `slider` | `0.3` | `0.01 .. 1.0` (step `0.05`) |
| | `listenBand` | `listen_band` | `strobe_listen_band` | Trigger Band | `list` | `1` | `0 .. 7` (`Band 1`..`Band 8`) |
| **Chromatic Chaser** ([`Chromatic_chaser_mode`](../../modes/Chromatic_chaser_mode.py)) | `speed` | `speed` | `chaser_speed` | Travel Speed | `slider` | `2.0` | `0.2 .. 8.0` (step `0.2`) |
| | `fadeRatio` | `fade_ratio` | `chaser_fade_ratio` | Trail Fade | `slider` | `0.05` | `0.01 .. 0.5` (step `0.01`) |
| | `bounceEnabled` | `bounce_enabled` | `chaser_bounce_enabled` | Bounce At Edges | `switch` | `True` | `True`, `False` |
| **Metronome** ([`Metronome_mode`](../../modes/Metronome_mode.py)) | `brightnessMultiplier` | `brightness_multiplier` | `metronome_brightness` | Brightness | `slider` | `1.0` | `0.2 .. 2.0` (step `0.1`) |
| | `alternateSubBeats` | `alternate_sub_beats` | `metronome_alternate_sub_beats` | Alternate Sub-Beats | `switch` | `True` | `True`, `False` |
| | `accentColor` | `accent_color` | `metronome_accent_color` | Accent Color | `list` | `"blue"` | `"blue"`, `"purple"`, `"red"`, `"green"` |
| **Impact Shockwave** ([`Impact_shockwave_mode`](../../modes/Impact_shockwave_mode.py)) | `color_mode` | `color_mode` | `shockwave_color_mode` | Color Mode | `list` | `"vibrant_cycle"` | `"vibrant_cycle"`, `"neon_palette"`, `"single_hue"` |
| | `color_saturation` | `color_saturation` | `shockwave_saturation` | Color Saturation | `slider` | `1.0` | `0.5 .. 1.0` (step `0.05`) |
| | `base_hue` | `base_hue` | `shockwave_base_hue` | Base Hue | `slider` | `0.55` | `0.0 .. 1.0` (step `0.05`) |
| | `wave_width` | `wave_width` | `shockwave_width` | Wavefront Width | `slider` | `2.2` | `0.5 .. 4.0` (step `0.2`) |
| | `enable_ghost_ripples` | `enable_ghost_ripples` | `shockwave_ghost_ripples` | Ghost Ripples in Breakdowns | `switch` | `True` | `True`, `False` |
| | `damping` | `damping` | `shockwave_damping` | Wave Damping | `slider` | `0.02` | `0.005 .. 0.15` (step `0.005`) |

---

## 3. Mood-Modulated Autonomous Modes (`modes/*_mode.py`)

All remaining modes (`Bary_rainbow_mode`, `Middle_bar_mode`, `Proportion_rainbow_mode`, `Opposite_sides_mode`, `Coloured_middle_wave_mode`, `Power_bar_mode`, `Extending_waves_mode`) self-tune their internal physics, speeds, and trails via the continuous `Mode` scene modifiers (`self.mood_pace`, `self.mood_sharpness`, `self.mood_trail`, `self.mood_accent`) and mood palette (`self.mood_colors`, `self.palette_lut`, `self.highlight_color`).
