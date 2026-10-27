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

## 2. Per-Mode Configurable Settings Catalog (`get_settings_schema`)

Every mode exposes live-tunable parameters to the Web UI (`ModeSettings.tsx`) and `tools/mode_studio.py`:

| Mode | Setting Key | Label | Control | Type | Default | Range / Options |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| [`Rainbow_mode`](../../modes/Rainbow_mode.py) | `color_mode` | Color Mode | `list` | `string` | `"mood"` | `"mood"`, `"rainbow"` |
| | `speed_divisor` | Rainbow Speed Divisor | `slider` | `number` | `20.0` | `2.0 .. 80.0` (step `1.0`) |
| | `fade_ratio` | Smoothness Ratio | `slider` | `number` | `0.2` | `0.02 .. 0.8` (step `0.02`) |
| [`Bary_rainbow_mode`](../../modes/Bary_rainbow_mode.py) | `color_mode` | Color Mode | `list` | `string` | `"mood"` | `"mood"`, `"rainbow"` |
| | `fade_ratio` | Smoothness Ratio | `slider` | `number` | `0.2` | `0.02 .. 0.8` (step `0.02`) |
| [`Middle_bar_mode`](../../modes/Middle_bar_mode.py) | `color_mode` | Color Mode | `list` | `string` | `"mood"` | `"mood"`, `"classic"` |
| | `fade_ratio` | Fade Speed | `slider` | `number` | `0.15` | `0.02 .. 0.5` (step `0.01`) |
| | `bar_scale` | Bar Width Scale | `slider` | `number` | `0.85` | `0.3 .. 1.0` (step `0.05`) |
| [`Shining_stars_mode`](../../modes/Shining_stars_mode.py) | `color_mode` | Color Mode | `list` | `string` | `"mood"` | `"mood"`, `"classic"` |
| | `sub_segment_size` | Star Density Size | `slider` | `integer` | `40` | `10 .. 100` (step `5`) |
| | `fade_ratio` | Trail Fade Speed | `slider` | `number` | `0.1` | `0.02 .. 0.4` (step `0.02`) |
| [`Proportion_rainbow_mode`](../../modes/Proportion_rainbow_mode.py) | `color_mode` | Color Mode | `list` | `string` | `"mood"` | `"mood"`, `"rainbow"` |
| | `fade_ratio` | Smoothness Ratio | `slider` | `number` | `0.2` | `0.02 .. 0.8` (step `0.02`) |
| [`PSG_mode`](../../modes/PSG_mode.py) | `fade_ratio` | Smoothness Ratio | `slider` | `number` | `0.3` | `0.05 .. 0.8` (step `0.05`) |
| | `center_gap_ratio` | Center Gap Ratio | `slider` | `number` | `0.2` | `0.05 .. 0.5` (step `0.05`) |
| [`Opposite_sides_mode`](../../modes/Opposite_sides_mode.py) | `fade_ratio` | Smoothness Ratio | `slider` | `number` | `0.3` | `0.05 .. 0.8` (step `0.05`) |
| | `gradient_width` | Center Gradient Width | `slider` | `integer` | `10` | `2 .. 30` (step `2`) |
| [`Plasma_fire_mode`](../../modes/Plasma_fire_mode.py) | `color_mode` | Color Mode | `list` | `string` | `"mood"` | `"mood"`, `"fire"` |
| | `fire_cooling` | Fire Cooling | `slider` | `number` | `0.08` | `0.01 .. 0.25` (step `0.01`) |
| | `fire_sparking` | Sparking Probability | `slider` | `number` | `0.6` | `0.1 .. 1.0` (step `0.05`) |
| [`Hyper_strobe_mode`](../../modes/Hyper_strobe_mode.py) | `strobe_decay` | Strobe Decay | `slider` | `number` | `0.7` | `0.3 .. 0.95` (step `0.05`) |
| | `strobe_Flux_thresh` | Flux Threshold | `slider` | `number` | `0.25` | `0.05 .. 0.8` (step `0.05`) |
| [`Chromatic_chaser_mode`](../../modes/Chromatic_chaser_mode.py) | `chaser_speed` | Chaser Speed | `slider` | `number` | `1.5` | `0.2 .. 5.0` (step `0.1`) |
| | `chaser_trail_fade` | Trail Fade | `slider` | `number` | `0.15` | `0.02 .. 0.5` (step `0.02`) |
| | `chaser_bounce` | Bounce at Ends | `toggle` | `boolean` | `True` | `True`, `False` |
| [`Synesthesia_mode`](../../modes/Synesthesia_mode.py) | `syn_fade_ratio` | Smoothness Ratio | `slider` | `number` | `0.2` | `0.02 .. 0.6` (step `0.02`) |
| [`Metronome_mode`](../../modes/Metronome_mode.py) | `metro_decay` | Pulse Decay | `slider` | `number` | `0.85` | `0.5 .. 0.98` (step `0.02`) |
| | `metro_color` | Beat Color | `list` | `string` | `"mood"` | `"mood"`, `"cyan"`, `"white"`, `"magenta"`, `"gold"`, `"green"` |
| [`Flying_ball_mode`](../../modes/Flying_ball_mode.py) | `color_mode` | Color Mode | `list` | `string` | `"mood"` | `"mood"`, `"classic"` |
| | `ball_radius` | Ball Radius | `slider` | `integer` | `3` | `1 .. 10` (step `1`, `LEDs`) |
| | `fade_ratio` | Trail Fade Speed | `slider` | `number` | `0.3` | `0.05 .. 0.8` (step `0.05`) |
| [`Coloured_middle_wave_mode`](../../modes/Coloured_middle_wave_mode.py) | `color_mode` | Color Mode | `list` | `string` | `"mood"` | `"mood"`, `"classic"` |
| | `fade_ratio` | Fade Speed | `slider` | `number` | `0.1` | `0.02 .. 0.5` (step `0.02`) |
| | `smooth_ratio` | Color Smoothness | `slider` | `number` | `0.2` | `0.05 .. 0.8` (step `0.05`) |
| [`Rhythm_breather_mode`](../../modes/Rhythm_breather_mode.py) | `color_mode` | Color Mode | `list` | `string` | `"mood"` | `"mood"`, `"classic"` |
| | `sharpness` | Pulse Sharpness | `slider` | `number` | `2.5` | `1.0 .. 5.0` (step `0.25`) |
| | `spatial_falloff` | Edge Falloff | `slider` | `number` | `0.5` | `0.0 .. 1.0` (step `0.05`) |
| | `fade_ratio` | Smoothness | `slider` | `number` | `0.25` | `0.05 .. 0.8` (step `0.05`) |
| [`Beat_runner_mode`](../../modes/Beat_runner_mode.py) | `color_mode` | Color Mode | `list` | `string` | `"mood"` | `"mood"`, `"classic"` |
| | `head_width` | Beam Width | `slider` | `number` | `2.5` | `1.0 .. 8.0` (step `0.5`, `LEDs`) |
| | `trail_fade` | Trail Persistence | `slider` | `number` | `0.22` | `0.05 .. 0.6` (step `0.02`) |
| | `motion_style` | Motion Style | `list` | `string` | `"bounce"` | `"bounce"`, `"sweep"` |
| [`Impact_shockwave_mode`](../../modes/Impact_shockwave_mode.py) | `color_mode` | Color Mode | `list` | `string` | `"vibrant_cycle"` | `"vibrant_cycle"`, `"mood"`, `"classic"` |
| | `ring_width` | Wavefront Width | `slider` | `number` | `2.2` | `1.0 .. 6.0` (step `0.2`, `LEDs`) |
| | `damping` | Wave Damping | `slider` | `number` | `0.02` | `0.005 .. 0.08` (step `0.005`) |
| | `afterglow_fade` | Afterglow Persistence | `slider` | `number` | `0.25` | `0.05 .. 0.6` (step `0.05`) |
| [`Static_wave_mode`](../../modes/Static_wave_mode.py) | `color_mode` | Color Mode | `list` | `string` | `"mood"` | `"mood"`, `"classic"` |
| | `fade_ratio` | Smoothness Ratio | `slider` | `number` | `0.2` | `0.02 .. 0.8` (step `0.02`) |
| | `edge_cap_width` | White Edge Cap Width | `slider` | `integer` | `10` | `0 .. 30` (step `2`, `LEDs`) |
| [`Power_bar_mode`](../../modes/Power_bar_mode.py) | `color_mode` | Color Mode | `list` | `string` | `"mood"` | `"mood"`, `"classic"` |
| | `fade_ratio` | Bar Smoothness | `slider` | `number` | `0.2` | `0.02 .. 0.8` (step `0.02`) |
| | `peak_gravity` | Peak Dot Gravity | `slider` | `number` | `0.2` | `0.05 .. 1.0` (step `0.05`) |
| [`Extending_waves_mode`](../../modes/Extending_waves_mode.py) | `color_mode` | Color Mode | `list` | `string` | `"mood"` | `"mood"`, `"classic"` |
| | `wave_speed_divisor` | Wave Speed Divisor | `slider` | `integer` | `4` | `1 .. 10` (step `1`) |
| | `fade_ratio` | Smoothness Ratio | `slider` | `number` | `0.2` | `0.02 .. 0.8` (step `0.02`) |
| [`Magnetic_ball_mode`](../../modes/Magnetic_ball_mode.py) | `color_mode` | Color Mode | `list` | `string` | `"mood"` | `"mood"`, `"classic"` |
| | `spring_force` | Center Spring Force | `slider` | `number` | `5.0` | `1.0 .. 15.0` (step `0.5`) |
| | `impulse_scale` | Audio Impulse Scale | `slider` | `number` | `50.0` | `10.0 .. 120.0` (step `5.0`) |
| | `friction_coef` | Friction | `slider` | `number` | `0.85` | `0.5 .. 0.98` (step `0.02`) |
