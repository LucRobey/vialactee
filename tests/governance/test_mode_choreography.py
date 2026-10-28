"""
tests/governance/test_mode_choreography.py
Governance and behavioral stimulus tests for Law 7 (One Lead Timescale) in docs/contracts/mode_contract.md:
1. Every mode in config/modes.json declares a LEAD that is in DRIVERS.
2. SECONDARY is a tuple with at most one entry, each entry is in DRIVERS, and differs from LEAD.
3. The mode class docstring contains 'Lead:' (forces a one-line human explanation).
4. docs/reference/modes_catalog.md shows the exact same Lead and Secondary as the code.
5. DriverMuteProxy exposes all Listener/MusicalContextEngine attributes read by modes and faithfully
   mutes each of the 5 channels (beat, level, spectrum, transient, macro) across 8 and 16 bands.
6. Stimulus measurement across all 13 modes verifies provenance, in-process determinism, finite metrics
   (8 and 16 bands), and enforces calibrated Phase 4a/4b lead-dominance thresholds on conforming modes.
"""
import ast
import glob
import importlib
import json
import math
import os
import re
import unittest
import numpy as np

import modes.Mode as BaseModeMod
from utils.choreography import (
    DRIVERS,
    MUTE_CHANNELS,
    NEUTRAL_MOOD_MODIFIERS,
)
from utils.driver_mute import (
    ContextMuteProxy,
    DriverMuteProxy,
)
from tools.choreography_matrix import (
    DEFAULT_NB_BANDS,
    MATRIX_CONFIG,
    SYNTHETIC_CLIP_VERSION,
    SyntheticContext,
    SyntheticListener,
    compute_response_metrics,
    format_measurement_report,
    measure_all_registered_modes,
    measure_mode_choreography,
    step_synthetic_music,
)


# Modes that already conform to Law 7 before the Batch 2-4 redesigns.
# Pre-redesign modes (Middle_bar, Chromatic_chaser, Extending_waves, Rainbow, Proportion_rainbow,
# Shining_stars, Impact_shockwave) are tracked in diagnostic mode until their redesign batches land.
CONFORMING_MODES_PHASE_4A = frozenset({
    "Bary_rainbow_mode",
    "Opposite_sides_mode",
    "Hyper_strobe_mode",
    "Metronome_mode",
    "Coloured_middle_wave_mode",
    "Power_bar_mode",
})

# Calibrated thresholds from the Phase 4a 13 x 4 empirical measurement matrix:
#   f = minimum fraction of total audio-driven variance (R_std_full - R_std_mute_all) carried by LEAD
#   g = minimum fraction of R_std_full retained when only SECONDARY is muted
CALIBRATED_LEAD_FRACTION_F = 0.30
CALIBRATED_SEC_RETAINED_G = 0.65

# Provenance lock: changing the synthetic clip, band count, or MATRIX_CONFIG requires recalibrating f/g.
CALIBRATED_FOR = {
    "clip_version": "1",
    "nb_bands": 8,
    "matrix_config": {
        "num_leds": 40,
        "warmup_frames": 30,
        "eval_frames": 120,
    },
}


class TestModeChoreographyGovernance(unittest.TestCase):
    def setUp(self):
        self.repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.modes_json_path = os.path.join(self.repo_root, "config", "modes.json")
        self.modes_catalog_path = os.path.join(self.repo_root, "docs", "reference", "modes_catalog.md")
        with open(self.modes_json_path, "r", encoding="utf-8") as f:
            self.modes_data = json.load(f).get("standard_modes", [])

    def _iter_registered_mode_classes(self):
        for entry in self.modes_data:
            mode_name = entry["name"]
            mod_name = entry["module"]
            cls_name = entry["class"]
            mod = importlib.import_module(f"modes.{mod_name}")
            cls = getattr(mod, cls_name)
            yield mode_name, cls_name, cls

    def test_every_mode_declares_valid_lead_and_secondary(self):
        """Rules 1 & 2: Every mode declares LEAD in DRIVERS and SECONDARY (<= 1 entry in DRIVERS, != LEAD)."""
        violations = []
        for mode_name, cls_name, cls in self._iter_registered_mode_classes():
            lead = getattr(cls, "LEAD", "")
            if lead not in DRIVERS:
                violations.append(f"{cls_name} ({mode_name}): invalid or missing LEAD={lead!r} (expected one of {DRIVERS})")

            secondary = getattr(cls, "SECONDARY", None)
            if not isinstance(secondary, tuple):
                violations.append(f"{cls_name} ({mode_name}): SECONDARY must be a tuple, got {secondary!r}")
                continue
            if len(secondary) > 1:
                violations.append(f"{cls_name} ({mode_name}): SECONDARY may contain at most 1 driver, got {secondary!r}")
            for sec_driver in secondary:
                if sec_driver not in DRIVERS:
                    violations.append(f"{cls_name} ({mode_name}): invalid SECONDARY driver {sec_driver!r} (expected one of {DRIVERS})")
                if sec_driver == lead:
                    violations.append(f"{cls_name} ({mode_name}): SECONDARY driver {sec_driver!r} must differ from LEAD {lead!r}")

        self.assertEqual(
            violations,
            [],
            "Choreography LEAD / SECONDARY declaration violations:\n" + "\n".join(violations),
        )

    def test_every_mode_docstring_contains_lead_line(self):
        """Rule 3: Every mode class docstring must contain 'Lead:' explaining its choreography."""
        missing_doc = []
        for mode_name, cls_name, cls in self._iter_registered_mode_classes():
            doc = cls.__doc__ or ""
            if "Lead:" not in doc:
                missing_doc.append(f"{cls_name} ({mode_name}): class docstring is missing 'Lead:'")

        self.assertEqual(
            missing_doc,
            [],
            "Mode docstrings missing 'Lead:' explanation:\n" + "\n".join(missing_doc),
        )

    def test_modes_catalog_lead_and_secondary_parity(self):
        """Rule 4: docs/reference/modes_catalog.md table must match each mode's LEAD and SECONDARY."""
        with open(self.modes_catalog_path, "r", encoding="utf-8") as f:
            catalog_text = f.read()

        row_re = re.compile(
            r"^\|\s*\d+\s*\|\s*\*\*([^*]+)\*\*\s*\|\s*\[`([^`]+)`\]\([^)]+\)\s*\|[^|]+\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|",
            re.MULTILINE,
        )
        catalog_rows = {
            m.group(2).strip(): (m.group(1).strip(), m.group(3).strip(), m.group(4).strip())
            for m in row_re.finditer(catalog_text)
        }

        mismatches = []
        for mode_name, cls_name, cls in self._iter_registered_mode_classes():
            if cls_name not in catalog_rows:
                mismatches.append(f"{cls_name} ({mode_name}) row with Lead/Secondary columns not found in modes_catalog.md")
                continue
            _, cat_lead, cat_sec = catalog_rows[cls_name]
            code_lead = getattr(cls, "LEAD", "")
            code_sec_tuple = getattr(cls, "SECONDARY", ())
            code_sec = code_sec_tuple[0] if code_sec_tuple else "none"
            if cat_lead != code_lead:
                mismatches.append(f"{cls_name}: modes_catalog.md Lead='{cat_lead}' != code LEAD='{code_lead}'")
            if cat_sec != code_sec:
                mismatches.append(f"{cls_name}: modes_catalog.md Secondary='{cat_sec}' != code SECONDARY='{code_sec}'")

        self.assertEqual(
            mismatches,
            [],
            "Catalog <-> Code Lead/Secondary parity mismatches:\n" + "\n".join(mismatches),
        )


class TestDriverMuteProxyAndMetrics(unittest.TestCase):
    def setUp(self):
        self.repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.listener = SyntheticListener(nb_bands=8)
        self.proxy = DriverMuteProxy(self.listener)
        self.live_mods = np.array([1.0, 1.0, 1.0, 0.0], dtype=np.float32)

    def tearDown(self):
        BaseModeMod.Mode.reset_mood_colors()

    def test_proxy_exposes_all_listener_and_context_attributes_used_in_modes(self):
        """Risk 1 guard: DriverMuteProxy and its context proxy must expose every attribute read in modes/*.py."""
        modes_dir = os.path.join(self.repo_root, "modes")
        listener_attrs = set()
        context_attrs = set()

        for path in glob.glob(os.path.join(modes_dir, "*.py")):
            with open(path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=path)
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Attribute):
                    if node.value.attr == "listener":
                        listener_attrs.add(node.attr)
                    elif node.value.attr == "context":
                        context_attrs.add(node.attr)
                elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                    if node.value.id in ("listener",):
                        listener_attrs.add(node.attr)
                    elif node.value.id in ("ctx", "context"):
                        context_attrs.add(node.attr)
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "getattr":
                    if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant) and isinstance(node.args[1].value, str):
                        target = node.args[0]
                        attr_name = node.args[1].value
                        if isinstance(target, ast.Attribute) and target.attr == "listener":
                            listener_attrs.add(attr_name)
                        elif isinstance(target, ast.Name) and target.id == "listener":
                            listener_attrs.add(attr_name)
                        elif isinstance(target, ast.Name) and target.id in ("ctx", "context"):
                            context_attrs.add(attr_name)

        missing_listener = [a for a in sorted(listener_attrs) if not hasattr(self.proxy, a)]
        missing_context = [a for a in sorted(context_attrs) if not hasattr(self.proxy.context, a)]
        self.assertEqual(missing_listener, [], f"DriverMuteProxy missing Listener attributes: {missing_listener}")
        self.assertEqual(missing_context, [], f"ContextMuteProxy missing context attributes: {missing_context}")
        self.assertIsInstance(self.proxy.context, ContextMuteProxy)
        self.assertIsInstance(self.listener.context, SyntheticContext)

    def test_beat_mute_keeps_trust_high_and_freezes_phase_and_pulse(self):
        """Muting 'beat' keeps beat_trust=1.0 (stays on rhythmic branch) and freezes beat_phase, beat_count, and beat_pulse()."""
        for nb_bands in (8, 16):
            with self.subTest(nb_bands=nb_bands):
                listener = SyntheticListener(nb_bands=nb_bands)
                proxy = DriverMuteProxy(listener)
                live_mods = np.array([1.0, 1.0, 1.0, 0.0], dtype=np.float32)

                for f in range(30):
                    step_synthetic_music(listener, f, live_mods)
                    proxy.observe()

                proxy.set_muted("beat", True)
                proxy.set_muted("macro", True)
                proxy.sync_macro_modifiers(BaseModeMod.Mode, live_mods)

                rgb = np.zeros((16, 3), dtype=np.int32)
                mode = BaseModeMod.Mode("test", "seg", proxy, None, list(range(16)), rgb, {})
                unmuted_lock = float(
                    listener.context.beat_trust * (0.4 + 0.6 * listener.context.salience)
                )

                pulses = []
                phases = []
                counts = []
                for f in range(30, 90):
                    step_synthetic_music(listener, f, live_mods)
                    proxy.observe()
                    self.assertGreaterEqual(proxy.beat_trust, 0.85)
                    self.assertGreaterEqual(proxy.context.beat_trust, 0.85)
                    self.assertAlmostEqual(proxy.context.salience, 0.85, places=6)
                    self.assertLess(abs(mode.rhythm_lock - unmuted_lock), 0.10)
                    self.assertTrue(proxy.context.is_locked)
                    phases.append(proxy.beat_phase)
                    counts.append(proxy.beat_count)
                    pulses.append(mode.beat_pulse())

                self.assertEqual(len(set(phases)), 1, "beat_phase must remain frozen when 'beat' is muted")
                self.assertEqual(len(set(counts)), 1, "beat_count must remain frozen when 'beat' is muted")
                self.assertAlmostEqual(max(pulses), min(pulses), places=9, msg="beat_pulse() must be constant when beat+macro are muted")

    def test_level_spectrum_transient_and_macro_mute_semantics(self):
        """Verify level, spectrum, transient (including Mode.drop_hit), and macro mute channels across 8 and 16 bands."""
        for nb_bands in (8, 16):
            with self.subTest(nb_bands=nb_bands):
                listener = SyntheticListener(nb_bands=nb_bands)
                proxy = DriverMuteProxy(listener)
                live_mods = np.array([1.0, 1.0, 1.0, 0.0], dtype=np.float32)

                for f in range(30):
                    step_synthetic_music(listener, f, live_mods)
                    proxy.observe(alpha=0.1)

                proxy.set_muted("level", True)
                proxy.set_muted("spectrum", True)
                proxy.set_muted("transient", True)
                proxy.set_muted("macro", True)

                rgb = np.zeros((16, 3), dtype=np.int32)
                mode = BaseModeMod.Mode("test", "seg", proxy, None, list(range(16)), rgb, {})

                frozen_energy = proxy.context.energy
                frozen_bands = proxy.asserved_fft_band.copy()
                frozen_tilt = proxy.context.spectral_tilt
                self.assertEqual(len(frozen_bands), nb_bands)
                self.assertEqual(len(proxy.band_proportion), nb_bands)
                self.assertEqual(len(proxy.band_flux), nb_bands)

                # Frame 90 has a synthetic drop impact and beat wraps occur periodically
                for f in range(30, 120):
                    step_synthetic_music(listener, f, live_mods)
                    proxy.observe(alpha=0.1)
                    proxy.sync_macro_modifiers(BaseModeMod.Mode, live_mods)

                    # Level frozen
                    self.assertAlmostEqual(proxy.context.energy, frozen_energy, places=9)
                    self.assertAlmostEqual(proxy.asserved_total_power, frozen_energy, places=9)

                    # Spectrum frozen
                    np.testing.assert_allclose(proxy.asserved_fft_band, frozen_bands)
                    self.assertAlmostEqual(proxy.context.spectral_tilt, frozen_tilt, places=9)

                    # Transient suppressed (including Mode.drop_hit on frame 90)
                    self.assertFalse(proxy.is_beat)
                    self.assertFalse(proxy.is_real_beat)
                    self.assertFalse(proxy.context.is_real_beat)
                    self.assertFalse(proxy.context.is_drop_impact)
                    self.assertFalse(mode.drop_hit)
                    self.assertEqual(float(np.max(np.abs(proxy.band_flux))), 0.0)

                    # Macro neutralized
                    self.assertEqual(proxy.context.tension, 0.0)
                    self.assertEqual(mode.drop_decay, 0.0)
                    self.assertEqual(mode.mood_pace, 1.0)
                    self.assertEqual(mode.mood_sharpness, 1.0)
                    self.assertEqual(mode.mood_trail, 1.0)
                    self.assertEqual(mode.mood_accent, 0.0)

    def test_compute_response_metrics_static_and_oscillating(self):
        """R_std and R_diff are 0 on static frames and exact on synthetic square wave frames."""
        static = np.full((20, 10, 3), 120, dtype=np.int32)
        r_std, r_diff = compute_response_metrics(static)
        self.assertEqual(r_std, 0.0)
        self.assertEqual(r_diff, 0.0)

        osc = np.zeros((20, 10, 3), dtype=np.int32)
        osc[1::2] = 100
        r_std_osc, r_diff_osc = compute_response_metrics(osc)
        self.assertAlmostEqual(r_std_osc, 50.0, places=5)
        self.assertAlmostEqual(r_diff_osc, 100.0, places=5)


class TestChoreographyStimulusMeasurement(unittest.TestCase):
    def test_calibration_provenance_guard(self):
        """Guard against silent drift between synthetic clip/config and calibrated thresholds."""
        live = {
            "clip_version": SYNTHETIC_CLIP_VERSION,
            "nb_bands": DEFAULT_NB_BANDS,
            "matrix_config": dict(MATRIX_CONFIG),
        }
        self.assertEqual(
            live,
            CALIBRATED_FOR,
            "Synthetic clip version, band count, or MATRIX_CONFIG changed without updating CALIBRATED_FOR and recalibrating f/g thresholds.",
        )

    def test_in_process_measurement_determinism(self):
        """Measuring the same mode twice in-process produces identical metrics."""
        for mod_name in ("Bary_rainbow_mode", "Shining_stars_mode"):
            mod = importlib.import_module(f"modes.{mod_name}")
            cls = getattr(mod, mod_name)
            first = measure_mode_choreography(cls, **MATRIX_CONFIG, nb_bands=DEFAULT_NB_BANDS)
            second = measure_mode_choreography(cls, **MATRIX_CONFIG, nb_bands=DEFAULT_NB_BANDS)
            self.assertEqual(first, second, f"{mod_name} produced non-deterministic in-process metrics")

    def test_all_registered_modes_stimulus_and_calibrated_dominance(self):
        """Run the 13 x 4 synthetic stimulus suite (8 bands); verify finite metrics and enforce dominance on conforming modes."""
        results = measure_all_registered_modes(**MATRIX_CONFIG, nb_bands=DEFAULT_NB_BANDS)
        self.assertEqual(len(results), 13)

        conforming_failures = []
        for r in results:
            mode_name = r["mode"]
            for key in ("r_std_full", "r_diff_full", "r_std_mute_lead", "r_std_mute_sec", "r_std_mute_all"):
                val = r[key]
                self.assertTrue(math.isfinite(val) and val >= 0.0, f"{mode_name}: invalid {key}={val}")

            self.assertGreater(r["r_std_full"], 1.0, f"{mode_name}: expected non-trivial R_std(full)")

            if mode_name in CONFORMING_MODES_PHASE_4A:
                lead = r["lead"]
                sec = r["secondary"]
                contribs = r["contributions"]
                lead_c = r["lead_contrib"]
                best_driver = max(contribs, key=contribs.get)
                audio_budget = max(1e-6, r["r_std_full"] - r["r_std_mute_all"])

                if best_driver != lead:
                    conforming_failures.append(
                        f"{mode_name}: declared LEAD={lead!r} ({lead_c:+.2f}) is not dominant; max is {best_driver!r} ({contribs[best_driver]:+.2f})"
                    )
                if lead_c < CALIBRATED_LEAD_FRACTION_F * audio_budget:
                    conforming_failures.append(
                        f"{mode_name}: lead_contrib={lead_c:.2f} < {CALIBRATED_LEAD_FRACTION_F:.2f} * audio_budget ({audio_budget:.2f})"
                    )
                if sec != "none" and r["r_std_mute_sec"] < CALIBRATED_SEC_RETAINED_G * r["r_std_full"]:
                    conforming_failures.append(
                        f"{mode_name}: R_std(-sec)={r['r_std_mute_sec']:.2f} < {CALIBRATED_SEC_RETAINED_G:.2f} * R_std(full) ({r['r_std_full']:.2f})"
                    )

        self.assertEqual(
            conforming_failures,
            [],
            "Conforming modes failed calibrated Law 7 stimulus checks:\n" + "\n".join(conforming_failures),
        )

    def test_all_registered_modes_16_bands_diagnostic(self):
        """Run the 13 x 4 synthetic stimulus suite at 16 bands (diagnostic only: finite metrics, prints report)."""
        results_16 = measure_all_registered_modes(**MATRIX_CONFIG, nb_bands=16)
        self.assertEqual(len(results_16), 13)
        for r in results_16:
            mode_name = r["mode"]
            for key in ("r_std_full", "r_diff_full", "r_std_mute_lead", "r_std_mute_sec", "r_std_mute_all"):
                val = r[key]
                self.assertTrue(math.isfinite(val) and val >= 0.0, f"{mode_name} (16 bands): invalid {key}={val}")
            self.assertGreater(r["r_std_full"], 1.0, f"{mode_name} (16 bands): expected non-trivial R_std(full)")
        print("\n--- 16-Band Diagnostic Choreography Matrix ---\n" + format_measurement_report(results_16))


if __name__ == "__main__":
    unittest.main()
