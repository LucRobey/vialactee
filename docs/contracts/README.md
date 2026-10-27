# 🔒 Vialactée Sector Contracts (`docs/contracts/`)

> **Tier 1 — Canonical Specifications.** Each file here is the **front-door contract** for one sealed sector of the codebase. Nothing crosses a sector wall except what is listed in its contract, and each contract is backed by an executable governance test.

## The Four Sectors

| Sector | Code | Front Door | Contract | Governance Test |
| :--- | :--- | :--- | :--- | :--- |
| **Music & DSP** | [`music/`](../../music/) | [`music/api.py`](../../music/api.py) | [**`music_analyzer_contract.md`**](./music_analyzer_contract.md) | `tests/governance/test_music_isolation.py`, `tests/test_analyzer_contract_compliance.py` |
| **Mood & Palettes** | [`mood/`](../../mood/) | [`mood/api.py`](../../mood/api.py) | [**`mood_contract.md`**](./mood_contract.md) | `tests/governance/test_mood_isolation.py` |
| **Transitions** | [`transitions/`](../../transitions/) | [`transitions/api.py`](../../transitions/api.py) | [**`transition_contract.md`**](./transition_contract.md) | `tests/governance/test_transition_isolation.py` |
| **Visual Modes** | [`modes/`](../../modes/) | [`modes/Mode.py`](../../modes/Mode.py) | [**`mode_contract.md`**](./mode_contract.md) | `tests/test_all_modes_musical_context.py`, `tests/test_mode_helpers.py` |

## How the Sectors Connect

```
  microphone / audio file
            │
            ▼
   ┌─────────────────┐
   │     music/      │  ──► music_analyzer_contract.md
   │   (music.api)   │      (every signal carries a 🟢 HIGH / 🟡 MEDIUM / 🟠 LOW trust rating)
   └────────┬────────┘
            │  Listener + MusicalContext (speaker-aligned)
     ┌──────┴──────────────────────┐
     ▼                             ▼
┌──────────┐                 ┌──────────────┐
│  mood/   │                 │ transitions/ │
│(mood.api)│                 │(transitions. │
└────┬─────┘                 │     api)     │
     │ mood_colors (4,3)     └──────┬───────┘
     │ mood_pace/sharpness/         │ TransitionOrders + blend()
     │ trail/accent (2.5s xfade)    │ + cooperative handshake
     └──────────────┬───────────────┘
                    ▼
             ┌─────────────┐
             │   modes/    │  ──► mode_contract.md
             │  (Mode.py)  │
             └─────────────┘
```

All four sectors are wired together in [`core/Mode_master.py`](../../core/Mode_master.py) and [`core/Segment.py`](../../core/Segment.py) (see [`docs/architecture/core_orchestrator.md`](../architecture/core_orchestrator.md)).
