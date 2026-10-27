"""
tests/governance/test_docs_parity.py
Verifies documentation parity against code and configuration single sources of truth:
1. Single documentation root: no *.md files inside code directories (core/, music/, modes/,
   mood/, transitions/, config/, connectors/, hardware/, tools/, wabb-interface/) or root
   (other than README.md).
2. Link integrity: all relative markdown links in docs/** (excluding docs/archive/),
   README.md, and .agents/AGENT.md resolve to existing files or directories.
3. Retired symbols: Transition_Director, Transition_Engine, data/configurations_,
   /api/configurations, Configurator.tsx, MoodDirector, c:/Users/Users/, and MODE_RULES
   must not appear in docs/ outside docs/archive/.
4. Counts that cannot drift: modes.json (21 active modes) parity with
   docs/reference/modes_catalog.md, docs/README.md, and docs/architecture/system_overview.md.
5. app_config.json keys parity with docs/reference/configuration_schemas.md.
6. Listener & MusicalContextEngine public attributes documented in
   docs/contracts/music_analyzer_contract.md.
"""
import json
import os
import re
import unittest

from music.api import Listener


CODE_DIRS_WITHOUT_MD = (
    "core",
    "music",
    "modes",
    "mood",
    "transitions",
    "config",
    "connectors",
    "hardware",
    "tools",
    "wabb-interface",
)

SKIP_WALK_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    "dist",
    ".pytest_cache",
    ".venv",
}

RETIRED_DOC_SYMBOLS = (
    "Transition_Director",
    "Transition_Engine",
    "data/configurations_",
    "/api/configurations",
    "Configurator.tsx",
    "MoodDirector",
    "c:/Users/Users/",
    "MODE_RULES",
)

MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


class TestDocsParity(unittest.TestCase):
    def setUp(self):
        self.repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.docs_dir = os.path.join(self.repo_root, "docs")
        self.docs_archive_dir = os.path.abspath(os.path.join(self.docs_dir, "archive"))
        self.modes_json_path = os.path.join(self.repo_root, "config", "modes.json")
        self.modes_catalog_path = os.path.join(self.docs_dir, "reference", "modes_catalog.md")
        self.docs_readme_path = os.path.join(self.docs_dir, "README.md")
        self.system_overview_path = os.path.join(self.docs_dir, "architecture", "system_overview.md")
        self.app_config_path = os.path.join(self.repo_root, "config", "app_config.json")
        self.config_schemas_path = os.path.join(self.docs_dir, "reference", "configuration_schemas.md")
        self.music_contract_path = os.path.join(self.docs_dir, "contracts", "music_analyzer_contract.md")
        self.modes_dir = os.path.join(self.repo_root, "modes")

    def _iter_active_docs_md_files(self):
        """Yields all .md files under docs/ excluding docs/archive/."""
        for root, dirs, files in os.walk(self.docs_dir):
            dirs[:] = [
                d for d in dirs
                if d not in SKIP_WALK_DIRS
                and os.path.abspath(os.path.join(root, d)) != self.docs_archive_dir
            ]
            for fn in sorted(files):
                if fn.lower().endswith(".md"):
                    yield os.path.join(root, fn)

    def test_single_documentation_root_no_md_in_code_dirs(self):
        """Verify no *.md files exist in code directories or root (except README.md)."""
        stray_md = []
        for code_dir in CODE_DIRS_WITHOUT_MD:
            base = os.path.join(self.repo_root, code_dir)
            if not os.path.isdir(base):
                continue
            for root, dirs, files in os.walk(base):
                dirs[:] = [d for d in dirs if d not in SKIP_WALK_DIRS]
                for fn in files:
                    if fn.lower().endswith(".md"):
                        rel = os.path.relpath(os.path.join(root, fn), self.repo_root)
                        stray_md.append(rel.replace("\\", "/"))

        for fn in os.listdir(self.repo_root):
            full = os.path.join(self.repo_root, fn)
            if os.path.isfile(full) and fn.lower().endswith(".md") and fn != "README.md":
                stray_md.append(fn)

        self.assertEqual(
            stray_md,
            [],
            "Markdown files found outside docs/ (single-root violation):\n" + "\n".join(stray_md),
        )

    def test_relative_links_resolve(self):
        """Verify relative markdown links in docs/** (except archive/), README.md, and .agents/AGENT.md exist."""
        files_to_check = list(self._iter_active_docs_md_files())
        root_readme = os.path.join(self.repo_root, "README.md")
        agent_md = os.path.join(self.repo_root, ".agents", "AGENT.md")
        for extra in (root_readme, agent_md):
            if os.path.isfile(extra):
                files_to_check.append(extra)

        broken_links = []
        for md_path in files_to_check:
            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read()
            # Strip fenced code blocks before extracting links so code examples don't false-trigger
            stripped = re.sub(r"```.*?```", "", content, flags=re.DOTALL)
            for match in MARKDOWN_LINK_RE.finditer(stripped):
                raw_target = match.group(1).strip()
                if not raw_target or raw_target.startswith(("#", "http://", "https://", "mailto:", "ws://", "wss://", "file://")):
                    continue
                target_path = raw_target.split("#", 1)[0].split("?", 1)[0].strip()
                if not target_path:
                    continue
                resolved = os.path.normpath(os.path.join(os.path.dirname(md_path), target_path))
                if not os.path.exists(resolved):
                    rel_src = os.path.relpath(md_path, self.repo_root).replace("\\", "/")
                    broken_links.append(f"{rel_src} -> {raw_target}")

        self.assertEqual(
            broken_links,
            [],
            "Broken relative markdown links found:\n" + "\n".join(broken_links),
        )

    def test_no_retired_symbols_in_active_docs(self):
        """Verify retired symbols do not appear in docs/ outside docs/archive/."""
        violations = []
        for md_path in self._iter_active_docs_md_files():
            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read()
            rel_src = os.path.relpath(md_path, self.repo_root).replace("\\", "/")
            for symbol in RETIRED_DOC_SYMBOLS:
                if symbol in content:
                    violations.append(f"{rel_src} contains retired symbol '{symbol}'")

        self.assertEqual(
            violations,
            [],
            "Retired symbols found in active docs/:\n" + "\n".join(violations),
        )

    def test_modes_catalog_and_counts_parity(self):
        """
        Verify all modes in config/modes.json appear in docs/reference/modes_catalog.md,
        and the mode count in docs/README.md and docs/architecture/system_overview.md
        matches len(config/modes.json).
        """
        with open(self.modes_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        modes = data.get("standard_modes", [])
        expected_count = len(modes)
        self.assertGreater(expected_count, 0, "config/modes.json must register at least one mode")

        with open(self.modes_catalog_path, "r", encoding="utf-8") as f:
            catalog_content = f.read()

        missing = []
        for m in modes:
            mode_name = m.get("name")
            mode_class = m.get("class")
            if mode_name not in catalog_content and mode_class not in catalog_content:
                missing.append(f"{mode_name} ({mode_class})")

        self.assertEqual(missing, [], "Modes missing from docs/reference/modes_catalog.md:\n" + "\n".join(missing))

        for doc_path in (self.modes_catalog_path, self.docs_readme_path, self.system_overview_path):
            with open(doc_path, "r", encoding="utf-8") as f:
                doc_text = f.read()
            rel = os.path.relpath(doc_path, self.repo_root).replace("\\", "/")
            # Ensure the exact mode count is stated and no stale mode counts (e.g. "22 Active" / "22 modes") remain
            self.assertRegex(
                doc_text,
                rf"(?i)\b{expected_count}\b.*mode",
                f"{rel} must state the active mode count ({expected_count}) from config/modes.json",
            )
            stale_matches = re.findall(r"\b(\d+)\s+(?:active\s+)?(?:mounted\s+)?(?:visual\s+)?modes\b", doc_text, flags=re.IGNORECASE)
            for num_str in stale_matches:
                self.assertEqual(
                    int(num_str),
                    expected_count,
                    f"{rel} claims '{num_str} modes' but len(config/modes.json) == {expected_count}",
                )

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

    def test_guards_handle_edge_cases(self):
        """Verify link extraction handles #anchors, ignores fenced code blocks and URLs, and retired symbols list is complete."""
        sample_md = (
            "Valid [Portal](./README.md#tier-0) and [External](https://example.com/foo.md).\n"
            "```markdown\n[IgnoredInsideFence](./non_existent_in_code_block.md)\n```\n"
            "Broken [Missing](./definitely_does_not_exist_12345.md#sec1)."
        )
        stripped = re.sub(r"```.*?```", "", sample_md, flags=re.DOTALL)
        targets = [m.group(1).strip() for m in MARKDOWN_LINK_RE.finditer(stripped)]
        self.assertIn("./README.md#tier-0", targets)
        self.assertIn("./definitely_does_not_exist_12345.md#sec1", targets)
        self.assertNotIn("./non_existent_in_code_block.md", targets)
        for required_sym in (
            "Transition_Director",
            "Transition_Engine",
            "data/configurations_",
            "/api/configurations",
            "Configurator.tsx",
            "MoodDirector",
            "c:/Users/Users/",
            "MODE_RULES",
        ):
            self.assertIn(required_sym, RETIRED_DOC_SYMBOLS)


if __name__ == "__main__":
    unittest.main()
