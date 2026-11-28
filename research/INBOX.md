# Waiting for you

Built 2026-11-27 by `python -m research.inbox`. Do not edit by hand.

**0 proposal(s) to answer, 12 clip(s) to watch.**

## Music lab: proposals waiting for your yes or no

Nothing is waiting.

## Choreography lab: clips waiting for your choice

Start the clip page (`choreography-clips`, http://127.0.0.1:8768): the waiting clips come first.

- `Beat_blast_kick_mode` against `Monolithic_beat_blast_mode`, track 19 from 208 s (nominated 2026-11-27): Same rings as Monolithic Beat Blast, but punched by the kick the analyzer hears (rationed, never 4 flashes a second), calm in breaks, bass at the core and treble at the rim. Which one shows the beat better?
- `Beat_blast_kick_mode` against `Monolithic_beat_blast_mode`, track 13 from 30 s (nominated 2026-11-27): Same rings as Monolithic Beat Blast, but punched by the kick the analyzer hears (rationed, never 4 flashes a second), calm in breaks, bass at the core and treble at the rim. Which one shows the beat better?
- `Beat_blast_kick_mode` against `Monolithic_beat_blast_mode`, track 20 from 160 s (nominated 2026-11-27): Same rings as Monolithic Beat Blast, but punched by the kick the analyzer hears (rationed, never 4 flashes a second), calm in breaks, bass at the core and treble at the rim. Which one shows the beat better?
- `Ripple_kick_mode` against `Concentric_radial_ripple_mode`, track 19 from 208 s (nominated 2026-11-27): Same violet rings as Concentric Radial Ripple, but one ring and a white heart per heard kick, and a steady drift in breaks instead of pulsing on predicted beats. Is the kick clearer, and is the break right?
- `Ripple_kick_mode` against `Concentric_radial_ripple_mode`, track 13 from 30 s (nominated 2026-11-27): Same violet rings as Concentric Radial Ripple, but one ring and a white heart per heard kick, and a steady drift in breaks instead of pulsing on predicted beats. Is the kick clearer, and is the break right?
- `Ripple_kick_mode` against `Concentric_radial_ripple_mode`, track 20 from 160 s (nominated 2026-11-27): Same violet rings as Concentric Radial Ripple, but one ring and a white heart per heard kick, and a steady drift in breaks instead of pulsing on predicted beats. Is the kick clearer, and is the break right?
- `Band_vu_mode` against `Architectural_vu_equalizer_mode`, track 19 from 208 s (nominated 2026-11-27): A three-band equalizer instead of one column: bass red in the outer pillars and low bridges (punched white on each heard kick), middle amber in the inner pillars, treble cool white on the canopy. Can you read bass and treble apart, and is the kick clear?
- `Band_vu_mode` against `Architectural_vu_equalizer_mode`, track 13 from 30 s (nominated 2026-11-27): A three-band equalizer instead of one column: bass red in the outer pillars and low bridges (punched white on each heard kick), middle amber in the inner pillars, treble cool white on the canopy. Can you read bass and treble apart, and is the kick clear?
- `Band_vu_mode` against `Architectural_vu_equalizer_mode`, track 20 from 160 s (nominated 2026-11-27): A three-band equalizer instead of one column: bass red in the outer pillars and low bridges (punched white on each heard kick), middle amber in the inner pillars, treble cool white on the canopy. Can you read bass and treble apart, and is the kick clear?
- `Avalanche_bands_mode` against `Spectral_avalanche_mode`, track 19 from 208 s (nominated 2026-11-27): Same falling waterfall as Spectral Avalanche, but calm (the original strobes: up to 19.5 flashes a second), lit by bass low, mid middle, treble high, and flaring with a white front on every heard kick. Is it still an avalanche, and is the kick clear?
- `Avalanche_bands_mode` against `Spectral_avalanche_mode`, track 13 from 30 s (nominated 2026-11-27): Same falling waterfall as Spectral Avalanche, but calm (the original strobes: up to 19.5 flashes a second), lit by bass low, mid middle, treble high, and flaring with a white front on every heard kick. Is it still an avalanche, and is the kick clear?
- `Avalanche_bands_mode` against `Spectral_avalanche_mode`, track 20 from 160 s (nominated 2026-11-27): Same falling waterfall as Spectral Avalanche, but calm (the original strobes: up to 19.5 flashes a second), lit by bass low, mid middle, treble high, and flaring with a white front on every heard kick. Is it still an avalanche, and is the kick clear?

## Standing questions

- **Which tracks are kept aside?** We have 20 songs with a source of truth, and that is all of them. An agent tunes its idea on some songs; to know the idea is not just fitted to those, it must be checked on songs it never looked at. With only 20, the labs split them: 10 to tune on, 10 to check (`scoreboard/split.json`, odd and even numbers). Asked again on 2026-11-27 ("I thought we had 20"). Two ways to settle it: keep this split, or add new songs (the techno tracks below) and keep those aside so that all 20 can be tuned on.
- **Techno tracks.** The 20 truth tracks have 7 electronic ones, none of them hard techno. Pick the tracks you want the labs to be good on.
- **Drops, build-ups and section changes by ear.** (The no-beat lane is done: checked on all 20 songs on 2026-11-27.) No tool settles these, so the labs cannot grade them reliably. A first version is drawn for all three in the review tool (`truth-review`, port 8766), and `truth/REVIEW_LIST.md` says song by song what to look at. The owner agreed on 2026-11-27 to correct them there. Each lane you check unlocks the matching line of the music work list.
- **Snare and hi-hat.** Same problem: one tool only. A second tool, or your ear on a few passages, is needed before the labs can propose them.
- **The gate limits of the choreography lab** (flash limit 3 per second, "follows the music" by 20 points, and the others in `choreography/check_mode.py`) are proposals. Say if one is wrong.
- **Papers P2, P3 and P4** (`analyzer_trials/papers/`) are still drafts you have not answered. The labs were built on their proposals.
- **Cost on the Raspberry Pi** of the five signals promoted on 2026-11-27 is not measured.
- **`no_beat`: two things in the grading that look wrong to me** (run `2026-11-27_no_beat`; not changed, the grading tools are locked). A track that has no no-beat stretch is not graded for this signal at all, so a candidate that says "no beat" by mistake on it loses nothing (4 of the 10 open tracks). And the silence at the very end of a song counts as "there is a beat" unless the truth marks it (Plastic People, 429 s to 431 s), so answering "no beat" in silence is counted as a mistake there. The lab's tables also print "checked" for `no_beat` when a single graded track is.
- **`Kick_bands_safe_mode`: is a full flash at most every 0.46 s the right price for safety?** (work list C01) To stay within three flashes a second on any music, the mode gives a full flash at most every 0.46 s; a kick or a snare that comes sooner only gets a thin line or a sparkle. A steady kick keeps its full flash on every beat up to 130 beats a minute; faster than that, every other kick is soft. With 0.40 s (every kick up to 150) the mode also passes the gate, but on made-up fast hits it reached 3.5 flashes in a second in 4 of 170 trials. Is 130 enough for the music you play?
- **The flash rule of the choreography gate is tried on three passages only** (none faster than about 128 beats a minute, none with fast irregular hits). The first version of `Kick_bands_safe_mode` passed it and could still go over the limit on made-up fast hits. A fast or irregular passage among the standard ones would close that hole. Not changed: the gate is locked for a lab agent.
- **`Beat_blast_kick_mode`: how much should a break move?** (work list C10) This lab copy of Monolithic Beat Blast keeps its rings drifting in a break but holds the total light nearly steady: the profile counts 8% to 12% of the normal movement (the original: 70% to 85%, but with 2.3 flashes a second on beats that are not there). Making the break pulse on the beat tracker brought 1.3 to 1.9 pulses a second back into the breaks, so I dropped it. On Nobody Rules the Streets you once preferred the version whose break kept moving. When you watch the three clips, say whether the break is too still.
- **Two installation modes fail the lab's flash rule** (found while adapting the Global Modes, C10 and C12). Through the gate, `Spectral_avalanche_mode` reaches 19.5 flashes in one second (Another One Bites The Dust; 6.5 to 19.5 on the three passages: its waterfall jumps with the frame-to-frame change of the 16 bands) and `Monolithic_beat_blast_mode` 3.5 (Nobody Rules the Streets); the limit is 3 (WCAG 2.3.1). Both run on the installation today and nothing was changed in `modes/` (locked for a lab agent). Careful: the clips `*_vs_Spectral_avalanche_mode_*` in your queue show the original strobing. Do you want them fixed in `modes/`, or replaced by their lab copies if you prefer those?

## Recently closed

- `2026-11-27_no_beat` (no_beat): approved by you on 2026-11-27
- `2026-11-27_best_beat` (beat, bpm): approved by you on 2026-11-27
- `2026-11-27_bands_kick` (kick, kick_present, band_bass, band_mid, band_high): approved by you on 2026-11-27

Where everything stands: [`scoreboard/STATUS.md`](scoreboard/STATUS.md) (signals) and [`choreography/STATUS.md`](choreography/STATUS.md) (modes).
