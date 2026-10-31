"""
tests/test_coherence_loader.py - Test Coherence Policy Loader, Schema, and JSON Integrity.
"""

import copy
import json
import os
import tempfile
import unittest

from config.coherence_loader import (
    resolve_coherence_file_path,
    load_coherence_config,
    validate_coherence_dict,
    COHERENCE_FULL_PATH,
    COHERENCE_SMALL_PATH,
    COHERENCE_SCHEMA_PATH,
)


def _make_valid_coherence_dict():
    return {
        "version": 1,
        "settings": {
            "maxDifferentModes": 3,
            "temperature": 1.0,
            "memoryDepth": 4,
            "repeatPenalty": 1.5,
        },
        "zones": {
            "all": {
                "segments": ["s1", "s2"],
                "groupings": [
                    {
                        "id": "unison",
                        "weight": 1.0,
                        "groups": [["s1", "s2"]],
                    }
                ],
            }
        },
        "rules": [
            {
                "id": "r1",
                "when": [{"at": "orientation:vertical", "tag": "layer:accent"}],
                "effect": "forbid",
            }
        ],
    }


class TestCoherenceLoader(unittest.TestCase):
    def test_resolve_default_to_full(self):
        resolved = resolve_coherence_file_path(None)
        self.assertTrue(os.path.isabs(resolved))
        self.assertTrue(resolved.endswith("coherence_full.json"))

    def test_resolve_small_profile(self):
        resolved = resolve_coherence_file_path({"hardware_profile": "small"})
        self.assertTrue(os.path.isabs(resolved))
        self.assertTrue(resolved.endswith("coherence_small.json"))

    def test_resolve_explicit_override(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
            tf.write("{}")
            tmp_path = tf.name
        self.addCleanup(os.unlink, tmp_path)

        resolved = resolve_coherence_file_path({"coherence_file": tmp_path})
        self.assertEqual(resolved, os.path.abspath(tmp_path))

    def test_validate_coherence_dict_success(self):
        valid = _make_valid_coherence_dict()
        validate_coherence_dict(valid)

    def test_validate_coherence_dict_missing_keys(self):
        with self.assertRaises(ValueError):
            validate_coherence_dict({"settings": {}})
        with self.assertRaises(ValueError):
            validate_coherence_dict({"settings": {"maxDifferentModes": 0}})

    def test_load_full_config_partitions(self):
        from transitions.fakes import make_fake_installation
        from transitions.policy import compile_policy

        self.assertTrue(os.path.exists(COHERENCE_FULL_PATH))
        data = load_coherence_config({"hardware_profile": "full"})
        self.assertEqual(data.get("version"), 1)
        self.assertEqual(set(data["zones"].keys()), {"pillars", "horizontals"})
        self.assertEqual(set(data["zones"]["pillars"]["segments"]), {"v1", "v2", "v3", "v4"})
        self.assertEqual(
            set(data["zones"]["horizontals"]["segments"]),
            {"h00", "h10", "h11", "h20", "h30", "h31", "h32"},
        )

        inst = make_fake_installation()
        compiled = compile_policy(data, inst.segments, inst.modes)
        for zname, zone in compiled.zones.items():
            zone_set = set(zone.segments)
            for grp in zone.groupings:
                seen = [s for g in grp.groups for s in g]
                self.assertEqual(set(seen), zone_set, f"Grouping {grp.id} failed exact partition of {zname}")
                self.assertEqual(len(seen), len(zone_set), f"Grouping {grp.id} has overlapping segments")

    def test_load_small_config_partitions(self):
        from transitions.fakes import make_fake_small_installation
        from transitions.policy import compile_policy

        self.assertTrue(os.path.exists(COHERENCE_SMALL_PATH))
        data = load_coherence_config({"hardware_profile": "small"})
        self.assertEqual(data.get("version"), 1)
        zone_strips = data["zones"]["strips"]
        all_segs = set(zone_strips["segments"])
        self.assertEqual(all_segs, {"s1", "s2", "s3"})

        inst = make_fake_small_installation()
        compiled = compile_policy(data, inst.segments, inst.modes)
        for grp in compiled.zones["strips"].groupings:
            seen = [s for g in grp.groups for s in g]
            self.assertEqual(set(seen), all_segs, f"Grouping {grp.id} failed exact partition")
            self.assertEqual(len(seen), len(all_segs), f"Grouping {grp.id} has overlapping segments")

    def test_schema_exists_and_is_valid_draft_07(self):
        self.assertTrue(os.path.exists(COHERENCE_SCHEMA_PATH))
        with open(COHERENCE_SCHEMA_PATH, "r", encoding="utf-8") as fh:
            schema = json.load(fh)
        self.assertIn("draft-07", schema.get("$schema", ""))
        self.assertIn("settings", schema.get("properties", {}))
        self.assertIn("zones", schema.get("properties", {}))
        self.assertIn("rules", schema.get("properties", {}))

    def test_resolve_missing_explicit_path_returns_candidate(self):
        bogus = "c:/non_existent_coherence_12345.json"
        resolved = resolve_coherence_file_path(bogus)
        self.assertEqual(resolved, os.path.abspath(bogus))

        resolved_dict = resolve_coherence_file_path({"coherence_file": "missing.json"})
        self.assertTrue(resolved_dict.endswith("missing.json"))

    def test_load_coherence_config_missing_file_raises_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            load_coherence_config("c:/non_existent_coherence_12345.json")

        with self.assertRaises(FileNotFoundError):
            load_coherence_config({"coherence_file": "missing.json"})

    def test_validate_coherence_dict_rejects_booleans_in_settings(self):
        valid = _make_valid_coherence_dict()
        for bad_key, bad_val in [
            ("maxDifferentModes", True),
            ("temperature", True),
            ("memoryDepth", False),
            ("repeatPenalty", False),
        ]:
            bad = copy.deepcopy(valid)
            bad["settings"][bad_key] = bad_val
            with self.subTest(key=bad_key, val=bad_val):
                with self.assertRaises(ValueError):
                    validate_coherence_dict(bad)

    def test_validate_coherence_dict_rejects_invalid_weights(self):
        valid = _make_valid_coherence_dict()
        # Negative / zero rule weight
        for bad_w in [-1.0, 0.0, True, False, "1.0"]:
            bad = copy.deepcopy(valid)
            bad["rules"][0] = {"id": "r1", "when": [{"tag": "layer:bed"}], "weight": bad_w}
            with self.subTest(rule_weight=bad_w):
                with self.assertRaises(ValueError):
                    validate_coherence_dict(bad)

        # Negative / zero grouping weight
        for bad_gw in [-1.0, 0.0, True, False, "1.0"]:
            bad = copy.deepcopy(valid)
            bad["zones"]["all"]["groupings"][0]["weight"] = bad_gw
            with self.subTest(grouping_weight=bad_gw):
                with self.assertRaises(ValueError):
                    validate_coherence_dict(bad)


if __name__ == "__main__":
    unittest.main()
