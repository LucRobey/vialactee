"""
tests/governance/test_docs_parity.py
Verifies documentation parity against code and configuration single sources of truth.
- modes.json (22 active modes) parity with docs/reference/modes_catalog.md
- app_config.json keys parity with docs/reference/configuration_schemas.md
"""
import json
import os
import unittest


class TestDocsParity(unittest.TestCase):
    def setUp(self):
        self.repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.modes_json_path = os.path.join(self.repo_root, "config", "modes.json")
        self.modes_catalog_path = os.path.join(self.repo_root, "docs", "reference", "modes_catalog.md")
        self.app_config_path = os.path.join(self.repo_root, "config", "app_config.json")
        self.config_schemas_path = os.path.join(self.repo_root, "docs", "reference", "configuration_schemas.md")

    def test_modes_catalog_parity(self):
        """Verify all 22 modes in config/modes.json appear in docs/reference/modes_catalog.md."""
        with open(self.modes_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        modes = data.get("standard_modes", [])
        self.assertEqual(len(modes), 22, f"Expected 22 standard modes, found {len(modes)}")

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


if __name__ == "__main__":
    unittest.main()
