# 💡 Vialactée — Next-Session Ideas & Personal Scratchpad (`IDEAS.md`)

> [!CAUTION]
> **AGENT INSTRUCTION — NOT SYSTEM TRUTH (TIER 4 SCRATCHPAD):**
> This file is the user's personal reminder pad and brainstorming backlog for **future sessions**.
> - **NONE of the ideas in this file are currently true or implemented in the codebase.**
> - **DO NOT cite this file as architectural truth, specification, or current behavior.**
> - **DO NOT implement anything from this file automatically** unless the user explicitly asks to work on a specific idea during a session.
> - When an idea from this file is implemented in a future session, remove or check it off here and document the actual implementation in `docs/` and `work_history/`.

---

## 🎭 Transitions & Visual Choreography Ideas

### 1. Perceptual Duration for Global "Showstopper" Transitions
- Normal full-chandelier transitions with a clear beginning, build-up, and climax (like `explosion`) are great, **provided they last long enough**.
- When a global transition is too short, the viewer does not have enough time to realize a transition is happening, which makes it lose its dramatic importance.
- Keep big global transitions long enough to feel like real events.

### 2. Negligible / Subtle Micro-Transitions on 1 or 2 Segments Only
- Keep small, subtle, almost "negligible" transitions alongside the big global ones.
- However, **do not run negligible transitions across all segments at once** — instead, have them change only **1 or 2 segments at a time** so the chandelier quietly evolves piece-by-piece between big moments.

### 3. Personal / Bespoke Ultra-Complex Transitions per Mode
- Give individual modes their own deeply complex, multi-stage personal transitions built around that mode's specific visual physics.
- **Example (`Extending_waves_mode`):**
  - White waves start coming toward the middle / end of the segment.
  - When a white wave reaches the end, **it does not disappear** — instead, the white builds up and stacks wave after wave until the entire strip is completely white, and then transitions into the next mode.

### 4. Revisit `Opposite_sides_mode` Firework Sparkles ("Pop-Depop" Crackle)
- The bass-vs-treble VU tug-of-war bars and fixed 8% core are in place, but the **sparkle effect still needs visual tuning**.
- **Target look:** When the beat is locked and `beat_phase` reaches `1.0`, the sparkles should look like a **firework crackle** — many tiny, ultra-bright, strictly local (1-LED) pure-white pinpoints that pop and depop rapidly one after another ("pop de pop pop depop") at scattered locations rather than appearing/fading together as a group.
- Revisit timing, contrast against the underlying colored bars (e.g., briefly punching through or darkening a 1-LED hole around the pinpoint, or tuning hold/depop cadence in Mode Studio) in a future session.

### 5. Mode-Coherence Engine — Deferred Extensions (after the simple v1 works)
Context: the v1 picks one grouping (from a human-written catalogue) and one mode per group, scored by rules. These are the "life" ideas parked for later:
- **Wildcard / surprise:** with a small probability (e.g. 5–10%) per transition, ignore the *soft* rules (rewards/discouragements) so unexpected-but-safe combinations appear. **Hard rules (forbid) are never relaxed.** Optionally also a short list of explicitly declared "spicy" combinations that are normally forbidden.
- **Partial re-roll:** a transition changes only some groups (e.g. only the horizontals) while the others keep playing, so the chandelier evolves gradually. Needs a small edit to the "every non-blocked segment is retargeted" invariant; the kept groups act as fixed constraints for the new draw.
- **Adjacency rules:** rules about *touching* groups (e.g. "these two modes must not play on neighbouring groups"), using physical neighbours derived from the segment layout.
- **Deeper nested groupings:** groups that contain sub-groupings with their own alternatives (v1 format reserved for this, v1 itself stays 2 levels).
- **Rules that act on the grouping choice itself** (e.g. "v1 and v2 like to be together" as a rule instead of a catalogue weight).

---

## 📝 Random Notes / Future Session Reminders

- **Look at the agent conversation about the new mode.**
- *(Drop any raw thoughts, half-baked ideas, or reminders for future sessions here)*

