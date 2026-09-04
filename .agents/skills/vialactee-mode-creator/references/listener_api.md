# Listener Facade API Reference for Modes

Visual modes receive the `listener` instance upon initialization (`self.listener`). The `Listener` acts as a facade providing synchronized audio features, beat predictions, and spectral metrics.

## 1. Timing & Frame Metrics

| Property | Type | Description |
|---|---|---|
| `self.listener.dt` | `float` | Delta time in seconds since the last frame (typically $\approx 0.0166\text{s}$ at 60 FPS). |
| `self.listener.fps_ratio` | `float` | Multiplier relative to 60 FPS ($\text{dt} \times 60$). Use to scale physics/speeds consistently. |
| `self.listener.dynamic_audio_latency` | `float` | Dynamic ingestion latency buffer offset (seconds). |

---

## 2. Rhythmic & Beat Tracking ("Oracle" Flywheel)

| Property | Type | Description |
|---|---|---|
| `self.listener.is_beat` | `bool` | `True` for exactly 1 frame when the beat tracker fires a rhythmic beat tick at speaker time. |
| `self.listener.is_real_beat` | `bool` | `True` when the beat tick corresponds to an actual acoustic transient (drop-out immunity check). |
| `self.listener.is_dropped_beat` | `bool` | `True` during silent breakdowns where the flywheel freewheels a phantom beat tick. |
| `self.listener.beat_count` | `int` | Monotonically increasing counter of total beats detected since startup. |
| `self.listener.beat_tag` | `str` | Frequency classification of the onset: `'Bass/Kick'`, `'Snare/Mid'`, or `'Hi-hat/Cymbal'`. |
| `self.listener.beat_phase` | `float` | Continuous phase from `0.0` to `1.0` in speaker time ($0.0 = \text{downbeat}, 0.5 = \text{upbeat}$). |
| `self.listener.standalone_phase` | `float` | Alias for `beat_phase` for backward compatibility. |
| `self.listener.beat_confidence`| `float` | Pearson correlation confidence score ($0.0$ to $1.0$) of the rhythmic locking consensus. |
| `self.listener.flywheel_status`| `str` | Status of the beat engine: `'locked'` or `'coasting'`. |
| `self.listener.bpm` | `float` | Estimated consensus Beats Per Minute (e.g. `124.0`). |
| `self.listener.standalone_bpm` | `float` | Alias for `bpm` for backward compatibility. |

---

## 3. Spectral & Audio Energy

| Property | Type | Description |
|---|---|---|
| `self.listener.nb_of_fft_band` | `int` | Number of FFT frequency bands (default: 8). |
| `self.listener.fft_band_values` | `np.ndarray` | Raw energy for each of the 8 Mel-scale bands (speaker-delayed, normalized $0.0$ to $1.0$). |
| `self.listener.smoothed_fft_band_values` | `np.ndarray` | ADSR-filtered band values (fast attack, smooth release). |
| `self.listener.asserved_fft_band` | `np.ndarray` | Auto-gain normalized band energy ($0.0$ to $1.0$). **Recommended for color scaling**. |
| `self.listener.band_proportion` | `np.ndarray` | Relative distribution of spectral energy across bands (sums to $1.0$). |
| `self.listener.band_means` | `np.ndarray` | Long-term running average energy per band. |
| `self.listener.smoothed_total_power` | `float` | Instantaneous total volume level ($0.0$ to $1.0$). |
| `self.listener.asserved_total_power` | `float` | Auto-gain controlled total power ($0.0$ to $1.0$). |
| `self.listener.band_peak` | `np.ndarray` | Boolean array of length 8 indicating instantaneous transient peaks per band. |
| `self.listener.band_flux` | `np.ndarray` | Spectral flux / rate of change per band. |
| `self.listener.sensi` | `float` | Current audio sensitivity scale (from web interface / config). |
| `self.listener.luminosite` | `float` | Global master brightness scale ($0.0$ to $1.0$). |

---

## 4. Musical Pitch & Harmony (Chromagram)

| Property | Type | Description |
|---|---|---|
| `self.listener.chroma_values` | `np.ndarray` | 12-dimensional pitch energy array mapping to chromatic notes `[C, C#, D, D#, E, F, F#, G, G#, A, A#, B]`. |
| `self.listener.smoothed_chroma_values` | `np.ndarray` | ADSR-filtered 12-note chromatic array. Ideal for harmonic color mapping (e.g. synesthesia modes). |

---

## 5. Structural Song Progression & Novelty

| Property | Type | Description |
|---|---|---|
| `self.listener.is_song_change` | `bool` | Speaker-delayed `True` for 1 frame when novelty analysis detects a new track or complete stylistic change. |
| `self.listener.is_verse_chorus_change` | `bool` | Speaker-delayed `True` for 1 frame on major structural shifts (e.g. verse to drop/chorus transition). |
| `self.listener.asserved_novelty` | `float` | Speaker-delayed auto-gain normalized novelty metric ($0.0$ to $1.0$). |
| `self.listener.combined_novelty` | `float` | Speaker-delayed raw combined timbre + power novelty metric. |
| `self.listener.live_is_song_change` | `bool` | Unbuffered real-time ingestion-time song change flag. |
| `self.listener.live_is_verse_chorus_change` | `bool` | Unbuffered real-time ingestion-time verse/chorus change flag. |
| `self.listener.live_asserved_novelty` | `float` | Unbuffered real-time auto-gain normalized novelty metric ($0.0$ to $1.0$). |
| `self.listener.live_combined_novelty` | `float` | Unbuffered real-time raw combined novelty metric. |
