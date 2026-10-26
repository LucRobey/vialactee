# Listener Facade API Reference for Modes

Visual modes receive the `listener` instance upon initialization (`self.listener`, implementing `music.api.ListenerProtocol`). See [`docs/contracts/music_analyzer_contract.md`](../../../../docs/contracts/music_analyzer_contract.md) and [`modes/MODE_RULES.md`](../../../../modes/MODE_RULES.md) for the authoritative signal contract. How much we trust each `music/` signal is stated **only** in the producer contract, [`music_analyzer_contract.md`](../../../../docs/contracts/music_analyzer_contract.md); this file does not repeat per-signal ratings.

## 1. Timing & Frame Metrics

| Property | Trust | Type | Description |
|---|:-:|---|---|
| `self.dt` *(on `Mode`)* | 🟢 Helper | `float` | Delta time in seconds since the last frame (`Mode.dt`). |
| `self.fps_ratio` *(on `Mode`)* | 🟢 Helper | `float` | Multiplier relative to 60 Hz reference ($\text{dt} \times 60$, `Mode.fps_ratio`). |
| `self.listener.dynamic_audio_latency` | see contract | `float` | Dynamic ingestion latency buffer offset (seconds). |

---

## 2. Rhythmic & Beat Tracking ("Oracle" Flywheel)

> **Guidance:** Tempo and phase are probabilistic estimates and can drift on beatless intros, breakdowns, or polyrhythms. Modes reading `beat_phase`, `is_beat`, `bpm`, `is_real_beat`, or `beat_count` should gate or blend by a confidence signal (`self.rhythm_lock`, `beat_trust`, `rhythm_salience`, `is_locked`, `beat_confidence`, or `self.beat_pulse()`) and keep animating smoothly when confidence is `0.0`. Per-signal trust: see [`music_analyzer_contract.md`](../../../../docs/contracts/music_analyzer_contract.md).

| Property | Type | Description |
|---|---|---|
| `self.listener.is_beat` | `bool` | `True` for 1 frame when `beat_phase` wraps across `0.0` at speaker time. |
| `self.listener.is_real_beat` | `bool` | `True` when the beat tick corresponds to an actual acoustic transient. |
| `self.listener.is_dropped_beat` | `bool` | `True` during silent breakdowns where the flywheel freewheels a phantom beat tick. |
| `self.listener.beat_count` | `int` | Monotonically increasing counter of total beats detected since startup/reset. |
| `self.listener.beat_tag` | `str` | Frequency classification of the onset: `'Bass/Kick'`, `'Snare/Mid'`, or `'Hi-hat/Cymbal'`. |
| `self.listener.beat_phase` | `float` | Continuous phase in $[0.0, 1.0)$ in speaker time ($0.0 = \text{strike}$). |
| `self.listener.standalone_phase` | `float` | Backward-compatibility alias for `beat_phase`. |
| `self.listener.beat_confidence` | `float` | Pearson correlation confidence score ($0.0$ to $1.0$) at lookahead time. |
| `self.listener.beat_trust` | `float` | Speaker-delayed beat tracking trust score ($0.0$ to $1.0$). |
| `self.listener.rhythm_salience` | `float` | Speaker-delayed rhythmic salience ($0.0$ to $1.0$). |
| `self.listener.flywheel_status` | `str` | Status of the beat engine: `'locked'` or `'coasting'`. |
| `self.listener.bpm` | `float` | Effective metrical tempo in BPM (`effective_bpm` when sub-pulses are active). |
| `self.listener.standalone_bpm` | `float` | Backward-compatibility alias for `bpm`. |

---

## 3. Spectral & Audio Energy

| Property | Type | Description |
|---|---|---|
| `self.listener.nb_of_fft_band` | `int` | Number of coarse FFT frequency bands (default: `8`). |
| `self.listener.fft_band_values` | `np.ndarray` | Raw energy for each of the 8 Mel-scale bands ($\ge 0.0$, speaker-delayed). |
| `self.listener.smoothed_fft_band_values` | `np.ndarray` | ADSR-filtered band values (fast attack, slow release). |
| `self.listener.asserved_fft_band` | `np.ndarray` | Auto-gain normalized 8-band energy ($0.0$ to $1.0$). **Recommended for mode drive**. |
| `self.listener.band_proportion` | `np.ndarray` | Relative distribution of spectral energy across the 8 bands (sums to $\le 1.0$). |
| `self.listener.band_means` | `np.ndarray` | Long-term running average energy per band. |
| `self.listener.band_flux` | `np.ndarray` | Half-wave rectified spectral flux per band ($\ge 0.0$). |
| `self.listener.smoothed_total_power` | `float` | Smoothed total acoustic power ($\ge 0.0$). |
| `self.listener.asserved_total_power` | `float` | Auto-gain normalized total power ($0.0$ to $1.0$) at speaker time. |
| `self.listener.sensi` | `float` | Current audio sensitivity scale (from web interface / config). |
| `self.listener.luminosite` | `float` | Global master brightness scale ($0.0$ to $1.0$). |

---

## 4. Musical Pitch & Harmony (Chromagram)

> **Guidance:** `chroma_values` and `smoothed_chroma_values` are currently uncalibrated against broadband percussion/harmonics, so we trust them little. Avoid building new visuals on them for now. See [`music_analyzer_contract.md`](../../../../docs/contracts/music_analyzer_contract.md).

| Property | Type | Description |
|---|---|---|
| `self.listener.chroma_values` | `np.ndarray` | 12-dimensional pitch energy array mapping to `[C, C#, D, D#, E, F, F#, G, G#, A, A#, B]`. |
| `self.listener.smoothed_chroma_values` | `np.ndarray` | ADSR-filtered 12-note chromatic array. |

---

## 5. Structural Progression & Novelty

> **Guidance:** Scene, drop, boundary, and novelty signals are heuristics that can jitter or false-trigger. Concrete modes should not read `scene`, `is_drop_impact`, `is_drop_imminent`, `is_song_change`, `is_verse_chorus_change`, or `is_structural_cut` directly; use the debounced/smoothed `self.mood_pace`, `self.mood_sharpness`, `self.mood_trail`, `self.mood_accent`, `self.drop_hit`, and `self.drop_decay` on `Mode` instead. See [`music_analyzer_contract.md`](../../../../docs/contracts/music_analyzer_contract.md).

| Property | Type | Description |
|---|---|---|
| `self.listener.asserved_novelty` | `float` | Speaker-delayed auto-gain normalized novelty metric ($0.0$ to $1.0$). |
| `self.listener.combined_novelty` | `float` | Speaker-delayed raw combined timbre + power novelty metric. |
| `self.listener.is_song_change` | `bool` | Speaker-delayed 1-frame song boundary flag (reserved for `transitions/`). |
| `self.listener.is_verse_chorus_change` | `bool` | Speaker-delayed 1-frame section boundary flag (reserved for `transitions/`). |
