"""
tests/governance/test_mode_choreography.py
Governance test for Law 7 (One Lead Timescale) in docs/contracts/mode_contract.md:
1. Every mode in config/modes.json declares a LEAD that is in DRIVERS.
2. SECONDARY is a tuple with at most one entry, each entry is in DRIVERS, and differs from LEAD.
3. The mode class docstring contains 'Lead:' (forces a one-line human explanation).
4. docs/reference/modes_catalog.md shows the exact same Lead and Secondary as the code.
"""
import importlib
import json
import os
import re
import unittest

from utils.choreography import DRIVERS


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

        # Parse table rows from Section 1:
        # | # | **Mode Name** | [`Class_mode`](...) | Orientation | `lead` | `secondary` | Description |
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


if __name__ == "__main__":
    unittest.main()
