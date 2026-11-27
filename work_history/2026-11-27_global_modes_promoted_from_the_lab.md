# [2026-11-27] Four lab Global Modes added to the installation

> **Date:** 2026-11-27  
> **Session ID:** lab agent (same session as the C10 to C12 cycles)  
> **Agent / Model:** Claude Opus 5.5  
> **Primary Goal:** Owner's request ("add them to our real system"): register the four lab copies of Global Modes on the installation.  
> **Status:** COMPLETED  
> **Commits:** none (the supervisor commits)  
> **Skills Used:** `vialactee-mode-creator`  
> **Skill Friction:** the mode-creator skill describes standard modes; global modes have no catalog to update, and their tests live in `tests/test_global_modes.py`.

---

## 1. Context & Motivation

* The owner asked to add the lab modes of C10, C11 and C12 to the real system. They had not yet watched the 12 queued clips: this is the owner's call, made before the blind comparison.

## 2. Changes Made

### Modes
* **[NEW]** `modes/Beat_blast_kick_mode.py`, `modes/Ripple_kick_mode.py`, `modes/Band_vu_mode.py`, `modes/Avalanche_bands_mode.py`: copies of the lab modes of `research/choreography/candidates/` with a header that points back to the lab, and `get_settings_schema()` for the settings they already read (`wave_speed`, `wave_width`; `ring_speed`; `gravity`; Band VU has none).
* `Avalanche_bands_mode` is declared `LEAD = "transient"`, `SECONDARY = ("spectrum",)` on the installation (the lab copy says spectrum / transient): the driver mute measurement gives transient 6.04 against spectrum 2.87.
* **[MODIFY]** `config/modes.json`: four entries at the end of `global_modes` ("Beat Blast Kick", "Ripple Kick", "Band VU", "Avalanche Bands") with `dna` and tags. The originals are unchanged.

### Driver mute
* **[MODIFY]** `utils/driver_mute.py`: `DriverMuteProxy.signals` returns a `SignalsMuteProxy`: hits read as no hit when `transient` is muted, the band levels as 0.5 when `spectrum` is muted, loudness and instrument levels as 0.5 when `level` is muted; states pass through; a listener without `signals` gives None (the mode falls back). These are the first modes of `modes/` to read `listener.signals`.

### Tests
* **[MODIFY]** `tests/test_global_modes.py`: the four modes added to `GLOBAL_MODE_SPECS` (roles, silence, frame budget and zero allocation, Law 7 lead dominance, settings honesty, panel picks); the panel test no longer names the last mode of the list.

## 3. Verification & Testing

* `.venv/Scripts/python.exe -m pytest -q tests/test_global_modes.py` → 7 passed, 108 subtests passed (first run: Avalanche Bands lead was not spectrum; the panel test named Spectral Avalanche).
* `.venv/Scripts/python.exe -m pytest -q` → 829 passed, 5 deselected, 460 subtests passed.
* `.venv/Scripts/python.exe -m pytest -q research/tests tests/governance` → 231 passed, 140 subtests passed.
* Not verified: on the Raspberry Pi (frame cost measured on this PC only), on the real installation, and by the owner's eye.

## 4. Architecture Decisions & Trade-offs

* Added next to the originals, not instead of them: the owner can pick either, and compare.
* The lab copies stay unchanged in `candidates/`: their gates and the queued clips were measured on that code. The installation copies are now separate; a change to one is not a change to the other.

## 5. Pitfalls & Lessons Learned

* `research.guard check choreography` now names files outside the lab (`modes/`, `config/`, `utils/`, `tests/`): expected, this was not lab work.
* Other uncommitted changes were in the tree before this work (`config/Configuration_manager.py`, `config/app_config.json`, `docs/reference/configuration_schemas.md`, `tests/test_audio_presets.py`); they are not part of it.

## 6. Open Items & Next Steps

* [ ] The owner watches the queued clips; a mode the owner does not like can be removed from `config/modes.json`.
* [ ] The owner answers whether `Spectral_avalanche_mode` (19.5 flashes a second in the lab's gate) and `Monolithic_beat_blast_mode` (3.5) should be fixed or retired.
* [ ] A frame-cost check on the Raspberry Pi.
