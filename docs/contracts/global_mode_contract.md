# Global Mode Sector Contract & Architectural Rules (`modes/` with `IS_GLOBAL = True`)

> **Location:** `docs/contracts/global_mode_contract.md` (Tier 1 Canonical Specification — Sealed Sector Contract)  
> **Scope:** Every global visual mode in [`modes/`](../../modes/) (and its base class [`modes/Mode.py`](../../modes/Mode.py)) orchestrating all 11 segments across the chandelier (1,304 physical LEDs) as a single physical instrument.  
> **Inheritance & Hierarchy:** Global modes inherit all foundational sector invariants from [`docs/contracts/mode_contract.md`](./mode_contract.md) while establishing global installation-wide spatial, perceptual, and performance invariants.  
> **Enforced by:** `tests/test_global_modes.py`, `tests/test_cast_modes.py`, `tests/test_ensemble_modes.py`, `tests/test_mode_helpers.py`, `tests/governance/test_axiom_01_frame_budget.py`, `tests/governance/test_axiom_02_zero_allocation.py`, `tests/governance/test_axiom_03_geometry.py`, `tests/governance/test_axiom_07_code_governance.py`, `tests/governance/test_mode_choreography.py`, `tests/governance/test_docs_parity.py`.

---

## Executive Architectural Summary & Scope

Unlike local sector modes—which execute independent visual algorithms on isolated segments—a **Global Audio Mode** (`IS_GLOBAL: bool = True`) orchestrates the entire physical installation as a unified kinetic light sculpture. 

The physical chandelier consists of **1,304 WS2812B LEDs** distributed across **11 segments** (4 vertical pillars, 4 horizontal bridges, and 3 canopy bars). Because the installation occupies a 2D room bounding box of $432 \times 246$ units with an active LED fill factor under 2%, treating the chandelier as a conventional 2D bitmap screen produces visual noise and spatial incoherence ("The Display Fallacy").

### The Three Global Mode Families (`FAMILY`)

**Global modes may be complex.** What every global mode owes the spectator is legibility, and there are three sanctioned ways to earn it. Each is a family, declared by the class attribute `FAMILY` (absent = `"field"`):

| Family | Unit of decision | Time | Space | Examples |
| :--- | :--- | :--- | :--- | :--- |
| **Field** (`"field"`) | Each LED samples one continuous function $f(x_{\text{norm}}, y_{\text{norm}}, t)$ | Continuous accumulation every frame | Room coordinates, centroid, polar | Monolithic Beat Blast, Architectural VU Equalizer, Concentric Radial Ripple, Horizon Scanning Blade, Spectral Avalanche |
| **Cast** (`"cast"`) | Each **segment is one light fixture** (on / off / colour slot) | Quantized: state changes only on musical steps (beat, bar, phrase) and is **held** in between | Architectural identity: groups, mirror pairs, floors, build order | Tableaux, Bar Clock, Construction, Flip-Flop, Negative Space, Mosaic |
| **Ensemble** (`"ensemble"`) | Each **part is an instrument with its own job** (one driver, one mechanic). Different parts may listen to different drivers | Free per part: continuous, or quantized and held | Parts: a segment, a topology group, or a section of a segment cut at an architectural landmark | Stalagmites (each bass hit throws a red bar up the inner pillars, each snare hit throws a blue bar down the outer pillars, the canopy sparkles on hi-hats) |

How each family earns legibility:
- **Field** — one metaphor, one driver, every LED in unison (Laws 7 and 8).
- **Cast** — one rule, one driver, structural groups play roles of it (Law C4).
- **Ensemble** — several jobs at once, each simple and separately readable; the complexity lives in the combination (Laws E1–E6). This is the family for multi-driver and multi-mechanic modes.

Field modes read the chandelier as a sparse surface; cast modes read it as an **11-fixture lighting rig** (a lighting console, not a video wall); ensemble modes read it as a **band of instruments**, each part playing its own line. All families obey Laws 1–10 below, except where **Part B2 — Cast Mode Laws** or **Part B3 — Ensemble Mode Laws** replaces a clause for that family. Cast modes subclass [`modes/Cast_mode_base.py`](../../modes/Cast_mode_base.py) and implement only their cast rule. Ensemble modes subclass [`modes/Ensemble_mode_base.py`](../../modes/Ensemble_mode_base.py) and implement only their parts.

> The single-driver, all-in-unison rules (Law 7 hegemony, Law 8.1–8.2) describe the **field** family. They are not a ceiling on what a global mode may do. Where the 2026-11-09 research document (`docs/research/`) states them as universal, this contract wins.

A Global Mode must resolve this physical reality by operating as a **pure visual consumer** across five sealed upstream boundaries:
1. **Music (`music/`)** — Delayed speaker-aligned audio metrics ($T_{\text{speaker}}$) per [`docs/contracts/music_analyzer_contract.md`](./music_analyzer_contract.md).
2. **Mood (`mood/`)** — Crossfaded palettes and continuous kinetics per [`docs/contracts/mood_contract.md`](./mood_contract.md).
3. **Transitions (`transitions/`)** — Cooperative dual-buffer handshakes per [`docs/contracts/transition_contract.md`](./transition_contract.md).
4. **Sanctioned Helpers (`modes/Mode.py`)** — Pre-gated confidence envelopes, timers, and transient triggers.
5. **Global Spatial Resolver (`utils/global_mode.py`)** — Pre-allocated 2D/3D room coordinates, strip-intrinsic profiles, and architectural classifications.

This contract defines:
- **Part A — The Doors of Global Modes:** Boundary definitions for every input and output crossing into or out of a global mode.
- **Part B — Architectural & Perceptual Laws:** The 10 rigid laws governing legibility, single-driver dominance, bright neon color aesthetics, flywheel fallback, and zero-churn execution.
- **Part C — Verification & Governance:** Pytest suites, memory churn harnesses, driver mute verification, and the formal 6-dimension evaluation rubric.
- **Standard Code Templates:** Compliant implementation blueprints for production global modes.

---

# Part A — The Doors of Global Modes

Global modes operate within a strict architectural sandbox. Concrete modes never import from `mood.*`, `transitions.*`, `connectors.*`, `hardware.*`, or `core.*`, and never reach into `music.*` internals. All communication passes exclusively through base class attributes and constructor arguments injected by `core/Segment.py` and `core/Mode_master.py`.

```
                  ┌──────────────────────────────────────────────┐
                  │       UPSTREAM SEALED SECTORS                │
                  │  Music / Mood / Transitions / Spatial Mesh   │
                  └──────────────────────┬───────────────────────┘
                                         │
        ┌────────────────────────────────┼────────────────────────────────┐
        ▼                                ▼                                ▼
  [ DOOR 1: MUSIC ]              [ DOOR 2: MOOD ]               [ DOOR 5: SPATIAL ]
  T_speaker stream               self.mood_colors               SegmentSpatialProfile
  31-signal dictionary           self.palette_lut               x_norm, y_norm, alt
  Signal trust levels            Continuous modifiers           Polar (r, theta)
        │                                │                                │
        └────────────────────────────────┼────────────────────────────────┘
                                         │
                                         ▼
                 ┌──────────────────────────────────────────────┐
                 │          GLOBAL MODE INSTANCE                │
                 │          IS_GLOBAL: bool = True              │
                 │  • Door 3: Cooperative Handshake Hooks       │
                 │  • Door 4: Sanctioned Gated Helpers          │
                 │  • Laws 1-10: Perceptual & Performance Laws  │
                 └──────────────────────┬───────────────────────┘
                                         │
                                         ▼
                 ┌──────────────────────────────────────────────┐
                 │       DOOR OUT: PIXEL BUFFER MUTATION        │
                 │       self.rgb_list: (nb_of_leds, 3) int32   │
                 │       In-place NumPy mutation (0..255)       │
                 └──────────────────────────────────────────────┘
```

---

## A.1 Inputs: What Enters a Global Mode (`IN`)

### Door 1 — Music & Rhythm Context (`self.listener` and `self.listener.context`)

Audio signals originate in `music/` and pass through `music/Listener.py` and `music/MusicalContextEngine.py`. 

#### The Dual Time-Horizon Invariant ($T_{\text{lookahead}}$ vs $T_{\text{speaker}}$)
The beat tracking engine employs a 5.0-second lookahead window (`fakeDelay = 5.0s`) to identify tempo and phase without causal tracking lag:
1. **Lookahead Horizon ($T_{\text{lookahead}} = t$):** Raw signals exiting the DSP front-end are prefixed with `live_*` (e.g. `live_asserved_total_power`, `live_beat_trust`, `live_is_song_change`). **Forbidden in visual modes.** Reading lookahead signals causes visual impacts to anticipate physical sounds by up to 5 seconds.
2. **Speaker Horizon ($T_{\text{speaker}} = t - 5.0\text{s}$):** Signals delayed through the circular ring buffer in `music/Listener.py`. **Mandatory for all Global Modes.** Ensures visual motion aligns with sound waves reaching spectators' ears within $< 50\text{ ms}$ (AXIOM-05).

#### The 31-Signal Audio Dictionary & Trust Levels
Signal trust ratings are defined in [`docs/contracts/music_analyzer_contract.md`](./music_analyzer_contract.md) (§2):

| Signal Name | Source Object | Data Type & Shape | Numerical Range | Trust Level | Time Horizon | Semantic Definition & Visual Role |
| :--- | :--- | :--- | :--- | :---: | :---: | :--- |
| `asserved_fft_band` | `listener` | `np.ndarray (16,) float64` | $[0.0, 1.0]$ | 🟢 HIGH | $T_{\text{speaker}}$ | Primary per-band energy normalized by rolling local/global envelopes. Directly drives vertical spectrum heights, pillar hydraulic extensions, and frequency auroras. |
| `band_proportion` | `listener` | `np.ndarray (16,) float64` | $[0.0, 1.0], \sum \le 1.0$ | 🟢 HIGH | $T_{\text{speaker}}$ | Normalized spectral distribution. Indicates relative timbre dominance without volume bias. |
| `band_means` | `listener` | `np.ndarray (16,) float64` | $\ge 0.0$ | 🟢 HIGH | $T_{\text{speaker}}$ | Long-term exponential moving averages per Mel band. Used for noise floor calculation and dynamic baseline contrast. |
| `band_flux` | `listener` | `np.ndarray (16,) float64` | $\ge 0.0$ | 🟢 HIGH | $T_{\text{speaker}}$ | Half-wave rectified positive spectral onset flux $\max(0, E_b[t] - E_b[t-1])$. Drives instantaneous transient impacts and shockwave triggers. |
| `asserved_total_power` | `listener` | `float` | $[0.0, 1.0]$ | 🟢 HIGH | $T_{\text{speaker}}$ | Local-to-global max normalized acoustic power. Direct fallback for overall visual volume and base brightness. |
| `smoothed_total_power` | `listener` | `float` | $\ge 0.0$ | 🟢 HIGH | $T_{\text{speaker}}$ | Exponentially smoothed raw acoustic power. Used for slow baseline luminance bias. |
| `dynamic_audio_latency` | `listener` | `float` | $\ge 0.0$ (seconds) | 🟢 HIGH | Hardware | Dynamic PortAudio capture-to-Hanning-window-center latency calibration (~0.069s). |
| `energy` | `listener.context` | `float` | $[0.0, 1.0]$ | 🟢 HIGH | $T_{\text{speaker}}$ | Multi-dimensional composite energy: $\text{clamp}(0.50 P + 0.30 S + 0.20 (S \cdot T), 0.0, 1.0)$. Lead signal for `level` driver modes; primary fallback breathing envelope. |
| `power` | `listener.context` | `float` | $[0.0, 1.0]$ | 🟢 HIGH | $T_{\text{speaker}}$ | Speaker-aligned `asserved_total_power` proxied through the context engine. |
| `spectral_tilt` | `listener.context` | `float` | $[-1.0, 1.0]$ | 🟢 HIGH | $T_{\text{speaker}}$ | High-frequency vs low-frequency balance. Negative = bass-dominated (deep tones, downward tilt); Positive = treble-dominated (neon brilliance, upward tilt). |
| `vertical_center` | `listener.context` | `float` | $[0.0, 1.0]$ | 🟢 HIGH | $T_{\text{speaker}}$ | Spectral center of mass across Mel bands. Normalizes physical altitude of floating elements (orbs, liquid horizon). |
| `is_power_high` | `listener.context` | `bool` | `True` / `False` | 🟢 HIGH | $T_{\text{speaker}}$ | Schmitt-triggered power flag (enter $\ge 0.50$, exit $< 0.35$). Gates high-intensity visual enhancements. |
| `is_silent` | `listener.context` | `bool` | `True` / `False` | 🟢 HIGH | $T_{\text{speaker}}$ | Schmitt-triggered acoustic silence guard (enter $\le 0.05$, exit $\ge 0.08$). Mandatory gate for fading smoothly to black. |
| `beat_phase` | `listener` | `float` | $[0.0, 1.0)$ | 🟡 MEDIUM | $T_{\text{speaker}}$ | Continuous cyclic metrical phase ($0.0 = \text{beat strike}$, $0.5 = \text{upbeat}$). Driven by speaker back-projected flywheel. Must be gated/blended by `rhythm_lock`. |
| `bpm` / `standalone_bpm` | `listener` | `float` | $[40.0, 220.0]$ | 🟡 MEDIUM | $T_{\text{speaker}}$ | Current estimated tempo in beats per minute. Governs periodic rates and kinetic speeds. |
| `beat_count` | `listener` | `int` | $\ge 0$ | 🟡 MEDIUM | $T_{\text{speaker}}$ | Cumulative integer count of validated beats since startup/reset. |
| `is_beat` | `listener` | `bool` | `True` / `False` | 🟡 MEDIUM | $T_{\text{speaker}}$ | 1-frame impulse true when `beat_phase` wraps across $0.0$. Ghost beats may occur during breakdowns; gate with `is_real_beat`. |
| `is_real_beat` | `listener` / `context` | `bool` | `True` / `False` | 🟡 MEDIUM | $T_{\text{speaker}}$ | 1-frame impulse true on beat ticks validated by physical acoustic transient energy. Authoritative trigger for 1-frame strobes/shocks. |
| `is_dropped_beat` | `listener` | `bool` | `True` / `False` | 🟡 MEDIUM | $T_{\text{speaker}}$ | 1-frame impulse true when the flywheel coasts through an acoustic dropout without a physical transient. |
| `beat_confidence` | `listener` | `float` | $[0.0, 1.0]$ | 🟡 MEDIUM | $T_{\text{lookahead}}$ | Raw Pearson template correlation score from the lookahead tempo judge. |
| `beat_trust` | `listener` / `context` | `float` | $[0.0, 1.0]$ | 🟡 MEDIUM | $T_{\text{speaker}}$ | Speaker-delayed beat tracking reliability score. Rises on consistent metronomic pulses; drops during polyrhythms, ambient, and speech. |
| `rhythm_salience` / `salience` | `listener` / `context` | `float` | $[0.0, 1.0]$ | 🟡 MEDIUM | $T_{\text{speaker}}$ | Pulse clarity, crest factor, and periodicity score. Measures presence of percussive rhythm regardless of tempo lock. |
| `rhythm_lock` | `Mode` (helper) | `float` | $[0.0, 1.0]$ | 🟡 MEDIUM | $T_{\text{speaker}}$ | Authoritative confidence blend: $\text{beat\_trust} \cdot (0.4 + 0.6 \cdot \text{rhythm\_salience})$. Master interpolator between rhythmic and acoustic drive. |
| `beat_tag` | `listener` | `str` | `"Bass/Kick"`, `"Snare/Mid"`, `"Hi-hat/Cymbal"` | 🟡 MEDIUM | $T_{\text{speaker}}$ | Frequency classification of the most recent beat transient. Modulates specific physical zones (e.g. Kick on pillars, Snare on bridges). |
| `is_locked` | `listener.context` | `bool` | `True` / `False` | 🟡 MEDIUM | $T_{\text{speaker}}$ | Schmitt-triggered beat trust lock (enter $\ge 0.50$, exit $< 0.35$). Binary indicator of metrical lock. |
| `is_syncopated` | `listener.context` | `bool` | `True` / `False` | 🟡 MEDIUM | $T_{\text{speaker}}$ | True when rhythmic salience is high but 4/4 flywheel trust is low (breakbeats, jazz, polyrhythms). |
| `drop_hit` | `Mode` (helper) | `bool` | `True` / `False` | 🟢 HIGH | $T_{\text{speaker}}$ | Sanctioned 1-frame arrival trigger on the exact frame a drop impacts. Spawns supernova shockwaves; never stays true for multiple frames. |
| `drop_decay` | `Mode` (helper) | `float` | $[0.0, 1.0]$ | 🟢 HIGH | $T_{\text{speaker}}$ | Smoothly decays $1.0 \to 0.0$ across the 1.5s `DROP_IMPACT` scene dwell ($0.0$ otherwise). Modulates post-drop amplitude boost. |
| `scene` | `listener.context` | `MusicalScene` | `CHILL`, `GROOVE`, `BUILDUP`, `DROP_IMPACT` | 🟠 LOW | $T_{\text{speaker}}$ | Active macro musical scene. **Do not branch directly in concrete modes.** Consumed upstream by `mood/`. |
| `tension` | `listener.context` | `float` | $[0.0, 1.0]$ | 🟠 LOW | $T_{\text{speaker}}$ | Macro structural tension curve combining buildup progress and novelty. Safe as a bounded speed/sharpness multiplier ($\pm 30\%$). |
| `chroma_values` | `listener` | `np.ndarray (12,) float64` | $\ge 0.0$ | 🟠 LOW | $T_{\text{speaker}}$ | Raw 12-pitch chromagram. Uncalibrated against broadband percussion; avoid direct geometric driving. |

#### Handling Signals by Trust in Global Modes
- 🟢 **HIGH Trust:** Consume directly every frame. Drives continuous spatial geometry, hydraulic height, liquid volume, and baseline intensity.
- 🟡 **MEDIUM Trust:** Gate or blend smoothly with `self.rhythm_lock` or `self.beat_pulse()`. Never branch conditionally on `beat_trust == 0.0` or allow an unverified phase wrap to trigger full-strip flashes.
- 🟠 **LOW Trust:** Never branch directly on raw scene flags (`ctx.scene == "DROP_IMPACT"`). Use continuous modifiers (`self.mood_*`) and sanctioned helpers (`self.drop_hit`, `self.drop_decay`).

---

### Door 2 — Mood Palette & Modifiers (bound by `Mode_master` from `mood.api`)

Global modes draw color and macro kinetics from buffers updated once per frame:

| Property on `self` | Type / Shape | Range | Trust | Purpose |
| :--- | :--- | :--- | :---: | :--- |
| `self.mood_colors` | `np.ndarray (4, 3)` `int32` | `0..255` | 🟢 **HIGH** | `[0]` Primary, `[1]` Secondary, `[2]` Accent, `[3]` Background / Shadow. Crossfaded over `2.5s` by `mood/`. |
| `self.palette_lut` | `np.ndarray (256, 3)` `int32` | `0..255` | 🟢 **HIGH** | 256-entry gradient ramp across palette slots 0 to 2. |
| `self.palette_sample(t, out)` | method | `t in [0, 1]` | 🟢 **HIGH** | Allocation-free vectorized LUT interpolation into `out`. |
| `self.highlight_color` | `np.ndarray (3,)` `int32` | `0..255` | 🟢 **HIGH** | Luminance-safe accent (brightest slot pushed 40% toward white). Used for peak transient crests. |
| `self.mood_pace` | `float` | `[0.82, 1.22]` | 🟢 **HIGH** | Kinetic velocity multiplier (`0.82` in `CHILL`, `1.00` in `GROOVE`, `1.12` in `BUILDUP`, `1.22` in `DROP_IMPACT`). |
| `self.mood_sharpness` | `float` | `[0.78, 1.22]` | 🟢 **HIGH** | Beat attack decay exponent multiplier. |
| `self.mood_trail` | `float` | `[0.88, 1.18]` | 🟢 **HIGH** | Persistence and phosphor decay length multiplier. |
| `self.mood_accent` | `float` | `[0.00, 0.28]` | 🟢 **HIGH** | Blend weight toward `self.highlight_color` or slot 2 accent. |

**Color Governance Invariant:** Active foreground elements must adhere to a high saturation floor ($S \ge 0.92$) and active value floor ($V \ge 0.85$). Inactive LEDs must be pure black `(0, 0, 0)` (see Law 4).

---

### Door 3 — Transition Handshake & Lifecycle Hooks

Global modes declare `IS_GLOBAL: bool = True` at the class level. This flag commands `core/Mode_master.py` to switch all 11 segments in unison when the mode is selected:

| Property / Hook on `self` | Type | Range | Purpose |
| :--- | :--- | :--- | :--- |
| `self.IS_GLOBAL` | `bool` | `True` | Class-level declaration commanding synchronous chandelier-wide orchestration. |
| `self._exit_progress` | `float` | `[0.0, 1.0]` | `0.0` in steady state; rises $0.0 \to 1.0$ when the mode is transitioning out under `mode_handshake=True`. |
| `self._enter_progress` | `float` | `[0.0, 1.0]` | `1.0` in steady state; rises $0.0 \to 1.0$ when the mode is entering under `mode_handshake=True`. |
| `self.transition_scale` | `float` | `[0.0, 1.0]` | Combined energy scale factor automatically applied during cooperative crossfades. |
| `self.on_transition_exit(progress)` | method | `0.0..1.0` | Cooperative callback executed each frame while exiting. |
| `self.on_transition_enter(progress)` | method | `0.0..1.0` | Cooperative callback executed each frame while entering. |
| `self.on_transition_reset()` | method | — | Resets `_exit_progress = 0.0`, `_enter_progress = 1.0`. |

**Dual-Buffer Redirection Rule:** During crossfades, `core/Segment.py` temporarily redirects `self.rgb_list` to `Segment.dual_rgb_list`. **Modes must never cache views or slices of `self.rgb_list` in `__init__`**. All per-frame rendering must write dynamically to `self.rgb_list` or pass `self.rgb_list` to helper methods.

---

### Door 4 — Sanctioned Gated Helpers on `Mode`

The base class [`modes/Mode.py`](../../modes/Mode.py) provides pre-gated helpers to ensure mathematical stability:

| Helper on `self` | Signature / Type | Range | What It Computes |
| :--- | :--- | :--- | :--- |
| `self.dt` | `float` | `> 0.0` | Elapsed seconds since previous frame (falls back to `1/60`). |
| `self.fps_ratio` | `float` | `~1.0..2.0` | Normalized time multiplier `self.dt * 60.0` (`1.0` at 60 Hz, `2.0` at 30 FPS). |
| `self.alpha(rate_hz)` | `float` | `[0.0, 1.0]` | Frame-rate independent exponential smoothing factor $1 - e^{-\text{dt} \cdot \text{rate\_hz}}$. |
| `self.rhythm_lock` | `float` | `[0.0, 1.0]` | Authoritative confidence blend: $\text{beat\_trust} \cdot (0.4 + 0.6 \cdot \text{rhythm\_salience})$. |
| `self.beat_pulse(sharpness=2.2)` | `float` | `[0.0, 1.0]` | Seamless confidence-blended beat envelope (rhythmic pump when locked, continuous breathing when unlocked). Returns `0.0` in silence. |
| `self.drop_hit` | `bool` | `True` / `False` | **Sanctioned 1-frame trigger:** `True` for **at most 1 frame** when a drop lands. Never persists across frames. |
| `self.drop_decay` | `float` | `[0.0, 1.0]` | Smooth post-drop dwell envelope decaying $1.0 \to 0.0$ across 1.5 seconds. |

---

### Door 5 — Global Spatial Resolver (`utils/global_mode.py`)

Each segment instance binds a pre-allocated `SegmentSpatialProfile` (`self.spatial`), mapping its physical LEDs into unified room coordinates with zero runtime heap allocation:

```python
class SegmentSpatialProfile:
    nb_of_leds: int          # Length N of the segment (47 to 205 LEDs)
    seg_id: str              # Canonical ID ('v1'..'v4', 'h00'..'h32', 's1'..'s3')
    u: np.ndarray            # (N,) float64 in [0.0, 1.0] from start to end
    u_center: np.ndarray     # (N,) float64 in [0.0, 1.0] from center outward (|2u - 1|)
    x_norm: np.ndarray       # (N,) float64 in [0.0, 1.0] normalized room horizontal coordinate
    y_norm: np.ndarray       # (N,) float64 in [0.0, 1.0] normalized room vertical coordinate (0=top, 1=floor)
    altitude: np.ndarray     # (N,) float64 in [0.0, 1.0] normalized height above floor (1.0 - y_norm)
    role: str                # 'pillar' | 'bridge' | 'canopy' | 'composite'
    tier: str                # 'pillar' | 'canopy' | 'mid' | 'low' | 'composite'
    half: str                # 'left' | 'right'
    pillar_index: int        # 0 ('v1'), 1 ('v2'), 2 ('v3'), 3 ('v4')
    is_inner_pillar: bool    # True for core inner pillars ('v2', 'v3', 's2')
```

#### Physical Coordinate System & Architectural Bounding Box
- **Room Width:** $X \in [0.0, 431.0]$ ($\text{ROOM\_MAX\_X} = 431.0$, spanning 432 columns).
- **Room Height:** $Y \in [0.0, 245.0]$ ($\text{ROOM\_MAX\_Y} = 245.0$, spanning 246 rows).
- **Altitude Coordinate:** $Z = 1.0 - y_{\text{norm}}$ ($0.0 = \text{physical floor}$, $1.0 = \text{ceiling canopy}$).
- **Architectural Centroid:** $(\text{CORE\_X}, \text{CORE\_Y}) = (0.620, 0.450)$ (normalized center of mass of the 4 vertical pillars).
- **Normalized Polar Coordinates:**
  $$r = \sqrt{(x_{\text{norm}} - 0.620)^2 + (y_{\text{norm}} - 0.450)^2}, \quad \theta = \operatorname{atan2}(y_{\text{norm}} - 0.450, x_{\text{norm}} - 0.620)$$

#### Canonical Segment Topology Matrix (1,304 LEDs across 11 Segments)
From `config/segments_full.json`:

| Segment ID | Hardware Port & GPIO | LEDs | Role | Tier | Start $(X, Y)$ | Step $(\Delta X, \Delta Y)$ | Altitude Span ($Z$) | Notes |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| `v1` | `segs_2`: 9002 (GPIO 18) | 173 | `pillar` | `pillar` | $(205, 188)$ | $(0, -1)$ | $0.236 \rightarrow 0.935$ | Outer left pillar |
| `v2` | `segs_2`: 9002 (GPIO 18) | 173 | `pillar` | `pillar` | $(292, 245)$ | $(0, -1)$ | $0.004 \rightarrow 0.703$ | **Inner core pillar** |
| `v3` | `segs_1`: 9001 (GPIO 21) | 173 | `pillar` | `pillar` | $(383, 245)$ | $(0, -1)$ | $0.004 \rightarrow 0.703$ | **Inner core pillar** |
| `v4` | `segs_1`: 9001 (GPIO 21) | 173 | `pillar` | `pillar` | $(431, 204)$ | $(0, -1)$ | $0.171 \rightarrow 0.870$ | Outer right pillar |
| `h00` | `segs_1`: 9001 (GPIO 21) | 205 | `canopy` | `canopy` | $(0, 16)$ | $(1, 0)$ | $0.935$ (fixed) | Wide left canopy wing |
| `h20` | `segs_1`: 9001 (GPIO 21) | 91 | `canopy` | `canopy` | $(292, 16)$ | $(1, 0)$ | $0.935$ (fixed) | Center canopy crown |
| `h30` | `segs_1`: 9001 (GPIO 21) | 47 | `canopy` | `canopy` | $(383, 1)$ | $(1, 0)$ | $0.996$ (fixed) | Top right canopy wing |
| `h11` | `segs_2`: 9002 (GPIO 18) | 87 | `bridge` | `mid` | $(205, 73)$ | $(1, 0)$ | $0.703$ (fixed) | Mid bridge (`v1` $\leftrightarrow$ `v2`) |
| `h32` | `segs_1`: 9001 (GPIO 21) | 48 | `bridge` | `mid` | $(383, 85)$ | $(1, 0)$ | $0.654$ (fixed) | Mid bridge (`v3` $\leftrightarrow$ `v4`) |
| `h10` | `segs_2`: 9002 (GPIO 18) | 86 | `bridge` | `low` | $(205, 189)$ | $(1, 0)$ | $0.232$ (fixed) | Low bridge (`v1` $\leftrightarrow$ `v2`) |
| `h31` | `segs_1`: 9001 (GPIO 21) | 48 | `bridge` | `low` | $(383, 171)$ | $(1, 0)$ | $0.305$ (fixed) | Low bridge (`v3` $\leftrightarrow$ `v4`) |

#### Cast Topology, Clock & Fixture Looks (`utils/cast.py`, cast family only)

[`utils/cast.py`](../../utils/cast.py) gives every canonical segment an architectural identity and provides the shared cast machinery (all zero-allocation in the hot path):

| Segment | Group | Colour slot | Mirror | Build order |
| :---: | :--- | :---: | :---: | :---: |
| `v2` / `v3` | `core_pillar` | 0 (pillars) | each other | 0 / 1 |
| `h10` / `h31` | `low_rung` | 1 (rungs) | each other | 2 / 3 |
| `v1` / `v4` | `outer_pillar` | 0 | each other | 4 / 5 |
| `h11` / `h32` | `mid_rung` | 1 | each other | 6 / 7 |
| `h00` / `h30` | `wing` | 2 (canopy) | each other | 8 / 9 |
| `h20` | `crown` | 2 | — | 10 |

- **Fixtures (`build_fixtures`):** a canonical segment renders 1 fixture (itself). A small-profile strip (`s1` canopy, `s2` pillars, `s3` rungs) or tag-only strip renders its group, split into one sub-fixture per member. A composite studio/test strip renders a miniature 11-fixture chandelier (pillars bottom third, rungs middle, canopy top).
- **`CastClock`:** counts `step`, `bar = step // 4`, `phrase = step // 16`. Locked (`rhythm_lock` $\ge 0.45$, exit $< 0.30$): one step per `beat_count` increment. Unlocked: one step per bass `band_flux` onset (0.25 s refractory) or, failing that, an energy-scaled timer (1.25 s → 0.55 s). `music/` exposes no downbeat, so bar alignment is arbitrary; spectators perceive the 4-cycle.
- **Fixture looks (`render_fixture`, the `look` list setting):** `snap` (white strike frame, then solid), `neon` (deterministic strike flicker seeded by `Mode.segment_phase_offset`, release flutter), `rise` (pillars fill from the floor, other fixtures from the centre, over ≈ ¼ beat), `flash` (white strike then exponential decay scaled by `mood_trail`), `steady` (plain on/off colour, no strike crest).

---

## A.2 Outputs: What Leaves a Global Mode (`OUT`)

1. **Pixel Buffer Mutation (`self.rgb_list`):**
   - The method `render(self, buffer=None, audio_ctx=None, frame_info=None)` or `run(self)` mutates `self.rgb_list` **in place**.
   - Array shape: `(nb_of_leds, 3)`, dtype: `np.int32`, valid color range: `0..255`.
2. **Settings Schema (`get_settings_schema()`):**
   - Declares real-time interactive parameters for the Web UI and Mode Studio (`key`, `label`, `valueType`, `default`, `min`/`max`/`step`, `attr`).
   - Every declared setting must be actively consumed during rendering (Law 5).

---

# Part B — Architectural & Perceptual Laws of Global Modes

---

### Law 1: Universal Flywheel Resilience (Always Alive & Rhythm-Locked)

> **Cast family:** clauses 1 and 3 are replaced by Cast Laws C3 and C2. Clauses 2, 4 and 5 apply unchanged.
>
> **Ensemble family:** clauses 1–3 are applied per part through Ensemble Law E4. Clauses 4 and 5 apply unchanged.

A Global Mode must satisfy both halves of the confidence continuum without jarring snaps or freezing:

1. **Fallback Half (`self.rhythm_lock == 0.0`):**
   When beat trust is zero (ambient music, rubato passages, classical, spoken word, or unquantized live instruments), the mode must continue to generate smooth, continuous light animations driven by continuous acoustic energy (`energy`, `power`, `asserved_fft_band`, `vertical_center`, `spectral_tilt`). **No mode may freeze, turn black, or wait for beat triggers.**
2. **Rhythm-Locked Half (`self.rhythm_lock -> 1.0`):**
   When the beat tracker is confident, the visual motion phase-locks tightly to the metrical grid (`beat_phase`, `bpm`, `self.beat_pulse()`).
3. **Continuous Kinetic Accumulation (Anti-Popping Formula):**
   Modes must never assign absolute angles from phase (e.g. $\theta = \text{beat\_phase} \cdot 2\pi$). Instead, they accumulate delta steps every frame using soft confidence blending:
   $$\Delta\theta_{\text{rhythmic}} = (\Delta\phi \pmod{1.0}) \cdot 2\pi \cdot \text{mood\_pace}$$
   $$\Delta\theta_{\text{acoustic}} = \text{dt} \cdot \omega_{\text{base}} \cdot \text{mood\_pace} \cdot (0.45 + 0.55 \cdot \text{energy})$$
   $$\omega_{\text{base}} = 2\pi \cdot \left(\frac{\text{bpm}}{60.0}\right) \quad (\text{falling back to } 2\pi \cdot 2.0 \approx 12.57\text{ rad/s when BPM is unestimated})$$
   $$g(L) = \min\left(1.0, \frac{\text{rhythm\_lock}}{0.45}\right)$$
   $$\Delta\theta = g(L) \cdot \Delta\theta_{\text{rhythmic}} + (1.0 - g(L)) \cdot \Delta\theta_{\text{acoustic}}$$
   $$\theta[t] = (\theta[t-1] + \Delta\theta) \pmod{2\pi}$$
4. **Phase Wrap Anomaly Protection:**
   When calculating $\Delta\phi = \phi[t] - \phi[t-1] \pmod{1.0}$, if $\Delta\phi > 0.5$, clamp $\Delta\phi = 0.0$ to prevent reverse snapping during tracking corrections.
5. **Silence Protocol:**
   When `ctx.is_silent` is `True`, modes must drain internal ballistic states (`level_h`, `white_flash`, `tip_flare`, `shock_amp`, `cooldown`, etc.) to $0.0$ to prevent explosive visual popping upon audio resumption, while executing smooth exponential fading toward black:
   ```python
   # Law 1 Silence Protocol: Drain ballistic states and fade smoothly toward black
   if ctx is not None and getattr(ctx, "is_silent", False):
       self.drain_ballistic_states()  # Decay level_h, white_flash, tip_flare, shock_amp to 0.0
       self.fade_to_black_segment_vectorized(0.35, 0, self.nb_of_leds - 1)
       return
   ```
   **Instant clearing (`rgb_list.fill(0)`) or early return without draining internal ballistic states is strictly forbidden.**

---

### Law 2: Subtle Mood Governance (Zero Scene Branching)

Macro musical scenes (`CHILL`, `GROOVE`, `BUILDUP`, `DROP_IMPACT`) are resolved upstream by `mood/` with a 0.30s debounce and a 2.5s cosine crossfade.

1. **Strict Prohibition on `ctx.scene` Branching:**
   Never write `if scene == "DROP_IMPACT": ...` or `elif scene == "BUILDUP": ...` inside concrete modes.
2. **The 90-Frame Flash Hazard:**
   `DROP_IMPACT` is a **1.5-second scene dwell** (45 to 90 consecutive frames). Hard branches on `DROP_IMPACT` lock the chandelier into a blinding, frozen white bar and overflow particle pools.
3. **Continuous Kinetic Scaling:**
   Modes scale kinetics via `self.mood_pace` (speed), `self.mood_trail` (decay), `self.mood_sharpness` (attack), and `self.mood_accent` (highlight mix). These modifiers evolve organically without code branches.

---

### Law 3: Transient Physics (1-Frame Spikes vs Multi-Frame Envelopes)

High-energy optical impacts must be strictly partitioned into 1-frame spikes and continuous decays:

1. **1-Frame Impulse Triggers:**
   Hard strobes, shockwave emissions, and laser sparks must trigger strictly on **1-frame boolean events**:
   - `self.drop_hit` (strictly 1 frame on drop arrival),
   - `ctx.is_real_beat and ctx.is_locked` (acoustically validated beat tick),
   - `band_flux[b] > threshold` with an enforced refractory cooldown ($\ge 0.12\text{s}$).
2. **Multi-Frame Dwell Modulation:**
   To sustain post-drop intensity, modulate visual parameters gently using `self.drop_decay` (at most $+20..30\%$ amplitude boost, decaying smoothly to zero). Never hold a full-strip flash across frames.
3. **The White-Crest Highlight Rule:**
   Peak transient impacts ignite at **Pure White `(255, 255, 255)`** or `self.highlight_color` for exactly 1 frame, then decay immediately into the saturated mood palette.

---

### Law 4: Palette Gradient Lookup & Anti-Mud Law

WS2812B LEDs produce light via narrow spectral peaks. Linear RGB interpolation between complementary colors produces washed-out gray mud at the midpoint:

```
Linear RGB Interpolation (MUD HAZARD):
Cyan (0, 240, 255) ─────────────> Dull Gray-Olive (127, 180, 127) ─────────────> Orange (255, 120, 0)
                                      [CONTRAST COLLAPSE]

Curved HSV Geodesic (MANDATORY):
Cyan (H=0.51, S=1.0) ───────────> Perimeter Arc (S >= 0.92, V >= 0.85) ─────────> Orange (H=0.09, S=1.0)
                                      [PURE VIBRANCY]
```

1. **Curved Color Interpolation:**
   Interpolate colors along the circular hue arc in HSV space or sample the pre-computed gradient `self.palette_lut` / `self.palette_sample(t, out)`. Never blend complementary RGB primaries directly without preserving saturation.
2. **High Saturation Floor ($S \ge 0.92$):**
   In steady-state animation, active colors must maintain $S \ge 0.92$. Desaturated pastels ($S < 0.70$) scatter into milky white under acrylic chandelier diffusers.
3. **Active Value Floor ($V_{\text{active}} \ge 0.85$):**
   Active visual elements must operate near maximum luminance ($V \in [0.85, 1.0]$).
4. **Pure Black Figure-Ground Rule ($V_{\text{idle}} = 0$):**
   Unlit LEDs must be set to **Pure Black `(0, 0, 0)`**. Ambient background glow destroys perceived dynamic range. Contrast against absolute darkness makes 500 lumens appear brighter than 1,000 lumens against an ambient wash.

---

### Law 5: Settings Schema Honesty

Every parameter declared in `get_settings_schema()` is exposed to the React Web UI and Mode Studio. **Every declared setting must be actively read and consumed inside `render()` / `run()`**. Unused schema entries that have no visible effect violate system integrity (enforced by `tests/test_mode_helpers.py`).

---

### Law 6: Zero-Churn Performance Invariant (AXIOM-01, AXIOM-02)

The chandelier refresh cycle is strictly **30 FPS** ($33.33\text{ ms}$ per frame):

$$\begin{aligned}
T_{\text{audio}} &\le 3.00\text{ ms} \quad (\text{FFT, Flywheel, Context Engine}) \\
T_{\text{global\_render}} &\le 10.00\text{ ms} \quad (\text{All 11 segments combined}) \\
T_{\text{neopixel\_tx}} &\le 15.00\text{ ms} \quad (\text{DMA NeoPixel transmission}) \\
T_{\text{margin}} &\ge 5.33\text{ ms} \quad (\text{Headroom guard})
\end{aligned}$$

1. **AXIOM-01 Compute Cap:**
   Each segment instance must execute in **$\le 0.20\text{ ms}$** on Raspberry Pi 4B hardware, ensuring the complete 11-segment installation renders in $< 10.0\text{ ms}$.
2. **AXIOM-02 Zero Heap Allocation:**
   Strictly zero heap allocations are permitted inside the hot render path:
   - Pre-allocate all scratch buffers, distance arrays, and coordinate vectors in `__init__`.
   - Never invoke `np.zeros()`, `np.empty()`, `np.array()`, list comprehensions, or dict/tuple packing inside `run()` / `render()`.
   - Use in-place NumPy functions exclusively (`out=self.scratch`, slice assignments `self.target[:] = ...`).

---

### Law 7: One Lead Timescale & Driver Hegemony

> **Ensemble family:** the hierarchy below is enforced **per part**, not over the whole chandelier (Ensemble Laws E2 and E3). The driver table still defines the four drivers and their mute behaviour.

Choreographic clarity requires strict visual hierarchy. Every global mode declares exactly one `LEAD` driver and at most one `SECONDARY` driver from `("beat", "spectrum", "level", "transient")`:

| Driver | Timescale | Signals Consumed | Physical Role | Mute Behavior (Mute Test of Truth) |
| :--- | :--- | :--- | :--- | :--- |
| `beat` | Meso ($0.2\text{s} - 1.0\text{s}$) | `beat_phase`, `beat_pulse()`, `bpm` | Kinetic motion, rotating searchlights, traveling waves | `beat_phase` frozen at `0.38`; motion halts completely |
| `level` | Meso slow ($0.5\text{s} - 2.0\text{s}$) | `ctx.energy`, `total_power` | Global breathing, sphere expansion, solid liquid column height | Energy frozen at `0.50`; volume breathing ceases |
| `spectrum` | Micro ($10\text{ms} - 100\text{ms}$) | `asserved_fft_band`, `vertical_center`, `tilt` | Hydraulic frequency bars, altitudinal stratification | Mel bands frozen at `0.35`; equalizer bars freeze |
| `transient` | Micro event ($1\text{ frame}$) | `ctx.is_real_beat`, `drop_hit`, `band_flux` | Lightning sparks, shockwaves, tip flares | Events forced to `False`; shockwaves cease spawning |

#### The 70 / 20 / 10 Amplitude Allocation Rule (>= 85% Perceptual Salience)
- **Lead Driver (>= 70% Algorithmic Variance, >= 85% Perceptual Salience):** Commands at least 70% of all audio-driven visual variance ($f \ge 0.30$ in choreography test suites), directing the primary visual geometry (position, scale, primary luminance). Because human vision applies non-linear contrast expansion to monolithic motion while suppressing secondary accents in the Magnocellular pathway, an algorithmic 70% lead commands $\ge 85\%$ subjective attentional salience at 5 to 10 meters.
- **Secondary Driver (<= 20% Algorithmic Variance):** Restricted to subtle edge shimmer, trail decay, or spark emission. Must retain $g \ge 0.65$ of full variance under secondary driver mute.
- **Macro Modulators (<= 10% Algorithmic Variance):** Mood modifiers scale speed, trail length, and palette tones without altering core geometry.
- **Mute Test of Truth:** Muting the `LEAD` driver must visibly flatten or freeze the mode's primary motion. Muting the `SECONDARY` driver must leave the primary shape fully recognizable ($g \ge 0.65$ retained variance).

---

### Law 8: Monolithic Visual Simplicity & Immediate Legibility

> **Cast family:** clauses 1 and 2 are read through Cast Law C4 (one rule, roles allowed). Clause 3 (the 2-bar spectator test) applies unchanged.
>
> **Ensemble family:** clauses 1 and 2 do not apply; they are replaced by Ensemble Laws E1–E3 (one job per part, different drivers on different parts allowed). Clause 3 is applied per part (Law E6).

The Display Fallacy occurs when sparse 1D LED strips are treated as a dense 2D TV screen. Because the chandelier has a physical fill factor under 2%, spectators 5 to 10 meters away rely on the visual system's **Magnocellular (M-pathway)** processing, which tracks large-scale coherent motion and high contrast while discarding fine topological details.

```
┌────────────────────────────────────────────────────────────────────────┐
│                   THE 4 LAWS OF SPECTATOR LEGIBILITY                  │
├────────────────────────────────────────────────────────────────────────┤
│ 1. SINGLE DOMINANT DRIVER: Exactly 1 audio driver owns the visual core.│
│ 2. MONOLITHIC COMMON FATE: All 1,304 LEDs share congruent motion.     │
│ 3. THE 5-TO-10 METER TEST: Untrained observer deduces rule in <= 2 bars.│
│ 4. PURE CONTRAST: Active light emerges from absolute pitch black.      │
└────────────────────────────────────────────────────────────────────────┘
```

1. **Gestalt Common Fate (Monolithic Synchrony):**
   When the chandelier animates, motion vectors across segments must be topologically congruent:
   - If a pulse travels upward, it travels upward on **all 4 pillars in absolute unison**.
   - If a ripple expands outward, its radius $R(t)$ expands uniformly across all segments from a single shared origin.
   - If an equalizer column rises, all pillars track identical normalized elevations.
2. **Ban on Multi-Tier Driver Fragmentation (field family):**
   A field mode never assigns Driver A to pillars, Driver B to bridges, and Driver C to the canopy: it would break the single continuous function the family is built on. A mode that wants different drivers on different parts declares `FAMILY = "ensemble"` and follows Part B3.
3. **The 5-to-10 Meter Spectator Test (The 2-Bar Rule):**
   An untrained spectator at 8 meters must be able to state the audio-visual relationship within **2 musical bars ($\le 3$ seconds)**:
   - *"When the kick hits, light shoots straight up to the ceiling."*
   - *"When the music gets louder, the pillars fill up like glowing water columns."*
   - *"Every beat sends a massive glowing ring rippling through the room."*

---

### Law 9: Vibrant High-Luminance Color Aesthetics

Modes must maximize physical LED punch across the room:
1. **Neon Accent Palettes:**
   Prioritize high-luminance primaries and secondaries: Electric Cyan `(0, 240, 255)`, Laser Magenta `(255, 0, 140)`, Toxic Lime `(57, 255, 20)`, Acid Yellow `(240, 255, 0)`, and Solar Gold `(255, 220, 0)`.
2. **Complementary Spatial Segregation:**
   Never blend complementary hues additively on the same LED. If Cyan and Pink are used, assign them to distinct structural elements (e.g. Cyan pillar core vs Pink bridge cross-brace) or transition via White-Crest flashes.
3. **Strict Ban on Desaturated Pastels and Ambient Washes:**
   Milky pastels, gray-olive blends, and idle background glows are prohibited.

---

### Law 10: Physical Spatial Invariance

Global modes must respect the physical electrical and geometric assembly of the chandelier:
1. **The Vertical Invariant (AXIOM-03):**
   All 4 vertical pillars (`v1`, `v2`, `v3`, `v4`) are wired **bottom-to-top** (`step.y = -1`, start coordinate at the floor, index 0 at the bottom).
2. **Direction Inversion Bypass:**
   In `core/Segment.py`, when `IS_GLOBAL == True`, `Segment.update_leds()` **must bypass the user `way == "DOWN"` inversion**, ensuring index 0 is always at the physical floor across all segments.
3. **Concentric Core / Flank Symmetry:**
   Pillars `v2` and `v3` form the inner core ($X \in [292, 383]$), flanked symmetrically by outer pillars `v1` ($X = 205$) and `v4` ($X = 431$). Wave propagations and sweeps must maintain geometric continuity across segment boundaries without tearing. *(Field family only; see Cast Law C6 and Ensemble Law E5.)*

---

# Part B2 — Cast Mode Laws (`FAMILY = "cast"`)

Cast modes treat the chandelier as 11 fixtures with an identity. The laws below replace the field-only clauses noted in Laws 1, 8 and 10. **Laws 2, 3, 4, 5, 6, 7, 9 and 10.1–10.2 apply unchanged.**

### Law C1: The Segment Is the Unit
A cast rule decides per **segment** (`segment_slot(seg_id)` → colour slot or `OFF`), never per LED. Variation *inside* a fixture comes only from the shared fixture look (`u` / `u_center` fill, strike flicker, decay), never from room coordinates (`x_norm`, `y_norm`, polar). A lit fixture shows one solid colour slot from `self.mood_colors`; pillars, rungs and canopy use distinct slots (Law 9 complementary segregation by structure).

### Law C2: Quantized Time (Hold Still Between Steps)
Fixture state changes only on `CastClock` steps (beat / bar / phrase) or on a 1-frame transient event (Law 3), and is **held** between them. Continuous kinetic accumulation (Law 1.3) does not apply: there is nothing to accumulate. A held state is not a "full-strip flash" (Law 3.2): only the strike frame may be white.

### Law C3: Alive Without the Flywheel
When `rhythm_lock` drops, the clock must keep stepping from acoustic onsets or the energy-scaled timer, so the chandelier keeps changing pose. A cast mode may never freeze or go dark while audio plays. Transient-led cast modes (e.g. Negative Space) fall back to `band_flux` onsets with a refractory period of at least 0.12 s.

### Law C4: One Rule, Roles Allowed
The whole chandelier obeys **one legible rule** driven by **one lead driver**. Structural groups may play different *roles of that same driver* (Bar Clock: pillars count beats, rungs count bars, canopy marks the phrase — all the beat driver). What remains banned is Law 8.2's real hazard: different *drivers* on different tiers. A spectator must be able to state the rule within 2 bars: *"each beat adds a piece"*, *"the chandelier is counting"*, *"every kick cuts the pillars out"*.

### Law C5: Deterministic Agreement
Segment instances share no state. Every decision is a pure function of `(seg_id, CastClock counters, shared listener signals)`: no unseeded randomness, no per-instance history that could diverge. Pseudo-random choices use `utils.cast.mix_index`. Every cast mode resets its clock and fixture state in `start()` and in silence, so all segments restart on the same frame.

### Law C6: Boundaries Are Features
Law 10.3 continuity does not apply. A fixture switching on or off at a segment boundary is the intended visual event, not tearing.

---

# Part B3 — Ensemble Mode Laws (`FAMILY = "ensemble"`)

Ensemble modes treat the chandelier as a band: each part plays its own line, and the mode is the combination. This is where complex global modes live. The laws below replace Law 1.1–1.3, the whole-chandelier reading of Law 7, Law 8.1–8.2 and Law 10.3. **Laws 2, 3, 4, 5, 6, 9 and 10.1–10.2 apply unchanged.**

The one thing that stays banned is what made the rejected `Architectural_drum_mode` unreadable: **several drivers stacked on the same LEDs**. Different drivers on *different* parts is the point of the family.

### Law E1: The Part Is the Unit
The chandelier is divided into named **parts**. A part is one segment, one `CAST_TOPOLOGY` group (e.g. `outer_pillar`, `low_rung`, `wing`), or a section of a segment cut at an architectural landmark (a rung altitude, the segment midpoint). Parts never overlap. Each part has exactly **one job**: one driver from `DRIVERS` and one mechanic (a bar, a blink, a sliding dot, a fill, a stamp, a sparkle...). Inside a part, motion is free: any direction, continuous or quantized and held. A part uses strip-intrinsic coordinates only (position along the part, altitude within it); a continuous function of room coordinates across parts is a field mode, not an ensemble.

### Law E2: Declared Score
The class declares its parts and their drivers, and the class docstring gives each part one line:

```python
class Stalagmites_mode(Ensemble_mode_base):       # modes/Stalagmites_mode.py
    """
    Stalagmites: the drum kit drawn on the chandelier.
    Lead: transient (onset strength per frequency range, from band_flux)
    Secondary: spectrum (a held note keeps a short stub of its bar lit)
    Part stalagmites:  inner pillars; red bar thrown up from the floor by each bass onset (transient)
    Part stalactites:  outer pillars; blue bar thrown down from the top by each snare onset (transient)
    Part bass_rungs:   mid rungs; struck when a bass hit throws its bar to the top (transient)
    Part treble_rungs: low rungs; struck when a snare hit throws its bar to the bottom (transient)
    Part canopy:       sparkles on hi-hat onsets (transient)
    """
    LEAD: str = "transient"           # driver of the parts covering the most LEDs
    SECONDARY: tuple = ("spectrum",)   # at most one, as for every mode
    PARTS: dict = {"stalagmites": "transient", "stalactites": "transient", "bass_rungs": "transient",
                   "treble_rungs": "transient", "canopy": "transient"}
```

Here every part listens to the same driver but to a **different frequency range** of it, which is as valid a split as different drivers: what matters is one job per part. A part may carry a small contribution from a second signal (the stub above) as long as it still passes the per-part mute test of Law E3.

`LEAD` remains mandatory: the registry needs one `lead:` tag per mode and the transition policy reads it. It names the driver whose parts cover the most LEDs. `SECONDARY` keeps its at-most-one limit; `PARTS` is the full picture.

[`modes/Ensemble_mode_base.py`](../../modes/Ensemble_mode_base.py) (`ABSTRACT = True`, `IS_GLOBAL = True`, `FAMILY = "ensemble"`) owns part resolution, the silence protocol and the final clip / copy. A concrete mode implements `part_of(seg_id)` (the part a canonical segment belongs to), `on_frame(ctx, dt)` (shared per-frame state, computed once), `render_part(part, fx, out)` (draw one part), plus the optional `on_bind()` and `on_reset()`. Shared mechanics: `draw_bar` (solid bar grown from either end of the part) and `draw_solid` (whole part at a level, with an optional white strike frame). Part resolution reuses `utils.cast.build_fixtures`: a canonical segment is one part, a small-profile strip stands for its group, and a composite studio/test strip renders a miniature 11-segment chandelier.

### Law E3: One Job Per Part (the Per-Part Mute Test)
Law 7 is enforced inside each part instead of over the whole chandelier. Measured on that part's LEDs only:
- Muting the part's declared driver must flatten or freeze it: the declared driver is the dominant one and carries $f \ge 0.30$ of the part's audio-driven variance.
- Muting any *other* driver must leave it recognizable: $g \ge 0.65$ of its variance retained.
- Mood modifiers stay macro ($\le 10\%$), as in Law 7.

A part therefore has one driver; anything else it reads must stay small enough to pass the second check. A part's job is fixed for the life of the mode: it never swaps driver or mechanic mid-run. A setting may choose between layouts, applied at `start()`.

### Law E4: Alive, Part by Part
- While audio plays, the mode never goes fully dark and never fully freezes: at least one part is always visibly responding.
- A part may be dark by design (a drop light, a peak light) for as long as its trigger is absent.
- A part driven by `beat` must survive `rhythm_lock == 0.0`: a continuously moving part blends to acoustic motion with the Law 1.3 accumulation formula; a quantized part keeps stepping from `CastClock` (Law C3).
- Law 1.4 (phase wrap protection) and Law 1.5 (silence protocol) apply to every part, with the cast debounce: the silence detector fires in the short gaps between hits, so parts keep rendering through silence shorter than 0.6 s (the audio itself pulls them down), then drain their state and fade to black.

### Law E5: Interplay Allowed, Agreement Required
Parts may react to each other: a rung lights when the bars on both its pillars pass its altitude; outer pillars repeat what the inner pillars showed one beat ago. Segment instances still share no state, so an instance that needs another part's state **recomputes it** from the shared listener signals and its own deterministic history. No unseeded randomness (`utils.cast.mix_index`), and every instance resets in `start()` and after sustained silence so all segments agree on every frame. Law 10.3 continuity does not apply: a change of behaviour at a part boundary is intended.

### Law E6: Legible Part by Part
The 2-bar spectator test (Law 8.3) applies to **each part alone**: someone watching only that part can state its job within 2 bars (*"that pillar is the bass"*, *"the top flashes on the hi-hat"*). The whole mode may take longer to take in, and that is accepted: it is the price of complexity and the reason to choose this family. There is no cap on the number of parts or jobs. The mode's docstring must be able to state every job in one line (Law E2); a job that needs two lines is two jobs and must be split across two parts.

---

# Part C — Verification & Governance

---

## C.1 Automated Test Suites

Every compliant Global Mode must pass four automated verification suites in CI:

```bash
# 1. Functional role resolution, silence decay, and flywheel resilience (field, cast and ensemble families)
pytest tests/test_global_modes.py tests/test_cast_modes.py tests/test_ensemble_modes.py

# 2. Base Mode helper stability, dead settings ratchet, and transition hooks
pytest tests/test_mode_helpers.py

# 3. Governance: AXIOM-01 frame budget, AXIOM-02 memory allocation, AXIOM-03 geometry
pytest tests/governance/test_axiom_01_frame_budget.py tests/governance/test_axiom_02_zero_allocation.py tests/governance/test_axiom_03_geometry.py

# 4. Law 7 choreography dominance & mute tests of truth
pytest tests/governance/test_mode_choreography.py tests/governance/test_mode_choreography_profiles.py
```

**Ensemble family:** `pytest tests/test_ensemble_modes.py` covers every mode listed in its `ENSEMBLE_MODE_SPECS`: the declared score (Laws E1–E2), the per-part mute test (Law E3), a lockstep 11-segment and 3-segment run proving agreement (Law E5), aliveness without beat lock and the debounced silence protocol (Law E4), AXIOM-01/02, Law 5 honesty, and real-orchestrator part resolution. The per-part mute test is measured by `tools/ensemble_matrix.py`, which also prints the per-part table: `python -m tools.ensemble_matrix Stalagmites_mode`. The whole-chandelier Law 7 dominance check in `tests/test_global_modes.py` does not apply to ensemble modes.

---

## C.2 Performance & Zero-Allocation Test Harness

From `tests/test_global_modes.py`:

```python
def test_axiom_01_and_02_performance_and_zero_allocation(self):
    """Enforces AXIOM-01 (<= 0.20 ms per segment) and AXIOM-02 (0 heap allocations)."""
    rgb = np.zeros((60, 3), dtype=np.int32)
    mode = CompliantGlobalMode("Test", "studio_preview", self.listener, None, list(range(60)), rgb, {})
    
    # Warmup
    for _ in range(30):
        mode.run()
        
    # Timing benchmark (AXIOM-01)
    start_t = time.perf_counter()
    for _ in range(100):
        mode.run()
    frame_ms = (time.perf_counter() - start_t) * 1000.0 / 100.0
    assert frame_ms <= 0.20, f"Exceeded per-segment budget: {frame_ms:.4f} ms > 0.20 ms"
    
    # Memory churn benchmark (AXIOM-02)
    gc.collect()
    tracemalloc.start()
    s1 = tracemalloc.take_snapshot()
    for _ in range(100):
        mode.run()
    s2 = tracemalloc.take_snapshot()
    tracemalloc.stop()
    
    allocs = [
        stat for stat in s2.compare_to(s1, "lineno")
        if "Compliant_global_mode.py" in stat.traceback.format()[0] and stat.size_diff > 512
    ]
    assert allocs == [], f"AXIOM-02 heap allocation detected: {allocs}"
```

---

## C.3 The Formal 6-Dimension Evaluation Rubric

Every proposed Global Mode is evaluated across 6 quantitative dimensions (0 to 10 points each).

$$\text{Total Score} = \sum_{i=1}^6 D_i \quad (\text{Max } 60\text{ points})$$

- **Acceptance Threshold:** Total Score $\ge 48 / 60$ with **all dimensions $\ge 6.0$**.
- **Rejection Condition:** Total Score $< 48 / 60$ or **any single dimension $< 6.0$**.

> **Scoring Formalism Note:** The total score is calculated as the direct unweighted sum across all six dimensions:
> $$\text{Total Score} = \sum_{i=1}^6 D_i \quad (\text{Maximum } 60\text{ points, Threshold } \ge 48.0)$$
> The percentage weights assigned to dimensions ($D_1: 20\%, D_2: 20\%, D_3: 15\%, D_4: 15\%, D_5: 15\%, D_6: 15\%$) represent relative conceptual prioritization. Evaluating modes under the normalized weighted composite formula ($S_{\text{weighted}} = 6 \sum w_i D_i$) yields identical verdicts without altering any threshold boundaries ($55.8 - 58.4$ for proposed modes, $41.0 - 44.3$ for baseline modes).

| # | Dimension | Weight | Scoring Standard (0 - 10) |
|---|---|:---:|---|
| **D1** | **Instant Spectator Legibility** | 20% | **9-10:** Understood in $\le 1$ bar ($\le 1.5\text{s}$). Whole room moves as one acoustic mirror.<br>**7-8:** Understood in 2-3 bars. Clear primary motion.<br>**5-6:** Takes 5-10s to decode. Conflicting sub-motions create hesitation.<br>**0-4:** Indistinguishable from random uncoordinated lighting.<br>*Ensemble family: scored per part (Law E6) — the time to read one part's job, not the whole mode.* |
| **D2** | **Visual Simplicity & Monolithic Metaphor** | 20% | **9-10:** Exactly 1 bold physical metaphor. All 1,304 LEDs share congruent motion (cast family: all 11 fixtures obey one legible rule, Law C4).<br>**7-8:** Unified metaphor with minor role variations.<br>**5-6:** Split across tiers (bass on pillars, treble on canopy). Visual clutter.<br>**0-4:** Multi-layered chaos. Conflicting algorithms fight for attention.<br>*Ensemble family: this dimension is read as **Clarity of Parts**. **9-10:** every part has one job and one driver, passes the per-part mute test (Law E3), and no two drivers share an LED. **5-6:** a part mixes two drivers or changes job mid-run. **0-4:** drivers stacked on the same LEDs. Splitting drivers across parts is not penalized.* |
| **D3** | **Bright Color Vibrancy & Anti-Mud** | 15% | **9-10:** Saturated neon primaries ($S \ge 0.95, V \ge 0.95$), pure black unlit space `(0, 0, 0)`, blinding white 1-frame transient crests, zero gray mud.<br>**7-8:** Bright vivid colors, solid contrast, near-black inactive space.<br>**5-6:** Noticeable desaturation during blends; faint ambient glow reduces contrast.<br>**0-4:** Washed-out pastels, linear RGB mud, or low dynamic range. |
| **D4** | **NumPy Vectorization & Zero Heap Churn** | 15% | **9-10:** Strictly 0 bytes allocated per frame in `run()`. All buffers pre-allocated in `__init__`. In-place operations exclusively.<br>**7-8:** Zero allocations in steady-state; minor scalars in initialization.<br>**5-6:** Occasional allocations during rare scene events.<br>**0-4:** Allocates arrays or lists inside `run()`. Fails `tracemalloc`. |
| **D5** | **30 FPS Frame Budget (AXIOM-01)** | 15% | **9-10:** Total render time across 11 segments $\le 0.15\text{ ms}$ ($>99.5\%$ CPU headroom).<br>**7-8:** Render time $\le 0.35\text{ ms}$.<br>**5-6:** Render time between $0.35\text{ ms}$ and $0.80\text{ ms}$.<br>**0-4:** Exceeds $1.0\text{ ms}$ or drops frames on Raspberry Pi 4B. |
| **D6** | **Flywheel Resilience & Graceful Fallback** | 15% | **9-10:** Smooth continuous acoustic fallback when `rhythm_lock == 0.0`; tight phase lock when confident; seamless exponential decay to pure black in silence; zero visual pops.<br>**7-8:** Graceful fallback to energy, smooth silent fade, minor re-lock jump.<br>**5-6:** Noticeable visual stutter or jump when flywheel locks or unlocks.<br>**0-4:** Mode goes black or freezes when beat tracking is lost. |

---

# Standard Code Templates for Compliant Global Modes

Below is the production-grade implementation template for a compliant Global Mode adhering to all 10 Architectural Laws:

```python
"""
modes/Compliant_global_template_mode.py
Canonical Golden Standard Template for Global Audio Modes adhering strictly to docs/contracts/global_mode_contract.md.
Lead: beat
"""
from typing import List, Dict, Any, Optional
import math
import numpy as np

from modes.Mode import Mode
from utils.global_mode import SegmentSpatialProfile


class Compliant_global_template_mode(Mode):
    """
    Canonical template demonstrating 100% compliance with global_mode_contract.md:
    - Door 1: Dual-horizon audio ingestion & trust-conscious signal usage.
    - Door 2: Pure black background & high-saturation palette sampling.
    - Door 3: Global lifecycle & dual-buffer redirection immunity.
    - Door 4: Sanctioned gated helpers (dt, alpha, rhythm_lock, beat_pulse, drop_hit).
    - Door 5: Spatial coordinate integration via SegmentSpatialProfile.
    - Laws 1-10: Flywheel fallback, 1 lead driver (~70% variance), AXIOM-01/02 zero allocation.
    """
    IS_GLOBAL: bool = True
    LEAD: str = "beat"
    SECONDARY: tuple = ("transient",)

    def __init__(
        self,
        name: str,
        segment_name: str,
        listener: Any,
        leds: Any,
        indexes: List[int],
        rgb_list: np.ndarray,
        infos: Dict[str, Any],
    ) -> None:
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)

        # Door 5: Global Spatial Profile
        self.spatial = SegmentSpatialProfile(
            segment_name=segment_name,
            nb_of_leds=self.nb_of_leds,
            tags=infos.get("tags", ()),
            orientation=infos.get("orientation"),
        )

        # Dynamic user settings
        self.speed: float = float(infos.get("speed", 1.0))
        self.pulse_width: float = float(infos.get("pulse_width", 0.12))

        # Internal state tracking
        self.angle: float = 0.0
        self.prev_phase: float = 0.0
        self.shock_radius: float = 0.0
        self.shock_amp: float = 0.0

        # AXIOM-02: Pre-allocate all scratch buffers in __init__ (ZERO per-frame heap allocations)
        n = max(1, self.nb_of_leds)
        self._dist_scratch = np.zeros(n, dtype=np.float64)
        self._shock_scratch = np.zeros(n, dtype=np.float64)
        self._intensity = np.zeros(n, dtype=np.float64)
        self._target_rgb = np.zeros((n, 3), dtype=np.float64)
        self._lut_rgb = np.zeros((n, 3), dtype=np.float64)
        self._lut_idx = np.clip((self.spatial.altitude * 255.0).astype(np.int32), 0, 255)

    def get_settings_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": "speed",
                "label": "Rotation Speed",
                "valueType": "number",
                "min": 0.2,
                "max": 3.0,
                "default": 1.0,
                "step": 0.1,
                "attr": "speed",
            },
            {
                "key": "pulse_width",
                "label": "Pulse Width",
                "valueType": "number",
                "min": 0.04,
                "max": 0.30,
                "default": 0.12,
                "step": 0.02,
                "attr": "pulse_width",
            },
        ]

    def run(self) -> None:
        ctx = getattr(self.listener, "context", None)

        # Law 1 Silence Protocol: Drain ballistic states and fade smoothly toward black
        if ctx is not None and getattr(ctx, "is_silent", False):
            self.shock_amp = 0.0
            self.shock_radius = 0.0
            self.fade_to_black_segment_vectorized(0.35, 0, self.nb_of_leds - 1)
            return

        energy = float(getattr(ctx, "energy", 0.5)) if ctx is not None else 0.5
        phase = float(getattr(self.listener, "beat_phase", 0.0))

        # Law 1 Phase Wrap Anomaly Protection
        phase_delta = (phase - self.prev_phase) % 1.0
        if phase_delta > 0.5:
            phase_delta = 0.0
        self.prev_phase = phase

        # Law 1 Continuous Kinetic Accumulation (BPM-coupled anti-deceleration)
        bpm = float(getattr(self.listener, "bpm", 120.0))
        if bpm <= 0.0:
            bpm = 120.0
        omega_base = 2.0 * math.pi * (bpm / 60.0)

        lock_gate = min(1.0, self.rhythm_lock / 0.45)
        rhythmic_step = phase_delta * 2.0 * math.pi * self.mood_pace * self.speed
        acoustic_step = self.dt * omega_base * self.mood_pace * self.speed * (0.45 + 0.55 * energy)
        step = lock_gate * rhythmic_step + (1.0 - lock_gate) * acoustic_step
        self.angle = (self.angle + step) % (2.0 * math.pi)

        # Law 3: Transient Physics (1-Frame Spikes)
        if self.drop_hit or (ctx is not None and getattr(ctx, "is_real_beat", False) and self.rhythm_lock > 0.4):
            self.shock_amp = 1.0 if self.drop_hit else 0.85
            self.shock_radius = 0.0

        if self.shock_amp > 0.01:
            self.shock_radius += self.dt * 2.5 * self.mood_pace
            self.shock_amp *= math.exp(-self.dt * (4.0 / self.mood_trail))

        # Law 7 & 8: Monolithic Lead Driver Geometry (~70% Visual Variance)
        wave_center = (self.angle / (2.0 * math.pi))
        np.subtract(self.spatial.altitude, wave_center, out=self._dist_scratch)
        np.abs(self._dist_scratch, out=self._dist_scratch)
        np.minimum(self._dist_scratch, 1.0 - self._dist_scratch, out=self._dist_scratch)

        sigma = max(0.01, self.pulse_width * 0.5)
        inv_two_sigma_sq = 1.0 / (2.0 * sigma * sigma)
        np.multiply(self._dist_scratch, self._dist_scratch, out=self._dist_scratch)
        np.multiply(self._dist_scratch, -inv_two_sigma_sq, out=self._dist_scratch)
        np.exp(self._dist_scratch, out=self._intensity)

        pulse = self.beat_pulse(sharpness=2.2)
        gain = 0.20 + 0.80 * pulse + 0.20 * self.drop_decay
        np.multiply(self._intensity, gain, out=self._intensity)

        np.clip(self._intensity, 0.0, 1.0, out=self._intensity)

        # Law 4: Palette Gradient Lookup & Pure Black Background
        self._lut_rgb[:] = self.palette_lut[self._lut_idx]
        np.multiply(self._lut_rgb, self._intensity[:, np.newaxis], out=self._target_rgb)

        # Secondary Driver: Transient crest flare (~20% Visual Variance, in-place AXIOM-02)
        if self.shock_amp > 0.05:
            np.multiply(self._intensity, self.shock_amp * 70.0, out=self._shock_scratch)
            np.add(self._target_rgb, self._shock_scratch[:, np.newaxis], out=self._target_rgb)

        np.maximum(0.0, self._target_rgb, out=self._target_rgb)
        np.minimum(255.0, self._target_rgb, out=self._target_rgb)
        np.copyto(self.rgb_list, self._target_rgb, casting="unsafe")
```

## Cast Family Template

A cast mode implements only its rule; [`modes/Cast_mode_base.py`](../../modes/Cast_mode_base.py) owns the clock, fixtures, looks, silence protocol and the `look` setting. Hooks: `on_step(clock)` (once per musical step and on the first frame), `on_frame(ctx)` (optional per-frame events), `segment_slot(seg_id)` (colour slot or `OFF`), `on_reset()`, `cast_settings()`, and `request_restrike()` (re-strike every lit fixture, e.g. on `drop_hit`). Reference: [`modes/Construction_mode.py`](../../modes/Construction_mode.py).

```python
"""
modes/Compliant_cast_template_mode.py
Lead: beat
"""
from typing import Any, Dict, List

from modes.Cast_mode_base import Cast_mode_base
from utils.cast import OFF, PILLARS, topology_slot


class Compliant_cast_template_mode(Cast_mode_base):
    """
    One pillar per beat, walking v1 -> v4 (Laws C1-C6).
    Lead: beat
    """
    LEAD: str = "beat"
    SECONDARY: tuple = ("transient",)
    DEFAULT_LOOK: str = "snap"

    def __init__(self, name, segment_name, listener, leds, indexes, rgb_list, infos) -> None:
        self.walk_back: bool = bool(infos.get("walk_back", False))
        self._beat: int = 0
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)

    def cast_settings(self) -> List[Dict[str, Any]]:
        return [{"key": "walk_back", "label": "Walk Back", "valueType": "boolean",
                 "default": False, "attr": "walk_back"}]

    def on_step(self, clock) -> None:          # C2: state changes only here
        self._beat = (3 - clock.beat_in_bar) if self.walk_back else clock.beat_in_bar

    def on_frame(self, ctx) -> None:           # Law 3: 1-frame transient accent
        if self.drop_hit:
            self.request_restrike()

    def segment_slot(self, seg_id: str) -> int:  # C1 + C5: pure function of (seg_id, counters)
        if seg_id in PILLARS and PILLARS.index(seg_id) == self._beat:
            return topology_slot(seg_id)
        return OFF
```

---

## Contract Verification Attestation

This contract is sealed and authoritative. Any global mode failing to adhere to Laws 1 through 10 as scoped for its family (Part B2 for cast, Part B3 for ensemble), or failing the automated test suites, will be rejected by the governance engine and CI pipelines.
