# Music Events Architecture: Prospective Concepts & Future Ideas

> **Status:** Prospective / Research & Design Archive  
> **Source:** Extracted from `.agents/docs/music_events_architecture.md`  
> **Context:** Captures conceptual music perception features, Hard Song Cut rules, Harmonic Product Spectrum vocal isolation, and multi-song mood tracking not yet active in production code.

---

## 1. Hard Song Cut Detection (Song Change Type II)

### Conceptual Rule:
$$\Delta\text{BPM} > 8.0 \quad \land \quad \text{Current Confidence} < (\text{LTM Confidence} \times 0.6)$$

### Motivation:
When a playlist jumps tracks or a DJ hard-cuts into a brand new song at a completely different tempo, the rhythmic grid shatters:
- The calculated BPM jumps abruptly away from the historical tempo class in the lookahead buffer.
- The Pearson correlation score collapses below 60% of the long-term baseline.

### Planned Execution Logic:
1. When `AudioAnalyzer` detects a tempo jump $\Delta\text{BPM} > 8.0$ accompanied by a $>40\%$ collapse in template correlation confidence:
   - Declare a Hard Song Cut: `is_song_change = True`.
   - Update long-term tempo baseline to the incoming tempo.
   - Force-snap the speaker-time flywheel to the newly identified phase target.
   - Notify `Transition_Director` to abort ongoing transitions and initiate an emergency mode shift.

---

## 2. Harmonic Product Spectrum (HPS) Vocal Isolation (`vocals_present`)

### Conceptual Rule:
Extract fundamental human vocal frequencies ($100\text{ Hz} - 1000\text{ Hz}$) by downsampling and multiplying spectral FFT arrays across harmonic ratios:
$$HPS(\omega) = \prod_{r=1}^{R} |X(r \cdot \omega)|$$

### Planned Execution Logic:
- Detect pitch presence in human vocal registers to distinguish instrumental beats from vocal choruses/solos.
- Surface `listener.vocals_present: bool` to allow visual modes to illuminate dedicated centerpiece segments during vocal performances.
- Currently stubbed as `self.vocals_present = False` in `AudioAnalyzer.py:275`.

---

## 3. Multi-Song Mood & Triple-Note Architecture

### Conceptual Framework:
Track musical characteristics across three distinct time-windows:
- **Consensus Note ($N_c$):** Stable median of the last 5 completed songs (requires at least 3 similar songs to confirm `mood_detected = True`).
- **Live Note ($N_l$):** Running 3-second short-term average.
- **Lookahead Note ($N_f$):** 5-second future queue state.

### Planned Composite Metrics (Normalized $0.0 - 1.0$):
- **Danceability ($N_{dance}$):** Weighted composite of Pulse Clarity ($P_{pulse}$), Tempo Proximity to 120 BPM ($P_{tempo}$), Bass Prominence ($P_{bass}$), and Rhythmic Regularity ($P_{stability}$).
- **Intensity ($N_{intensity}$):** Asserved RMS volume and high-frequency spectral flux.
- **Drama ($N_{drama}$):** Dynamics variance and timbral entropy.
