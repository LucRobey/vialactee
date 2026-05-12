# Vialactée — Inter-Review Changelog

This file tracks **what has been done between reviews**.
Update it as you work. The next review agent will read this to know what changed.

**How to use:**
- Mark items `[x]` when done, add the date in parentheses.
- Add new entries under the current period with `[+]` for new features, `[~]` for refactors.
- When a new review is run, move the current period to the archive at the bottom.

---

## 🟢 Current Period: after 2026-05-12 reviews

### Code Fixes (from `2026-05-12_code_review.md`)

#### 🔴 High Priority
- [ ] **`is_song_change` never resets** — add `self.is_song_change = False` at top of `detect_band_peaks()` in `AudioAnalyzer.py`
- [ ] **Threading lock on `audio_data`** — add `threading.Lock` in `Local_Microphone.py` around `np.roll` + read in `listen()`
- [ ] **WebSocket reconnection** — add exponential-backoff reconnect in `controlBridge.ts`
- [ ] **`spatial_images` module-level I/O** — wrap in `try/except` in `Transition_Engine.py` to prevent import failure

#### 🟡 Medium Priority
- [ ] **Vectorize `update_leds`** in `Segment.py` — replace Python loop with numpy slice assignment
- [ ] **Vectorize `asserv_fft_bands`** in `AudioIngestion.py` — replace `for` loop with `np.where`
- [ ] **Vectorize `asserv_total_power`** — replace accumulator loop with `np.sum`
- [ ] **Load simulator geometry from `segments.json`** instead of hardcoding in `Fake_leds.py`
- [ ] **Add `requirements.txt`** — list `numpy`, `sounddevice`, `aiohttp`/`websockets`, `pygame`, etc.

#### 🟢 Low Priority
- [ ] **Remove duplicate JSON write** at end of `test_runner.py`
- [ ] **Remove dead `apply_fake_fft` `fft_bary`** computation — dead code in simulation path
- [ ] **Remove `hasattr` guards on `chroma_values`** — initialize unconditionally in `AudioIngestion.__init__`
- [ ] **Run `nbstripout`** on playground notebooks before next commit
- [ ] **Remove unreachable `self.is_in_transition = False`** in `execute_mode_swap` in `Segment.py`
- [ ] **Unify mode list** between `wabb-interface/src/constants/modes.ts` and `config/modes.json`

---

### Docs Fixes (from `2026-05-12_docs_review.md`)

#### 🔴 Critical
- [ ] **Resolve `evaluate_context()` vs `update()` contradiction** — verify in `Transition_Director.py`, fix `core/README.md` and `transition_director.md`
- [ ] **Retitle or tombstone `.agents/PLAN.md`** — convert future-tense to past-tense or delete
- [ ] **Delete duplicate hardware Mermaid diagram** from `hardware/README.md`; link to `PLAN.md` instead
- [ ] **Fix Acoustic Breakdown Python-comment artifact** in `music_events_architecture.md` (`# ===` → `###`)
- [ ] **Document `app_config.json` schema** in `config/README.md` — add full key/type/default/description table

#### 🟡 High
- [ ] **Add orientation column** to `modes/modes_description.md` (horizontal / vertical / both per mode)
- [ ] **Expand `modes/README.md`** — add `run()` vs `update()` distinction, `infos` injection, `rgb_list` structure
- [ ] **Fix double `## 3.` heading** in `music_events_architecture.md`
- [ ] **Correct `AGENT.md` hardware section** — list all 5 files in `hardware/`, not just `Fake_leds.py`
- [ ] **Add `HARDWARE_MODE` entry** and hardware routing to `00_AGENT_NAVIGATION.md`

#### 🟢 Medium
- [ ] **Add status column** to `wabb-interface/webapp_architecture.md` (Implemented / In Progress / Planned)
- [ ] **Add `bpm_trust_architecture.md` reference** to `00_AGENT_NAVIGATION.md`
- [ ] **Clarify `data/` vs `config/` path** for `configurations.json` in `mode_master.md`
- [ ] **Add "design signatures" explanation** header to `wabb-interface/design signatures/`

---

### Web App Fixes (from `2026-05-12_webapp_review.md`)

#### HIGH
- [ ] **Add WS connection status badge** — 🟢/🔴 dot in tab bar; export `status` from `ControlBridge`
- [ ] **Replace hardcoded telemetry** — extend `ModeMasterState` with real CPU/FPS/latency from Python backend
- [ ] **Add `window.confirm` gate** on "REBOOT RASPBERRY PI" button
- [ ] **Fix segment map overflow** — add `overflow-x: auto` or fix `MAP_OFFSET_C` calculation
- [ ] **Hide/mark Stage Architect tab as WIP** until implemented

#### MEDIUM
- [ ] **Add exponential backoff** to `ControlBridge.scheduleReconnect()`
- [ ] **Fix `onerror` not nulling `this.socket`** in `controlBridge.ts`
- [ ] **Replace native `alert()` on UPD save** with inline styled notification
- [ ] **Split `TopologyEditor.tsx`** (1,183 lines) into sub-components
- [ ] **Add `direction` to segment type** in `topologyData.ts`; remove all `(seg as any).direction` casts
- [ ] **Fix `persistPlaylistStore` setState after unmount** in `TopologyEditor.tsx`

#### LOW
- [ ] **Fix junction box z-index** — raise above segments or restructure render order
- [ ] **Add `—` placeholder** for empty CONFIG field in telemetry bar
- [ ] **Fix pending edits leaking** across WS reconnects in Mode Settings
- [ ] **Remove redundant `String(currentValue)` branch** in Mode Settings (line 304)
- [ ] **Move `roguePieces` out of render** in `App.tsx`
- [ ] **Memoize junction O(n²) AABB check** with `useMemo` in `TopologyEditor.tsx`

---

### New Work (not from any review)

<!-- Add entries here as new features/refactors are done during this period -->
<!-- Format: [+] YYYY-MM-DD — Short description (file changed) -->

---

## 📦 Archive

### Period: initial setup (before 2026-05-12)
*No prior reviews — this is the first review cycle.*
