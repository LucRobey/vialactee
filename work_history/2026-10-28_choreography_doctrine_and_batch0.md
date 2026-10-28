# Session Log: 2026-10-28 — Choreography Doctrine (Law 7) & Batch 0 Mode Removals

* **Date:** 2026-10-28
* **Agent / Author:** Antigravity
* **Status:** **COMPLETED**
* **Commits:** `52b7deb` (Phase 1), `97d5f37` (Phase 2 / Batch 0), `bc26d6a` (Phase 3), `75cd390` (Phase 4a), `1649ce4` (Phase 5)

---

## 1. Objective & Scope

Implement the **Choreography Doctrine (Revision 2)** end-to-end across the Vialactée repository with strict per-phase git discipline:
1. **Phase 1 — Name it:** Add **Law 7: One Lead Timescale (The Choreography Doctrine)** to [`docs/contracts/mode_contract.md`](../docs/contracts/mode_contract.md) and Section 0 (**The Four-Question Worksheet**) to [`docs/manuals/mode_authoring_guide.md`](../docs/manuals/mode_authoring_guide.md).
2. **Phase 2 — Batch 0 (Mode Removals):** Remove the 8 retired modes (`PSG_mode.py`, `Plasma_fire_mode.py`, `Flying_ball_mode.py`, `Synesthesia_mode.py`, `Magnetic_ball_mode.py`, `Beat_runner_mode.py`, `Rhythm_breather_mode.py`, `Static_wave_mode.py`) and update [`config/modes.json`](../config/modes.json), [`transitions/mode_dna.py`](../transitions/mode_dna.py), [`docs/reference/modes_catalog.md`](../docs/reference/modes_catalog.md), architecture/contract docs, and test suites from 21 to 13 active modes.
3. **Phase 3 — Declare it:** Create [`utils/choreography.py`](../utils/choreography.py) (`DRIVERS`, `MUTE_CHANNELS`), declare `LEAD` and `SECONDARY` + `Lead:` class docstrings on all 13 mode classes without touching [`modes/Mode.py`](../modes/Mode.py) (499/500 lines cap under AXIOM-07), add `Lead` and `Secondary` columns to [`docs/reference/modes_catalog.md`](../docs/reference/modes_catalog.md), and enforce governance rules 1–4 in [`tests/governance/test_mode_choreography.py`](../tests/governance/test_mode_choreography.py) and [`tests/governance/test_docs_parity.py`](../tests/governance/test_docs_parity.py).
4. **Phase 4a — Measure:** Implement `DriverMuteProxy`, `ContextMuteProxy`, `compute_response_metrics` (`R_std` amplitude budget + `R_diff` busyness), and the deterministic synthetic stimulus runner (subsequently split into [`utils/choreography.py`](../utils/choreography.py), [`utils/driver_mute.py`](../utils/driver_mute.py), and [`tools/choreography_matrix.py`](../tools/choreography_matrix.py)); run and record the 13 × 4 measurement matrix; add proxy attribute-coverage and mute-semantics unit tests plus calibrated dominance checks in [`tests/governance/test_mode_choreography.py`](../tests/governance/test_mode_choreography.py).
5. **Phase 5 — See it & Roadmap Annotations:** Integrate `DriverMuteProxy` into [`tools/mode_studio.py`](../tools/mode_studio.py) via [`tools/studio_mutes.py`](../tools/studio_mutes.py) (HUD readout `LEAD: ... · SECONDARY: ... · muted: [...]` and `[Ctrl+B/L/S/T/M]` / `[Ctrl+0]` mute toggles), update [`.agents/skills/vialactee-mode-creator/SKILL.md`](../.agents/skills/vialactee-mode-creator/SKILL.md) and [`boilerplate_mode.py`](../.agents/skills/vialactee-mode-creator/examples/boilerplate_mode.py), and add `Lead / Secondary / Macro handles` lines to all 13 mode specs in the roadmap (Phase 6 mode redesigns not yet started).

---

## 2. Phase 4a Empirical Measurement Matrix (`13 Modes × 4 Conditions` + Ablation)

Executed via `.venv\Scripts\python.exe -m tools.choreography_matrix` (historical snapshot at `num_leds=60`, `warmup_frames=60`, `eval_frames=240` at 60 FPS on the orthogonal synthetic music clip; see [`2026-10-28_choreography_corrections.md`](2026-10-28_choreography_corrections.md) for the unified `40/30/120` matrix):

### 2.1 Primary `R_std` & `R_diff` Matrix

| Mode | `LEAD` | `SECONDARY` | `R_std(full)` | `R_std(-lead)` | `R_std(-sec)` | `R_std(-all)` | `Δ(lead)` | `Δ(sec)` | `R_diff(full)` |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| [`Rainbow_mode`](../modes/Rainbow_mode.py) | `spectrum` | `none` | `23.45` | `19.06` | `23.45` | `11.99` | `+4.40` | `+0.00` | `2.69` |
| [`Bary_rainbow_mode`](../modes/Bary_rainbow_mode.py) | `spectrum` | `beat` | `27.63` | `18.84` | `25.13` | `1.43` | `+8.79` | `+2.50` | `2.62` |
| [`Middle_bar_mode`](../modes/Middle_bar_mode.py) | `beat` | `spectrum` | `39.07` | `32.36` | `27.29` | `0.00` | `+6.71` | `+11.78` | `3.73` |
| [`Shining_stars_mode`](../modes/Shining_stars_mode.py) | `transient` | `spectrum` | `43.42` | `43.25` | `40.84` | `0.00` | `+0.17` | `+2.58` | `15.59` |
| [`Proportion_rainbow_mode`](../modes/Proportion_rainbow_mode.py) | `spectrum` | `none` | `33.97` | `25.45` | `33.97` | `0.00` | `+8.53` | `+0.00` | `4.89` |
| [`Opposite_sides_mode`](../modes/Opposite_sides_mode.py) | `spectrum` | `transient` | `59.52` | `28.09` | `59.52` | `8.15` | `+31.42` | `+0.00` | `4.85` |
| [`Hyper_strobe_mode`](../modes/Hyper_strobe_mode.py) | `transient` | `none` | `39.82` | `0.00` | `39.82` | `0.00` | `+39.82` | `+0.00` | `12.43` |
| [`Chromatic_chaser_mode`](../modes/Chromatic_chaser_mode.py) | `beat` | `level` | `40.68` | `40.69` | `40.68` | `39.03` | `-0.01` | `+0.00` | `7.51` |
| [`Metronome_mode`](../modes/Metronome_mode.py) | `beat` | `none` | `29.33` | `0.46` | `29.33` | `0.00` | `+28.87` | `+0.00` | `6.25` |
| [`Coloured_middle_wave_mode`](../modes/Coloured_middle_wave_mode.py) | `spectrum` | `beat` | `31.21` | `9.52` | `31.13` | `0.00` | `+21.69` | `+0.07` | `2.77` |
| [`Impact_shockwave_mode`](../modes/Impact_shockwave_mode.py) | `transient` | `level` | `34.29` | `34.29` | `34.28` | `0.00` | `+0.00` | `+0.00` | `6.65` |
| [`Power_bar_mode`](../modes/Power_bar_mode.py) | `level` | `beat` | `35.78` | `24.50` | `27.99` | `0.91` | `+11.27` | `+7.79` | `4.53` |
| [`Extending_waves_mode`](../modes/Extending_waves_mode.py) | `level` | `beat` | `26.49` | `26.49` | `26.49` | `0.00` | `+0.00` | `+0.00` | `5.15` |

### 2.2 Per-Driver Ablation Contributions (`Δ(d) = R_std(full) - R_std(mute_d)`)

| Mode | `LEAD` | `Δ(beat)` | `Δ(level)` | `Δ(spectrum)` | `Δ(transient)` | Phase 4a Verdict |
| :--- | :--- | ---: | ---: | ---: | ---: | :--- |
| `Rainbow_mode` | `spectrum` | `+3.23` | `+0.39` | **`+4.40`** | `+0.00` | Confirms **R6**: `spectrum` (`+4.40`) barely leads `beat` (`+3.23`) because `0.40*band + 0.60*(0.35*energy + 0.65*pulse)` mixes 3 timescales on brightness |
| `Bary_rainbow_mode` | `spectrum` | `+2.50` | `+4.87` | **`+8.79`** | `+0.00` | ✅ Conforms (`spectrum` dominant, `beat` secondary) |
| `Middle_bar_mode` | `beat` | `+6.71` | `+1.44` | **`+11.78`** | `+0.00` | 🔧 Pre-Batch 2 redesign (`target_width` currently scaled by `0.45 + 0.95 * v_center`) |
| `Shining_stars_mode` | `transient` | `+4.66` | `-0.07` | `+2.58` | `+0.17` | 🔧 Band-energy fallback `(1.0 - 0.6 * lock) * band_val * threshold * 2.8` stays above `current_threshold` even when locked (and `beat` mute forcing `salience = 1.0` shifted `lock` from `0.819` to `1.000`; resolved in [`2026-10-28_choreography_corrections.md`](2026-10-28_choreography_corrections.md)) |
| `Proportion_rainbow_mode` | `spectrum` | **`+10.35`** | `+1.58` | `+8.53` | `+0.00` | 🔧 Same R6 brightness multiplier (`0.40*energy + 0.60*pulse`) competing with `band_proportion` zone widths |
| `Opposite_sides_mode` | `spectrum` | `+2.61` | `+0.15` | **`+31.42`** | `+0.00` | ✅ Conforms (`spectrum` strongly dominant at `+31.42`) |
| `Hyper_strobe_mode` | `transient` | `+0.00` | `+0.00` | `+0.00` | **`+39.82`** | ✅ Conforms (100% pure `transient` lead) |
| `Chromatic_chaser_mode` | `beat` | `-0.01` | `+0.00` | `-1.04` | `+0.00` | 🔧 Pre-Batch 3 redesign (currently sweeps at constant BPM-scaled speed without reading `beat_phase` or `energy`) |
| `Metronome_mode` | `beat` | **`+28.87`** | `-0.58` | `+0.00` | `+0.00` | ✅ Conforms (98.4% `beat` lead) |
| `Coloured_middle_wave_mode` | `spectrum` | `+0.07` | `+0.19` | **`+21.69`** | `+0.00` | ✅ Conforms (69.5% `spectrum` lead) |
| `Impact_shockwave_mode` | `transient` | `+0.06` | `+0.00` | `+0.00` | `+0.00` | 🔧 Redundant `is_beat or is_real_beat or phase_wrapped` OR-gate (muting both `beat` and `transient` drops `R_std` from `34.29` to `0.00`) |
| `Power_bar_mode` | `level` | `+7.79` | **`+11.27`** | `-0.13` | `-0.02` | ✅ Conforms (`level` lead `+11.27`, `beat` secondary `+7.79`) |
| `Extending_waves_mode` | `level` | `+0.00` | `+0.00` | `+0.00` | `+0.00` | 🔧 Pre-Batch 4 redesign (currently spawns discrete pulses on `is_beat or phase_wrapped` instead of continuous `level` fountain) |

### 2.3 Calibrated Phase 4b Thresholds (`f` and `g`)
- **`CALIBRATED_LEAD_FRACTION_F = 0.30`**: Muting `LEAD` reduces audio-driven temporal standard deviation (`R_std(full) - R_std(mute_all)`) by at least `30%`, and `Δ(LEAD) == max_d Δ(d)`.
- **`CALIBRATED_SEC_RETAINED_G = 0.65`**: Muting `SECONDARY` retains at least `65%` of `R_std(full)`.

---

## 3. Non-Obvious Technical Findings

1. **Neutral `beat_phase` freeze point (`0.38`) and `beat_trust = 1.0` on `beat` mute:**
   - In [`modes/Mode.py`](../modes/Mode.py) (`beat_pulse()`), `rhythmic = (1 - phase) ** effective_sharpness` and `return confidence * rhythmic + (1 - confidence) * acoustic`.
   - If `beat_phase` is frozen at whatever phase the warm-up happened to end on (e.g., `0.032` near the beat peak), `beat_pulse()` is pinned near `0.95` (almost 3× its cycle average), artificially amplifying any signal multiplied by `beat_pulse()`. Freezing `_frozen_beat_phase = 0.38` (where `(1 - 0.38) ** 2.2 ≈ 0.35`, the exact cycle mean) and setting `beat_trust = 1.0` when `"beat"` is muted keeps modes 100% on their rhythmic branch at the neutral cycle mean without leaking `(1 - confidence) * acoustic` (`level`).
2. **How `Mode.drop_hit` and `Mode.drop_decay` are neutralized without touching `Mode.py`:**
   - `Mode.drop_hit` reads `bool(self.listener.context.is_drop_impact)` and `Mode.drop_decay` reads `self.listener.context.drop_progress`. `_ContextMuteProxy.is_drop_impact` returns `False` when `"transient"` is muted, and `_ContextMuteProxy.drop_progress` returns `0.0` when `"macro"` is muted.
3. **Dual trigger in `Impact_shockwave_mode` and band-energy leak in `Shining_stars_mode`:**
   - `Impact_shockwave_mode` gates ring spawns on `drop_hit or (is_beat and ...) or (phase_wrapped and ...)`. Because `is_beat` belongs to `transient` while `beat_phase` belongs to `beat`, muting either channel alone leaves the other branch of the `or` gate firing on every beat.
   - `Shining_stars_mode` has no phase-wrap gate; instead, `drive = max(flux_val, (1.0 - 0.6 * lock) * band_val * self.threshold * 2.8)` leaves `40%` of the `2.8x` band-energy fallback active even at `lock = 1.0`, allowing loud spectral bands (`spectrum`) to keep stars lit when `band_flux` (`transient`) is muted. Both issues were resolved in [`2026-10-28_choreography_corrections.md`](2026-10-28_choreography_corrections.md).

---

## 4. Files Modified / Created / Deleted

- **Contracts & Manuals:**
  - [`docs/contracts/mode_contract.md`](../docs/contracts/mode_contract.md) (Added Law 7: One Lead Timescale)
  - [`docs/manuals/mode_authoring_guide.md`](../docs/manuals/mode_authoring_guide.md) (Added Section 0: Four-Question Worksheet)
  - [`docs/reference/modes_catalog.md`](../docs/reference/modes_catalog.md) (Updated to 13 active modes with `Lead` and `Secondary` columns)
  - [`docs/manuals/developer_tools.md`](../docs/manuals/developer_tools.md) (Documented Mode Studio `[Ctrl+B/L/S/T/M]` / `[Ctrl+0]` choreography mute toggles)
  - [`README.md`](../README.md), [`docs/README.md`](../docs/README.md), [`docs/architecture/system_overview.md`](../docs/architecture/system_overview.md), [`docs/contracts/README.md`](../docs/contracts/README.md), [`docs/architecture/audio_pipeline.md`](../docs/architecture/audio_pipeline.md), [`docs/contracts/transition_contract.md`](../docs/contracts/transition_contract.md)
- **Choreography Infrastructure & Tools:**
  - [`utils/choreography.py`](../utils/choreography.py), [`utils/driver_mute.py`](../utils/driver_mute.py), [`tools/studio_mutes.py`](../tools/studio_mutes.py), [`tools/choreography_matrix.py`](../tools/choreography_matrix.py) (Created `DRIVERS`, `MUTE_CHANNELS`, `DriverMuteProxy`, `ContextMuteProxy`, `compute_response_metrics`, `measure_all_registered_modes`)
  - [`tools/mode_studio.py`](../tools/mode_studio.py) (Integrated `DriverMuteProxy`, HUD choreography line, and `[Ctrl+B/L/S/T/M]` / `[Ctrl+0]` mute keys)
- **Active Modes (13 annotated with `LEAD`, `SECONDARY`, and `Lead:` docstring) & Retired Modes (8 deleted):**
  - Annotated: `Rainbow_mode.py`, `Bary_rainbow_mode.py`, `Middle_bar_mode.py`, `Shining_stars_mode.py`, `Proportion_rainbow_mode.py`, `Opposite_sides_mode.py`, `Hyper_strobe_mode.py`, `Chromatic_chaser_mode.py`, `Metronome_mode.py`, `Coloured_middle_wave_mode.py`, `Impact_shockwave_mode.py`, `Power_bar_mode.py`, `Extending_waves_mode.py`
  - Deleted (`git rm`): `PSG_mode.py`, `Plasma_fire_mode.py`, `Flying_ball_mode.py`, `Synesthesia_mode.py`, `Magnetic_ball_mode.py`, `Beat_runner_mode.py`, `Rhythm_breather_mode.py`, `Static_wave_mode.py`
  - Registry & DNA: [`config/modes.json`](../config/modes.json), [`transitions/mode_dna.py`](../transitions/mode_dna.py), [`core/Segment.py`](../core/Segment.py)
- **Skills & Governance Tests:**
  - [`.agents/skills/vialactee-mode-creator/SKILL.md`](../.agents/skills/vialactee-mode-creator/SKILL.md) & [`examples/boilerplate_mode.py`](../.agents/skills/vialactee-mode-creator/examples/boilerplate_mode.py)
  - [`tests/governance/test_mode_choreography.py`](../tests/governance/test_mode_choreography.py) (Created: rules 1–4 governance + proxy coverage/mute unit tests + 13 × 4 stimulus test)
  - [`tests/governance/test_docs_parity.py`](../tests/governance/test_docs_parity.py)

---

## 5. Verification

- `.venv\Scripts\python.exe -m pytest -q tests/governance/` $\to$ **`47 passed in 7.81s`**
- `.venv\Scripts\python.exe -m pytest -q tests/governance/ tests/transitions/ tests/test_all_modes_musical_context.py tests/test_mode_helpers.py tests/test_mood_and_transitions.py` $\to$ **all passed**
- `.venv\Scripts\python.exe -m tools.choreography_matrix` $\to$ **13 × 4 matrix & ablation table generated cleanly (`exit code 0`)**

---

## 6. Open Items & Next Steps

1. **Execute Redesign Batches 1–5** per the updated roadmap:
   - **Batch 1 (`Rainbow`, `Bary Rainbow`, `Proportion Rainbow`):** Remove competing `beat` multiplier on `Rainbow` and `Proportion Rainbow` brightness (fixing R6) and upgrade to 16 Mel bands.
   - **Batch 2 (`Middle Bar`, `Opposite Sides`, `Power Bar`):** Fuse `Middle Bar` with `Static Wave` + pure white caps (`beat` lead), lock `Opposite Sides` center (`spectrum` lead + `transient` collision spark).
   - **Batch 3 (`Chromatic Chaser`):** Implement twin-runner center collision (`beat` lead + `level` spark size).
   - **Batch 4 (`Impact Shockwave`, `Extending Waves`, `Coloured Middle Wave`):** Implement continuous center-outward color fountain in `Extending Waves` (`level` lead + `beat` secondary). (`Impact Shockwave` and `Shining Stars` were promoted to `CONFORMING_MODES_PHASE_4A` in [`2026-10-28_choreography_corrections.md`](2026-10-28_choreography_corrections.md).)
2. **Phase 4b Promotion:** Add each redesigned mode to `CONFORMING_MODES_PHASE_4A` in [`tests/governance/test_mode_choreography.py`](../tests/governance/test_mode_choreography.py) as each batch lands until all 13 modes are enforced as hard CI checks.
