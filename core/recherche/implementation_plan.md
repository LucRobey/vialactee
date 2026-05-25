# Mood Analysis & Predictive Transition Plan

This plan defines the architecture for the `Mood_Analysis` component and its integration into the Vialactée core engine. The goal is to detect musical moods over long periods and anticipate style changes using audio lookahead.

## 1. Core Logic: The Triple-Note System

The system evaluates three distinct time-windows to ensure stability and reactivity:
- **Consensus Note ($N_c$)**: The stable average of the last 5 songs (requires at least 3 similar songs to set `mood_detected = True`).
- **Live Note ($N_l$)**: Current audio state averaged over ~3 seconds to ignore short breaks.
- **Lookahead Note ($N_f$)**: The audio state in the 5-second future queue provided by `Listener`.

### Characteristics (Strictly Normalized 0.0 to 1.0)
1. **BPM**: Tempo from 60 to 180 BPM (using Median).
2. **Energy**: Average RMS power (using Median).
3. **Density**: Spectral richness/timbre (Bass vs Treble balance).
4. **Stability**: Rhythmic regularity (variance of beat timing).
5. **Dynamics**: Intra-song power variance (Standard Deviation of power over time).
6. **Danceability**: A composite metric reflecting suitability for dancing based on rhythm clarity, ideal tempo proximity, bass force, and power stability.

### Danceability Calculation ($N_{dance}$)
To compute `danceability` in real-time, the system combines four physical audio characteristics (each normalized between `0.0` and `1.0`):
1. **Pulse Clarity ($P_{pulse}$)**: Directly mapped from the `binary_trust` of the autocorrelation grid in `AudioAnalyzer`, showing how defined the rhythmic grid is.
2. **Tempo Weight ($P_{tempo}$)**: Centers around a Gaussian curve peaking at 120 BPM (ideal house/dance tempo) and falling off smoothly:
   $$P_{tempo} = \exp\left(-0.5 \cdot \left(\frac{\text{BPM} - 120.0}{30.0}\right)^2\right)$$
3. **Bass Prominence ($P_{bass}$)**: The ratio of dynamic low-frequency flux (`bass_flux` from `AudioAnalyzer`) relative to the total power, rewarding heavy kicks and sub-bass transients:
   $$P_{bass} = \min\left(1.0, \frac{\text{bass\_flux}}{\text{smoothed\_total\_power} + 1.0} \cdot C_{scale}\right)$$
4. **Rhythmic Stability ($P_{stability}$)**: The inverse of dynamics ($1.0 - \text{Dynamics}$), reflecting that dance/club tracks maintain a very consistent power flow compared to pop acoustic bridges or classical transitions.

The final **Danceability Note** ($N_{dance}$) is a weighted combination of these four pillars:
$$N_{dance} = w_{pulse} \cdot P_{pulse} + w_{tempo} \cdot P_{tempo} + w_{bass} \cdot P_{bass} + w_{stability} \cdot P_{stability}$$
*(Recommended defaults: $w_{pulse} = 0.3$, $w_{tempo} = 0.2$, $w_{bass} = 0.3$, $w_{stability} = 0.2$)*

## 2. Decision State Machine

### Phase A: Mood Detection (History)
- Store a `deque` of the last 5 songs.
- When `is_song_change` is detected, push the finished song's metrics.
- Check if a cluster of 3+ songs exists within a predefined interval.
- If found, `mood_detected = True` and set the **Consensus Target**.

### Phase B: Predictive Rupture Detection (Lookahead)
- Continuously compare $N_c$ with $N_f$.
- If $Distance(N_c, N_f) > Threshold_{Rupture}$:
    - Set `Mood_Analysis.pre_break_detected = True`.
    - **Trigger**: `Transition_Director` enters `PREPARING_MOOD_SHIFT` state.

### Phase C: Confirmation & Abort (The 5s Window)
- During the 5 seconds of lookahead:
    - **Confirmation**: If the deviation is sustained for > 2.5s, the transition is confirmed.
    - **Abort**: If the future audio returns to the consensus (false positive), the transition is faded back to zero and aborted.

### Phase D: Mood Re-entry (Return to Consensus)
- If `mood_detected` is False but the future ($N_f$) matches the Consensus ($N_c$):
    - Set `Mood_Analysis.pre_reentry_detected = True`.
    - **Trigger**: `Transition_Director` starts a "Smooth Re-entry" transition.
    - If confirmed over the 5s window, `mood_detected` becomes True again.

## 3. Visual Integration

### Transition_Director
- **New State `PREPARING_MOOD_SHIFT`**: Applies a global visual modifier (e.g., increasing red tint, rising pulse rate) over the active configuration.
- **Execution**: When lookahead reaches T=0, call `mode_master.change_configuration()` with a configuration matching the new style.

### Mode_master
- **New Method `pick_configuration_by_mood(notes)`**:
    - Filter configurations in `configurations.json` using `mood_criteria` (intervals like `[0.2, 0.5]`).
    - **Defaulting**: If a criterion is missing from the JSON, it defaults to `[0.0, 1.0]` (ignored).
    - Return a random match from the filtered list.

## 4. Configuration Schema Update

Configurations in `data/configurations.json` will be updated with optional criteria:
```json
"mood_criteria": {
  "bpm": [0.4, 0.7],
  "energy": [0.6, 1.0],
  "density": [0.5, 0.9],
  "dynamics": [0.0, 0.3],
  "stability": [0.7, 1.0],
  "danceability": [0.6, 1.0]
}
```

## 5. Verification Plan

- **Mock Data Test**: Simulate a sequence of Jazz songs followed by a sudden Techno track in a scratch script.
- **Confirmation Test**: Simulate a short 2-second "heavy" bridge within a Jazz song and verify the transition is aborted before impact.
- **Lookahead Sync**: Verify that the visual "preparation" starts exactly 5 seconds before the audio change.
