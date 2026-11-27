"""
tests/test_band_kick_signals.py
music/BandKickSignals.py: the five truth-mirrored slots the production analyzer writes itself
(band_bass, band_mid, band_high, kick, kick_present; docs/contracts/music_analyzer_contract.md section 6).

Driven here with a scripted kick stream, so the rules are checked without any audio:
the slots wait for the speakers, a kick comes out exactly look-ahead seconds after it was heard,
kick_present looks both ways, and a tick allocates nothing (AXIOM-02).
"""
import tracemalloc
import unittest

import numpy as np

from music.BandKickSignals import BandKickSignals
from music.MusicSignals import PRODUCED, MusicSignals

FPS = 60
LOOKAHEAD = 1.0
LEAD = int(LOOKAHEAD * FPS)
NB_BANDS = 32
no_beat = []          # the no_beat slot on every tick of the latest _run


def _run(seconds, kick_ticks, low_share=1.0, bands=None, bk=None, sig=None, confidence=1.0):
    """Feed `seconds` of ticks; a kick of the stream is one tick at 1.0. Returns the slots seen on every tick."""
    bk = bk or BandKickSignals(NB_BANDS, LOOKAHEAD)
    sig = sig or MusicSignals()
    bands = np.full(NB_BANDS, 10.0) if bands is None else bands
    seen = []
    no_beat.clear()
    for k in range(int(seconds * FPS)):
        y = 1.0 if k in kick_ticks else 0.0
        bk.update(k / FPS, 1.0 / FPS, bands, y, low_share * y, sig, confidence(k / FPS) if callable(confidence) else confidence)
        seen.append((sig.kick, sig.kick_present, sig.band_bass, sig.band_mid, sig.band_high))
        no_beat.append(sig.no_beat)
    return bk, sig, seen


class TestBandKickSignals(unittest.TestCase):
    def test_it_writes_exactly_the_produced_slots(self):
        _, sig, _ = _run(3.0, {30, 60, 90})
        filled = tuple(name for name, value in sig.as_dict().items() if value is not None)
        self.assertEqual(filled, tuple(n for n in MusicSignals.__slots__ if n in PRODUCED))

    def test_slots_wait_until_the_music_reaches_the_speakers(self):
        _, _, seen = _run(3.0, {30})
        for k in range(LEAD - 1):
            self.assertEqual(seen[k], (None, None, None, None, None), f"tick {k}")
        self.assertIsNotNone(seen[LEAD + 2][2])

    def test_a_kick_comes_out_lookahead_seconds_after_it_was_heard(self):
        kicks = set(range(60, 360, 30))                                  # every half second from 1.0 s to 5.5 s
        _, _, seen = _run(8.0, kicks)
        out = [k for k, s in enumerate(seen) if s[0]]
        self.assertEqual(len(out), len(kicks))
        for heard, played in zip(sorted(kicks), out):
            self.assertLessEqual(abs(played - (heard + LEAD)), 1, f"kick heard at tick {heard} came out at {played}")
        for k in out:
            self.assertTrue(0.0 < seen[k][0] <= 1.0)

    def test_kick_present_needs_a_kick_before_and_after(self):
        kicks = set(range(60, 360, 30))                                  # heard 1.0 s to 5.5 s, played 2.0 s to 6.5 s
        _, _, seen = _run(12.0, kicks)
        at = lambda speaker_seconds: seen[int(speaker_seconds * FPS)][1]
        self.assertIs(at(4.0), True)                                     # in the middle of the stretch
        self.assertIs(at(6.6), False)                                    # just after the last kick: none is coming
        self.assertIs(at(10.0), False)

    def test_no_beat_waits_for_the_speakers_then_needs_no_kick_and_an_unsure_tempo(self):
        kicks = set(range(240, 480, 30))                                 # kicks heard from 4.0 s to 7.5 s, played 5.0 s to 8.5 s
        unsure = lambda t: 0.2                                           # the tempo judge is unsure all along
        _run(14.0, kicks, confidence=unsure)
        at = lambda speaker_seconds: no_beat[int(speaker_seconds * FPS)]
        self.assertTrue(all(v is None for v in no_beat[:LEAD - 1]))      # nothing has reached the speakers yet
        self.assertIs(at(2.0), True)                                     # no kick around, judge unsure
        self.assertIs(at(6.5), False)                                    # kicks before and after
        self.assertIs(at(12.0), True)                                    # the kick is gone again

    def test_no_beat_stays_off_while_the_tempo_judge_is_sure(self):
        _run(8.0, set(), confidence=0.9)                                 # no kick at all, but a sure tempo: a pulse without drums
        self.assertFalse(any(v for v in no_beat if v is not None))
        self.assertIs(no_beat[-1], False)

    def test_a_peak_without_low_band_is_not_a_kick(self):
        _, _, seen = _run(5.0, set(range(60, 240, 30)), low_share=0.05)
        self.assertEqual(sum(1 for s in seen if s[0]), 0)

    def test_levels_stay_between_zero_and_one_and_fall_when_the_music_gets_quieter(self):
        bk, sig, loud = _run(3.0, set(), bands=np.full(NB_BANDS, 1000.0))
        _, _, quiet = _run(3.0, set(), bands=np.full(NB_BANDS, 1.0), bk=bk, sig=sig)
        for s in loud + quiet:
            for level in s[2:]:
                if level is not None:
                    self.assertTrue(0.0 <= level <= 1.0)
        for i in (2, 3, 4):
            self.assertGreater(loud[-1][i], quiet[-1][i] + 0.3)

    def test_reset_forgets_everything(self):
        bk, sig, _ = _run(4.0, set(range(60, 240, 30)))
        bk.reset()
        sig.clear()
        _, _, seen = _run(0.5, set(), bk=bk, sig=sig)
        self.assertTrue(all(s == (None, None, None, None, None) for s in seen))

    def test_axiom_02_a_tick_allocates_nothing(self):
        bk, sig, _ = _run(4.0, set(range(60, 240, 30)))                  # steady state: the delay line is full
        bands = np.full(NB_BANDS, 10.0)
        tracemalloc.start()
        before = tracemalloc.take_snapshot()
        for k in range(240, 540):
            y = 1.0 if k % 30 == 0 else 0.0
            bk.update(k / FPS, 1.0 / FPS, bands, y, y, sig)
        after = tracemalloc.take_snapshot()
        tracemalloc.stop()
        stats = [s for s in after.compare_to(before, "lineno") if "BandKickSignals.py" in s.traceback[0].filename]
        grown = sum(s.size_diff for s in stats if s.size_diff > 0)
        # a few float objects are swapped for new ones of the same size; an array per tick would be kilobytes
        self.assertLess(grown, 512, "\n".join(str(s) for s in stats))


if __name__ == "__main__":
    unittest.main()
