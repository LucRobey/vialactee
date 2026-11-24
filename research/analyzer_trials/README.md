# Analyzer trials: free MIR tools on 20 chosen tracks

Goal: see what free, local tools output on 20 tracks from `assets/musics/mp3_files/` (list in `tracks.json`),
before deciding whether a paid analyser or hand labelling is needed. Nothing here is ground truth: every
output is a machine opinion. Own venv in `.venv/` (kept out of the main project environment), CPU only.

Run everything with `.venv/Scripts/python.exe <script> [track ids]` from this folder. Outputs go to `output/`
(git-ignored; audio never committed).

| Script | Tool | Output |
|---|---|---|
| `run_beats.py` | Beat This (beats + downbeats), librosa baseline, existing BeatNet files from `research/benchmarks/ground_truth/neural/` | `output/beats/<id>.json` |
| `compare_beats.py` | mir_eval F-measure between the three trackers | table on stdout |
| `run_chords.py` | BTC chord model (170-label vocabulary), cloned to `vendor/BTC-ISMIR19` | `output/chords/<id>.json` |
| `run_demucs.py` | Demucs htdemucs stems (~1.5x track length on CPU) | `output/stems/<id>/*.wav` |
| `derive_from_stems.py` | heuristics on the stems: vocal on/off segments, kick/snare/hat onset times | `output/vocals/`, `output/drums/` |
| `run_adtof.py` | ADTOF trained drum model (PyTorch port in `vendor/ADTOF-pytorch`), on the mix and on the drum stem: kick, snare, tom, hat, cymbal | `output/adtof/<id>.json` |
| `run_sections.py` | librosa/scipy novelty-curve boundary baseline (no labels) | `output/sections/<id>.json` |

## Combined grid
`build_grid.py` merges Beat This, the BeatNet rerun and librosa into one grid per track (`output/grid/<id>.json`):
beats within 70 ms are one beat at their average time, gaps are filled at the finest tempo level any tracker follows,
off-grid single-tracker beats are dropped, and each beat keeps `votes` (how many trackers marked it).
`eval_grid.py` scores timing against drum onsets from the Demucs drum stem. On tracks 01-14 the average had less
jitter (7.9 ms) than Beat This (10.5) or BeatNet (10.8) alone. Smoothing the grid helps steady studio tracks and
hurts live or tempo-changing ones (Piece of My Heart 11.4 -> 19.0 ms), so the viewer shows the unsmoothed average.
Open: many grid breaks on tracks 11, 15 and 19, and no decision on which beat is "1".

`add_salience.py` then adds a `salience` (0..1, drum-stem level at the beat) per grid beat and `quiet_regions`:
- `no_beat`: Beat This and BeatNet do not land together for 5 s or more, decided beat by beat. Beats are flagged
  `no_beat`, to be ignored by a benchmark rather than scored. Drum loudness alone is not used for this: out-of-time
  percussion is loud. The start of a region is pulled back over beats with no drum hit, because
  trackers coast after the drums stop. Against the hand labels in `hand_labels.json` (Plastic People) the three
  edges timed by ear are detected at +1.0 s, +0.2 s and +0.2 s.
  The agreement tolerance widens to 10% of the beat in slow music and a region must last 6 beats as well as 5 s
  (Bohemian Rhapsody: two regions the listener called wrong were a slow passage and an 8-beat BeatNet glitch).
- `implied`: drum stem silent but the trackers agree (e.g. a guitar intro). Beats kept with low salience.
- `drum_hits` and per-beat `drums`: the kick / snare / hat hits from `derive_from_stems.py`. One label per hit, so
  a hat played together with a kick is lost (Stayin' Alive: 1 beat of 484 carries a hat). Times are usable, the
  split is not yet.
- Removed: a `check` kind from an "onsets off the grid" test. The one stretch checked by ear had a clear beat.
Thresholds are first guesses, tuned on that one track only.

## Beat viewer (check by eye and ear)
`.venv/Scripts/python.exe beat_viewer.py`, then open http://127.0.0.1:8765 (`beat_viewer.py` + `viewer.html`).
Plays a track with one flashing lamp per tracker, beat ticks under a scrolling waveform (red = bass band),
chords, and an optional click on each tracker's beats. The click is mixed into the audio, so it is the reliable
check; the lamps can lag on Bluetooth output.

## Finding: part of the existing BeatNet reference is on a wrong time base
In `research/benchmarks/ground_truth/neural/`, 10 of the 70 `.beats.txt` files have beats running to about 2x the
real song length (Stayin' Alive, Another One Bites The Dust, 01-Plastic-People, Nobody Rules the Streets, Boogie
Wonderland, Djon maya mai, Feeling Good, Money For Nothing_1, Roxanne, September). 14 `.meta.json` files report a
duration of exactly 2x the real one (the 10 above plus Nightcall, Palladium, Pumped Up Kicks, Sugar). Cause not traced.

Cause: `load_audio_file` in `research/benchmarks/engine/evaluator.py` returns the cached `librosa/*.npz` audio
(44.1 kHz) labelled with whatever `target_sr` was asked for. The extractor asks for 22.05 kHz, so BeatNet analysed
those tracks at half speed. `run_beatnet.py` reruns BeatNet on correctly decoded audio -> `output/beatnet/<id>.json`
(mean F-measure against Beat This on the 20 tracks: 0.92, against 0.72 for the existing files).

## Building madmom here (BeatNet needs it)
No MSVC, but the gcc shipped with Strawberry Perl (`C:\Strawberry\c\bin`) works. With `cython` installed in the venv:

    # mingw.cfg:  [build] compiler=mingw32   [build_ext] compiler=mingw32  define=MS_WIN64
    DIST_EXTRA_CONFIG=<path to mingw.cfg> pip install --no-build-isolation --no-deps git+https://github.com/CPJKU/madmom
    pip install pyaudio

## Not working on this machine
- `allin1` (section labels) not retried since madmom was built; it may work now.
- `essentia` has no Windows wheel and fails to build.
- scikit-learn's DLLs are blocked by the Windows app-control policy, so nothing here may import sklearn.
