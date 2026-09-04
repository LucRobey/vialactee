# Modes Visual Description

This document provides a precise, visual-first description of every lighting mode available in the `modes/` directory for the Vialactée chandelier project. It explains exactly how each mode looks when displayed on the physical LED chandelier or visualizer.

Modes registered in [`config/modes.json`](file:///c:/Users/Users/Desktop/vialact%C3%A9e/vialactee/config/modes.json) are mounted at runtime and selectable via the web app Live Deck. Dormant modes remain available in the codebase for experimentation or future integration.

---

## Active Audio-Reactive Modes (Mounted in `config/modes.json`)

| Mode Name | Orientation | Visual Description |
| :--- | :--- | :--- |
| **Bary_rainbow_mode** | Horizontal / Both | Symmetrical rainbow gradient starting from the center of the segment and mirroring outwards to both ends. The colors are fully saturated, and the overall hue shift changes dynamically based on the spectral barycenter (pitch) of the music. Lower bass frequencies pull the gradient towards red/orange, while treble shifts it towards purple/blue. The center LED is always the brightest anchor point. |
| **Chromatic_chaser_mode** | Horizontal / Both | A concentrated, intensely colored laser head that continuously sweeps across the strip and bounces at the ends, leaving a smooth exponential decay trail behind it. The color of the laser head sweeps across the color wheel in real-time according to the dominant musical pitch (barycenter). |
| **Coloured_middle_wave_mode** | Horizontal | The strip is divided symmetrically into frequency sections. The center represents bass (red/orange), while outer edges represent treble (blue/purple). Colored sections light up and pulse outwards proportionally to band volumes, creating a center-outward audio-reactive equalizer. |
| **Flying_ball_mode** | Horizontal | A luminous cluster (~7 LEDs wide) darts left and right across the strip leaving an exponential fade trail. The ball's position correlates to spectral pitch balance (low frequencies pull left, high frequencies pull right), and its color sweeps along the spectrum. |
| **Hyper_strobe_mode** | Omnidirectional (Both) | Strip remains black until high-energy kick transients hit. On kick detection, the entire segment flashes blinding pure white and decays sharply to black within a few frames, creating an aggressive, kinetic strobe. |
| **Matrix_rain_mode** | Vertical | Classic digital rain inspired by *The Matrix*. Neon green raindrops spawn at the top of vertical strips on high-frequency transients (snares/hi-hats) and slide downwards pixel-by-pixel, leaving smooth fading green tails. |
| **Metronome_mode** | Omnidirectional (Both) | The entire LED segment pulses rhythmically with the Anticipation Flywheel ("Oracle"). On downbeats (primary beat), it flashes pure white; on sub-beats, it pulses deep blue, using sharp attack and smooth exponential decay. |
| **Middle_bar_mode** | Horizontal | A solid colored bar grows symmetrically outward from the exact center of the strip. The bar width expands and contracts in direct proportion to the energy of an auto-selected frequency band, fading smoothly to black outside the active bar. |
| **Opposite_sides_mode** | Horizontal | Dual complementary bars: from the middle-left, a red/orange bar expands outward in sync with bass energy; from the middle-right, a blue/purple bar expands in sync with treble energy, creating an energetic visual tug-of-war across the center gap. |
| **Plasma_fire_mode** | Vertical | Simulates a fiery plasma column rising from the base of the strip. Flame height modulates dynamically with total volume power. The color palette gradients smoothly from deep crimson at the base to fiery orange, yellow, and white tips. |
| **Proportion_rainbow_mode** | Omnidirectional (Both) | Full rainbow gradient spanning the strip where the width and distribution of each color slice expands or contracts dynamically based on the proportional energy distribution of its corresponding FFT band. |
| **PSG_mode** | Horizontal | Red bar expands from the left edge (bass) and blue bar expands from the right edge (treble). A single stark white balance indicator dot dynamically positions itself at the exact equilibrium point between low and high energy. |
| **Rainbow_mode** | Omnidirectional (Both) | Continuous smooth rainbow spectrum covering the strip. While color positions remain stable or gently drift, the brightness and saturation of specific color regions pulse dynamically with their respective frequency bands. |
| **Shining_stars_mode** | Omnidirectional (Both) | Dark, ambient canvas where individual LEDs ("stars") twinkle and flash into existence at random positions when specific frequency bands peak, matching their color to the triggering band before fading away. |
| **Synesthesia_mode** | Omnidirectional (Both) | The entire LED segment displays a uniform, harmonically driven hue computed from real-time chromagram pitch analysis (12-note chromatic scale mapped to the color wheel). Chords blend constituent note hues, while master brightness pulses with power. |

---

## Dormant / Experimental Modes (Unmounted)

> [!NOTE]
> The following modes exist in `modes/` as self-contained implementations inheriting from `Mode.Mode`, but are **not currently mounted** in [`config/modes.json`](file:///c:/Users/Users/Desktop/vialact%C3%A9e/vialactee/config/modes.json). They can be run in standalone tests or mounted into custom playlists.

| Mode Name | Orientation | Visual Description |
| :--- | :--- | :--- |
| **Alcool_randomer** | Omnidirectional (Both) | An arcade-style shot roulette wheel. A bright cursor accelerates along the strip through three distinct phases (ramp-up, constant cruise, deceleration) before stopping at a randomized LED position to select an outcome. Configurable via `shot_base_speed`, `shot_max_speed`, and `shot_fade_ratio`. |
| **Extending_waves_mode** | Horizontal | On each detected beat, a new colored wavefront is injected at the strip center and travels outward towards both edges like ripples in water. Wave speed and luminosity scale with audio power. |
| **Magnetic_ball_mode** | Horizontal | A physics-simulated ball modeled with mass, spring tension toward center, and friction. Audio transients deliver kinetic impulses that kick the ball toward the boundaries, where it bounces elastically. Ball radius expands with audio power. |
| **Power_bar_mode** | Vertical | Classic audio VU peak meter. A solid colored column rises vertically with instantaneous power. A persistent peak-hold white dot floats at the maximum crest and descends slowly under gravity. |
| **Static_wave_mode** | Horizontal | Symmetrical central pulse band whose thickness breathes in and out strictly to bass transients, framed by bright white outer caps with interior color modulated by overall audio power. |
