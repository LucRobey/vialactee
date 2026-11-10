"""
Tests for the ensemble Global Mode family (each part is an instrument with its own job):
modes/Ensemble_mode_base.py, tools/ensemble_matrix.py and the ensemble modes (Stalagmites).
Enforces Ensemble Laws E1-E6 plus Laws 1.5, 3, 4, 5 and 6 of docs/contracts/global_mode_contract.md.
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
from modes.Ensemble_mode_base import Ensemble_mode_base, SILENCE_FADE_S
from modes.Stalagmites_mode import Stalagmites_mode
from tests.test_mode_helpers import TestDeadSettingsRatchet
from tools.choreography_matrix import SyntheticListener, step_synthetic_music
from tools.ensemble_matrix import format_part_report, measure_parts, part_violations
from utils.cast import ALL_SEGMENTS, CANOPY, PILLARS, RUNGS
from utils.choreography import DRIVERS

ENSEMBLE_MODE_SPECS = [
    ("Stalagmites", Stalagmites_mode, "transient"),
]
SMALL_SEGMENTS = ("s1", "s2", "s3")
FULL_PROFILE_LEDS = {"v1": 173, "v2": 173, "v3": 173, "v4": 173, "h10": 86, "h11": 87,
                     "h31": 48, "h32": 48, "h00": 205, "h20": 91, "h30": 47}


def _make(cls, seg_name, listener, n=48, infos=None):
    rgb = np.zeros((n, 3), dtype=np.int32)
    mode = cls(cls.__name__, seg_name, listener, None, list(range(n)), rgb, infos or {})
    mode.start()
    return mode


def _chandelier(cls, listener, segments=ALL_SEGMENTS):
    return {s: _make(cls, f"Segment {s}", listener) for s in segments}


def _run(modes, frames=1):
    for _ in range(frames):
        for m in modes.values():
            m.run()


def _run_clip(modes, listener, frames, start=0, each_frame=None):
    mods = np.array([1.0, 1.0, 1.0, 0.0], dtype=np.float32)
    for f in range(start, start + frames):
        step_synthetic_music(listener, f, mods)
        _run(modes)
        if each_frame is not None:
            each_frame(modes)


class TestEnsembleFamily(unittest.TestCase):
    def setUp(self):
        BaseMode.reset_mood_colors()
        self.addCleanup(BaseMode.reset_mood_colors)

    def test_registered_declared_and_documented(self):
        """E1 + E2: registry entry, declared score, one docstring line per part, every segment cast."""
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "modes.json")
        with open(path, "r", encoding="utf-8") as f:
            entries = {m["name"]: m for m in json.load(f)["global_modes"]}
        for name, cls, lead in ENSEMBLE_MODE_SPECS:
            with self.subTest(mode=name):
                self.assertIn(name, entries)
                self.assertEqual(entries[name]["class"], cls.__name__)
                self.assertIn(f"lead:{lead}", entries[name]["tags"])
                self.assertTrue(cls.IS_GLOBAL)
                self.assertEqual(cls.FAMILY, "ensemble")
                self.assertEqual(cls.LEAD, lead)
                self.assertFalse(cls.__dict__.get("ABSTRACT", False))
                self.assertLessEqual(len(cls.SECONDARY), 1)
                self.assertIn("Lead:", cls.__doc__)
                self.assertTrue(cls.PARTS)
                for part, driver in cls.PARTS.items():
                    self.assertIn(driver, DRIVERS, f"{part} declares unknown driver {driver!r}")
                    self.assertIn(f"Part {part}:", cls.__doc__, f"{part} has no docstring line")

                # Every canonical segment belongs to exactly one declared part.
                probe = _make(cls, "Segment v1", SyntheticListener())
                leds_by_driver = {}
                for seg, n in FULL_PROFILE_LEDS.items():
                    part = probe.part_of(seg)
                    self.assertIn(part, cls.PARTS, f"{seg} is cast in undeclared part {part!r}")
                    leds_by_driver[cls.PARTS[part]] = leds_by_driver.get(cls.PARTS[part], 0) + n
                # E2: LEAD names the driver whose parts cover the most LEDs.
                self.assertEqual(max(leds_by_driver, key=leds_by_driver.get), lead)
        self.assertTrue(Ensemble_mode_base.ABSTRACT)

    def test_part_resolution_canonical_small_and_composite(self):
        for name, cls, _ in ENSEMBLE_MODE_SPECS:
            with self.subTest(mode=name):
                listener = SyntheticListener()
                one = _make(cls, "Segment v2", listener)
                self.assertEqual(one.part_slices(), [(one.part_of("v2"), 0, 48)])
                small = _make(cls, "Segment s2", listener)
                self.assertEqual([p for p, _, _ in small.part_slices()], [small.part_of(s) for s in PILLARS])
                composite = _make(cls, "studio_preview", listener, n=60)
                slices = composite.part_slices()
                self.assertEqual(len(slices), 11)
                self.assertEqual((slices[0][1], slices[-1][2]), (0, 60))
                self.assertEqual({p for p, _, _ in slices}, set(cls.PARTS))

    def test_lockstep_agreeing_alive_and_silent(self):
        """E5 + E4 + Law 1.5: instances agree, stay alive without beat lock, hold short gaps, decay to black."""
        for name, cls, _ in ENSEMBLE_MODE_SPECS:
            for segments in (ALL_SEGMENTS, SMALL_SEGMENTS):
                with self.subTest(mode=name, profile=len(segments)):
                    listener = SyntheticListener()
                    modes = _chandelier(cls, listener, segments)
                    lit = set()

                    def check(ms):
                        lit.update(s for s, m in ms.items() if int(m.rgb_list.max()) > 0)
                        if len(ms) == 11:           # same part, same size -> identical picture
                            for a, b in (("v1", "v4"), ("v2", "v3"), ("h10", "h31"), ("h11", "h32")):
                                self.assertTrue(np.array_equal(ms[a].rgb_list, ms[b].rgb_list), f"{a} != {b}")

                    _run_clip(modes, listener, 300, each_frame=check)
                    self.assertEqual(lit, set(segments), "some segment never lit")

                    # Flywheel lost: the picture keeps moving
                    listener.beat_trust = listener.context.beat_trust = 0.0
                    listener.rhythm_salience = listener.context.salience = 0.0
                    history = []
                    _run_clip(modes, listener, 180, start=300,
                              each_frame=lambda ms: history.append(sum(int(m.rgb_list.sum()) for m in ms.values())))
                    self.assertGreater(len(set(history)), 60, "chandelier froze without beat lock")

                    # A silence gap shorter than the debounce keeps rendering
                    listener.context.is_silent = True
                    _run(modes, int(0.5 * SILENCE_FADE_S * 60))
                    self.assertTrue(any(int(m.rgb_list.max()) > 0 for m in modes.values()))
                    # Sustained silence fades to pure black
                    _run(modes, 240)
                    for s, m in modes.items():
                        self.assertTrue(np.all(m.rgb_list == 0), f"{name}/{s} failed to decay to black")

    def test_law_e3_per_part_mute(self):
        """E3: inside each part the declared driver dominates and no other driver moves it."""
        for name, cls, _ in ENSEMBLE_MODE_SPECS:
            with self.subTest(mode=name):
                report = measure_parts(cls)
                self.assertEqual(set(report), set(cls.PARTS))
                problems = part_violations(report)
                self.assertEqual(problems, [], format_part_report(name, report))

    def test_axiom_01_and_02(self):
        files = ("Ensemble_mode_base.py", "cast.py")
        for name, cls, _ in ENSEMBLE_MODE_SPECS:
            for seg, n in (("studio_preview", 60), ("Segment h00", 205), ("Segment v2", 173)):
                with self.subTest(mode=name, seg=seg):
                    listener = SyntheticListener()
                    mode = _make(cls, seg, listener, n=n)
                    mods = np.array([1.0, 1.0, 1.0, 0.0], dtype=np.float32)
                    for f in range(60):
                        step_synthetic_music(listener, f, mods)
                        mode.run()
                    gc.collect()
                    tracemalloc.start()
                    s1 = tracemalloc.take_snapshot()
                    for f in range(60, 160):
                        step_synthetic_music(listener, f, mods)
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

    def test_law_5_settings_honesty_and_geometry_rebind(self):
        for name, cls, _ in ENSEMBLE_MODE_SPECS:
            with self.subTest(mode=name):
                mode = _make(cls, "Segment v1", SyntheticListener())
                used = set()
                for klass in cls.__mro__:
                    if klass.__module__.startswith("modes."):
                        used |= TestDeadSettingsRatchet._self_loads_outside_setup(
                            inspect.getsource(sys.modules[klass.__module__])
                        )
                for descriptor in mode.get_settings_schema():
                    self.assertIn(descriptor["attr"], used, f"{name} declares dead setting {descriptor['attr']!r}")
                mode.bind_segment_geometry("h00", "horizontal", ("tier:canopy", "half:left"), None)
                self.assertEqual(mode.part_slices(), [(mode.part_of("h00"), 0, 48)])
                mode.run()


    def test_mode_master_casts_every_real_segment(self):
        """In the real orchestrator each of the 11 segments resolves to exactly one declared part."""
        import core.Mode_master as Mode_master
        from music.MusicalContextEngine import MusicalContextEngine
        from tests.test_all_modes_musical_context import MockListener

        listener = MockListener()
        engine = MusicalContextEngine(listener)
        engine._is_silent = False
        listener.context = engine
        leds_1 = np.zeros((785, 3), dtype=np.int32)
        leds_2 = np.zeros((519, 3), dtype=np.int32)
        mm = Mode_master.Mode_master(listener, {"hardware_profile": "full", "useMicrophone": False}, leds_1, leds_2)
        for name, cls, _ in ENSEMBLE_MODE_SPECS:
            with self.subTest(mode=name):
                self.assertTrue(mm.handle_panel_command({"type": "set_segment_mode", "segment": "v4", "mode": name}))
                self.assertEqual(len(mm.segments_list), 11)
                for seg in mm.segments_list:
                    self.assertEqual(seg.get_current_mode(), name)
                    mode = seg.modes[name]
                    self.assertEqual(mode.part_slices(), [(mode.part_of(seg.id), 0, FULL_PROFILE_LEDS[seg.id])])
                    mode.run()


class TestStalagmitesRules(unittest.TestCase):
    """The five jobs of Stalagmites, each checked on a real 11-segment chandelier."""

    RED = (255, 24, 0)
    BLUE = (0, 110, 255)
    KICK_BAND = 0          # 20 - 190 Hz
    SNARE_BAND = 7         # 2.4 - 3.2 kHz
    HAT_BAND = 15

    def setUp(self):
        BaseMode.reset_mood_colors()
        self.addCleanup(BaseMode.reset_mood_colors)
        self.listener = SyntheticListener()
        self.listener.asserved_fft_band[:] = 0.0
        self.listener.band_flux[:] = 0.0
        self.modes = _chandelier(Stalagmites_mode, self.listener)
        for m in self.modes.values():                      # raw hits: the rules below are exact
            m.apply_settings({"smoothness": 0.0})

    def _lit(self, seg):
        return self.modes[seg].rgb_list.max(axis=1) > 0

    def _hit(self, **bands):
        """One frame carrying the given onsets (band index -> flux), then the flux is cleared."""
        for band, value in bands.items():
            self.listener.band_flux[int(band[1:])] = value
        _run(self.modes)
        self.listener.band_flux[:] = 0.0

    def _all_black(self):
        return all(not self._lit(seg).any() for seg in ALL_SEGMENTS)

    def test_kick_throws_the_red_bar_up_from_the_floor(self):
        self._hit(b0=500.0)
        for seg in ("v2", "v3"):
            self.assertTrue(self._lit(seg).all(), f"{seg}: a full-strength kick throws the bar to the top")
            self.assertEqual(tuple(self.modes[seg].rgb_list[0]), self.RED)
        for seg in ("h11", "h32"):
            self.assertTrue(np.all(self.modes[seg].rgb_list == 255), f"{seg}: struck rung, white strike frame")
        for seg in ("v1", "v4", "h10", "h31") + CANOPY:
            self.assertFalse(self._lit(seg).any(), f"{seg} must stay pure black on a kick")

        _run(self.modes, 6)                                # 0.1 s later: falling, not fallen
        lit = self._lit("v2")
        self.assertTrue(0.5 < lit.mean() < 1.0)
        self.assertTrue(lit[0] and not lit[-1], "the bar falls back toward the floor (LED 0)")
        self.assertFalse(np.all(self.modes["h11"].rgb_list == 255), "the white crest lasts one frame")
        _run(self.modes, 60)
        self.assertTrue(self._all_black(), "with no sound left every part returns to pure black")

    def test_hit_strength_sets_the_height(self):
        self._hit(b0=500.0)
        _run(self.modes, 60)
        self._hit(b0=250.0)                                # half as hard as the hit that set the scale
        lit = self._lit("v2")
        self.assertTrue(0.4 < lit.mean() < 0.7, f"half-strength kick reached {lit.mean():.2f}")
        self.assertTrue(np.array_equal(lit, np.sort(lit)[::-1]), "the bar is one solid block from the floor")
        for seg in ("h11", "h32"):
            self.assertFalse(self._lit(seg).any(), f"{seg}: a weak hit does not reach the rung")

    def test_snare_throws_the_blue_bar_down_and_holds_the_red_back(self):
        self._hit(b0=500.0, b7=100.0)                      # set both scales
        _run(self.modes, 60)
        self._hit(b0=500.0, b7=100.0)                      # snare: low thump + crack
        for seg in ("v1", "v4"):
            self.assertTrue(self._lit(seg).all(), f"{seg}: a full-strength snare throws the bar to the bottom")
            self.assertEqual(tuple(self.modes[seg].rgb_list[-1]), self.BLUE)
        for seg in ("h10", "h31"):
            self.assertTrue(np.all(self.modes[seg].rgb_list == 255), f"{seg}: struck rung, white strike frame")
        red = self._lit("v2").mean()
        self.assertTrue(0.6 < red < 0.9, f"the red bar is held back on a snare, got {red:.2f}")

        _run(self.modes, 6)
        lit = self._lit("v1")
        self.assertTrue(lit[-1] and not lit[0], "the blue bar hangs from the top (last LED)")
        _run(self.modes, 60)
        self._hit(b0=500.0)                                # kick alone
        self.assertTrue(self._lit("v2").all(), "a lone kick is the tallest red")
        self.assertFalse(self._lit("v1").any(), "a lone kick leaves the blue bar black")
        _run(self.modes, 60)
        self._hit(b7=45.0)                                 # hi-hat leak / voice in the snare range
        self.assertLess(self._lit("v1").mean(), 0.2, "a weak snap barely moves the blue bar")

    def test_held_note_keeps_only_a_stub(self):
        self.listener.asserved_fft_band[:2] = 0.9          # sustained bass, no onset
        _run(self.modes, 60)
        lit = self._lit("v2")
        self.assertTrue(lit[0] and 0.05 < lit.mean() < 0.25, f"stub covers {lit.mean():.2f} of the pillar")
        for seg in ("v1", "v4") + RUNGS + CANOPY:
            self.assertFalse(self._lit(seg).any(), seg)

    def test_canopy_sparkles_only_on_hi_hats(self):
        _run(self.modes, 10)
        self._hit(b0=500.0)                                # a kick is not a canopy event
        for seg in CANOPY:
            self.assertFalse(self._lit(seg).any(), f"{seg} must ignore low onsets")
        _run(self.modes, 60)

        self._hit(b15=30.0)                                # hi-hat
        for seg in CANOPY:
            lit = self._lit(seg)
            self.assertTrue(0.0 < lit.mean() < 1.0, f"{seg}: an onset lights some cells, not all")
            self.assertTrue(np.all(self.modes[seg].rgb_list[lit] == 255), "Law 3: sparks strike white")
        for seg in PILLARS + RUNGS:
            self.assertFalse(self._lit(seg).any(), f"{seg} must ignore hi-hats")
        _run(self.modes, 90)
        self.assertTrue(self._all_black(), "sparks must decay to pure black")

    def test_drop_hit_flashes_the_whole_canopy_for_one_frame(self):
        _run(self.modes, 5)
        self.listener.context.is_drop_impact = True
        _run(self.modes)
        self.listener.context.is_drop_impact = False
        for seg in CANOPY:
            self.assertTrue(np.all(self.modes[seg].rgb_list == 255), seg)
        _run(self.modes)
        for seg in CANOPY:
            self.assertFalse(np.all(self.modes[seg].rgb_list == 255), f"{seg}: white lasts one frame")

    def test_default_smoothness_softens_the_hit(self):
        """At the default setting the bar rises over several frames and the rungs never flash white."""
        modes = _chandelier(Stalagmites_mode, self.listener)
        self.listener.band_flux[self.KICK_BAND] = 500.0
        _run(modes)
        self.listener.band_flux[:] = 0.0
        heights = [float((modes["v2"].rgb_list.max(axis=1) > 0).mean())]
        whites = [bool(np.all(modes["h11"].rgb_list == 255))]
        for _ in range(40):
            _run(modes)
            heights.append(float((modes["v2"].rgb_list.max(axis=1) > 0).mean()))
            whites.append(bool(np.all(modes["h11"].rgb_list == 255)))
        peak = int(np.argmax(heights))
        self.assertLess(heights[0], 0.5, "the bar must not jump to the top in one frame")
        self.assertGreaterEqual(peak, 3, f"the rise should take several frames, peaked at frame {peak}")
        self.assertGreater(max(heights), 0.75, "a full-strength kick still throws the bar most of the way")
        self.assertTrue(all(b >= a for a, b in zip(heights[:peak], heights[1:peak + 1])), "monotonic rise")
        self.assertFalse(any(whites), "no white strike frame at the default smoothness")
        self.assertEqual(heights[-1], 0.0)

    def test_mood_palette_setting_replaces_the_fixed_colours(self):
        for m in self.modes.values():
            self.assertEqual(m.apply_settings({"mood_palette": True}), {"mood_palette": True})
        self._hit(b0=500.0)
        expected = tuple(int(c) for c in self.modes["v2"].mood_colors[0])
        self.assertEqual(tuple(self.modes["v2"].rgb_list[0]), expected)


if __name__ == "__main__":
    unittest.main()
