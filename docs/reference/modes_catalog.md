# Modes Visual Catalog (All 21 Active Modes)

> **Location:** `docs/reference/modes_catalog.md` (Tier 1 Canonical Specification)  
> **Registry:** [`config/modes.json`](../../config/modes.json) (21 mounted active modes)  
> **Source Directory:** [`modes/`](../../modes/)  
> **Sector Contract:** [`docs/contracts/mode_contract.md`](../contracts/mode_contract.md)

This catalog provides the canonical visual description, orientation support, behavioral characteristics, and live-tunable parameter schemas for all 21 active mounted modes in Vialactée.

---

## 1. Active Mounted Modes Table

| # | Mode Name | Python Class | Orientation | Visual Description & Dynamics |
|:---:|:---|:---|:---:|:---|
| 1 | **Rainbow** | [`Rainbow_mode`](../../modes/Rainbow_mode.py) | Omnidirectional | Continuous smooth rainbow spectrum covering the strip. Brightness and saturation of frequency regions pulse dynamically with respective FFT bands. |
| 2 | **Bary Rainbow** | [`Bary_rainbow_mode`](../../modes/Bary_rainbow_mode.py) | Both / Horizontal | Symmetrical rainbow gradient mirrored outward from the segment center. Center hue is driven by `ctx.vertical_center` and gentle continuous drift (`mood_pace`), while brightness and saturation pulse with `ctx.energy` and `self.beat_pulse()`. |
| 3 | **Middle Bar** | [`Middle_bar_mode`](../../modes/Middle_bar_mode.py) | Horizontal | Solid colored bar growing symmetrically outward from the exact center. Width expands/contracts in proportion to auto-selected FFT band energy. |
| 4 | **Shining Stars** | [`Shining_stars_mode`](../../modes/Shining_stars_mode.py) | Omnidirectional | Ambient dark canvas where individual LEDs twinkle and flash into existence at random positions when frequency bands peak, matching their color to the triggering band. |
| 5 | **Proportion Rainbow** | [`Proportion_rainbow_mode`](../../modes/Proportion_rainbow_mode.py) | Omnidirectional | Full rainbow gradient spanning the strip where the width of each color slice expands or contracts based on proportional FFT band energy distribution. |
| 6 | **PSG** | [`PSG_mode`](../../modes/PSG_mode.py) | Horizontal | Opposing left/right mood-colored bars (`mood_colors[0]` and `mood_colors[1]`, warmed by `mood_accent`) whose heights scale with `ctx.energy`, `self.beat_pulse()`, and `ctx.spectral_tilt`, with a `highlight_color` balance dot driven by `spectral_tilt` and gentle sway. |
| 7 | **Opposite Sides** | [`Opposite_sides_mode`](../../modes/Opposite_sides_mode.py) | Horizontal | Dual complementary mood-colored bars advancing toward a central equilibrium gradient zone. Balance center shifts with `ctx.spectral_tilt` (plus gentle sway when rhythm lock is low), and bar depths scale with `ctx.energy` and `self.beat_pulse()`. |
| 8 | **Plasma Fire** | [`Plasma_fire_mode`](../../modes/Plasma_fire_mode.py) | Vertical | Simulates a fiery plasma column rising from strip base. Flame height modulates dynamically with total volume power. Color gradients from deep crimson to yellow/white tips. |
| 9 | **Hyper Strobe** | [`Hyper_strobe_mode`](../../modes/Hyper_strobe_mode.py) | Omnidirectional | Kinetic strobe and pulse gated on verified acoustic beats (`ctx.is_real_beat` with `beat_trust > 0.4`), `self.drop_hit`, or spectral flux peaks (`band_flux`), flashing `highlight_color` blended with `mood_colors[2]`. Smoothly crossfades to an acoustic breathing glow when `rhythm_lock` is low. |
| 10 | **Chromatic Chaser** | [`Chromatic_chaser_mode`](../../modes/Chromatic_chaser_mode.py) | Horizontal / Both | Concentrated laser head sweeping across the strip (with optional edge bounce) leaving an exponential decay trail (`mood_trail`). Speed synchronizes to `listener.bpm` (gated by `rhythm_lock`), `ctx.tension`, and `mood_pace`; head color blends `mood_colors` by `ctx.vertical_center` and `mood_accent`. |
| 11 | **Synesthesia** | [`Synesthesia_mode`](../../modes/Synesthesia_mode.py) | Omnidirectional | Maps 12-note chromagram pitch analysis (`smoothed_chroma_values`) onto a circular color wheel, blended with `mood_colors[0]` and `mood_accent`, modulated by `ctx.energy`, `self.beat_pulse()`, and a traveling spatial sine wave so the strip shimmers continuously. |
| 12 | **Metronome** | [`Metronome_mode`](../../modes/Metronome_mode.py) | Omnidirectional | Pulses rhythmically with the Anticipation Flywheel (`beat_phase`, `beat_count`) when confident (`rhythm_lock`), alternating between `highlight_color` on downbeats and `mood_colors[2]` / configurable accent color on sub-beats, and smoothly crossfading into acoustic breathing when beat tracking is lost. |
| 13 | **Flying Ball** | [`Flying_ball_mode`](../../modes/Flying_ball_mode.py) | Horizontal | Luminous cluster (~7 LEDs wide) darting left/right leaving an exponential fade trail. Position correlates to spectral balance (bass left, treble right). |
| 14 | **Coloured Middle Wave** | [`Coloured_middle_wave_mode`](../../modes/Coloured_middle_wave_mode.py) | Horizontal | Strip divided symmetrically into frequency bands. Center represents bass (red/orange), edges treble (blue/purple). Sections pulse outward with band volumes. |
| 15 | **Rhythm Breather** | [`Rhythm_breather_mode`](../../modes/Rhythm_breather_mode.py) | Omnidirectional | Continuous phase-locked breathing visual. Pumps with tight percussive envelope on locked rhythm; decays gracefully into gentle volume glow on low confidence. |
| 16 | **Beat Runner** | [`Beat_runner_mode`](../../modes/Beat_runner_mode.py) | Horizontal / Both | Dynamic BPM-scaled kinematic laser bead sweeping across strip and striking boundaries precisely on beat ticks ($T_{\text{speaker}}$). Diffuses to volume cloud on uncertainty. |
| 17 | **Impact Shockwave** | [`Impact_shockwave_mode`](../../modes/Impact_shockwave_mode.py) | Horizontal / Both | Center-outward expanding ripple waves whose speed scales to BPM. Spawns kinetic shockwaves on verified acoustic hits (`is_real_beat`); suppresses flashes on ghost beats. |
| 18 | **Static Wave** | [`Static_wave_mode`](../../modes/Static_wave_mode.py) | Horizontal | Symmetrical central pulse band whose thickness breathes in and out strictly to bass transients, framed by bright white outer caps with color modulated by total audio power. |
| 19 | **Power Bar** | [`Power_bar_mode`](../../modes/Power_bar_mode.py) | Vertical | Classic audio VU peak meter. Solid colored column rises vertically with instantaneous power. Persistent peak-hold white dot floats at maximum crest and descends under gravity. |
| 20 | **Extending Waves** | [`Extending_waves_mode`](../../modes/Extending_waves_mode.py) | Horizontal | On each detected beat, a new colored wavefront injects at strip center and travels outward towards both edges like ripples in water. Wave speed and luminosity scale with audio power. |
| 21 | **Magnetic Ball** | [`Magnetic_ball_mode`](../../modes/Magnetic_ball_mode.py) | Horizontal | Physics-simulated ball with mass, spring tension toward center, and friction. Audio transients deliver kinetic impulses that kick ball toward boundaries where it bounces elastically. |

---

## 2. Live Web UI Configurable Settings (`get_settings_schema()`)

Eight modes override `Mode.get_settings_schema()` to expose live-tunable parameters to the Web UI (`ModeSettings.tsx`) and `tools/mode_studio.py` (persisted under `mode_settings` in `config/app_config.json`):

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
| **Rhythm Breather** ([`Rhythm_breather_mode`](../../modes/Rhythm_breather_mode.py)) | `base_hue` | `base_hue` | `rhythm_breather_base_hue` | Base Hue | `slider` | `0.6` | `0.0 .. 1.0` (step `0.05`) |
| | `pulse_sharpness` | `pulse_sharpness` | `rhythm_breather_sharpness` | Beat Sharpness | `slider` | `2.2` | `1.0 .. 4.0` (step `0.2`) |
| | `ambient_floor` | `ambient_floor` | `rhythm_breather_ambient_floor` | Ambient Floor | `slider` | `0.08` | `0.0 .. 0.3` (step `0.02`) |
| | `drift_speed` | `drift_speed` | `rhythm_breather_drift_speed` | Hue Drift Speed | `slider` | `0.01` | `0.0 .. 0.05` (step `0.005`) |
| **Beat Runner** ([`Beat_runner_mode`](../../modes/Beat_runner_mode.py)) | `motion_style` | `motion_style` | `beat_runner_motion_style` | Motion Style | `list` | `"pendulum"` | `"pendulum"`, `"sweep"` |
| | `base_hue` | `base_hue` | `beat_runner_base_hue` | Laser Hue | `slider` | `0.08` | `0.0 .. 1.0` (step `0.05`) |
| | `head_width` | `head_width` | `beat_runner_head_width` | Laser Width | `slider` | `1.5` | `0.8 .. 4.0` (step `0.2`) |
| | `trail_decay` | `trail_decay` | `beat_runner_trail_decay` | Trail Decay | `slider` | `0.22` | `0.05 .. 0.5` (step `0.05`) |
| **Impact Shockwave** ([`Impact_shockwave_mode`](../../modes/Impact_shockwave_mode.py)) | `color_mode` | `color_mode` | `shockwave_color_mode` | Color Mode | `list` | `"vibrant_cycle"` | `"vibrant_cycle"`, `"neon_palette"`, `"single_hue"` |
| | `color_saturation` | `color_saturation` | `shockwave_saturation` | Color Saturation | `slider` | `1.0` | `0.5 .. 1.0` (step `0.05`) |
| | `base_hue` | `base_hue` | `shockwave_base_hue` | Base Hue | `slider` | `0.55` | `0.0 .. 1.0` (step `0.05`) |
| | `wave_width` | `wave_width` | `shockwave_width` | Wavefront Width | `slider` | `2.2` | `0.5 .. 4.0` (step `0.2`) |
| | `enable_ghost_ripples` | `enable_ghost_ripples` | `shockwave_ghost_ripples` | Ghost Ripples in Breakdowns | `switch` | `True` | `True`, `False` |
| | `damping` | `damping` | `shockwave_damping` | Wave Damping | `slider` | `0.02` | `0.005 .. 0.15` (step `0.005`) |

---

## 3. Additional `infos` Dictionary Overrides (`modes/*_mode.py`)

In addition to the 8 Web UI schemas above, two modes accept optional startup/runtime overrides via the global `infos` dictionary:

| `infos` Key | Consuming Mode | Default | Description |
| :--- | :--- | :---: | :--- |
| `fire_fade_ratio` | [`Plasma_fire_mode`](../../modes/Plasma_fire_mode.py) | `0.18` | Exponential smoothing ratio for rising plasma embers. |
| `fire_height_multiplier` | [`Plasma_fire_mode`](../../modes/Plasma_fire_mode.py) | `1.3` | Multiplier scaling flame column height against audio power. |
| `synesthesia_fade_ratio` | [`Synesthesia_mode`](../../modes/Synesthesia_mode.py) | `0.15` | Exponential smoothing ratio for pitch-class color transitions. |
| `synesthesia_brightness` | [`Synesthesia_mode`](../../modes/Synesthesia_mode.py) | `1.0` | Master brightness multiplier for chromagram pitch colors. |

All remaining modes (`Bary_rainbow_mode`, `Middle_bar_mode`, `Proportion_rainbow_mode`, `PSG_mode`, `Opposite_sides_mode`, `Flying_ball_mode`, `Coloured_middle_wave_mode`, `Static_wave_mode`, `Power_bar_mode`, `Extending_waves_mode`, `Magnetic_ball_mode`) self-tune their internal physics, speeds, and trails via the continuous `Mode` scene modifiers (`self.mood_pace`, `self.mood_sharpness`, `self.mood_trail`, `self.mood_accent`) and mood palette (`self.mood_colors`, `self.palette_lut`, `self.highlight_color`).
