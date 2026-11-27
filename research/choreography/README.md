# research/choreography: the choreography lab

Where light shows are tried, compared and judged, without touching the installation. Design:
`research/analyzer_trials/papers/P3_choreography_contract.md` (draft, not answered by the owner yet).

There is no ground truth for a show. A mode is judged in three layers: laws (the existing mode tests),
measures (numbers that filter out what clearly fails), and the owner's choice between versions of a clip.
Only the owner's choice promotes a mode.

## What is here

| File | Role |
|---|---|
| `layout.py` | the 11 segments and the room position of the 1,304 LEDs, from `config/segments_full.json` |
| `feeds.py` | what a mode under test hears through `listener.signals`: the truth, an analyzer's recording, or nothing extra |
| `render.py` | plays a song through the production `Listener` (5 s look-ahead), lays the feed over its signals, and draws one mode instance per segment |
| `measures.py` | first measures: kick punch, alive |
| `build_clips.py` | renders a passage once per feed and writes a clip (frames, audio, `meta.json`) |
| `profile.py` | what the light does on a passage, in numbers and in words: amount of light, reaction to a kick, a snare, a drop, behaviour in a break, where the light sits, colours, flicker, repetition |
| `pictures.py` | stills an agent can read: the time strip, the contact sheet, the reaction curves |
| `profile_clip.py` | profiles every version of the clips already built (`output/profiles/<clip>/PROFILE.md`) |
| `clip_server.py`, `clips.html` | the page where the owner watches versions side by side and chooses |
| `candidates/` | lab modes. Not registered, never run on the installation |
| `verdicts.jsonl` | every choice the owner makes, appended. Committed: it is the owner's word |

## Use

    research/analyzer_trials/.venv/Scripts/python.exe -m research.choreography.build_clips --defaults
    research/analyzer_trials/.venv/Scripts/python.exe -m research.choreography.clip_server

then open http://127.0.0.1:8768 (or start `choreography-clips` from `.claude/launch.json`). About 15 s to
build a clip. Clips go to `output/` (not committed: they contain audio). Tests:
`python -m pytest research/tests/test_choreography_lab.py tests/governance/test_lab_isolation.py`.

## How an agent sees a mode

An agent cannot watch a clip. After `build_clips`, run

    research/analyzer_trials/.venv/Scripts/python.exe -m research.choreography.profile_clip

and read `output/profiles/<clip>/PROFILE.md`: a table of the versions side by side, a paragraph in words per
version, and three pictures per version. Open the pictures: the time strip (time left to right, LEDs top to
bottom, truth marks above) shows in one look whether flashes fall on the kicks, whether a break is calm, and
whether anything travels. The profile says what a show does, never whether it is good.

## The three feeds

The same mode is drawn three times on the same passage:

| Feed | The mode hears | It shows |
|---|---|---|
| truth | every signal of the contract, from the truth file | the best the idea can look |
| candidate | the signals a research analyzer produced on that song (the music lab's recording) | what the installation could do |
| today | the production analyzer as it is; empty slots fall back inside the mode | what the installation does now |

Everything else the mode reads (energy, beat phase, mood colours) comes from the production `Listener` in
all three cases, so the versions differ only by the signals under test.

## Rules

- **The two labs never import each other** (`tests/governance/test_lab_isolation.py`). This lab reaches the
  analyzer only through `music.api`. What it takes from the music lab is data: the signal contract
  (`config/music_signals.json`), the truth files, and recordings whose columns are the contract's slot names.
- **A lab mode names a fallback for every signal it reads**, so it still works on today's analyzer.
- **A mode that reads a signal the installation does not have cannot be promoted** until that signal is there.
- **Measures filter, they do not rank.** No threshold is set yet.
- **Choices are blind by default**: the page shuffles the versions and says which was which only after the
  owner has chosen.

## Not built yet

- the "realistic" feed (truth degraded by a measured error profile);
- thresholds on the profile's numbers (none is set: they describe, they do not judge yet);
- "what drives it": the profile under the mute test (beat, level, spectrum, hits muted in turn);
- passages drawn at random on held-out tracks, hidden references, repeated pairs;
- comparing two different modes (the page compares feeds of one mode);
- a check against the real installation: the page is a drawing on a screen.
