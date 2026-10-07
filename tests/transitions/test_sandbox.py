"""Tests for the fakes and the headless sandbox: the sector must run with no project code at all."""
import unittest

from transitions import fakes, sandbox


class TestFakes(unittest.TestCase):
    def test_fake_music_follows_the_script(self):
        self.assertEqual(fakes.fake_music(5.0).scene, "CHILL")
        self.assertEqual(fakes.fake_music(20.0).scene, "GROOVE")
        self.assertEqual(fakes.fake_music(32.0).scene, "BUILDUP")
        self.assertTrue(fakes.fake_music(fakes.DROP_AT).is_drop_impact)
        self.assertEqual(fakes.fake_music(65.0).scene, "CHILL")  # loops

    def test_fake_music_has_a_metronome(self):
        beats = sum(fakes.fake_music(i / 30.0, 120.0).is_beat for i in range(300))  # 10 s at 2 beats/s
        self.assertAlmostEqual(beats, 20, delta=2)

    def test_fake_installation_has_pillars_and_rings(self):
        inst = fakes.fake_installation()
        orientations = {s.orientation for s in inst.segments}
        self.assertEqual(orientations, {"vertical", "horizontal"})
        self.assertTrue(all(len(s.available_modes) > 5 for s in inst.segments))


class TestSandbox(unittest.TestCase):
    def test_sandbox_fires_transitions_covering_every_segment(self):
        fired = sandbox.run(seconds=40, interval=5.0, seed=1, echo=None)
        self.assertGreaterEqual(len(fired), 3)
        n = len(fakes.fake_installation().segments)
        for orders in fired:
            self.assertEqual(len(orders.orders), n)

    def test_sandbox_is_reproducible_with_a_seed(self):
        a = sandbox.run(seconds=30, interval=5.0, seed=7, echo=None)
        b = sandbox.run(seconds=30, interval=5.0, seed=7, echo=None)
        self.assertEqual([o.orders for o in a], [o.orders for o in b])

    def test_sandbox_echoes_decisions(self):
        lines = []
        sandbox.run(seconds=20, interval=5.0, seed=1, echo=lines.append)
        self.assertTrue(any("technique=" in line for line in lines))
        self.assertTrue(lines[-1].endswith("transitions in 20s"))


if __name__ == "__main__":
    unittest.main()
