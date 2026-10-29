"""
tests/governance/test_mode_choreography_profiles.py
Governance and behavioral stimulus tests across the 3 realistic rhythm-lock synthetic profiles:
1. Locked profiles (`high_lock`, `groove_lock`): All 8 modes in `CONFORMING_MODES_PHASE_4A`
   (including `Shining_stars_mode`) satisfy all 3 Law 7 assertions:
   - Declared LEAD is strictly the largest single-driver ablation among {beat, level, spectrum, transient}
     (with the LOCK_CONFOUNDED rule documented for |delta_lock| > 0.10 when muting `beat` lifts `beat_trust -> 1.0`).
   - d(lead) >= 0.30 * (R_std(full) - R_std(-all)) (f = 0.30).
   - R_std(-sec) >= 0.65 * R_std(full) (g = 0.65).
2. Unlocked profile (`loose_lock`): `test_loose_lock_modes_stay_alive` verifies every registered mode
   stays alive under Law 1 (R_std(full) > 1.0 and R_std(full) >= 0.20 * R_std(high_lock)).
"""
import io
import math
import unittest
from contextlib import redirect_stdout
import numpy as np

import modes.Mode as BaseModeMod
from tools.choreography_matrix import (
    DEFAULT_NB_BANDS,
    LOCK_CONFOUND_TOLERANCE,
    LOCKED_PROFILES,
    MATRIX_CONFIG,
    PROFILE_NAMES,
    SYNTHETIC_PROFILES,
    SyntheticContext,
    SyntheticListener,
    main as matrix_main,
    measure_all_registered_modes,
)
from tests.governance.test_mode_choreography import (
    CALIBRATED_LEAD_FRACTION_F,
    CALIBRATED_SEC_RETAINED_G,
    CONFORMING_MODES_PHASE_4A,
)


CALIBRATED_LOOSE_ALIVE_RATIO = 0.20


class TestModeChoreographyProfiles(unittest.TestCase):
    def tearDown(self):
        BaseModeMod.Mode.reset_mood_colors()

    def test_synthetic_lock_profile_specifications(self):
        """Verify high_lock (0.82), groove_lock (0.50), and loose_lock (0.25) parameters and rhythm_lock."""
        self.assertEqual(PROFILE_NAMES, ("high_lock", "groove_lock", "loose_lock"))
        self.assertEqual(LOCKED_PROFILES, ("high_lock", "groove_lock"))
        self.assertAlmostEqual(LOCK_CONFOUND_TOLERANCE, 0.10, places=6)

        expected = {
            "high_lock": (0.90, 0.85, True, 0.819),
            "groove_lock": (0.68, 0.55, True, 0.4964),
            "loose_lock": (0.38, 0.45, False, 0.2546),
        }
        rgb = np.zeros((8, 3), dtype=np.int32)
        for prof, (bt, sal, lck, exp_lock) in expected.items():
            spec = SYNTHETIC_PROFILES[prof]
            self.assertAlmostEqual(spec["beat_trust"], bt, places=6)
            self.assertAlmostEqual(spec["salience"], sal, places=6)
            self.assertEqual(spec["is_locked"], lck)

            listener = SyntheticListener(nb_bands=DEFAULT_NB_BANDS, profile=prof)
            mode = BaseModeMod.Mode("test", "seg", listener, None, list(range(8)), rgb, {})
            self.assertAlmostEqual(mode.rhythm_lock, exp_lock, places=3)

        with self.assertRaises(ValueError):
            SyntheticListener(profile="invalid_profile")
        with self.assertRaises(ValueError):
            SyntheticContext(profile="invalid_profile")

    def test_locked_profiles_law7_conformance(self):
        """
        On both locked profiles (`high_lock` and `groove_lock`), all 8 modes in CONFORMING_MODES_PHASE_4A
        must satisfy all 3 Law 7 assertions (strict lead dominance across all 4 drivers, f=0.30, g=0.65).
        Also verifies LOCK_CONFOUNDED detection when |delta_lock| > 0.10 under beat mute on groove_lock.
        """
        for prof in LOCKED_PROFILES:
            with self.subTest(profile=prof):
                results = measure_all_registered_modes(
                    **MATRIX_CONFIG, nb_bands=DEFAULT_NB_BANDS, profile=prof
                )
                self.assertEqual(len(results), 13)
                conforming_failures = []

                for r in results:
                    mode_name = r["mode"]
                    self.assertEqual(r["profile"], prof)
                    for key in ("r_std_full", "r_diff_full", "r_std_mute_lead", "r_std_mute_sec", "r_std_mute_all"):
                        val = r[key]
                        self.assertTrue(
                            math.isfinite(val) and val >= 0.0,
                            f"{mode_name} [{prof}]: invalid {key}={val}",
                        )
                    self.assertGreater(
                        r["r_std_full"], 1.0, f"{mode_name} [{prof}]: expected non-trivial R_std(full)"
                    )

                    # Verify LOCK_CONFOUNDED metadata: muting 'beat' forces beat_trust=1.0,
                    # so |delta_lock['beat']| <= 0.10 on high_lock (+0.091) and > 0.10 on groove_lock (+0.234).
                    if prof == "high_lock":
                        self.assertEqual(r["lock_confounded_drivers"], ())
                    elif prof == "groove_lock":
                        self.assertEqual(r["lock_confounded_drivers"], ("beat",))

                    if mode_name in CONFORMING_MODES_PHASE_4A:
                        lead = r["lead"]
                        sec = r["secondary"]
                        contribs = r["contributions"]
                        lead_c = r["lead_contrib"]
                        best_driver = max(contribs, key=contribs.get)
                        audio_budget = max(1e-6, r["r_std_full"] - r["r_std_mute_all"])

                        if best_driver != lead:
                            conforming_failures.append(
                                f"{mode_name} [{prof}]: declared LEAD={lead!r} ({lead_c:+.2f}) is not dominant; "
                                f"max is {best_driver!r} ({contribs[best_driver]:+.2f})"
                            )
                        if lead_c < CALIBRATED_LEAD_FRACTION_F * audio_budget:
                            conforming_failures.append(
                                f"{mode_name} [{prof}]: lead_contrib={lead_c:.2f} < "
                                f"{CALIBRATED_LEAD_FRACTION_F:.2f} * audio_budget ({audio_budget:.2f})"
                            )
                        if sec != "none" and r["r_std_mute_sec"] < CALIBRATED_SEC_RETAINED_G * r["r_std_full"]:
                            conforming_failures.append(
                                f"{mode_name} [{prof}]: R_std(-sec)={r['r_std_mute_sec']:.2f} < "
                                f"{CALIBRATED_SEC_RETAINED_G:.2f} * R_std(full) ({r['r_std_full']:.2f})"
                            )

                self.assertEqual(
                    conforming_failures,
                    [],
                    f"Conforming modes failed Law 7 checks on profile {prof!r}:\n"
                    + "\n".join(conforming_failures),
                )

    def test_loose_lock_modes_stay_alive(self):
        """
        Law 1 (Always Alive Without the Flywheel): under the unlocked `loose_lock` profile
        (beat_trust=0.38, salience=0.45, is_locked=False, rhythm_lock=0.25), every registered mode
        must remain alive with R_std(full) > 1.0 and R_std(full) >= 0.20 * R_std(high_lock).
        """
        high_results = {
            r["mode"]: r
            for r in measure_all_registered_modes(
                **MATRIX_CONFIG, nb_bands=DEFAULT_NB_BANDS, profile="high_lock"
            )
        }
        loose_results = measure_all_registered_modes(
            **MATRIX_CONFIG, nb_bands=DEFAULT_NB_BANDS, profile="loose_lock"
        )
        self.assertEqual(len(loose_results), 13)

        failures = []
        for r in loose_results:
            mode_name = r["mode"]
            r_loose = r["r_std_full"]
            r_high = high_results[mode_name]["r_std_full"]
            self.assertEqual(r["lock_confounded_drivers"], ("beat",))
            if not (math.isfinite(r_loose) and r_loose > 1.0):
                failures.append(f"{mode_name}: loose_lock R_std(full)={r_loose:.2f} <= 1.0")
            if r_loose < CALIBRATED_LOOSE_ALIVE_RATIO * r_high:
                failures.append(
                    f"{mode_name}: loose_lock R_std(full)={r_loose:.2f} < "
                    f"{CALIBRATED_LOOSE_ALIVE_RATIO:.2f} * high_lock ({r_high:.2f})"
                )

        self.assertEqual(
            failures,
            [],
            "Modes failed Law 1 alive checks under loose_lock:\n" + "\n".join(failures),
        )

    def test_cli_profile_argument(self):
        """CLI --profile option prints the requested profile section cleanly."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            matrix_main(["--profile", "groove_lock"])
        out = buf.getvalue()
        self.assertIn("Profile: groove_lock", out)
        self.assertIn("Shining_stars_mode", out)


if __name__ == "__main__":
    unittest.main()
