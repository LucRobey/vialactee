# Modes Visual Description

This document provides a precise, visual-first description of every lighting mode available in the `modes` directory for the Vialactée hardware project. It explains exactly how each mode will look when displayed on the physical LED strip.

## Core Audio-Reactive Modes

* **Bary_rainbow_mode**
  **Visual:** A static, symmetrical rainbow gradient that starts from the center of the strip and mirrors outward to both ends. The colors are fully saturated, but their overall hue shift changes based on the music's pitch. Lower frequencies (bass) pull the entire gradient towards red/orange, while higher frequencies shift it towards purple/blue. The center LED is always the most intensely lit color.
* **Chromatic_chaser_mode**
  **Visual:** A single, intensely colored "laser head" that continuously sweeps from one end of the strip to the other and bounces back. It leaves a trailing tail of colored light that smoothly fades to black. The color of the laser head changes dynamically in real-time, sweeping through the color spectrum (from red to blue) depending on the dominant pitch (frequency barycenter) of the music.
* **Coloured_middle_wave_mode**
  **Visual:** The strip is divided symmetrically into sections. The exact center represents the bass (colored red/orange), and the outer edges represent the treble (colored blue/purple). When music plays, these specific colored sections light up and throb in place proportionally to the volume of their respective frequencies. The result is a symmetrical, multi-colored equalizer where the center pulses to the kick drum and the edges flutter to the hi-hats.
* **Extending_waves_mode**
  **Visual:** Every time a strong beat hits, a block of bright, solid color is "injected" precisely at the center of the strip. This block of color then continuously slides outwards towards the two ends of the strip, like a ripple in a pond. As new beats hit, new colors are injected, creating a continuous flow of outward-moving colored bands. The bands flow faster when the music is louder.
* **Flying_ball_mode**
  **Visual:** A cluster of illuminated LEDs (a "ball" of about 7 LEDs wide) darts quickly left and right across the strip. It leaves a long, smooth trail that fades to black. The ball's position on the strip correlates directly to the music's pitch (low notes pull it left, high notes pull it right). Its color also sweeps through the spectrum (green/blue to purple) based on the pitch.
* **Hyper_strobe_mode**
  **Visual:** The strip spends most of its time completely dark. Whenever a heavy, isolated bass kick hits, the entire LED strip flashes instantly to blinding, pure white. Immediately after the flash, the white fades out to black extremely quickly, creating a harsh, aggressive, and highly kinetic strobe effect that perfectly isolates the beat.
* **Magnetic_ball_mode**
  **Visual:** A glowing ball of light that is constantly being pulled towards the dead center of the strip by a simulated magnetic force. When audio beats hit, they "kick" the ball, violently throwing it towards the edges. If it hits an edge, it bounces back elastically. The ball leaves a motion-blur tail behind it, and its core size expands when the volume gets louder.
* **Matrix_rain_mode**
  **Visual:** A falling rain effect. Brightly colored "raindrops" (usually green) randomly spawn at the very top of the strip whenever sharp, high-frequency sounds like snares or hi-hats hit. These drops continuously slide down the strip one pixel at a time, leaving a fading green tail behind them, perfectly mimicking the classic digital rain from the movie *The Matrix*.
* **Metronome_mode**
  **Visual:** The entire LED strip flashes synchronously like a visual metronome. On the primary beat, it flashes a bright, solid white. On the off-beats (sub-beats), it flashes a bright, solid blue. Instead of a hard blink, it uses a sharp attack and a smooth fade-out, giving it a pulsating, rhythmic heartbeat feel.
* **Middle_bar_mode**
  **Visual:** A solid, single-colored bar of light grows symmetrically outwards from the exact center of the strip. The width of this bar pulses in and out, directly tied to the volume of a single, randomly selected frequency band. The rest of the strip outside this moving bar smoothly fades to black.
* **Opposite_sides_mode**
  **Visual:** Features two separate, growing bars of light. From the middle-left, a red/orange bar grows outward towards the far left edge in sync with the bass. From the middle-right, a blue/purple bar grows outward towards the far right edge in sync with the treble. The center gap remains unlit, creating a visual tug-of-war between the low and high frequencies on opposite sides.
* **PSG_mode**
  **Visual:** The strip has a solid red bar growing from the left edge (reacting to bass) and a solid blue bar growing from the right edge (reacting to treble). Between these two bars, the rest of the strip is black, except for a single, stark white dot. This white dot constantly shifts left or right, resting exactly at the balance point between the red and blue power levels.
* **Plasma_fire_mode**
  **Visual:** Simulates a column of fire burning from the base of the strip upwards. The "height" of the flames shoots up and down based on the total audio volume. The lit section is a fixed gradient that goes from deep red at the bottom to bright yellow/white at the top. Any LEDs above the current flame height fade smoothly to black.
* **Power_bar_mode**
  **Visual:** A classic VU meter. A solid colored bar fills up from the bottom to the top, its height directly proportional to the overall volume of the music. At the very peak of the bar sits a single white dot. When the volume drops, the colored bar falls instantly, but the white dot slowly floats downwards due to gravity until the bar shoots back up and pushes it higher again.
* **Proportion_rainbow_mode**
  **Visual:** The entire strip is filled with a rainbow gradient. However, unlike a static rainbow, the *width* of each color band constantly changes. If the bass is loud, the red section of the rainbow expands massively, squishing the other colors. If the treble is loud, the blue/purple section expands. The colors ripple and stretch like an accordion reacting to the equalizer.
* **Rainbow_mode**
  **Visual:** A full, smooth rainbow gradient permanently covers the entire strip (red at one end to blue at the other). The position of the colors is static, but the *brightness* of specific colored sections pulses dynamically. If a bass note hits, the red section flashes brighter; if a high note hits, the blue section flashes brighter.
* **Shining_stars_mode**
  **Visual:** A very sparse, dark mode. Most of the strip is black. When specific frequency bands peak, individual "stars" (single LEDs) instantly pop up at random locations across the strip. The color of the star matches the frequency that triggered it (e.g., a bass hit creates a red star, a treble hit creates a blue star). The stars then quickly fade out to black, creating a twinkling effect.
* **Static_wave_mode**
  **Visual:** A thick, symmetrical band of light sits in the center of the strip. It pulses thicker and thinner (expanding outwards and shrinking inwards) strictly to the rhythm of the bass and kick drum. The extreme outer edges of this pulsing band have sharp, bright white tips, while the inside of the band is solidly colored, with its brightness fluctuating to the overall volume.
* **Synesthesia_mode**
  **Visual:** The entire LED strip lights up in a single, perfectly uniform color that smoothly and constantly morphs. The color is determined by mapping the exact musical notes (chromagram) being played to a color wheel (e.g., a C note is one hue, a G is another). When a chord is played, it mixes the colors of those notes together. The overall brightness pulses with the volume.
