# Modes Visual Catalog (All 21 Active Modes)

> **Location:** `docs/reference/modes_catalog.md` (Tier 1 Canonical Specification)  
> **Registry:** [`config/modes.json`](../../config/modes.json) (21 mounted active modes)  
> **Source Directory:** [`modes/`](../../modes/)

This catalog provides the canonical visual description, orientation support, and behavioral characteristics for all 21 active mounted modes in Vialactée.

---

## 1. Active Mounted Modes Table

| # | Mode Name | Python Class | Orientation | Visual Description & Dynamics |
|:---:|:---|:---|:---:|:---|
| 1 | **Rainbow** | `Rainbow_mode` | Omnidirectional | Continuous smooth rainbow spectrum covering the strip. Brightness and saturation of frequency regions pulse dynamically with respective FFT bands. |
| 2 | **Bary Rainbow** | `Bary_rainbow_mode` | Both / Horizontal | Symmetrical rainbow gradient mirrored outward from the segment center. Center hue is driven by `ctx.vertical_center` and gentle continuous drift (`mood_pace`), while brightness and saturation pulse with `ctx.energy` and `self.beat_pulse()`. |
| 3 | **Middle Bar** | `Middle_bar_mode` | Horizontal | Solid colored bar growing symmetrically outward from the exact center. Width expands/contracts in proportion to auto-selected FFT band energy. |
| 4 | **Shining Stars** | `Shining_stars_mode` | Omnidirectional | Ambient dark canvas where individual LEDs twinkle and flash into existence at random positions when frequency bands peak, matching their color to the triggering band. |
| 5 | **Proportion Rainbow** | `Proportion_rainbow_mode` | Omnidirectional | Full rainbow gradient spanning the strip where the width of each color slice expands or contracts based on proportional FFT band energy distribution. |
| 6 | **PSG** | `PSG_mode` | Horizontal | Opposing left/right mood-colored bars (`mood_colors[0]` and `mood_colors[1]`, warmed by `mood_accent`) whose heights scale with `ctx.energy`, `self.beat_pulse()`, and `ctx.spectral_tilt`, with a `highlight_color` balance dot driven by `spectral_tilt` and gentle sway. |
| 7 | **Opposite Sides** | `Opposite_sides_mode` | Horizontal | Dual complementary mood-colored bars advancing toward a central equilibrium gradient zone. Balance center shifts with `ctx.spectral_tilt` (plus gentle sway when rhythm lock is low), and bar depths scale with `ctx.energy` and `self.beat_pulse()`. |
| 8 | **Plasma Fire** | `Plasma_fire_mode` | Vertical | Simulates a fiery plasma column rising from strip base. Flame height modulates dynamically with total volume power. Color gradients from deep crimson to yellow/white tips. |
| 9 | **Hyper Strobe** | `Hyper_strobe_mode` | Omnidirectional | Kinetic strobe and pulse gated on verified acoustic beats (`ctx.is_real_beat` with `beat_trust > 0.4`), `self.drop_hit`, or spectral flux peaks (`band_flux`), flashing `highlight_color` blended with `mood_colors[2]`. Smoothly crossfades to an acoustic breathing glow when `rhythm_lock` is low. |
| 10 | **Chromatic Chaser** | `Chromatic_chaser_mode` | Horizontal / Both | Concentrated laser head sweeping across the strip (with optional edge bounce) leaving an exponential decay trail (`mood_trail`). Speed synchronizes to `listener.bpm` (gated by `rhythm_lock`), `ctx.tension`, and `mood_pace`; head color blends `mood_colors` by `ctx.vertical_center` and `mood_accent`. |
| 11 | **Synesthesia** | `Synesthesia_mode` | Omnidirectional | Maps 12-note chromagram pitch analysis (`smoothed_chroma_values`) onto a circular color wheel, blended with `mood_colors[0]` and `mood_accent`, modulated by `ctx.energy`, `self.beat_pulse()`, and a traveling spatial sine wave so the strip shimmers continuously. |
| 12 | **Metronome** | `Metronome_mode` | Omnidirectional | Pulses rhythmically with the Anticipation Flywheel (`beat_phase`, `beat_count`) when confident (`rhythm_lock`), alternating between `highlight_color` on downbeats and `mood_colors[2]` / configurable accent color on sub-beats, and smoothly crossfading into acoustic breathing when beat tracking is lost. |
| 13 | **Flying Ball** | `Flying_ball_mode` | Horizontal | Luminous cluster (~7 LEDs wide) darting left/right leaving an exponential fade trail. Position correlates to spectral balance (bass left, treble right). |
| 14 | **Coloured Middle Wave** | `Coloured_middle_wave_mode` | Horizontal | Strip divided symmetrically into frequency bands. Center represents bass (red/orange), edges treble (blue/purple). Sections pulse outward with band volumes. |
| 15 | **Rhythm Breather** | `Rhythm_breather_mode` | Omnidirectional | Continuous phase-locked breathing visual. Pumps with tight percussive envelope on locked rhythm; decays gracefully into gentle volume glow on low confidence. |
| 16 | **Beat Runner** | `Beat_runner_mode` | Horizontal / Both | Dynamic BPM-scaled kinematic laser bead sweeping across strip and striking boundaries precisely on beat ticks ($T_{\text{speaker}}$). Diffuses to volume cloud on uncertainty. |
| 17 | **Impact Shockwave** | `Impact_shockwave_mode` | Horizontal / Both | Center-outward expanding ripple waves whose speed scales to BPM. Spawns kinetic shockwaves on verified acoustic hits (`is_real_beat`); suppresses flashes on ghost beats. |
| 18 | **Static Wave** | `Static_wave_mode` | Horizontal | Symmetrical central pulse band whose thickness breathes in and out strictly to bass transients, framed by bright white outer caps with color modulated by total audio power. |
| 19 | **Power Bar** | `Power_bar_mode` | Vertical | Classic audio VU peak meter. Solid colored column rises vertically with instantaneous power. Persistent peak-hold white dot floats at maximum crest and descends under gravity. |
| 20 | **Extending Waves** | `Extending_waves_mode` | Horizontal | On each detected beat, a new colored wavefront injects at strip center and travels outward towards both edges like ripples in water. Wave speed and luminosity scale with audio power. |
| 21 | **Magnetic Ball** | `Magnetic_ball_mode` | Horizontal | Physics-simulated ball with mass, spring tension toward center, and friction. Audio transients deliver kinetic impulses that kick ball toward boundaries where it bounces elastically. |
