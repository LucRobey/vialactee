"""
Tests for the cast Global Mode family (segment-as-fixture): utils/cast.py helpers,
modes/Cast_mode_base.py, and the 6 cast modes (Tableaux, Bar Clock, Construction, Flip-Flop,
Negative Space, Mosaic). Enforces Cast Laws C1-C6 plus Laws 1.5, 3, 4, 5, 6 and 7 of
docs/contracts/global_mode_contract.md.
"""
import gc
import inspect
import json
import os
import sys
import time
import tracemalloc
import unittest

import numpy as np

from modes.Mode import Mode as BaseMode
from modes.Cast_mode_base import Cast_mode_base
from modes.Tableaux_mode import Tableaux_mode
from modes.Bar_clock_mode import Bar_clock_mode, RUNG_ORDER
from modes.Construction_mode import Construction_mode
from modes.Flip_flop_mode import Flip_flop_mode
from modes.Negative_space_mode import Negative_space_mode
from modes.Mosaic_mode import Mosaic_mode
from tests.test_mode_helpers import TestDeadSettingsRatchet
from tools.choreography_matrix import (
    DEFAULT_NB_BANDS, MATRIX_CONFIG, SyntheticListener, measure_mode_choreography, step_synthetic_music,
)
from utils.cast import (
    ALL_SEGMENTS, BUILD_ORDER, CANOPY, LOOKS, MIRROR_PAIRS, PILLARS, RUNGS, TABLEAUX_POSES,
    CastClock, build_fixtures,
)

CAST_MODE_SPECS = [
    ("Tableaux", Tableaux_mode, "beat"),
    ("Bar Clock", Bar_clock_mode, "beat"),
    ("Construction", Construction_mode, "beat"),
    ("Flip-Flop", Flip_flop_mode, "beat"),
    ("Negative Space", Negative_space_mode, "transient"),
    ("Mosaic", Mosaic_mode, "beat"),
]
SMALL_SEGMENTS = ("s1", "s2", "s3")


def _make(cls, seg_name, listener, n=48, infos=None):
    rgb = np.zeros((n, 3), dtype=np.int32)
    mode = cls(cls.__name__, seg_name, listener, None, list(range(n)), rgb, infos or {})
    mode.start()
    return mode


def _chandelier(cls, listener, segments=ALL_SEGMENTS, infos=None):
    return {s: _make(cls, f"Segment {s}", listener, infos=infos) for s in segments}


def _lit(modes):
    return frozenset(s for s, m in modes.items() if int(m.rgb_list.max()) > 0)


def _fixture_state(modes):
    return frozenset((s, fx.seg) for s, m in modes.items() for fx in m.fixtures if fx.on)


def _run_lockstep(modes, listener, frames, start=0, mods=None, on_step=None):
    """Advance the synthetic clip and every instance in lockstep; call on_step(modes) after each step."""
    mods = mods if mods is not None else np.array([1.0, 1.0, 1.0, 0.0], dtype=np.float32)
    ref = next(iter(modes.values()))
    for f in range(start, start + frames):
        step_synthetic_music(listener, f, mods)
        for m in modes.values():
            m.run()
        if on_step is not None and ref.clock.stepped:
            on_step(modes)


class TestCastHelpers(unittest.TestCase):
    def test_topology_covers_full_profile_and_mirror_pairs(self):
        self.assertEqual(set(BUILD_ORDER), set(ALL_SEGMENTS))
        self.assertEqual(len(ALL_SEGMENTS), 11)
        paired = {s for pair in MIRROR_PAIRS for s in pair}
        self.assertEqual(paired | {"h20"}, set(ALL_SEGMENTS))
        for density in TABLEAUX_POSES:
            for pose in density:
                self.assertTrue(pose and pose <= set(ALL_SEGMENTS))

    def test_fixture_resolution_canonical_small_and_composite(self):
        coord = np.zeros(60)
        one = build_fixtures("v2", "pillar", 60, 20, 40, coord, 0.3)
        self.assertEqual([(f.start, f.stop, f.seg) for f in one], [(0, 60, "v2")])
        self.assertAlmostEqual(coord[0], 0.0)      # pillars fill from the floor (LED 0)
        self.assertAlmostEqual(coord[59], 1.0)
        small = build_fixtures("s2", "pillar", 60, 20, 40, coord, 0.3)
        self.assertEqual([f.seg for f in small], list(PILLARS))
        composite = build_fixtures("studio_preview", "composite", 60, 20, 40, coord, 0.3)
        self.assertEqual([f.seg for f in composite], list(PILLARS + RUNGS + CANOPY))
        self.assertEqual(composite[0].start, 0)
        self.assertEqual(composite[-1].stop, 60)

    def test_cast_clock_locked_fallback_and_reset(self):
        clock = CastClock()
        clock.update(10, 0.9, 0.0, 0.5, 1 / 60)          # priming frame never steps
        self.assertEqual(clock.step, 0)
        self.assertTrue(clock.update(11, 0.9, 0.0, 0.5, 1 / 60))
        self.assertFalse(clock.update(11, 0.9, 5.0, 0.5, 1 / 60))   # locked: onsets ignored
        self.assertEqual(clock.step, 1)
        # Unlocked: a bass onset steps, but only after the refractory period
        self.assertFalse(clock.update(11, 0.0, 0.0, 0.5, 1 / 60))
        clock.since_step = 0.30
        self.assertTrue(clock.update(11, 0.0, 0.9, 0.5, 1 / 60))
        self.assertFalse(clock.update(11, 0.0, 0.9, 0.5, 1 / 60))
        # Unlocked with no onsets: the energy-scaled timer still steps (Cast Law C3)
        steps_before = clock.step
        for _ in range(120):
            clock.update(11, 0.0, 0.0, 1.0, 1 / 60)
        self.assertGreater(clock.step, steps_before)
        clock.reset()
        self.assertEqual((clock.step, clock.locked), (0, False))


class TestCastModes(unittest.TestCase):
    def setUp(self):
        BaseMode.reset_mood_colors()
        self.addCleanup(BaseMode.reset_mood_colors)

    def test_registered_in_modes_json_and_flagged_cast(self):
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "modes.json")
        with open(path, "r", encoding="utf-8") as f:
            entries = {m["name"]: m for m in json.load(f)["global_modes"]}
        for name, cls, lead in CAST_MODE_SPECS:
            with self.subTest(mode=name):
                self.assertIn(name, entries)
                self.assertEqual(entries[name]["class"], cls.__name__)
                self.assertIn(f"lead:{lead}", entries[name]["tags"])
                self.assertTrue(cls.IS_GLOBAL)
                self.assertEqual(cls.FAMILY, "cast")
                self.assertEqual(cls.LEAD, lead)
                self.assertFalse(cls.__dict__.get("ABSTRACT", False))
                self.assertIn("Lead:", cls.__doc__)
        self.assertTrue(Cast_mode_base.ABSTRACT)

    def test_lockstep_alive_agreeing_and_silent(self):
        """C5 + C3 + Law 1.5: all instances agree, stay alive with and without beat lock, decay to black."""
        for name, cls, _ in CAST_MODE_SPECS:
            for segments in (ALL_SEGMENTS, SMALL_SEGMENTS):
                with self.subTest(mode=name, profile=len(segments)):
                    listener = SyntheticListener()
                    modes = _chandelier(cls, listener, segments)
                    seen = set()
                    _run_lockstep(modes, listener, 240, on_step=lambda ms: seen.add(_fixture_state(ms)))
                    steps = {m.clock.step for m in modes.values()}
                    self.assertEqual(len(steps), 1, "instances disagree on the step count")
                    self.assertGreater(len(seen), 1, "chandelier never changed state")
                    self.assertTrue(any(seen), "chandelier never lit")

                    # Flywheel lost: steps keep coming from onsets / timer
                    listener.beat_trust = listener.context.beat_trust = 0.0
                    listener.rhythm_salience = listener.context.salience = 0.0
                    before = modes[segments[0]].clock.step
                    _run_lockstep(modes, listener, 180, start=240)
                    if cls is not Negative_space_mode:
                        self.assertGreater(modes[segments[0]].clock.step, before)
                    self.assertTrue(any(int(m.rgb_list.max()) > 0 for m in modes.values()))

                    listener.context.is_silent = True
                    for _ in range(180):
                        for m in modes.values():
                            m.run()
                    for s, m in modes.items():
                        self.assertTrue(np.all(m.rgb_list == 0), f"{name}/{s} failed to decay to black")

    def test_rules(self):
        """Per-mode rule invariants observed on every step of a lockstep chandelier."""
        checks = {
            Bar_clock_mode: lambda lit, ms: self.assertEqual(len(lit & set(PILLARS)), 1),
            Flip_flop_mode: lambda lit, ms: [self.assertFalse(a in lit and b in lit) for a, b in MIRROR_PAIRS],
            Construction_mode: lambda lit, ms: self.assertEqual(
                ms["v2"]._built if not ms["v2"]._dark else 0,
                len(lit) if not ms["v2"]._dark else 0,
            ),
        }
        for cls, check in checks.items():
            with self.subTest(mode=cls.__name__):
                listener = SyntheticListener()
                modes = _chandelier(cls, listener, infos={"look": "snap"})
                count = [0]

                def on_step(ms):
                    for m in ms.values():          # settle one frame past the strike crest
                        m.run()
                    count[0] += 1
                    check(_lit(ms), ms)

                _run_lockstep(modes, listener, 600, on_step=on_step)
                self.assertGreater(count[0], 10)

        # Construction lights exactly k segments, in build order, at phrase step k-1
        listener = SyntheticListener()
        modes = _chandelier(Construction_mode, listener, infos={"look": "snap"})
        _run_lockstep(modes, listener, 60 * 3)
        built = modes["v2"]._built
        self.assertEqual({s for s in BUILD_ORDER[:built]}, set(_lit(modes)) if not modes["v2"]._dark else set())

        # Mosaic: lit segments stay lit; each step changes exactly one segment (switch on or new colour)
        mosaic = _make(Mosaic_mode, "Segment v1", SyntheticListener())
        prev = dict(mosaic._slots)
        for step in range(1, 300):
            mosaic.clock.step = step
            mosaic.on_step(mosaic.clock)
            changed = [s for s in ALL_SEGMENTS if mosaic._slots[s] != prev[s]]
            self.assertEqual(len(changed), 1, f"step {step}: {changed}")
            self.assertTrue(all(mosaic._slots[s] != -1 for s in ALL_SEGMENTS if prev[s] != -1))
            prev = dict(mosaic._slots)
        self.assertTrue(all(v != -1 for v in prev.values()), "mosaic never filled the chandelier")

        # Tableaux never holds the same pose twice in a row
        tab = _make(Tableaux_mode, "Segment v1", SyntheticListener())
        keys = []
        for step in range(0, 400, 4):
            tab.clock.step = step
            tab.energy = (step % 13) / 13.0
            tab.on_step(tab.clock)
            keys.append(tab._pose_key)
        self.assertTrue(all(a != b for a, b in zip(keys, keys[1:])))

    def test_negative_space_cuts_tagged_group(self):
        listener = SyntheticListener()
        modes = _chandelier(Negative_space_mode, listener, infos={"look": "snap"})
        for tag, group in (("Bass/Kick", PILLARS), ("Snare/Mid", RUNGS), ("Hi-hat/Cymbal", CANOPY)):
            with self.subTest(tag=tag):
                for m in modes.values():
                    m.on_reset()
                listener.context.energy = 0.3
                listener.beat_tag = tag
                listener.is_real_beat = listener.context.is_real_beat = True
                for m in modes.values():
                    m.run()
                listener.is_real_beat = listener.context.is_real_beat = False
                for m in modes.values():
                    m.run()
                self.assertEqual(set(ALL_SEGMENTS) - _lit(modes), set(group))

    def test_every_look_renders_with_pure_black_off(self):
        for name, cls, _ in CAST_MODE_SPECS:
            for look in LOOKS:
                with self.subTest(mode=name, look=look):
                    listener = SyntheticListener()
                    modes = _chandelier(cls, listener, infos={"look": look})
                    lit_any = False
                    mods = np.array([1.0, 1.0, 1.0, 0.0], dtype=np.float32)
                    for f in range(200):
                        step_synthetic_music(listener, f, mods)
                        for m in modes.values():
                            m.run()
                            for fx in m.fixtures:
                                if not fx.on and fx.off_age > 0.2:
                                    self.assertEqual(int(m.rgb_list[fx.start:fx.stop].max()), 0)
                            lit_any = lit_any or int(m.rgb_list.max()) > 0
                    self.assertTrue(lit_any)

    def test_axiom_01_and_02(self):
        files = ("Cast_mode_base.py", "cast.py")
        for name, cls, _ in CAST_MODE_SPECS:
            for seg, n in (("studio_preview", 60), ("Segment h00", 205)):
                with self.subTest(mode=name, seg=seg):
                    listener = SyntheticListener()
                    mode = _make(cls, seg, listener, n=n, infos={"look": "rise"})
                    mods = np.array([1.0, 1.0, 1.0, 0.0], dtype=np.float32)
                    for f in range(60):
                        step_synthetic_music(listener, f, mods)
                        mode.run()
                    gc.collect()
                    tracemalloc.start()
                    s1 = tracemalloc.take_snapshot()
                    for _ in range(100):
                        mode.run()
                    s2 = tracemalloc.take_snapshot()
                    tracemalloc.stop()
                    allocs = [
                        st for st in s2.compare_to(s1, "lineno")
                        if any(fn in st.traceback.format()[0] for fn in files + (cls.__module__.split(".")[-1] + ".py",))
                        and st.size_diff > 512
                    ]
                    self.assertEqual(allocs, [], f"AXIOM-02 violation in {name}: {allocs}")
                    t0 = time.perf_counter()
                    for _ in range(200):
                        mode.run()
                    frame_ms = (time.perf_counter() - t0) * 1000.0 / 200.0
                    self.assertLessEqual(frame_ms, 0.20, f"{name} on {seg}: {frame_ms:.4f} ms > 0.20 ms")

    def test_law_7_lead_dominance(self):
        for name, cls, lead in CAST_MODE_SPECS:
            with self.subTest(mode=name):
                res = measure_mode_choreography(cls, **MATRIX_CONFIG, nb_bands=DEFAULT_NB_BANDS)
                contribs = res["contributions"]
                self.assertEqual(max(contribs, key=contribs.get), lead, f"{name}: {contribs}")
                budget = res["r_std_full"] - res["r_std_mute_all"]
                self.assertGreaterEqual(res["lead_contrib"], 0.30 * budget)
                self.assertGreaterEqual(res["r_std_mute_sec"], 0.65 * res["r_std_full"])

    def test_law_5_settings_honesty_and_geometry_rebind(self):
        for name, cls, _ in CAST_MODE_SPECS:
            with self.subTest(mode=name):
                mode = _make(cls, "Segment v1", SyntheticListener())
                used = set()
                for klass in cls.__mro__:
                    if klass.__module__.startswith("modes."):
                        used |= TestDeadSettingsRatchet._self_loads_outside_setup(
                            inspect.getsource(sys.modules[klass.__module__])
                        )
                schema = mode.get_settings_schema()
                self.assertEqual(schema[0]["key"], "look")
                self.assertEqual([o["value"] for o in schema[0]["options"]], list(LOOKS))
                for descriptor in schema:
                    self.assertIn(descriptor["attr"], used, f"{name} declares dead setting {descriptor['attr']!r}")
                mode.bind_segment_geometry("h00", "horizontal", ("tier:canopy", "half:left"), None)
                self.assertEqual([f.seg for f in mode.fixtures], ["h00"])


if __name__ == "__main__":
    unittest.main()
