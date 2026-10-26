"""
tests/governance/test_docs_parity.py
Verifies documentation parity against code and configuration single sources of truth.
- modes.json (21 active modes) parity with docs/reference/modes_catalog.md
- app_config.json keys parity with docs/reference/configuration_schemas.md
- Listener & MusicalContextEngine public attributes documented in docs/contracts/music_analyzer_contract.md
  (signal trust ratings live only in that contract; they are guidance, not enforced here)
"""
import json
import os
import unittest

from music.api import Listener


class TestDocsParity(unittest.TestCase):
    def setUp(self):
        self.repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.modes_json_path = os.path.join(self.repo_root, "config", "modes.json")
        self.modes_catalog_path = os.path.join(self.repo_root, "docs", "reference", "modes_catalog.md")
        self.app_config_path = os.path.join(self.repo_root, "config", "app_config.json")
        self.config_schemas_path = os.path.join(self.repo_root, "docs", "reference", "configuration_schemas.md")
        self.music_contract_path = os.path.join(self.repo_root, "docs", "contracts", "music_analyzer_contract.md")
        self.modes_dir = os.path.join(self.repo_root, "modes")

    def test_modes_catalog_parity(self):
        """Verify all 21 modes in config/modes.json appear in docs/reference/modes_catalog.md."""
        with open(self.modes_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        modes = data.get("standard_modes", [])
        self.assertEqual(len(modes), 21, f"Expected 21 standard modes, found {len(modes)}")

        with open(self.modes_catalog_path, "r", encoding="utf-8") as f:
            catalog_content = f.read()

        missing = []
        for m in modes:
            mode_name = m.get("name")
            mode_class = m.get("class")
            if mode_name not in catalog_content and mode_class not in catalog_content:
                missing.append(f"{mode_name} ({mode_class})")

        self.assertEqual(missing, [], "Modes missing from docs/reference/modes_catalog.md:\n" + "\n".join(missing))

    def test_app_config_schema_parity(self):
        """Verify all keys in config/app_config.json are documented in configuration_schemas.md."""
        with open(self.app_config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        with open(self.config_schemas_path, "r", encoding="utf-8") as f:
            schema_doc = f.read()

        missing = []
        for key in cfg.keys():
            if f"`{key}`" not in schema_doc and f'"{key}"' not in schema_doc:
                missing.append(key)

        self.assertEqual(missing, [], "Keys in app_config.json missing from configuration_schemas.md:\n" + "\n".join(missing))

    def test_ideas_scratchpad_non_authoritative_banner(self):
        """Verify IDEAS.md exists and carries an explicit NOT SYSTEM TRUTH disclaimer for AI agents."""
        ideas_path = os.path.join(self.repo_root, "docs", "ideas", "IDEAS.md")
        self.assertTrue(os.path.exists(ideas_path), "docs/ideas/IDEAS.md scratchpad must exist.")
        with open(ideas_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn(
            "NOT SYSTEM TRUTH",
            content,
            "IDEAS.md must contain the mandatory 'NOT SYSTEM TRUTH' disclaimer banner for AI agents.",
        )


    def test_music_contract_parity(self):
        """
        Verify every public attribute of Listener and MusicalContextEngine is documented
        as `{name}` in docs/contracts/music_analyzer_contract.md.

        Trust ratings (HIGH / MEDIUM / LOW) are engineering guidance stated only in that
        contract; this test checks documentation completeness, not trust tiers.
        """
        self.assertTrue(
            os.path.exists(self.music_contract_path),
            f"Missing contract file: {self.music_contract_path}",
        )
        with open(self.music_contract_path, "r", encoding="utf-8") as f:
            contract_doc = f.read()

        listener = Listener({"useMicrophone": False})
        ctx = listener.context

        surfaces = {
            "Listener": set(dir(Listener)) | set(dir(listener)),
            "MusicalContextEngine": set(dir(type(ctx))) | set(dir(ctx)),
        }
        for owner, names in surfaces.items():
            for name in sorted(n for n in names if not n.startswith("_")):
                self.assertIn(
                    f"`{name}`",
                    contract_doc,
                    f"{owner} public attribute '{name}' is missing as `{name}` in docs/contracts/music_analyzer_contract.md",
                )


if __name__ == "__main__":
    unittest.main()
