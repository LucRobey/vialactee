# Music lab: status

Built by `research/scoreboard/status.py`. Production scores from the scoreboard of 2026-11-27 (20 tracks, 0 to 100). Do not edit by hand.

## Signals

| Signal | In the contract | Production today | Truth | Runs on it | Best candidate on the check tracks |
|---|---|---|---|---|---|
| `beat` | bridged | 78 | checked | - | - |
| `bpm` | bridged | 67 | checked | - | - |
| `no_beat` | produced | 86 | checked | 1 | 87 (`2026-11-27_no_beat`) |
| `bar_position` | empty | - | - | - | - |
| `beats_per_bar` | empty | - | - | - | - |
| `beat_strength` | empty | - | - | - | - |
| `kick` | produced | 80 | checked | 1 | 85 (`2026-11-27_bands_kick`) |
| `snare` | empty | - | - | - | - |
| `hat` | empty | - | - | - | - |
| `tom` | empty | - | - | - | - |
| `cymbal` | empty | - | - | - | - |
| `kick_present` | produced | 85 | checked | 1 | 89 (`2026-11-27_bands_kick`) |
| `kick_level` | empty | - | - | - | - |
| `drop` | bridged | 5 | one tool only | - | - |
| `section_change` | bridged | 0 | one tool only | - | - |
| `breakdown` | empty | - | - | - | - |
| `buildup` | bridged | - | - | - | - |
| `riser` | empty | - | - | - | - |
| `silence` | bridged | 98 | checked | - | - |
| `bass_present` | empty | - | - | - | - |
| `drums_present` | empty | - | - | - | - |
| `vocal_present` | empty | - | - | - | - |
| `other_present` | empty | - | - | - | - |
| `bass_level` | empty | - | - | - | - |
| `drums_level` | empty | - | - | - | - |
| `vocal_level` | empty | - | - | - | - |
| `other_level` | empty | - | - | - | - |
| `layers` | empty | - | - | - | - |
| `loudness` | bridged | 66 | checked | - | - |
| `band_sub` | empty | - | - | - | - |
| `band_bass` | produced | 83 | checked | 1 | 84 (`2026-11-27_bands_kick`) |
| `band_mid` | produced | 89 | checked | 1 | 88 (`2026-11-27_bands_kick`) |
| `band_high` | produced | 93 | checked | 1 | 94 (`2026-11-27_bands_kick`) |
| `brightness` | bridged | 20 | checked | - | - |
| `fullness` | empty | - | - | - | - |
| `chord` | empty | - | - | - | - |

## Runs

| Run | Target | Candidate | Open tracks | Check tracks | State | Outcome |
|---|---|---|---|---|---|---|
| `2026-11-27_no_beat` | no_beat | NoBeatSlotAudioAnalyzer | no_beat 89 | no_beat 87 | decided | approved by the owner 2026-11-27. Owner: 'yes, we need that'. Promoted the same day into music/BandKickSignals.py. |
| `2026-11-27_bands_kick` | kick, kick_present, band_bass, band_mid, band_high | BandKickSlotsAudioAnalyzer | kick 75, kick_present 81, band_bass 82, band_mid 89, band_high 93 | kick 85, kick_present 89, band_bass 84, band_mid 88, band_high 94 | decided | approved by the owner 2026-11-27. Promoted the same day to music/BandKickSignals.py. |

The work list is `BACKLOG.md`. A run that is "waiting for the owner" also appears in `research/INBOX.md`.
