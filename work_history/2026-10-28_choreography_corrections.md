# [2026-10-28] Choreography Doctrine Corrective Plan v2 (Phases F0–F7)

> **Date:** 2026-10-28  
> **Session ID:** `453c481b-073e-468b-8f9b-005f3c92da3b`  
> **Agent / Model:** Gemini 4 Argon (High)  
> **Primary Goal:** Implement Corrective Plan v2 for Choreography Doctrine (module split, AXIOM-07 `utils/` governance, test hardening, `beat`-mute vs `rhythm_lock` evaluation, Mode Studio `Ctrl+B/L/S/T/M/0` keybindings, Impact Shockwave & Shining Stars conformance, and documentation corrections).  
> **Status:** COMPLETED  
> **Commits:** `2ffcbdb`, `dc73c08`, `9db5954`, `4e3bd56`, `d25dce2`, `e4fe95c`, `03ff24d`, `912cfb2`  
> **Skills Used:** `vialactee-project`, `vialactee-mode-creator`  
> **Skill Friction:** none

---

## 1. Context & Motivation

Follow-up corrective work for the Phase 1–5 Choreography Doctrine implementation:
* `utils/choreography.py` grew to 713 lines and imported `modes.*` and `pygame` across architectural layers.
* `utils/` was missing from `PRODUCTION_DIRS` in AXIOM-07 500-line governance tests.
* Calibration (`60/60/240`) and CI (`40/30/120`) stimulus configurations differed, and private `_SyntheticListener` / `_ContextMuteProxy` names were used in tests.
* `beat` mute sets `beat_trust = 1.0` and `salience = 1.0`, forcing `Mode.rhythm_lock = 1.0` and potentially confounding modes that blend on `rhythm_lock`.
* Mode Studio mute keys (`F1-F5`, `0`, `S`, `T`, `M`, `Shift+B/L`) collided or risked colliding with studio shortcuts; moved to `Ctrl+B/L/S/T/M` and `Ctrl+0`.
* `Impact_shockwave_mode` and `Shining_stars_mode` declared leads could not be muted independently.
* Documentation and work history required corrections for Shining Stars' diagnosis and updated module entrypoints.

---

## 2. Phase F0 — Baseline & Housekeeping

* **`git status`**: `config/app_config.json` modified in working tree (left untouched throughout all commits).
* **Environment**: Installed `anyio-4.15.1` in `.venv`.
* **Baseline Pytest Suite** (`.venv\Scripts\python.exe -m pytest -q --ignore=tests/test_benchmark_engine.py`):
  * **449 passed, 0 failed, 85 subtests passed** (all 7 async tests now pass).
* **Baseline Line Count**: `utils/choreography.py` = **713 lines**.
* **Golden Reference Captures** (`PYTHONHASHSEED=0`):
  * Saved `ci_config.json` (`40/30/120`), `report_config.json` (`60/60/240`), and `report.txt` in scratch golden directory.

---

## 3. Phase F1 & Phase F7 — Module Split & AXIOM-07 Governance Scope

* **Phase F1 (`2ffcbdb`)**: Split `utils/choreography.py` (713 lines) into:
  * [`utils/choreography.py`](../utils/choreography.py) (15 lines): `DRIVERS`, `MUTE_CHANNELS`, `NEUTRAL_MOOD_MODIFIERS`.
  * [`utils/driver_mute.py`](../utils/driver_mute.py) (374 lines): `ContextMuteProxy`, `DriverMuteProxy` (zero upward imports to `modes`, `importlib`, or `pygame`).
  * [`tools/studio_mutes.py`](../tools/studio_mutes.py) (54 lines): `format_hud_line`, `handle_studio_key`.
  * [`tools/choreography_matrix.py`](../tools/choreography_matrix.py) (353 lines): `SyntheticContext`, `SyntheticListener`, `compute_response_metrics`, `step_synthetic_music`, `run_mode_under_mutes`, `measure_mode_choreography`, `measure_all_registered_modes`, `format_measurement_report`.
  * Golden `ci_config.json` and `report_config.json` diffs were 100% empty.
* **Phase F7 (`dc73c08`)**: Added `"utils"` to `PRODUCTION_DIRS` in [`tests/governance/test_axiom_07_code_governance.py`](../tests/governance/test_axiom_07_code_governance.py) and [`tests/test_code_governance.py`](../tests/test_code_governance.py), and updated [`docs/axioms/AXIOM-07_CODE_GOVERNANCE.md`](../docs/axioms/AXIOM-07_CODE_GOVERNANCE.md). Verified with a temporary 501-line file in `utils/`.

---

## 4. Phase F2 — Test Hardening (`9db5954`)

* Exposed public `SyntheticContext`, `SyntheticListener`, and `ContextMuteProxy` names.
* Unified CLI and CI configuration under `MATRIX_CONFIG = {"num_leds": 40, "warmup_frames": 30, "eval_frames": 120}` (all 6 `CONFORMING_MODES_PHASE_4A` have identical conformance verdicts at `40/30/120` and `60/60/240` with `f = 0.30, g = 0.65`).
* Added `nb_bands` parameter and `--bands` CLI flag (`8` bands hard-asserted, `16` bands diagnostic test).
* Added in-process measurement determinism test and `CALIBRATED_FOR` provenance guard (`SYNTHETIC_CLIP_VERSION = "1"`).
* Documented Section 5 in [`docs/manuals/developer_tools.md`](../docs/manuals/developer_tools.md).

---

## 5. Phase F3 — `beat` Mute vs `rhythm_lock`

### 5.1 Modes Reading `rhythm_lock` and `beat_pulse()`
* **Modes reading `self.rhythm_lock` directly as a blend/gate:**
  * `Shining_stars_mode` (`(1.0 - 0.6 * lock)` band-energy fallback weight)
  * `Impact_shockwave_mode` (`(1.0 - lock) * energy * 0.22` center glow & `< 0.35` acoustic fallback)
  * `Middle_bar_mode` (`(1.0 - self.rhythm_lock) * 0.12` breath nudge)
  * `Opposite_sides_mode` (`(1.0 - 0.5 * self.rhythm_lock)` sway weight)
  * `Power_bar_mode` (`(1.0 - self.rhythm_lock) * 0.08` VU flutter)
  * `Chromatic_chaser_mode`, `Extending_waves_mode`, `Hyper_strobe_mode`, `Metronome_mode`
* **Modes reading `self.beat_pulse()`:**
  * `Bary_rainbow_mode`, `Coloured_middle_wave_mode`, `Impact_shockwave_mode`, `Middle_bar_mode`, `Opposite_sides_mode`, `Power_bar_mode`, `Proportion_rainbow_mode`, `Rainbow_mode`

### 5.2 Per-Mode Mean `rhythm_lock` Under `full` vs `mute beat` (P1 vs P3)

| Mode | `lock(full)` | `lock(P1, -beat)` | `Δlock(P1)` | `lock(P3, -beat)` | `Δlock(P3)` | `d(beat)` P1 | `d(beat)` P3 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `Rainbow_mode` | `0.8190` | `1.0000` | `+0.1810` | `0.9100` | `+0.0910` | `+3.16` | `+3.16` |
| `Bary_rainbow_mode` | `0.8190` | `1.0000` | `+0.1810` | `0.9100` | `+0.0910` | `+2.22` | `+2.22` |
| `Middle_bar_mode` | `0.8190` | `1.0000` | `+0.1810` | `0.9100` | `+0.0910` | `+11.52` | `+11.06` |
| `Shining_stars_mode` | `0.8190` | `1.0000` | `+0.1810` | `0.9100` | `+0.0910` | **`+5.11`** | **`+0.89`** |
| `Proportion_rainbow_mode` | `0.8190` | `1.0000` | `+0.1810` | `0.9100` | `+0.0910` | `+9.88` | `+9.88` |
| `Opposite_sides_mode` | `0.8190` | `1.0000` | `+0.1810` | `0.9100` | `+0.0910` | `+3.34` | `+2.96` |
| `Hyper_strobe_mode` | `0.8190` | `1.0000` | `+0.1810` | `0.9100` | `+0.0910` | `+0.00` | `+0.00` |
| `Chromatic_chaser_mode` | `0.8190` | `1.0000` | `+0.1810` | `0.9100` | `+0.0910` | `-0.13` | `+0.01` |
| `Metronome_mode` | `0.8190` | `1.0000` | `+0.1810` | `0.9100` | `+0.0910` | `+28.91` | `+26.10` |
| `Coloured_middle_wave_mode` | `0.8190` | `1.0000` | `+0.1810` | `0.9100` | `+0.0910` | `+1.17` | `+1.17` |
| `Impact_shockwave_mode` | `0.8190` | `1.0000` | `+0.1810` | `0.9100` | `+0.0910` | `+0.11` | `+0.09` |
| `Power_bar_mode` | `0.8190` | `1.0000` | `+0.1810` | `0.9100` | `+0.0910` | `+11.20` | `+9.95` |
| `Extending_waves_mode` | `0.8190` | `1.0000` | `+0.1810` | `0.9100` | `+0.0910` | `+0.00` | `+0.00` |

* **Outcome**: Under P1, `|Δlock| = 0.1810 >= 0.10`. Adopting **Option P3** (`beat_trust = 1.0`, `salience = _mean_salience`) keeps `beat_pulse()` strictly constant when `beat + macro` are muted, reduces `|Δlock|` to **`0.0910 < 0.10`** across every mode, and eliminates the artificial `d(beat) = +5.11 -> +0.89` distortion on `Shining_stars_mode` without changing any conforming mode verdict.

---

## 6. Phase F5 — Mode Studio Keys, HUD, & Footer (`d25dce2`)

* Replaced `[F1-F5/0]` / `[Shift+B/L, S, T, M]` key bindings in [`tools/studio_mutes.py`](../tools/studio_mutes.py) with `Ctrl+B` (`beat`), `Ctrl+L` (`level`), `Ctrl+S` (`spectrum`), `Ctrl+T` (`transient`), `Ctrl+M` (`macro`), and `Ctrl+0` (`clear all`), resolved dynamically from `CTRL_KEY_MAP` via `getattr(pygame, name)` and rejecting Shift/Alt/Meta combinations.
* Updated [`tools/mode_studio.py`](../tools/mode_studio.py) footer to `[Ctrl+B/L/S/T/M] Mute  ·  [Ctrl+0] Clear` (rendered width `1059 px` inside `1380 px` window, `160 px` margin each side) and verified HUD line at `(40, 44)` via headless offscreen PNG renders (`studio_unmuted.png`, `studio_muted.png`).
* Added [`tests/test_studio_mutes.py`](../tests/test_studio_mutes.py) (`6 passed`).

---

## 7. Phase F4 — `Impact_shockwave_mode` & `Shining_stars_mode` Conformance

### 7.1 Phase F4.0 & F4.1 — `Impact_shockwave_mode` Real-Audio Trigger Probe (`e4fe95c`)

Evaluated `Impact_shockwave_mode` on 5 real MP3 tracks (*Another One Bites The Dust*, *Boogie Wonderland*, *Come Together*, *Django*, *Bohemian Rhapsody*) stepped at 60 Hz (`735`-sample hop) and sampled by a 30 FPS reader under both `even` and `odd` frame parities:

| Track | Parity | `V0` Rings | `V-wrap` Rings | `V-flag` Rings | `V-wrap` Parity | `V-wrap` Shift | `V-wrap` Extra | `V-flag` Parity | `V-flag` Shift | `V-flag` Extra |
| :--- | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| *Another One Bites The Dust* | `even` | `170` | `170` | `98` | **`100.0%`** | `0.0 ms` | `0` | `57.1%` | `0.0 ms` | `1` |
| *Another One Bites The Dust* | `odd` | `170` | `170` | `95` | **`100.0%`** | `0.0 ms` | `0` | `55.9%` | `0.0 ms` | `0` |
| *Boogie Wonderland* | `even` | `199` | `199` | `103` | **`100.0%`** | `0.0 ms` | `0` | `51.3%` | `0.0 ms` | `1` |
| *Boogie Wonderland* | `odd` | `200` | `200` | `104` | **`100.0%`** | `0.0 ms` | `0` | `52.0%` | `0.0 ms` | `0` |
| *Come Together* | `even` | `267` | `267` | `179` | **`100.0%`** | `0.0 ms` | `0` | `66.3%` | `0.0 ms` | `2` |
| *Come Together* | `odd` | `271` | `271` | `144` | **`100.0%`** | `0.0 ms` | `0` | `52.4%` | `0.0 ms` | `2` |
| *Django* | `even` | `413` | `413` | `401` | **`100.0%`** | `0.0 ms` | `0` | `94.7%` | `0.0 ms` | `10` |
| *Django* | `odd` | `413` | `413` | `409` | **`100.0%`** | `0.0 ms` | `0` | `98.8%` | `0.0 ms` | `1` |
| *Bohemian Rhapsody* | `even` | `378` | `378` | `364` | **`100.0%`** | `0.0 ms` | `0` | `91.3%` | `0.0 ms` | `19` |
| *Bohemian Rhapsody* | `odd` | `378` | `378` | `358` | **`100.0%`** | `0.0 ms` | `0` | `85.2%` | `0.0 ms` | `36` |

* **Outcome**: `V-wrap` (`phase_wrapped` only + `drop_hit`) achieved **100.0% ring parity, 0.0 ms timing shift, and 0 extra rings** on every track and both parities, whereas `V-flag` (`is_beat` only) dropped 43–49% of rings on grooves at 30 FPS.
* Removed the `is_beat` branch from `verified_tick` in [`modes/Impact_shockwave_mode.py`](../modes/Impact_shockwave_mode.py), updated `LEAD = "beat"` (and [`docs/reference/modes_catalog.md`](../docs/reference/modes_catalog.md)), promoted `Impact_shockwave_mode` to `CONFORMING_MODES_PHASE_4A` (`d(beat) = +19.61`, `f = 0.535`, `g = 1.000`), and verified 100.0% ring parity on the updated class.

### 7.2 Phase F4.2 — `Shining_stars_mode` (`03ff24d`, `912cfb2`)

* **Deterministic RNG Seed (`03ff24d`)**: Replaced `hash((name, segment_name))` with `zlib.crc32(f"{name}:{segment_name}".encode("utf-8"))` at [`modes/Shining_stars_mode.py`](../modes/Shining_stars_mode.py) L89.
* **Stability Across Seeds (`PYTHONHASHSEED = 0..9` on pre-crc32 code with Option A)**:
  * Across seeds `0..9`, `R_std(full)` ranged in `[9.35, 10.69]`, `R_std(-lead) = 0.00`, `d(transient) = R_std(full)`, `f = 1.00`, and `g = 1.00` on every seed.
* **Star Spawn Density Table (`band = 0.8`, 8 bands at 60 FPS)**:

| `rhythm_lock` | Before (`1.0 - 0.6 * lock`) stars/s | After (`1.0 - lock`) stars/s | Retained Share |
| :---: | ---: | ---: | ---: |
| `0.3` | `480.0` | `480.0` | `100.0%` |
| `0.6` | `480.0` | `169.8` | `35.4%` |
| `0.8` | `480.0` | `5.2` | `1.1%` (pure onsets) |
| `1.0` | `169.8` | `5.2` | `3.1%` (pure onsets) |

* **Option A (`912cfb2`)**: Updated L166 to `drive = max(flux_val, (1.0 - lock) * band_val * self.threshold * 2.8)` and promoted `Shining_stars_mode` to `CONFORMING_MODES_PHASE_4A` (`d(transient) = +9.45`, `f = 1.00`, `g = 1.00`).

---

## 8. Final 13 × 4 Choreography Matrix (`MATRIX_CONFIG`: 40 LEDs / 30 Warmup / 120 Eval, 8 Bands)

```text
Mode                         Lead       Sec        R_std(full) R_std(-lead) R_std(-sec) R_std(-all)   d(lead)    d(sec)   R_diff
--------------------------------------------------------------------------------------------------------------------------------
Rainbow_mode                 spectrum   none             20.51        16.27       20.51        5.80     +4.25     +0.00     2.61
Bary_rainbow_mode            spectrum   beat             26.14        17.65       23.93        0.57     +8.49     +2.22     2.62
Middle_bar_mode              beat       spectrum         39.60        28.53       28.05        0.00    +11.06    +11.54     4.29
Shining_stars_mode           transient  spectrum          9.45         0.00        9.45        0.00     +9.45     +0.00     0.96
Proportion_rainbow_mode      spectrum   none             33.41        25.07       33.41        0.00     +8.34     +0.00     4.88
Opposite_sides_mode          spectrum   transient        58.24        29.08       58.24        9.31    +29.17     +0.00     5.04
Hyper_strobe_mode            transient  none             41.73         0.00       41.73        0.00    +41.73     +0.00    11.87
Chromatic_chaser_mode        beat       level            36.53        36.52       36.53       34.34     +0.01     +0.00     9.52
Metronome_mode               beat       none             29.39         3.28       29.39        2.43    +26.10     +0.00     6.03
Coloured_middle_wave_mode    spectrum   beat             30.76         8.81       29.59        0.00    +21.95     +1.17     3.00
Impact_shockwave_mode        beat       level            36.68        17.07       36.67        0.00    +19.61     +0.01     6.70
Power_bar_mode               level      beat             37.02        23.66       27.07        3.55    +13.36     +9.95     5.64
Extending_waves_mode         level      beat             30.71        30.71       30.71        0.00     +0.00     +0.00     5.50

Mode                         Lead          d(beat)   d(level)  d(spectrum)  d(transient)
----------------------------------------------------------------------------------------
Rainbow_mode                 spectrum        +3.16      +1.36        +4.25         +0.00
Bary_rainbow_mode            spectrum        +2.22      +4.08        +8.49         +0.00
Middle_bar_mode              beat           +11.06      +0.20       +11.54         +0.00
Shining_stars_mode           transient       +0.00      +0.00        +0.00         +9.45
Proportion_rainbow_mode      spectrum        +9.88      +1.51        +8.34         +0.00
Opposite_sides_mode          spectrum        +2.96      -0.37       +29.17         +0.00
Hyper_strobe_mode            transient       +0.00      +0.00        +0.00        +41.73
Chromatic_chaser_mode        beat            +0.01      +0.00        +1.07         +0.00
Metronome_mode               beat           +26.10      -0.03        +0.00         +0.00
Coloured_middle_wave_mode    spectrum        +1.17      -0.71       +21.95         +0.00
Impact_shockwave_mode        beat           +19.61      +0.01        +0.00         +0.00
Power_bar_mode               level           +9.95     +13.36        -0.14         -0.11
Extending_waves_mode         level           +0.00      +0.00        +0.00         +0.00
```

---

## 9. Verification & Testing

* **Command**: `.venv\Scripts\python.exe -m pytest -q --ignore=tests/test_benchmark_engine.py`
  * **Result**: **`459 passed, 0 failed, 89 subtests passed`**
* **Command**: `.venv\Scripts\python.exe -m tools.choreography_matrix` (and `--bands 16`)
  * **Result**: 8-band and 16-band matrices execute cleanly (`exit code 0`).
* **Line Counts**:
  * `utils/choreography.py`: 15 lines
  * `utils/driver_mute.py`: 374 lines
  * `tools/studio_mutes.py`: 57 lines
  * `tools/choreography_matrix.py`: 353 lines
* **`git diff --stat -- config/app_config.json`**: untouched in working tree, never staged.
