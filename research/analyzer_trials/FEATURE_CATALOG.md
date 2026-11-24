# Feature catalogue: what a song can tell the lights

Goal: build the most complete offline description of each track, as a reference for what the live analyzer could
try to detect later and as raw material for choreographies. Too much is fine. Everything here is produced by
machines unless it is in `hand_labels.json`.

Columns: **Have** = already in `output/` for the 20 tracks. **Live later** is my estimate of how hard it would be
for a causal, real-time analyzer on the Pi: *easy* (energy-like, no lookahead), *medium* (needs a tracker or a small
model), *hard* (needs seconds of context or a large model), *offline only* (needs the whole song).
Tools marked "not tried" were found by search only: install, licence and quality are unverified.

## 1. Pulse and meter

| Information | Use for lights | Offline source | Have | Live later |
|---|---|---|---|---|
| Beats | flash, step, chase on the beat | Beat This, BeatNet, librosa, combined grid | yes | medium |
| Beat agreement (votes) | confidence; strong vs weak metrical level | `build_grid.py` | yes | n/a |
| Downbeats, position in bar (1-2-3-4) | accent the "1", per-bar patterns | Beat This, BeatNet downbeats; not merged yet | partly | hard |
| Tempo curve, tempo changes | animation speed, re-sync after a change | from the grid | derivable | medium |
| Tempo level (half / double feel) | choose slow sweep vs fast strobe | grid votes at fine level | partly | hard |
| Time signature (4/4, 3/4, 6/8) | pattern length | BeatNet / madmom bar tracking | no | hard |
| Regular grid through gaps | keep moving through a break | planned (bridge when tempo lines up) | no | medium (flywheel) |
| No-beat regions | go ambient instead of faking beats | `add_salience.py` | yes | medium |
| Swing / microtiming | shuffle feel on off-beats | offsets of off-beat hits vs grid | no | hard |
| Phrases (4, 8, 16 bars) | change look every phrase | bar counting from downbeats + sections | no | hard |

## 2. Drums and percussion

| Information | Use for lights | Offline source | Have | Live later |
|---|---|---|---|---|
| Kick hits | the "boom": pulses, bass-colour hits | band rule on drum stem (weak) -> ADTOF (not tried) | weak | medium |
| Snare / clap hits | backbeat flash, white accents | same | weak | medium |
| Hi-hat hits, open vs closed | sparkle, fine subdivision | ADTOF hi-hat class; LarsNet stems (not tried) | weak | medium |
| Toms, crash and ride cymbals | fills and big accents (crash = burst) | ADTOF 5 classes; LarsNet 5 stems | no | hard |
| Drum salience per beat | brightness per beat | drum-stem level at the beat | yes | easy |
| Kick pattern type (four-on-the-floor, breakbeat, half-time) | pick an animation family | pattern of kicks per bar | no | medium |
| Fills and rolls (snare roll speeding up) | build-up effects | hit density and acceleration per bar | no | medium |
| Kick drop-out and return | breakdown and drop markers | kick presence over time | derivable | medium |
| Percussion density | busy vs sparse look | hits per second | derivable | easy |

## 3. Structure and big moments

| Information | Use for lights | Offline source | Have | Live later |
|---|---|---|---|---|
| Section boundaries | change scene | novelty baseline (`run_sections.py`) | weak | hard |
| Section labels (intro, verse, chorus, bridge, solo, break, outro) | one look per section type | allin1 (madmom now builds: retry); SongFormer (not tried) | no | offline only |
| Repeats (same chorus again) | reuse the same look | section labels + similarity | no | offline only |
| Build-up, drop, breakdown | the main show moments in electro / techno | energy + kick rules; `drop-detector` repo (not tried) | no | hard (drop itself: medium) |
| Risers and sweeps (noise or pitch rising) | rising fill before a drop | spectral centroid slope in "other" stem | no | medium |
| Stops and silences, final hit, fade-out | blackout, freeze, slow fade | level per stem, no-beat regions | partly | easy |
| Energy arc of the song | overall intensity envelope | loudness curve, smoothed | derivable | easy |
| Key change, tempo change | palette shift, re-sync | key per section, tempo curve | no | hard |

## 4. Harmony

| Information | Use for lights | Offline source | Have | Live later |
|---|---|---|---|---|
| Chords with times | colour per chord, change on chord change | BTC (`run_chords.py`) | yes | hard |
| Chord change times (harmonic rhythm) | slow colour moves locked to harmony | from chords | derivable | hard |
| Key and mode (major / minor) | base palette, warm vs cold | madmom key model (now installable), or chord statistics | no | hard (offline per song: easy) |
| Bass note / root | colour of the bass strip | chords, or pitch of bass stem | derivable | medium |
| Tension (dissonance, distance from key) | saturation, flicker | from chords relative to key | no | hard |
| Chroma (12 pitch classes over time) | direct pitch-to-colour mapping | librosa chroma | derivable | easy-medium |

## 5. Melody, bass line and notes

| Information | Use for lights | Offline source | Have | Live later |
|---|---|---|---|---|
| Bass line notes (pitch, start, length) | bass strip follows the notes | Basic Pitch on bass stem (not tried; ONNX on Windows, lists Python up to 3.11) | no | medium |
| Lead / vocal melody pitch curve | height or position follows the tune | RMVPE, torchcrepe or PESTO on vocal stem (not tried) | no | medium (PESTO is built for low latency) |
| Melody direction (rising / falling) | movement direction along a strip | from the pitch curve | no | medium |
| Note onsets per stem (guitar, synth, piano) | per-instrument sparkle | Basic Pitch on "other" stem | no | medium |
| Arpeggios and fast runs | running-light patterns | note density and regularity | no | hard |

## 6. Voice and lyrics

| Information | Use for lights | Offline source | Have | Live later |
|---|---|---|---|---|
| Vocal on / off | spotlight when the singer is in | vocal-stem level (current rule is wrong on instrumentals) | weak | medium |
| Vocal intensity (soft, belted, shouted) | brightness of the vocal layer | vocal-stem loudness and brightness | derivable | medium |
| Sung vs spoken vs rap | different look for talk passages | pitch stability of vocal stem | no | hard |
| Lyrics with word times | word-synced effects, chorus hooks | Whisper / WhisperX on vocal stem (not tried; built for speech, timing on singing unproven) | no | offline only |
| Phrase starts and ends, breaths | phrase-level swells | gaps in vocal activity | derivable | medium |
| Lead vs backing vocals, harmonies | wider look on stacked vocals | stereo spread of vocal stem; dedicated separators | no | hard |
| Long held notes | sustain / glow effects | pitch curve stability | no | medium |

## 7. Energy, timbre and space

| Information | Use for lights | Offline source | Have | Live later |
|---|---|---|---|---|
| Loudness curve | master brightness | RMS / LUFS | derivable | easy |
| Level per stem (drums, bass, vocals, other) | one strip per instrument family | Demucs stems | yes (stems) | hard (needs live separation) or proxy by bands |
| Guitar and piano stems | guitar-solo look, piano look | Demucs 6-stem model (guitar okay, piano poor per its author) | no | hard |
| Band energies (sub, bass, mid, high) | classic spectrum looks | FFT bands | derivable | easy |
| Brightness (spectral centroid), noisiness | colour temperature, white amount | librosa | derivable | easy |
| Transient vs sustained | sharp flashes vs smooth fades | harmonic / percussive split | derivable | easy-medium |
| Stereo position and width (per stem or band) | left / right placement on the installation | channel level differences | no | easy |
| Dynamic contrast (quiet verse, loud chorus) | scale effects to the section | loudness per section | derivable | medium |

## 8. Mood and style

| Information | Use for lights | Offline source | Have | Live later |
|---|---|---|---|---|
| Valence and arousal (happy-sad, calm-excited), per song or per segment | palette and speed presets (fits the repo's `mood/` work) | Music2Emo (not tried) | no | hard (per song offline: fine) |
| Mood tags, genre, danceability | choose a mode family automatically | Music2Emo tags; CLAP text-audio matching (not tried) | no | hard |
| Instrument presence over time | "guitar solo", "strings enter" | stems; tagging models (no good source found yet) | no | hard |

## What I would add first

1. **Drum transcription with a trained model (ADTOF)** on the drum stems: kick, snare, hi-hat, toms, cymbals. Biggest gap for choreography, and it fixes the hidden-hat problem.
2. **Downbeats and bar position merged into the grid**, then the regular grid through gaps.
3. **Section labels (allin1)**, now that madmom builds on this machine.
4. **Build-up / drop / breakdown markers** for the electro tracks: no ready library, so rules on kick presence, energy and risers, checked by ear.
5. **Key, bass line and vocal pitch curve**: madmom key, Basic Pitch on the bass stem, RMVPE or PESTO on the vocal stem.
6. **Lyrics with word times** (Whisper on the vocal stem), English and French.
7. **Stereo position, loudness and brightness curves**: cheap, no new tools.
8. **Mood per song** (Music2Emo) last: useful for presets, least certain.

## Web survey of 2026-11-23 (found by search only; nothing installed or tried)

Owner allows paid and online tools. Music.ai is a business platform (owner could not use it as an individual).

| Topic | Find | Adds |
|---|---|---|
| Drum pieces as audio | DrumSep (MDX23C, 5 or 6 stems: kick, snare, toms, hi-hat, ride, crash; original weights offline since 2026-07, wrapper `openmirlab/mdxnet-infer`); LarsNet (non-commercial) | crash and ride apart; fixes hats hidden behind kicks |
| Drum transcription | ADT_STR (2026, code public, onsets + velocity), Noise-to-Notes (2026, release unknown); ADTOF still the common baseline | hit strength (velocity) per hit |
| Sections with labels | SongFormer (boundary score 0.70 vs 0.60 for All-In-One, authors' numbers; 2 to 4 s per song) | labelled sections |
| Drop / build-up | no ready detector found (only a 2014 paper) | must come from rules plus the owner's ear, or a small detector trained on his labels |
| Emotion over time | MMAS (2026-11, arousal and valence every 0.5 s, open source per abstract) | an "excitement" curve; weak at tracking change inside one song by its authors' own argument |
| All notes to MIDI | MuScriptor (2026-07, open weights), about half the notes right by its own score | bass line and melody, unreliable |
| Song described in words | Music Flamingo (NVIDIA, open checkpoints; licence not checked): harmony, structure, timbre in text | per-song notes; timestamp accuracy unproven |
| Building blocks | MuQ, MERT, MusicFM (general music models) | a way to train small detectors from few labels |
| Live beat and bar | BeatNet+, BEAST (streaming beat and downbeat) | evidence that live downbeats are feasible; not checked on a Pi |
| Stems | RoFormer family ahead of Demucs on scores; one 2026 study finds it distorts drum attacks more than SCNet-XL | cleaner stems; test timing before switching |
| Music to light, end to end | Skip-BART (ICLR 2026, code and dataset public), SeqLight (several lights), AuraLuxMuse | models that learned from human lighting engineers; relevant to the choreography lab |
| Commercial reference | MaestroDMX (Limbic Media): intros, builds, drops, transitions, spoken parts, silences, energy | what a product considers enough |
| Apple devices | Music Understanding framework (2026): sections, phrases, beats, bars, key, instrument activity | usable only on Apple hardware |

## Caveats
- Almost all of this is model output. Only what the listener confirms in the viewer becomes truth.
- Several tools are untested here and some list older Python versions (Basic Pitch) or non-commercial weights (LarsNet).
- "Live later" ratings are estimates, not measurements on the Pi.

## Sources
- ADTOF: https://github.com/MZehren/ADTOF and paper https://arxiv.org/pdf/2111.11737.pdf
- LarsNet: https://arxiv.org/abs/2312.09663v3
- All-In-One (allin1): https://github.com/mir-aidj/all-in-one
- SongFormer: https://github.com/aslp-lab/songformer and https://arxiv.org/html/2510.02797v2
- Drop detection: https://github.com/felixmeyer6/drop-detector and https://archives.ismir.net/ismir2014/paper/000297.pdf
- WhisperX: https://arxiv.org/html/2303.00747v2 ; Whisper on separated vocals: https://arxiv.org/pdf/2506.15514
- Basic Pitch: https://github.com/spotify/basic-pitch
- RMVPE: https://arxiv.org/html/2306.15412v1 ; torchcrepe: https://pypi.org/project/torchcrepe/0.0.13 ; rmvpe-onnx: https://pypi.org/project/rmvpe-onnx/
- Demucs (6-stem note): https://github.com/adefossez/demucs
- Music2Emo: https://huggingface.co/amaai-lab/music2emo and https://arxiv.org/html/2502.03979v2
