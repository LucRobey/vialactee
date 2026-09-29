# 🎯 Source of Truth: Vialactée Ground Truth Architecture

The Vialactée benchmark harness relies on **immutable, reproducible ground truth** to evaluate real-time music tracking algorithms (`AudioAnalyzer`). 

Evaluating beat tracking cannot rely on a single data type:
- Pure math tracks are needed to test edge cases in isolation (clean room).
- Real human music is needed to test swing, syncopation, and drummer drift.
- Academic literature benchmarks are needed to objectively compare performance against published international MIR standards.

To achieve this, ground truth is organized into **Three Complementary Tiers**.

---

## The 3-Tier Architecture at a Glance

```
research/benchmarks/ground_truth/
├── synthetic/                    ← Tier 1: Synthetic Clean-Room Generators
│   └── generator.py
├── synthetic_cache/              ← Tier 1: Cached WAV audio & .beats.txt
├── neural/                       ← Tier 2: Neural Deep Learning Ground Truth
│   ├── <Track>.beats.txt
│   ├── <Track>.downbeats.txt
│   ├── <Track>.meta.json
│   └── manifest.json
├── extract_neural_reference.py   ← Tier 2: Neural Reference Extraction CLI
└── academic/                     ← Tier 3: Standard Academic Datasets (Ballroom)
    ├── loader.py                 ← Tier 3: mirdata Loader & CLI Manager
    ├── data/ballroom/            ← Downloaded annotations & metadata (698 tracks)
    └── ballroom/                 ← Exported .beats.txt for offline testing
```

| Tier | Dataset Scope | Source / Engine | Timing Accuracy | Captures Downbeats? | Human Groove / Drift? |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **Tier 1: Synthetic** | 8 Clean-Room Stress Scenarios | Pure Python / NumPy Audio Synthesis | Sub-microsecond ($< 0.1\text{ms}$) | Yes (4/4, 3/2) | Synthetic Drift Only |
| **Tier 2: Neural** | User Music Library (`assets/musics/mp3_files/`) | **BeatNet 1.1.1** (CRNN + DBN) | Sub-centisecond ($\sim 5\text{ms}$) | **Yes** (4/4, 3/4 Waltz, etc.) | **Yes** (Real Drumming & Swing) |
| **Tier 3: Academic** | 698 Ballroom Dance Tracks | Human Expert Musicologists (CPJKU/UPF via `mirdata`) | Ground Truth Standard | Yes (Meter Annotations) | **Yes** (Acoustic & Studio Dancers) |

---

## Tier 1: Synthetic Clean-Room Suite

### How It Works
- **Location:** Code in `research/benchmarks/ground_truth/synthetic/generator.py`, audio and beat timestamps in `research/benchmarks/ground_truth/synthetic_cache/`.
- Synthetic tracks are synthesized directly into 22,050 Hz 16-bit PCM WAV audio.
- Because every transient is generated mathematically (sine bursts, lowpass kick drums, bandpass hi-hats), the true beat timestamps are **100% known down to 0.0001 seconds**.
- No acoustic ambiguity, no audio decoding drift.

### Current 8 Stress Scenarios
1. `synthetic_click_120bpm`: Constant 120.0 BPM 4/4 metronome.
2. `synthetic_click_85bpm`: Slow 85.0 BPM metronome (tests low-tempo tracking).
3. `synthetic_click_140bpm`: Fast 140.0 BPM metronome (tests fast-tempo tracking).
4. `synthetic_step_tempo`: Instant tempo step from 120.0 BPM to 140.0 BPM at $t = 15\text{s}$ (measures re-lock latency).
5. `synthetic_breakdown_dropout`: 16 bars drums $\to$ 8 bars total silence $\to$ drums return (tests whether flywheel coasts or hallucinates ghost beats).
6. `synthetic_tempo_drift_accel`: Continuous linear tempo acceleration from 100 to 130 BPM over 30s (tests dynamic phase adaptation).
7. `synthetic_syncopated_reggae`: Soft kicks on downbeats, loud accented hi-hats on offbeats (tests immunity to 180° upbeat phase traps).
8. `synthetic_polyrhythm_3_against_2`: 3-against-2 metric cross-rhythms (tests subharmonic trap resistance).

### How to Enrich Tier 1 (Adding New Synthetic Tests)
1. Open `research/benchmarks/ground_truth/synthetic/generator.py`.
2. Add your generator function following this template:
   ```python
   def generate_custom_scenario(output_dir: str, duration: float = 30.0) -> Tuple[str, str]:
       sr = 22050
       num_samples = int(duration * sr)
       audio = np.zeros(num_samples, dtype=np.float32)
       beats = []
       
       # Define your mathematical beat timestamps
       t = 0.5
       bpm = 128.0
       dt = 60.0 / bpm
       while t < duration - 0.5:
           beats.append(t)
           idx = int(t * sr)
           # Synthesize kick transient
           kick = _synth_kick(sr=sr, decay=0.08)
           audio[idx : idx + len(kick)] += kick
           t += dt
           
       wav_path = os.path.join(output_dir, "synthetic_custom.wav")
       beats_path = os.path.join(output_dir, "synthetic_custom.beats.txt")
       _write_wav(wav_path, audio, sr)
       _write_beats(beats_path, beats)
       return wav_path, beats_path
   ```
3. Register your function in `generate_all_synthetic_tracks(output_dir)` in `generator.py`.
4. Run the generator:
   ```powershell
   python -m research.benchmarks.ground_truth.synthetic.generator
   ```

---

## Tier 2: Neural Deep Learning Ground Truth

### Why We Replaced the "Grid"
The old Tier 2 approach relied on a rigid comb-filter grid:
$$t_n = t_0 + n \cdot \frac{60}{\text{BPM}}$$
This was fundamentally flawed for real music because:
- Human drummers naturally swing and drift by tens of milliseconds.
- Complex tracks have tempo changes, rubato, and measure shifts.
- It could not detect **downbeats** (the "1" of a measure) or irregular meters (e.g. 3/4 waltzes).
- On songs like *Bohemian Rhapsody* or live recordings, a fixed periodic grid becomes completely de-synchronized.

### How It Works
- **Location:** Generated files stored in `research/benchmarks/ground_truth/neural/`.
- **Extractor:** `research/benchmarks/ground_truth/extract_neural_reference.py`.
- **Acoustic Engine**: **BeatNet 1.1.1** (Heydari et al., ISMIR 2021).
  - Uses a Convolutional Recurrent Neural Network (CRNN) to extract spectral onset probabilities.
  - Couples to a Dynamic Bayesian Network (DBN) that infers continuous bar positions and tempo probabilities simultaneously.
- **Numba Acceleration**: The inner Viterbi search loop is accelerated via `@numba.jit(nopython=True, fastmath=True)`, executing full tracks in ~5 to 15 seconds on standard CPU.
- **Three Synchronized Reference Files Generated per Track:**
  1. `<track_name>.beats.txt`: Every detected beat timestamp (in seconds, 4 decimal places).
  2. `<track_name>.downbeats.txt`: Every detected downbeat (measure start: beat 1 of each bar).
  3. `<track_name>.meta.json`: Track statistics: duration, total beats, total downbeats, estimated BPM, interval jitter, and compute time.

### How to Enrich Tier 2 When You Import More MP3 Songs
Whenever you drop new songs into your library:
1. **Copy your new audio files** (`.mp3` or `.wav`) into:
   ```
   assets/musics/mp3_files/
   ```
2. **Run the Neural Extractor:**
   ```powershell
   # Automatically scans assets/musics/mp3_files/, skips previously extracted tracks,
   # and extracts neural ground truth for all newly added songs:
   python -m research.benchmarks.ground_truth.extract_neural_reference
   ```
3. **Advanced Extraction Options:**
   ```powershell
   # Extract only a specific song:
   python -m research.benchmarks.ground_truth.extract_neural_reference --track "Daft Punk"

   # Extract a limited batch (e.g. 5 tracks):
   python -m research.benchmarks.ground_truth.extract_neural_reference --limit 5

   # Force re-extraction even if the .beats.txt file already exists:
   python -m research.benchmarks.ground_truth.extract_neural_reference --track "Palladium" --force
   ```

---

## Tier 3: Standard Academic MIR Datasets

### How It Works
- **Location:** Script in `research/benchmarks/ground_truth/academic/loader.py`, dataset cached in `research/benchmarks/ground_truth/academic/data/ballroom/`.
- **Dataset:** **Ballroom Dataset** (Krebs, Böck et al. via `mirdata`).
  - Contains **698 audio tracks** spanning 8 distinct ballroom dancing styles:
    * *Cha-cha-cha*
    * *Jive*
    * *Quickstep*
    * *Rumba*
    * *Samba*
    * *Tango*
    * *Viennese Waltz* (Fast 3/4 meter)
    * *Slow Waltz* (Slow 3/4 meter)
  - Hand-annotated by expert musicologists at Johannes Kepler University (CPJKU) and Music Technology Group (UPF Barcelona).
  - Used in hundreds of peer-reviewed MIR papers, providing an objective comparison against published literature.

### How to Use & Enrich Tier 3
1. **Check Local Status:**
   ```powershell
   python -m research.benchmarks.ground_truth.academic.loader --dataset ballroom --status
   ```
   *Currently: All 698 beat annotations and index are downloaded and cached locally.*

2. **Download the Complete Audio Archive (~1.35 GB):**
   The audio files can be fetched directly on demand from the official UPF archive:
   ```powershell
   python -m research.benchmarks.ground_truth.academic.loader --dataset ballroom --download-audio
   ```

3. **Export Annotations to Standard `.beats.txt`:**
   ```powershell
   python -m research.benchmarks.ground_truth.academic.loader --dataset ballroom --export
   ```

4. **Adding Additional Academic Datasets:**
   `research/benchmarks/ground_truth/academic/loader.py` is built on top of `mirdata`. You can initialize any standard dataset (e.g. `hainsworth`, `smc_mirex`, `gtzan_genre`) by calling:
   ```python
   from research.benchmarks.ground_truth.academic.loader import get_academic_dataset
   ds = get_academic_dataset("hainsworth")
   ```

---

## Running Benchmarks Against the Sources of Truth

The benchmark runner supports all sources of truth seamlessly:

```powershell
# 1. Evaluate against Tier 1 (Clean-Room Synthetic)
python -m research.benchmarks.run_benchmark --suite synthetic

# 2. Evaluate against Tier 2 (Neural Ground Truth across your library)
python -m research.benchmarks.run_benchmark --suite neural

# 3. Evaluate a specific song against Tier 2
python -m research.benchmarks.run_benchmark --suite neural --track "Bohemian Rhapsody"

# 4. Evaluate against Tier 3 (Academic Ballroom, once audio is downloaded)
python -m research.benchmarks.run_benchmark --suite academic

# 5. Run full suite and save experiment to LEADERBOARD.md
python -m research.benchmarks.run_benchmark --suite synthetic --save-run --name my_experiment
```

---

## Visualizing Discrepancies Against Ground Truth

To visually inspect where your tracking model diverges from the ground truth:

```powershell
python -m research.benchmarks.plot_diagnostics --track "Palladium"
```
This generates a high-resolution 4-panel diagnostic figure in `research/experiments/plots/<track>_diagnostic.png` displaying:
1. **Waveform with True Beats (solid green)** vs **Model Predicted Beats (dashed magenta)**.
2. **Spectral Flux (ODF) Onset Energy** and detection thresholds.
3. **Flywheel Phase Sawtooth $\phi(t) \in [0, 1)$** showing phase alignment and soft-snapping.
4. **Estimated BPM Track** with shaded Failure Episode regions (ghost beats, phase inversions, jitter bursts).
