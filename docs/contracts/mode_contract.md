# Mode Sector Contract & Architectural Rules (`modes/`)

> **Location:** `docs/contracts/mode_contract.md` (Tier 1 Canonical Specification — Sealed Sector Contract)  
> **Scope:** Every visual mode in [`modes/`](../../modes/) (and its base class [`modes/Mode.py`](../../modes/Mode.py)).  
> **Authoring Tutorial:** [`docs/manuals/mode_authoring_guide.md`](../manuals/mode_authoring_guide.md)  
> **Visual Catalog:** [`docs/reference/modes_catalog.md`](../reference/modes_catalog.md)  
> **Enforced by:** `tests/test_all_modes_musical_context.py`, `tests/test_mode_helpers.py`, `tests/test_code_governance.py`, `tests/governance/test_axiom_07_code_governance.py`.

Every mode on the chandelier is a **pure visual consumer** of the three upstream sealed sectors:
- **Music (`music/`)** — see [`docs/contracts/music_analyzer_contract.md`](./music_analyzer_contract.md)
- **Mood (`mood/`)** — see [`docs/contracts/mood_contract.md`](./mood_contract.md)
- **Transitions (`transitions/`)** — see [`docs/contracts/transition_contract.md`](./transition_contract.md)

This document defines:
1. **Part A — The Doors of `modes/`** (every input and output that crosses into or out of a mode, and how signal trust guides usage).
2. **Part B — The Architectural & Perceptual Laws** (smoothness, fallback, palette usage, and zero-allocation rendering).

---

# Part A — The Doors of `modes/`

A mode never imports from `mood.*`, `transitions.*`, `connectors.*`, or `hardware.*`, and never reaches into `music.*` internals. Everything enters through the constructor arguments and base-class attributes injected by `Segment` / `Mode_master`.

## A.1 Inputs: What Enters a Mode (`IN`)

### Door 1 — Music & Context (`self.listener` and `self.listener.context`)
Defined and trust-rated in [`docs/contracts/music_analyzer_contract.md`](./music_analyzer_contract.md) (§2). Per-signal trust (`HIGH` / `MEDIUM` / `LOW`) is stated only in [`music_analyzer_contract.md`](./music_analyzer_contract.md); trust is guidance, not a test-enforced rule.

#### Handling Signals by Trust in `modes/`

| Trust Level (from `music_analyzer_contract.md`) | How `modes/` Should Handle Signals at This Trust Level |
| :--- | :--- |
| 🟢 **HIGH** | **Use directly every frame.** Physical energy, 8-band spectrum, pitch, spectral shape, silence, and rhythmic salience are continuous and reliable even when beat tracking fails. |
| 🟡 **MEDIUM** | **Always blend or gate with confidence (`self.rhythm_lock` or `self.beat_pulse()`).** Tempo and beat phase can drift on ambient, vocal, or polyrhythmic passages. Never write a mode that freezes, goes dark, or teleports when `beat_trust == 0.0`. Always blend rhythmic drive with a `HIGH`-trust continuous fallback (`energy`, `band_energy`, `free_phase`). |
| 🟠 **LOW** | **Avoid reading directly in concrete modes.** Heuristic scene labels (`scene`), buildup countdowns (`is_drop_imminent`, `drop_countdown`), and structural boundary flags (`is_song_change`, `is_verse_chorus_change`, `is_structural_cut`) are noisy by nature and are already absorbed upstream by `mood/` (`2.5s` cosine crossfade + `0.30s` debounce) and `transitions/`. Modes should consume the resulting smoothed `self.mood_*` modifiers and the two sanctioned helpers on `Mode` (`self.drop_hit`, `self.drop_decay`) documented below. |

---

### Door 2 — Mood Palette & Scene Modifiers (bound by `Mode_master` from `mood.api`)
Defined in [`docs/contracts/mood_contract.md`](./mood_contract.md). `Mode_master` binds shared read-only buffers onto `Mode` (`Mode._mood_colors` and `Mode._mood_modifiers`) and updates them in place once per frame:

| Property on `self` | Type / Shape | Range | Trust | Purpose |
| :--- | :--- | :--- | :---: | :--- |
| `self.mood_colors` | `np.ndarray (4, 3)` `int32` | `0..255` | 🟢 **HIGH** | `[0]` Primary, `[1]` Secondary, `[2]` Accent, `[3]` Background / Highlight. Smoothly crossfaded over `2.5s`. |
| `self.palette_lut` | `np.ndarray (256, 3)` `int32` | `0..255` | 🟢 **HIGH** | Shared 256-entry gradient `mood_colors[0] -> [1] -> [2]`, refreshed in place only when `mood_colors` changes. |
| `self.palette_sample(t, out)` | method | `t in [0, 1]` | 🟢 **HIGH** | Allocation-free vectorized lookup into `self.palette_lut`. |
| `self.highlight_color` | `np.ndarray (3,)` `int32` | `0..255` | 🟢 **HIGH** | Luminance-safe flash color (brightest slot of `mood_colors` pushed 40% toward white). |
| `self.mood_pace` | `float` | `[0.82, 1.22]` | 🟢 **HIGH** | Continuous speed / drift multiplier (`0.82` in `CHILL`, `1.00` in `GROOVE`, `1.12` in `BUILDUP`, `1.22` in `DROP_IMPACT`). |
| `self.mood_sharpness` | `float` | `[0.78, 1.22]` | 🟢 **HIGH** | Beat envelope exponent multiplier (`0.78` in `CHILL`, `1.00` in `GROOVE`, `1.12` in `BUILDUP`, `1.22` in `DROP_IMPACT`). |
| `self.mood_trail` | `float` | `[0.88, 1.18]` | 🟢 **HIGH** | Persistence / decay length multiplier (`1.18` in `CHILL`, `1.00` in `GROOVE`, `0.92` in `BUILDUP`, `0.88` in `DROP_IMPACT`). |
| `self.mood_accent` | `float` | `[0.00, 0.28]` | 🟢 **HIGH** | Blend weight toward `self.highlight_color` / `mood_colors[2]` (`0.00` in `CHILL`, `0.05` in `GROOVE`, `0.15` in `BUILDUP`, `0.28` in `DROP_IMPACT`). |

---

### Door 3 — Transition Handshake Hooks (bound by `Segment` from `transitions.api`)
Defined in [`docs/contracts/transition_contract.md`](./transition_contract.md):

| Property / Hook on `self` | Type | Range | Purpose |
| :--- | :--- | :--- | :--- |
| `self._exit_progress` | `float` | `[0.0, 1.0]` | `0.0` in normal steady-state rendering; rises `0.0 -> 1.0` when the mode is being transitioned out under `mode_handshake=True`. |
| `self._enter_progress` | `float` | `[0.0, 1.0]` | `1.0` in normal steady-state rendering; rises `0.0 -> 1.0` when the mode is entering under `mode_handshake=True`. |
| `self.transition_scale` | `float` | `[0.0, 1.0]` | Combined energy/envelope scale factor during cooperative exit/enter (`1.0` outside transitions). Automatically applied inside `smooth_vectorized` and `fade_to_black`. |
| `self.on_transition_exit(progress)` | method | `0.0..1.0` | Called by `Segment` each frame while exiting in cooperative handshake mode. |
| `self.on_transition_enter(progress)` | method | `0.0..1.0` | Called by `Segment` each frame while entering in cooperative handshake mode. |
| `self.on_transition_reset()` | method | — | Resets `_exit_progress = 0.0`, `_enter_progress = 1.0`. |

---

### Door 4 — Sanctioned Gated Helpers on `Mode`
The base class [`modes/Mode.py`](../../modes/Mode.py) provides pre-gated helpers so individual modes never need raw scene branching or ad-hoc confidence math:

| Helper on `self` | Signature / Type | Range | What It Computes |
| :--- | :--- | :--- | :--- |
| `self.dt` | `float` | `> 0.0` | Seconds since previous frame (falls back to `1/60`). |
| `self.fps_ratio` | `float` | `~1.0..2.0` | `self.dt * 60.0` (`1.0` at 60 Hz, `2.0` at 30 FPS). |
| `self.alpha(rate_hz)` | `float` | `[0.0, 1.0]` | Frame-rate independent exponential smoothing factor $1 - e^{-\text{dt} \cdot \text{rate\_hz}}$. |
| `self.rhythm_lock` | `float` | `[0.0, 1.0]` | `beat_trust * (0.4 + 0.6 * rhythm_salience)`. Smoothly blends from `0.0` (ambient/unlocked) to `1.0` (locked percussive groove). |
| `self.beat_pulse(sharpness=2.2)` | `float` | `[0.0, 1.0]` | Confidence-blended beat envelope: blends a sharp `(1 - beat_phase) ** (sharpness * mood_sharpness + 1.2 * tension)` pump with continuous `energy` breathing when `beat_trust` is low. Returns `0.0` in silence. |
| `self.drop_hit` | `bool` | `True` / `False` | **Sanctioned 1-frame trigger:** `True` for **at most 1 frame** when a drop lands (`ctx.is_drop_impact`). Safe for spawning a wave/particle or giving a physics velocity kick. Never stays `True` across frames. |
| `self.drop_decay` | `float` | `[0.0, 1.0]` | **Sanctioned drop envelope:** Smoothly decays `1.0 -> 0.0` across the `DROP_IMPACT` dwell (`0.0` outside a drop). Safe for continuous modulation (never for hard branches or full-strip whiteouts). |
| `self.segment_phase_offset` | `float` | `[0.0, 1.0)` | Stable per-segment phase offset to stagger identical modes across the chandelier. |

---

## A.2 Outputs: What Leaves a Mode (`OUT`)

1. **Pixel Buffer (`self.rgb_list` / `buffer`):**
   - `render(self, buffer=None, audio_ctx=None, frame_info=None)` or `run(self)` mutates `self.rgb_list` (shape `(nb_of_leds, 3)`, `dtype=np.int32`, values `0..255`) **in place**.
2. **Settings Schema (`get_settings_schema(self) -> List[Dict[str, Any]]`):**
   - Declares live-tunable parameters exposed to the Web UI and Mode Studio (`key`, `label`, `valueType`, `default`, `min`/`max`/`step` or `options`, `attr`).
   - Every declared setting **must** be read in `run()` / `render()`.

---

## A.3 Boundary Invariants

- **Forbidden imports in `modes/*.py`:** `mood.*`, `transitions.*`, `connectors.*`, `hardware.*`, `core.*`. Only `music.api` (if needed for constants), `modes.Mode`, `utils.*`, `numpy`, and the Python standard library may be imported.
- **No direct `context.scene` branching in concrete modes:** Concrete modes (`modes/*_mode.py`) should not read `ctx.scene` or branch on `"CHILL" | "GROOVE" | "BUILDUP" | "DROP_IMPACT"`. Only the two base-class helpers `Mode.drop_hit` and `Mode.drop_decay` in `modes/Mode.py` touch the drop arrival/envelope state.

---

# Part B — Architectural & Perceptual Laws

### 1. Always Alive Without the Flywheel (`rhythm_lock == 0`) — and Rhythm-Locked When Confident (`rhythm_lock -> 1`)
Every mode must satisfy **both** halves of the confidence blend:
- **Fallback half (`rhythm_lock == 0.0`):** When `beat_trust == 0.0` and `rhythm_salience == 0.0` (ambient intros, vocal bridges, classical, breakdowns, or before the beat tracker locks), the mode must still produce a smooth, musical animation driven by continuous acoustic signals (`energy`, `power`, `asserved_fft_band`, `band_flux`, `spectral_tilt`, `vertical_center`, `smoothed_chroma_values`, or a slow free-running phase). **No mode may freeze, go dark, or depend solely on `is_beat` / `beat_phase` to emit light.**
- **Rhythm-locked half (`rhythm_lock -> 1.0`):** When a clear beat is present (`beat_trust` and `rhythm_salience` are high), the **same** visual algorithm must lock to the beat (`beat_phase`, `bpm`, `is_beat` gated by `is_real_beat`, `self.beat_pulse()`).
- **Blend, don't switch:** Combine both with `lock = self.rhythm_lock` or `self.beat_pulse(sharpness)`:
  ```python
  lock = self.rhythm_lock
  drive = lock * rhythmic_term + (1.0 - lock) * acoustic_term
  ```
- **Silence:** Only when `ctx.is_silent` is `True` should a mode fade smoothly toward black (`fade_to_black_segment_vectorized`), never via an instant cut (`rgb_list.fill(0)` without smoothing).

---

### 2. Subtle Mood Governance (No `if ctx.scene == ...` Branching in Modes)
Macro scenes (`CHILL`, `GROOVE`, `BUILDUP`, `DROP_IMPACT`) are **already handled upstream** by the sealed `mood/` sector (`mood/scene_policy.py` + `mood/engine.py` + `mood/service.py`):
- `mood/` debounces scene changes (`0.30s`), selects a curated palette, and crossfades `Mode.mood_colors` over `2.5s` (cosine easing).
- `mood/` also exposes four **continuous, cosine-smoothed scene modifiers** on `Mode` (`self.mood_pace`, `self.mood_sharpness`, `self.mood_trail`, `self.mood_accent`).

**Rules for modes:**
1. **Do NOT branch on `ctx.scene` in modes.** Never write `if scene == "CHILL": ... elif scene == "BUILDUP": ... elif scene == "DROP_IMPACT": ...` inside `modes/*_mode.py`.
2. **Why:** `DROP_IMPACT` is a **1.5-second scene dwell**, not a single frame. Any `if scene == "DROP_IMPACT": flash_white()` or `spawn_wave()` fires for **90 consecutive frames**, turning the chandelier into a frozen white bar or flooding wave pools. And raw `if scene == "CHILL"` branches snap parameters on a single frame whenever the classifier flickers.
3. **How to react to mood instead:** Multiply speeds by `self.mood_pace`, fade/damping lengths by `self.mood_trail`, and accent color mixes by `self.mood_accent`. Because `mood/` crossfades these over `2.5s`, the visual character evolves organically with zero code branches in the mode.

---

### 3. Beat & Drop Coupling (1-Frame Transients vs Envelopes)
- **Hard flashes / strobes / wave spawns** must fire on **1-frame events only**:
  - A verified acoustic beat: `is_beat and is_real_beat and beat_trust > 0.4` (or debounced `beat_phase` wrap when `is_locked`), **or**
  - The 1-frame drop arrival helper: `self.drop_hit`, **or**
  - A real spectral onset peak (`band_flux` above threshold) when the beat tracker is unlocked.
- **Never** hold a full-strip flash for the duration of `DROP_IMPACT`. If a mode wants extra energy after a drop lands, modulate amplitude gently with `self.drop_decay` (at most `+20..30%` boost, decaying smoothly to `0`).

---

### 4. Palette Usage (`mood_colors`, `palette_lut`, `highlight_color`)
- Modes using `"mood"` color mode should draw from `self.mood_colors`, `self.palette_lut` / `self.palette_sample(t, out)`, and `self.highlight_color`.
- **Do not assume `mood_colors[3]` is bright.** Slot 3 is `Background / Highlight` and is intentionally near-black on dark palettes (e.g. *Deep Ocean* `(0, 30, 60)`). For flashes, sparks, or peak dots, always use `self.highlight_color` (which picks the brightest palette slot and lifts it toward white).
- When mapping 8 frequency bands (`0..7`) to colors in `"mood"` mode, sample across the 256-entry gradient (`self.palette_lut[int(b * 255 / 7)]`) rather than `mood_colors[b % 4]` (which collapses 8 bands onto 4 colors and hides bands landing on dark slot 3).

---

### 5. Settings Schema Honesty
Every setting declared in `get_settings_schema()` (and exposed in the Web UI / Mode Studio) **must actually be read and used in `run()`** (enforced by `tests/test_mode_helpers.py::TestDeadSettingsRatchet`). Do not leave dead schema entries whose `self.<attr>` is ignored at render time.

---

### 6. Frame Budget & Zero Allocation (AXIOM-01, AXIOM-02)
- Pre-allocate all scratch arrays (`np.zeros`, `np.empty`, `np.linspace`, `np.arange`) in `__init__`.
- Never allocate NumPy arrays or Python lists inside `run()` / `render()`.
- **Never cache views of `self.rgb_list` in `__init__`**: during dual-mode transitions, `Mode.render(buffer=...)` temporarily redirects `self.rgb_list` to `Segment.dual_rgb_list`. Any view cached on `self.rgb_list` during `__init__` would write to the wrong buffer during transitions.
- Frame-rate independence: scale per-frame increments and exponential decays with `self.dt`, `self.fps_ratio`, or `self.alpha(rate_hz)`.
