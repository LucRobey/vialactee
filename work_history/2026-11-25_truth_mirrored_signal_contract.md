# 2026-11-25 Truth-Mirrored Signal Contract for the Analyzer

> **Date:** 2026-11-25  
> **Session ID:** `71d81268-3807-434b-a0b6-70555148b388`  
> **Agent / Model:** Claude Fable 5.2  
> **Primary Goal:** Give the audio analyzer a contract that looks exactly like the source of truth: one slot per truth value, present even when nothing produces it yet, so that we know what to test before testing.  
> **Status:** COMPLETED (contract, code slots, signal list and parity tests in place; the scoreboard against the truth is the next step)  
> **Commits:** `f3b0ee0` (pushed: yes)  
> **Skills Used:** none  
> **Skill Friction:** `vialactee-dsp-engine`: does not mention a truth to grade against; it will need a section on `listener.signals` once a slot is produced by a model.

---

## 1. Context & Motivation

* The owner declared the 20 truth drafts in `research/truth/` the full ground truth (the list of variables is closed) and asked that, before any measurement, the analyzer contract mirror it: every truth variable has its place in the analyzer, returning null for now where the analyzer cannot produce it.
* Earlier owner ruling kept: the signal list is a data file outside `music/`; trust is set by the owner only, in the contract document.

---

## 2. Changes Made

### Music sector (sealed, `music/`)
* **[NEW]** [`music/MusicSignals.py`](../music/MusicSignals.py): the record `MusicSignals`, 36 slots (`FIELDS`), all `None` until produced; `BRIDGED` names the 8 slots that an existing signal already expresses; `clear()`, `as_dict()`.
* **[MODIFY]** [`music/BaseAudioAnalyzer.py`](../music/BaseAudioAnalyzer.py): every analyzer owns `self.signals`. A model fills a slot by writing `self.signals.<name>` (value at speaker time) in its `update()`.
* **[MODIFY]** [`music/Listener.py`](../music/Listener.py): `listener.signals` is the analyzer's record; `_bridge_signals()` fills the 8 bridged slots after the context update (`beat`, `bpm`, `drop`, `section_change`, `buildup`, `silence`, `loudness`, `brightness`); `reset()` clears the record. 412 to 433 lines.
* **[MODIFY]** [`music/api.py`](../music/api.py): exports `MusicSignals`. `ListenerProtocol` is unchanged on purpose: modes do not read the record yet.

### Contract
* **[NEW]** [`config/music_signals.json`](../config/music_signals.json): the machine-readable list. Per slot: group, kind (event / state / value), type, range, meaning, the truth value it is graded against, how it is graded, status (bridged / empty) and source.
* **[MODIFY]** [`docs/contracts/music_analyzer_contract.md`](../docs/contracts/music_analyzer_contract.md): wall rule 5, door 7, exported symbol, `signals` among the `Listener` attributes, and the new section 6 (rules and one row per slot, generated from the JSON).
* **[MODIFY]** [`docs/architecture/audio_pipeline.md`](../docs/architecture/audio_pipeline.md): module table row for `MusicSignals.py`.

### Tests
* **[NEW]** [`tests/governance/test_music_signals_contract.py`](../tests/governance/test_music_signals_contract.py): record slots, JSON list and contract rows are identical and in the same order; bridged slots point at real signals; an empty record answers `None` everywhere and cannot grow; `Listener` fills only the bridged slots, for the three registered analyzers; a slot written by the analyzer is seen through the `Listener`.
* **[NEW]** [`research/tests/test_truth_contract_parity.py`](../research/tests/test_truth_contract_parity.py): on all 20 truth files, the contract and the truth hold the same values in both directions; the eight truth fields that are bookkeeping are listed with their reason.

---

## 3. Verification & Testing

* **Command**: `python -m pytest -q`
  * **Result**: 654 passed, 5 deselected, 406 subtests passed (44 s). Before this session: 644.
* After 5 ticks of a `Listener` without microphone, the record holds the 8 bridged values and `None` in the 28 other slots.

---

## 4. Architecture Decisions & Trade-offs

* **One record, not 36 properties.** `Listener.py` is at 433 lines under a 500-line cap; 36 properties would not fit and would touch `ListenerProtocol`, the mute proxy and the synthetic listener. One attribute, `listener.signals`, adds a single name to the public surface.
* **`None`, not `False`, for an empty slot.** `False` would be a claim ("there is no kick"). `None` says the analyzer does not know, and is still falsy for a careless reader.
* **Speaker time is the analyzer's job for the slots it fills.** The analyzer already emits `is_beat` at speaker time by back-projection; the same rule applies to every slot, so `Listener` needs no extra delay line per signal.
* **Bridging 8 slots now.** Where a signal already means the same thing (`is_beat`, `bpm`, `is_drop_impact`, `is_verse_chorus_change`, `is_buildup`, `is_silent`, `asserved_total_power`, `vertical_center`), the slot copies it. The copy is not a claim of quality: no slot is rated, and the scoreboard will say how good each one is.
* **Not bridged although related:** `beat_tag` (kick / snare / hat, on beats only), `is_locked` and `beat_trust` (near the opposite of `no_beat`), the 16-band spectrum (finer than the four truth bands). The scoreboard can test them as candidates for the empty slots.

---

## 5. Pitfalls & Lessons Learned

* `BaseAudioAnalyzer` already carried unused defaults of the same spirit (`is_downbeat`, `bar_phase`, `time_signature`, `vocals_present`, `musical_key`, ...). They are left in place; the record supersedes them and they can be removed once nothing reads them.
* Grading tolerances written in the signal list (50 ms, one beat, one bar, 4% of tempo) are proposals, not owner decisions.
* Truth levels and live values use different units (dB against 0..1): levels are graded on shape and delay, not on absolute value.

---

## 6. Open Items & Next Steps

* [ ] Build the scoreboard: run the production `Listener` (5 s look-ahead) on the 20 tracks and grade every slot against its truth value, marking which lines rest on truth that may grade (H, A, M2, X) and which are provisional.
* [ ] In the scoreboard, also try the related existing signals (`beat_tag`, `is_locked`, band groups) as candidates for empty slots.
* [ ] Owner: review by ear in the review tool; answers on papers P2 to P4; techno tracks to add; held-out list.
* [ ] Fold this section into the P2 paper when it is revised.
