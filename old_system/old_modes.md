# Legacy System Modes & Transitions

This document details every specific animation mode extracted from the legacy ESP32 lighting project, including their visual logic, mathematical quirks, and specific transitional behaviors.

## 1. Magnetic Ball (`magnetic_ball.cpp`)
*   **Visual:** A single "ball" or block of light that physically reacts to sound through simulated kinesthesis.
*   **Logic:** Uses a spring-mass physics simulation. Audio power translates to `acceleration`, creating moving momentum (`speed`). A physical `friction` multiplier is applied iteratively to cause deceleration. 
*   **Transitions:**
    *   *White:* The ball shoots out rapidly across the whole strip, leaving a permanent white trail until the entire strip is saturated white.
    *   *Black:* The ball slows to a halt and smoothly shrinks/fades to absolute black.

## 2. Band Wars (`band_wars.cpp`)
*   **Visual:** Two distinct spectral factions (low vs high frequencies) "push" against each other on the strip.
*   **Logic:** Heavily relies on the `musicCenter` (spectral centroid) math. Calculates an absolute central pivot. As bass hits, the pivot lowers; as treble hits, the pivot raises, balancing colors proportionally.

## 3. Coloured Middle Wave (`coloured_middle_wave.cpp`)
*   **Visual:** Color waves emitting dynamically from a central point and cascading outwards toward the endpoints.
*   **Logic:** Interpolates the 16 frequency bands to color arrays mapped from the middle symmetrically.
*   **Transitions:**
    *   *White:* First phase fires high-speed blanked white blocks outward from the center; the second phase slowly fills the remainder of the strip white.
    *   *Black:* A black block pushes outwards from the middle point, eating the remaining light array like a curtain.

## 4. Extending Waves (`extending_waves_mode.cpp`)
*   **Visual:** Pulses of frequencies travel down the strip sequentially, rippling outward.
*   **Logic:** Continuously pushes history arrays pixel-by-pixel, simulating physical propagation delays for frequency hits. The wave speed and amplitude change based on current `asservedPower`.
*   **Transitions:** Contains very explicit block-masking phases to fade edges inward/outward during transition times.

## 5. Fire Mode (`fire_mode.cpp`)
*   **Visual:** A realistic flame simulation modeled using heat gradients. 
*   **Logic:** Uses a 1D pixel array of `temperatures`. It artificially creates random "sparks" (adding 255 heat to random base pixels based on beat peaks), then blurs (`temperatures[i] = (temp[i-1] + temp[i-2] + temp[i])/3`) and applies uniform `refroidissement` (cooling/friction).
*   **Transitions:**
    *   *White:* Overrides the cooling phase, injecting continuous max heat until the whole rod is fully white.
    *   *Black:* Kills random spark generation, making the ambient cooling equation rapidly pull everything to pure black.

## 6. Flying Ball / Balls (`flying_ball.cpp`)
*   **Visual:** A responsive orb hovering and dynamically re-positioning along the bar based on the dominant frequency spectrum.
*   **Logic:** Uses a weighted average `musicGravityCenter` to identify if the sound is bass-heavy vs treble-heavy, moving the ball's position. The `realSize` and `ledsPower` dynamically pulse with global audio intensity.

## 7. Magma Mode (`magma_mode.cpp`)
*   **Visual:** Symmetrical slow-moving lava bubbles interspersed with rapid, instantaneous white sparks.
*   **Logic:** Creates a vector array of multiple `heatWaves` moving with pseudo-random `heatSpeeds`. When `samplePeak` reads multiple beats simultaneously, it generates random bright white `crépitements` (sparks).
*   **Transitions:**
    *   *White:* Increases maximum baseline heat until it forcibly hits 255 threshold universally.

## 8. Shining Stars (`mode_shining_stars.cpp`)
*   **Visual:** Random bright, localized flashes against a dark background, mapping frequency band colors onto random coordinate hits.
*   **Logic:** Checks if a frequency band hits a peak (`> 0.5`). If yes, it randomizes a position (`posSS`) and instantly fires a bright CHSV pixel.
*   **Transitions:**
    *   *White:* Uses a predefined, scrambled random list of indices (`permutationForWhiteTransition`). As the timer proceeds, it progressively turns on pixels in this random sequence to white, avoiding linear fills.

## 9. Power Bar (`power_bar.cpp`)
*   **Visual:** A standard EQ-style Volume Unit (VU) meter growing from the bottom up to the top.
*   **Logic:** `real_size` scales perfectly with `asservedPower`. However, it features a `white_dot_pos` capping the wave, which is subject to independent "gravity"; it rises instantly with the bar but takes longer to fall back down, creating an inertia cap effect.
*   **Transitions:**
    *   During Black termination, it smoothly pushes the bar maximum boundary down to zero length linearly.

## 10. Rainbow Bar (`rainbow_bar.cpp`)
*   **Visual:** Displays the full 16 bands smoothed over the entire LED list length, showing rainbow interpolation.
*   **Logic:** Uses a physical `amortissement` array multiplier for different frequencies to visually fix visual biases (e.g., treble bounds are usually naturally quieter in music). Color HUE is mapped positionally (`160 * i / size`).

## 11. Static Wave (`static_wave.cpp`)
*   **Visual:** A mirrored pulse extending strictly from the exact geometric center.
*   **Logic:** Tracks only the lowest 0-3 frequency bands to average `valuef`. The total illuminated size oscillates exclusively out from `middle`, with explicit symmetrical pixel mapping logic `leds_middle + pos` and `leds_middle - pos`.
