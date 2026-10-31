# Vialactée Work History & Agent Memory

This directory maintains the permanent chronological journal of all engineering and research work performed on the Vialactée project.

---

## Why this exists

AI agents and human developers regularly modify core math, modes, React components, and hardware configurations. Without an immutable audit trail, critical architectural context, bug fixes, benchmark results, and rationale are easily lost between sessions ("agent amnesia").

Every engineering session that modifies code or project configuration **must create or update a dated entry in this folder.**

---

## Protocol for Agents

Whenever an agent performs work on this repository:

1. **Before Starting:** Check the latest entries in the table below to understand what was recently changed and what immediate next steps remain open.
2. **Standard Template:** Copy [`TEMPLATE.md`](file:///c:/Users/Users/Desktop/vialactée/vialactee/work_history/TEMPLATE.md) to a new file named `YYYY-MM-DD_<short_topic_slug>.md`.
3. **During/After Session:**
   - Record exact files modified with clickable links.
   - Record exact tests run and their verification outcomes.
   - Note non-obvious design decisions, trade-offs, and lessons learned.
   - List any unfinished tasks under *Open Items & Next Steps*.
4. **Update Master Index:** Add your new entry to the chronological table below.
5. **Commit & Push:** Commit the code **and** the session log together, push, then record the commit hash(es) in the log's `Commits` field. See the *Commit & Push Protocol* in [`vialactee-project/SKILL.md`](../.agents/skills/vialactee-project/SKILL.md).

---

## Master Chronological Index

| Date | Session File | Agent / Author | Topic / Goal | Status |
| :--- | :--- | :--- | :--- | :--- |
| **2026-10-31** | [`2026-10-31_mode_coherence_engine_v1.md`](2026-10-31_mode_coherence_engine_v1.md) | Antigravity | Mode Coherence Engine v1 delivery and post-delivery test cleanup | **COMPLETED** |
| **2026-10-29** | [`2026-10-29_environment_fixes.md`](2026-10-29_environment_fixes.md) | Gemini 4 Argon (High) | Environment Fixes, Shining Stars Musical Dynamics & Multi-Profile Choreography Suite (Phases S1–S6): align Mode Studio to 8-band visual FFT + coarse Mel flux (`--bands`), add `requirements-dev.txt` & benchmark pytest guard, add `tools/choreography_probe.py` (`--track`), fix `Shining_stars_mode` dominant-band onset triggering & band-energy brightness scaling, add 3 synthetic lock profiles (`high_lock`, `groove_lock`, `loose_lock`) & Law 1/Law 7 tests, and sync docs/skills | **COMPLETED** |
| **2026-10-28** | [`2026-10-28_choreography_corrections.md`](2026-10-28_choreography_corrections.md) | Gemini 4 Argon (High) | Choreography Doctrine Corrective Plan v2 (Phases F0–F7): split `utils/choreography.py` into `utils/choreography.py`, `utils/driver_mute.py`, `tools/studio_mutes.py`, `tools/choreography_matrix.py`; add `utils/` to AXIOM-07 500-line scope; unify calibration/CI `MATRIX_CONFIG` with 16-band diagnostic & provenance guard; hold `rhythm_lock` steady under `beat` mute (P3); move Mode Studio mutes to `Ctrl+B/L/S/T/M` + `Ctrl+0`; promote `Impact_shockwave_mode` (`LEAD="beat"`) and `Shining_stars_mode` (`(1 - lock)` fallback + `crc32` seed) to `CONFORMING_MODES_PHASE_4A` | **COMPLETED** |
| **2026-10-28** | [`2026-10-28_choreography_doctrine_and_batch0.md`](2026-10-28_choreography_doctrine_and_batch0.md) | Antigravity | Choreography Doctrine (Law 7: One Lead Timescale) & Batch 0 Mode Removals: remove 8 retired modes (`21 -> 13`), declare `LEAD`/`SECONDARY` across all 13 modes, build `DriverMuteProxy` + 13×4 stimulus measurement (`python -m tools.choreography_matrix`), add Mode Studio mute toggles (`Ctrl+B/L/S/T/M/0`), and enforce governance + calibrated dominance tests | **COMPLETED** |
| **2026-10-27** | [`2026-10-27_modes_part1_contract_and_bug_fixes.md`](2026-10-27_modes_part1_contract_and_bug_fixes.md) | Antigravity | Modes Audit & Contract Alignment (Part 1): resolve `S1`–`S7` (`transition_scale` cooperative handshake, `MODE_DNA` spatial roles, phase staggering, `drop_decay`, public `asserved_fft_band`, chroma floor subtraction, full-strip Silence Law decay) and fix 7 mode rendering bugs | **COMPLETED** |
| **2026-10-27** | [`2026-10-27_esp32_compact_control_panel.md`](2026-10-27_esp32_compact_control_panel.md) | Antigravity | Compact ESP32 Control Panel (`Fake_ESP32.py --hud-only`): display Segment Modes table, Transition Tester controls, and optional Music Analyzer HUD in `"esp32"` mode without rendering simulated LEDs | **COMPLETED** |
| **2026-10-27** | [`2026-10-27_docs_consolidation_plan_v2.md`](2026-10-27_docs_consolidation_plan_v2.md) | Antigravity | Vialactée Docs Consolidation (Plan v2) & Post-Audit Fixes: single `docs/` root (0 `.md` in code dirs), `mode_contract.md`, `core_orchestrator.md`, `web_ui_design_system.md`, governance link/backtick/schema parity tests, and restoration of `api_and_wire_protocol.md`, `contracts/README.md`, `raspberry_pi_deployment.md`, `docs/README.md`, and `AGENT_HANDOFF_2026-09-05.md` | **COMPLETED** |
| **2026-10-26** | [`2026-10-26_entity_architecture_and_trust_rated_contracts.md`](2026-10-26_entity_architecture_and_trust_rated_contracts.md) | Antigravity | Entity Architecture & Trust-Rated Contracts (v4): extract 10 DSP/context files from `core/` to `music/` with `music/api.py` door, consolidate trust-rated contracts in `docs/contracts/`, and enforce signal parity & mode trust tiers via AST governance tests | **COMPLETED** |
| **2026-10-24** | [`2026-10-24_subtle_mood_governance_and_resilient_modes.md`](2026-10-24_subtle_mood_governance_and_resilient_modes.md) | Antigravity | Subtle mood governance (`mood.modifiers()` cosine shock absorber, 4.0s palette dwell) & refactoring all 21 modes for continuous, scene-branch-free, flywheel-resilient visuals | **COMPLETED** |
| **2026-10-19** | [`2026-10-19_modes_audit_and_phase1.md`](2026-10-19_modes_audit_and_phase1.md) | Antigravity | Modes audit, removal of Alcool_randomer & Matrix_rain, shared `Mode` helpers (drop_hit, palette LUT, beat_pulse...), Coloured_middle_wave transition-buffer fix, Extending_waves polish | **IN PROGRESS** |
| **2026-10-14** | [`2026-10-14_architectural_simplification_and_config_removal.md`](2026-10-14_architectural_simplification_and_config_removal.md) | Antigravity | Architectural simplification (5 steps): 4-scene migration, `BeatGridQuantizer` & `band_peak` removal, `Segment` caching & transition deduplication, staggered auto-transitions, and complete removal of presets/playlists/configurations (`AppConfigStore`) | **COMPLETED** |
| **2026-10-14** | [`2026-10-14_skills_audit_pruning_and_eval_engine.md`](2026-10-14_skills_audit_pruning_and_eval_engine.md) | Antigravity | Skills audit across 223 past conversations, pruning redundant skills to archive, harmonizing Research Manager & Researcher, building automated skill governance test & eval engine | **COMPLETED** |
| **2026-10-14** | [`2026-10-14_agent_environment_cleanup.md`](2026-10-14_agent_environment_cleanup.md) | Antigravity | Agent environment cleanup: reconcile 30 FPS budget, slim `AGENT.md`, split researcher skill, fix `hardware-deploy` YAML frontmatter | **COMPLETED** |
| **2026-10-13** | [`2026-10-13_transitions_sector_cleanup_and_desync_fix.md`](2026-10-13_transitions_sector_cleanup_and_desync_fix.md) | Antigravity | Transitions sector cleanup: fix all-blocked director desync, delete dead director state & pass `dt` directly, remove `_Host`/`_SegmentView`/`_MusicView` shim, deduplicate `engine.py`/`stagger.py`, update `transition_contract.md` | **COMPLETED** |
| **2026-10-13** | [`2026-10-13_startup_transition_instability_defense.md`](2026-10-13_startup_transition_instability_defense.md) | Antigravity | Startup Transition Instability: 5-layer multi-tier defense eliminating cold-start novelty spikes, ring buffer contamination, premature buildup triggers, and zero-phase downbeat fallthrough | **COMPLETED** |
| **2026-10-07** | [`2026-10-07_priority_3_per_segment_and_staggered_transitions.md`](2026-10-07_priority_3_per_segment_and_staggered_transitions.md) | Antigravity | Priority 3: Per-Segment & Staggered Transitions with local segment timing, director completion sync, cohort staggering patterns (`transitions/stagger.py`), and AXIOM-01/02 zero-allocation compliance | **COMPLETED** |
| **2026-10-02** | [`2026-10-02_pure_random_startup_and_playlist_retirement.md`](2026-10-02_pure_random_startup_and_playlist_retirement.md) | Antigravity | Pure random startup, playlist retirement, Mode_master delegation to LocalTransitionManager, 6 mood palettes in LiveDeck, app_config settings persistence | **COMPLETED** |
| **2026-10-02** | [`2026-10-02_local_audio_file_streaming_in_main.md`](2026-10-02_local_audio_file_streaming_in_main.md) | Gemini 3.8 Flash | Local MP3/WAV file streaming in `Main.py` with 5s lookahead parity, sample-accurate 60 FPS ingestion, Pygame simulator transport controls, and CLI options | **COMPLETED** |
| **2026-10-02** | [`2026-10-02_mode_dna_mood_and_flexible_transitions.md`](2026-10-02_mode_dna_mood_and_flexible_transitions.md) | Antigravity | Mode DNA catalog (`mode_dna.py`), master color harmony (`GlobalMoodManager.py`), probabilistic cohort matchmaking & downbeat quantization (`LocalTransitionManager.py`), Mode delegation hooks | **COMPLETED** |
| **2026-10-02** | [`2026-10-02_offer_4_unified_3_tier_musical_context.md`](2026-10-02_offer_4_unified_3_tier_musical_context.md) | Antigravity | Offer 4: Unified 3-Tier Musical Context (`core/MusicalContextEngine.py`): Tier 1 continuous kinetics, Tier 2 macro scenes (`CHILL`, `GROOVE`, `BUILDUP`, `DROP_IMPACT`), Tier 3 micro badges, full backward compatibility, updated developer studios | **COMPLETED** |
| **2026-10-02** | [`2026-10-02_unified_visual_conductor.md`](2026-10-02_unified_visual_conductor.md) | Antigravity | Unified Visual Conductor (`MusicalContextEngine.py`): multi-signal ingestion, $\Delta P$, Schmitt triggers, triple-trigger drop buildup, silence guard, visual facade (`energy`, `tension`, `is_drop_impact`, `tilt`, `vertical_center`) | **COMPLETED** |
| **2026-10-02** | [`2026-10-02_developer_tools_salience_telemetry.md`](2026-10-02_developer_tools_salience_telemetry.md) | Antigravity | Developer Tools upgrade (`mode_studio.py` and `music_studio.py`): 5-card HUD, canonical regime badges, salience/trust gauges, countdown alerts, and 2x2 state matrix | **COMPLETED** |
| **2026-10-02** | [`2026-10-02_musical_context_engine.md`](2026-10-02_musical_context_engine.md) | Antigravity | Musical Context Engine (`core/MusicalContextEngine.py`), 6 canonical regimes, delayed `beat_trust` in `Listener.py`, Schmitt trigger hysteresis, pre-drop countdown | **COMPLETED** |
| **2026-10-02** | [`2026-10-02_rhythmic_salience_contract_and_modes.md`](2026-10-02_rhythmic_salience_contract_and_modes.md) | Antigravity | Real-time `rhythm_salience` engine (4 pillars), Audio Analyzer contract, `beat_tag` speaker delay fix, `band_peak` removal, `Shining_stars_mode` migration | **COMPLETED** |
| **2026-09-29** | [`2026-09-29_architectural_reorganization_and_axioms_governance.md`](2026-09-29_architectural_reorganization_and_axioms_governance.md) | Antigravity | Architectural Reorg v2.2: 9 Golden Axioms, 5-Tier docs, headless telemetry decoupling, ratchet headroom reclaim, fast governance CI | **COMPLETED** |
| **2026-09-28** | [`2026-09-28_master_production_plan_implementation.md`](file:///c:/Users/Users/Desktop/vialactée/vialactee/work_history/2026-09-28_master_production_plan_implementation.md) | Antigravity | Master Production Plan v2.0 execution: headless testing, network throttling, 4 modes, full-scope atomic debouncing, code governance | **COMPLETED** |
| **2026-09-23** | [`2026-09-23_project_cleanup_and_work_history.md`](file:///c:/Users/Users/Desktop/vialactée/vialactee/work_history/2026-09-23_project_cleanup_and_work_history.md) | Gemini 3.8 Flash | Project diagnostic, root cleanup, `.gitignore` resolution, and establishing `work_history/` | **COMPLETED** |
| *2026-09-05* | [`docs/archive/AGENT_HANDOFF_2026-09-05.md`](../docs/archive/AGENT_HANDOFF_2026-09-05.md) | Prior Agent | Audio DSP benchmark engine, synthetic suite (F1 92.0%), and BeatNet neural references | *HISTORICAL* |
| *2026-05-22* | `.agents/reviews/2026-05-22_review_resume.md` | Prior Review | Code review, webapp review, and architecture sync | *HISTORICAL* |
| *2026-05-12* | `.agents/reviews/2026-05-12_review_resume.md` | Prior Review | Initial comprehensive code & webapp review | *HISTORICAL* |

---

## Guidelines for Entries

* **Be explicit about testing**: Never write "tests passed" without showing the command and pass count (e.g. `python -m pytest -q` $\to$ `110 passed`).
* **Preserve failure notes**: Documenting what failed and why is twice as valuable as documenting what worked.
* **Keep file links clickable**: Always format links using relative or workspace markdown paths.
