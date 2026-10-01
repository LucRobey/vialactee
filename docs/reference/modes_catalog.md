# Modes Visual Catalog (All 22 Active Modes)

> **Location:** `docs/reference/modes_catalog.md` (Tier 1 Canonical Specification)  
> **Registry:** [`config/modes.json`](../../config/modes.json) (22 mounted active modes)  
> **Source Directory:** [`modes/`](../../modes/)

This catalog provides the canonical visual description, orientation support, and behavioral characteristics for all 22 active mounted modes in Vialactée, plus the unmounted arcade mode.

---

## 1. Active Mounted Modes Table

| # | Mode Name | Python Class | Orientation | Visual Description & Dynamics |
|:---:|:---|:---|:---:|:---|
| 1 | **Rainbow** | `Rainbow_mode` | Omnidirectional | Continuous smooth rainbow spectrum covering the strip. Brightness and saturation of frequency regions pulse dynamically with respective FFT bands. |
| 2 | **Bary Rainbow** | `Bary_rainbow_mode` | Both / Horizontal | Symmetrical rainbow gradient starting from segment center and mirroring outwards. Global hue dynamically shifts based on spectral barycenter (pitch). Center LED is the brightest anchor. |
| 3 | **Middle Bar** | `Middle_bar_mode` | Horizontal | Solid colored bar growing symmetrically outward from the exact center. Width expands/contracts in proportion to auto-selected FFT band energy. |
| 4 | **Shining Stars** | `Shining_stars_mode` | Omnidirectional | Ambient dark canvas where individual LEDs twinkle and flash into existence at random positions when frequency bands peak, matching their color to the triggering band. |
| 5 | **Proportion Rainbow** | `Proportion_rainbow_mode` | Omnidirectional | Full rainbow gradient spanning the strip where the width of each color slice expands or contracts based on proportional FFT band energy distribution. |
| 6 | **PSG** | `PSG_mode` | Horizontal | Red bar expands from left edge (bass) and blue bar expands from right edge (treble). A stark white balance dot positions itself at the exact low/high equilibrium. |
| 7 | **Opposite Sides** | `Opposite_sides_mode` | Horizontal | Dual complementary bars: red/orange expands from mid-left on bass; blue/purple expands from mid-right on treble, creating a visual tug-of-war across the center gap. |
| 8 | **Matrix Rain** | `Matrix_rain_mode` | Vertical | Digital rain inspired by *The Matrix*. Neon green raindrops spawn at the top of vertical strips on high-frequency transients and slide downwards leaving fading tails. |
| 9 | **Plasma Fire** | `Plasma_fire_mode` | Vertical | Simulates a fiery plasma column rising from strip base. Flame height modulates dynamically with total volume power. Color gradients from deep crimson to yellow/white tips. |
| 10 | **Hyper Strobe** | `Hyper_strobe_mode` | Omnidirectional | Black strip until high-energy kick transient hits. On kick detection (gated with `is_real_beat`), flashes pure white and decays sharply to black within a few frames. |
| 11 | **Chromatic Chaser** | `Chromatic_chaser_mode` | Horizontal / Both | Intensely colored laser bead sweeping continuously across strip and bouncing at ends, leaving an exponential decay trail. Bead hue reflects dominant musical pitch. |
| 12 | **Synesthesia** | `Synesthesia_mode` | Omnidirectional | Displays uniform, harmonically driven hue computed from real-time chromagram pitch analysis (12-note chromatic scale mapped to color wheel). Chords blend note hues. |
| 13 | **Metronome** | `Metronome_mode` | Omnidirectional | Segment pulses rhythmically with the Anticipation Flywheel ("Oracle"). Downbeats flash pure white; sub-beats pulse deep blue with sharp attack and exponential decay. |
| 14 | **Flying Ball** | `Flying_ball_mode` | Horizontal | Luminous cluster (~7 LEDs wide) darting left/right leaving an exponential fade trail. Position correlates to spectral balance (bass left, treble right). |
| 15 | **Coloured Middle Wave** | `Coloured_middle_wave_mode` | Horizontal | Strip divided symmetrically into frequency bands. Center represents bass (red/orange), edges treble (blue/purple). Sections pulse outward with band volumes. |
| 16 | **Rhythm Breather** | `Rhythm_breather_mode` | Omnidirectional | Continuous phase-locked breathing visual. Pumps with tight percussive envelope on locked rhythm; decays gracefully into gentle volume glow on low confidence. |
| 17 | **Beat Runner** | `Beat_runner_mode` | Horizontal / Both | Dynamic BPM-scaled kinematic laser bead sweeping across strip and striking boundaries precisely on beat ticks ($T_{\text{speaker}}$). Diffuses to volume cloud on uncertainty. |
| 18 | **Impact Shockwave** | `Impact_shockwave_mode` | Horizontal / Both | Center-outward expanding ripple waves whose speed scales to BPM. Spawns kinetic shockwaves on verified acoustic hits (`is_real_beat`); suppresses flashes on ghost beats. |
| 19 | **Static Wave** | `Static_wave_mode` | Horizontal | Symmetrical central pulse band whose thickness breathes in and out strictly to bass transients, framed by bright white outer caps with color modulated by total audio power. |
| 20 | **Power Bar** | `Power_bar_mode` | Vertical | Classic audio VU peak meter. Solid colored column rises vertically with instantaneous power. Persistent peak-hold white dot floats at maximum crest and descends under gravity. |
| 21 | **Extending Waves** | `Extending_waves_mode` | Horizontal | On each detected beat, a new colored wavefront injects at strip center and travels outward towards both edges like ripples in water. Wave speed and luminosity scale with audio power. |
| 22 | **Magnetic Ball** | `Magnetic_ball_mode` | Horizontal | Physics-simulated ball with mass, spring tension toward center, and friction. Audio transients deliver kinetic impulses that kick ball toward boundaries where it bounces elastically. |

---

## 2. Unmounted Game Modes

| Mode Name | Python Class | Orientation | Description |
|:---|:---|:---:|:---|
| **Alcool_randomer** | `Alcool_randomer` | Omnidirectional | Arcade shot roulette wheel. Cursor accelerates through ramp-up, constant cruise, and deceleration before stopping at a randomized LED to select an outcome. |
