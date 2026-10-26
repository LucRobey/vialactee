# Listener Facade API Reference for Modes

Visual modes receive the `listener` instance upon initialization (`self.listener`, implementing `music.api.ListenerProtocol`). See [`docs/contracts/music_analyzer_contract.md`](../../../../docs/contracts/music_analyzer_contract.md) and [`modes/MODE_RULES.md`](../../../../modes/MODE_RULES.md) for the authoritative signal trust contract enforced by `TestDocsParity`.

## 1. Timing & Frame Metrics

| Property | Trust | Type | Description |
|---|:-:|---|---|
| `self.dt` *(on `Mode`)* | 🟢 Helper | `float` | Delta time in seconds since the last frame (`Mode.dt`). |
| `self.fps_ratio` *(on `Mode`)* | 🟢 Helper | `float` | Multiplier relative to 60 Hz reference ($\text{dt} \times 60$, `Mode.fps_ratio`). |
| `self.listener.dynamic_audio_latency` | 🟢 HIGH | `float` | Dynamic ingestion latency buffer offset (seconds). |

---

## 2. Rhythmic & Beat Tracking ("Oracle" Flywheel — 🟡 MEDIUM Trust)

> **Rule B (`test_modes_respect_trust_tiers`):** Any concrete mode reading `beat_phase`, `is_beat`, `bpm`, `is_real_beat`, or `beat_count` **must** also reference a confidence gate (`self.rhythm_lock`, `beat_trust`, `rhythm_salience`, `is_locked`, `beat_confidence`, or `self.beat_pulse()`).

| Property | Trust | Type | Description |
|---|:-:|---|---|
| `self.listener.is_beat` | 🟡 MEDIUM | `bool` | `True` for 1 frame when `beat_phase` wraps across `0.0` at speaker time. |
| `self.listener.is_real_beat` | 🟡 MEDIUM | `bool` | `True` when the beat tick corresponds to an actual acoustic transient. |
| `self.listener.is_dropped_beat` | 🟡 MEDIUM | `bool` | `True` during silent breakdowns where the flywheel freewheels a phantom beat tick. |
| `self.listener.beat_count` | 🟡 MEDIUM | `int` | Monotonically increasing counter of total beats detected since startup/reset. |
| `self.listener.beat_tag` | 🟡 MEDIUM | `str` | Frequency classification of the onset: `'Bass/Kick'`, `'Snare/Mid'`, or `'Hi-hat/Cymbal'`. |
| `self.listener.beat_phase` | 🟡 MEDIUM | `float` | Continuous phase in $[0.0, 1.0)$ in speaker time ($0.0 = \text{strike}$). |
| `self.listener.standalone_phase` | 🟡 MEDIUM | `float` | Backward-compatibility alias for `beat_phase`. |
| `self.listener.beat_confidence` | 🟡 MEDIUM | `float` | Pearson correlation confidence score ($0.0$ to $1.0$) at lookahead time. |
| `self.listener.beat_trust` | 🟡 MEDIUM | `float` | Speaker-delayed beat tracking trust score ($0.0$ to $1.0$). |
| `self.listener.rhythm_salience` | 🟡 MEDIUM | `float` | Speaker-delayed rhythmic salience ($0.0$ to $1.0$). |
| `self.listener.flywheel_status` | 🟡 MEDIUM | `str` | Status of the beat engine: `'locked'` or `'coasting'`. |
| `self.listener.bpm` | 🟡 MEDIUM | `float` | Effective metrical tempo in BPM (`effective_bpm` when sub-pulses are active). |
| `self.listener.standalone_bpm` | 🟡 MEDIUM | `float` | Backward-compatibility alias for `bpm`. |

---

## 3. Spectral & Audio Energy (🟢 HIGH & ⚙️ CONFIG)

| Property | Trust | Type | Description |
|---|:-:|---|---|
| `self.listener.nb_of_fft_band` | ⚙️ CONFIG | `int` | Number of coarse FFT frequency bands (default: `8`). |
| `self.listener.fft_band_values` | 🟢 HIGH | `np.ndarray` | Raw energy for each of the 8 Mel-scale bands ($\ge 0.0$, speaker-delayed). |
| `self.listener.smoothed_fft_band_values` | 🟢 HIGH | `np.ndarray` | ADSR-filtered band values (fast attack, slow release). |
| `self.listener.asserved_fft_band` | 🟢 HIGH | `np.ndarray` | Auto-gain normalized 8-band energy ($0.0$ to $1.0$). **Recommended for mode drive**. |
| `self.listener.band_proportion` | 🟢 HIGH | `np.ndarray` | Relative distribution of spectral energy across the 8 bands (sums to $\le 1.0$). |
| `self.listener.band_means` | 🟢 HIGH | `np.ndarray` | Long-term running average energy per band. |
| `self.listener.band_flux` | 🟢 HIGH | `np.ndarray` | Half-wave rectified spectral flux per band ($\ge 0.0$). |
| `self.listener.smoothed_total_power` | 🟢 HIGH | `float` | Smoothed total acoustic power ($\ge 0.0$). |
| `self.listener.asserved_total_power` | 🟢 HIGH | `float` | Auto-gain normalized total power ($0.0$ to $1.0$) at speaker time. |
| `self.listener.sensi` | ⚙️ CONFIG | `float` | Current audio sensitivity scale (from web interface / config). |
| `self.listener.luminosite` | ⚙️ CONFIG | `float` | Global master brightness scale ($0.0$ to $1.0$). |

---

## 4. Musical Pitch & Harmony (Chromagram — 🟢 HIGH Trust)

| Property | Trust | Type | Description |
|---|:-:|---|---|
| `self.listener.chroma_values` | 🟢 HIGH | `np.ndarray` | 12-dimensional pitch energy array mapping to `[C, C#, D, D#, E, F, F#, G, G#, A, A#, B]`. |
| `self.listener.smoothed_chroma_values` | 🟢 HIGH | `np.ndarray` | ADSR-filtered 12-note chromatic array. Ideal for harmonic color mapping. |

---

## 5. Structural Progression & Novelty (🟠 LOW Trust)

> **Rule A (`test_modes_respect_trust_tiers`):** Concrete modes (`modes/*_mode.py`) **must not** read `scene`, `is_drop_impact`, `is_drop_imminent`, `is_song_change`, `is_verse_chorus_change`, or `is_structural_cut`. Consume debounced/smoothed `self.mood_pace`, `self.mood_sharpness`, `self.mood_trail`, `self.mood_accent`, `self.drop_hit`, and `self.drop_decay` on `Mode` instead.

| Property | Trust | Type | Description |
|---|:-:|---|---|
| `self.listener.asserved_novelty` | 🟠 LOW | `float` | Speaker-delayed auto-gain normalized novelty metric ($0.0$ to $1.0$). |
| `self.listener.combined_novelty` | 🟠 LOW | `float` | Speaker-delayed raw combined timbre + power novelty metric. |
| `self.listener.is_song_change` | 🟠 LOW *(Forbidden in modes)* | `bool` | Speaker-delayed 1-frame song boundary flag (reserved for `transitions/`). |
| `self.listener.is_verse_chorus_change` | 🟠 LOW *(Forbidden in modes)* | `bool` | Speaker-delayed 1-frame section boundary flag (reserved for `transitions/`). |
