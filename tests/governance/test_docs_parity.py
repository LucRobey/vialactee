"""
tests/governance/test_docs_parity.py
Verifies documentation parity against code and configuration single sources of truth.
- modes.json (21 active modes) parity with docs/reference/modes_catalog.md
- app_config.json keys parity with docs/reference/configuration_schemas.md
- Listener & MusicalContextEngine public attributes parity with music.api trust sets and docs/contracts/music_analyzer_contract.md
- AST enforcement of Mode Sector Contract trust tiers across all 21 concrete modes
"""
import ast
import json
import os
import unittest

from music.api import (
    CONTEXT_HIGH_TRUST,
    CONTEXT_INTERNAL_ATTRS,
    CONTEXT_LOW_TRUST,
    CONTEXT_MEDIUM_TRUST,
    CONTEXT_TRUST_SETS,
    LISTENER_CONFIG_TRUST,
    LISTENER_HIGH_TRUST,
    LISTENER_INTERNAL_ATTRS,
    LISTENER_LOW_TRUST,
    LISTENER_MEDIUM_TRUST,
    LISTENER_TRUST_SETS,
    Listener,
)


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
        ideas_path = os.path.join(self.repo_root, "IDEAS.md")
        self.assertTrue(os.path.exists(ideas_path), "Root IDEAS.md scratchpad must exist.")
        with open(ideas_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn(
            "NOT SYSTEM TRUTH",
            content,
            "IDEAS.md must contain the mandatory 'NOT SYSTEM TRUTH' disclaimer banner for AI agents.",
        )

    def test_music_contract_parity(self):
        """
        Verify every public attribute of Listener and MusicalContextEngine is:
        1. Either in LISTENER_INTERNAL_ATTRS / CONTEXT_INTERNAL_ATTRS, or in exactly one trust set in music.api.
        2. Documented as `{name}` in docs/contracts/music_analyzer_contract.md.
        3. Free of stale entries in trust sets or internal allowlists.
        """
        self.assertTrue(
            os.path.exists(self.music_contract_path),
            f"Missing contract file: {self.music_contract_path}",
        )
        with open(self.music_contract_path, "r", encoding="utf-8") as f:
            contract_doc = f.read()

        listener = Listener({"useMicrophone": False})
        ctx = listener.context

        listener_all_public = {
            name for name in (set(dir(Listener)) | set(dir(listener))) if not name.startswith("_")
        }
        ctx_all_public = {
            name for name in (set(dir(type(ctx))) | set(dir(ctx))) if not name.startswith("_")
        }

        listener_signals = listener_all_public - LISTENER_INTERNAL_ATTRS
        ctx_signals = ctx_all_public - CONTEXT_INTERNAL_ATTRS

        # 1. Check Listener signals are in exactly one trust set and documented
        listener_sets = [
            ("LISTENER_HIGH_TRUST", LISTENER_HIGH_TRUST),
            ("LISTENER_MEDIUM_TRUST", LISTENER_MEDIUM_TRUST),
            ("LISTENER_LOW_TRUST", LISTENER_LOW_TRUST),
            ("LISTENER_CONFIG_TRUST", LISTENER_CONFIG_TRUST),
        ]
        for sig in sorted(listener_signals):
            matching_sets = [set_name for set_name, trust_set in listener_sets if sig in trust_set]
            self.assertEqual(
                len(matching_sets),
                1,
                f"Listener public signal '{sig}' must appear in exactly 1 trust set in music.api, found in: {matching_sets}",
            )
            self.assertTrue(
                f"`{sig}`" in contract_doc,
                f"Listener public signal '{sig}' is missing as `{sig}` in docs/contracts/music_analyzer_contract.md",
            )

        # 2. Check MusicalContextEngine signals are in exactly one trust set and documented
        ctx_sets = [
            ("CONTEXT_HIGH_TRUST", CONTEXT_HIGH_TRUST),
            ("CONTEXT_MEDIUM_TRUST", CONTEXT_MEDIUM_TRUST),
            ("CONTEXT_LOW_TRUST", CONTEXT_LOW_TRUST),
        ]
        for sig in sorted(ctx_signals):
            matching_sets = [set_name for set_name, trust_set in ctx_sets if sig in trust_set]
            self.assertEqual(
                len(matching_sets),
                1,
                f"MusicalContextEngine public signal '{sig}' must appear in exactly 1 trust set in music.api, found in: {matching_sets}",
            )
            self.assertTrue(
                f"`{sig}`" in contract_doc,
                f"MusicalContextEngine public signal '{sig}' is missing as `{sig}` in docs/contracts/music_analyzer_contract.md",
            )

        # 3. Check for stale entries in Listener trust sets and internal allowlist
        all_listener_declared = (
            LISTENER_INTERNAL_ATTRS
            | LISTENER_HIGH_TRUST
            | LISTENER_MEDIUM_TRUST
            | LISTENER_LOW_TRUST
            | LISTENER_CONFIG_TRUST
        )
        stale_listener = all_listener_declared - listener_all_public
        self.assertEqual(
            stale_listener,
            set(),
            f"Stale attributes declared in music.api Listener sets that do not exist on Listener: {sorted(stale_listener)}",
        )

        # 4. Check for stale entries in MusicalContextEngine trust sets and internal allowlist
        all_ctx_declared = (
            CONTEXT_INTERNAL_ATTRS
            | CONTEXT_HIGH_TRUST
            | CONTEXT_MEDIUM_TRUST
            | CONTEXT_LOW_TRUST
        )
        stale_ctx = all_ctx_declared - ctx_all_public
        self.assertEqual(
            stale_ctx,
            set(),
            f"Stale attributes declared in music.api Context sets that do not exist on MusicalContextEngine: {sorted(stale_ctx)}",
        )

        # 5. Also verify internal attributes are documented in music_analyzer_contract.md
        for internal_attr in sorted(LISTENER_INTERNAL_ATTRS | CONTEXT_INTERNAL_ATTRS):
            self.assertTrue(
                f"`{internal_attr}`" in contract_doc,
                f"Internal attribute '{internal_attr}' is missing as `{internal_attr}` in docs/contracts/music_analyzer_contract.md",
            )

    @staticmethod
    def _extract_mode_signal_identifiers(tree: ast.AST) -> set:
        """
        Extract code-level identifiers from a mode AST:
        - ast.Attribute (.attr)
        - ast.Name (.id)
        - ast.Call to getattr/hasattr with a string literal 2nd argument
        Never inspects docstrings or comments.
        """
        identifiers = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                identifiers.add(node.attr)
            elif isinstance(node, ast.Name):
                identifiers.add(node.id)
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in ("getattr", "hasattr")
                and len(node.args) >= 2
                and isinstance(node.args[1], ast.Constant)
                and isinstance(node.args[1].value, str)
            ):
                identifiers.add(node.args[1].value)
        return identifiers

    def test_modes_respect_trust_tiers(self):
        """
        AST-based enforcement of Mode Sector Contract trust tiers across all concrete modes:
        - Rule A (LOW trust forbidden): Concrete modes must not access LOW-trust structural/scene flags.
        - Rule B (MEDIUM trust gated): Any concrete mode accessing MEDIUM-trust beat/tempo signals
          must also reference at least one sanctioned confidence gate or helper.
        """
        forbidden_low_trust = {
            "scene",
            "is_drop_impact",
            "is_drop_imminent",
            "is_song_change",
            "is_verse_chorus_change",
            "is_structural_cut",
        }
        medium_trust_signals = {
            "beat_phase",
            "is_beat",
            "bpm",
            "is_real_beat",
            "beat_count",
        }
        required_gates = {
            "rhythm_lock",
            "beat_trust",
            "rhythm_salience",
            "is_locked",
            "beat_confidence",
            "beat_pulse",
        }

        # Guard the guard: verify AST extractor catches getattr() string lookups and ignores docstrings/comments
        synthetic_tree = ast.parse(
            '"""Docstring mentioning listener.bpm and ctx.scene."""\n'
            '# Comment mentioning is_drop_impact\n'
            'x = getattr(ctx, "scene", None)\n'
            'y = getattr(listener, "beat_phase", 0.0)\n'
        )
        synthetic_ids = self._extract_mode_signal_identifiers(synthetic_tree)
        self.assertIn("scene", synthetic_ids)
        self.assertIn("beat_phase", synthetic_ids)
        self.assertNotIn("bpm", synthetic_ids)
        self.assertNotIn("is_drop_impact", synthetic_ids)

        # Ratchet sets for grandfathered exceptions (currently 0 exceptions across all 21 modes)
        low_trust_grandfathered = frozenset()
        medium_trust_grandfathered = frozenset()

        mode_files = sorted(
            f
            for f in os.listdir(self.modes_dir)
            if f.endswith(".py") and f not in ("Mode.py", "__init__.py")
        )
        self.assertEqual(len(mode_files), 21, f"Expected 21 concrete mode files, found {len(mode_files)}")

        rule_a_violations = []
        rule_b_violations = []
        seen_low_grandfathered = set()
        seen_medium_grandfathered = set()

        for fname in mode_files:
            fpath = os.path.join(self.modes_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=fpath)

            identifiers = self._extract_mode_signal_identifiers(tree)

            # Rule A: Forbidden LOW-trust signals
            used_low = identifiers & forbidden_low_trust
            if used_low:
                if fname in low_trust_grandfathered:
                    seen_low_grandfathered.add(fname)
                else:
                    rule_a_violations.append(
                        f"{fname}: accesses forbidden LOW-trust signal(s) {sorted(used_low)}"
                    )

            # Rule B: MEDIUM-trust signals require at least one confidence gate/helper
            used_medium = identifiers & medium_trust_signals
            used_gates = identifiers & required_gates
            if used_medium and not used_gates:
                if fname in medium_trust_grandfathered:
                    seen_medium_grandfathered.add(fname)
                else:
                    rule_b_violations.append(
                        f"{fname}: accesses MEDIUM-trust signal(s) {sorted(used_medium)} without any gate in {sorted(required_gates)}"
                    )

        self.assertEqual(
            rule_a_violations,
            [],
            "Rule A (LOW-trust forbidden in concrete modes) violations:\n" + "\n".join(rule_a_violations),
        )
        self.assertEqual(
            rule_b_violations,
            [],
            "Rule B (MEDIUM-trust signals must be gated) violations:\n" + "\n".join(rule_b_violations),
        )

        # Ratchet check: ensure no stale entries in grandfathered sets
        stale_low = low_trust_grandfathered - seen_low_grandfathered
        stale_medium = medium_trust_grandfathered - seen_medium_grandfathered
        self.assertEqual(
            stale_low,
            frozenset(),
            f"Stale entries in low_trust_grandfathered (please remove): {sorted(stale_low)}",
        )
        self.assertEqual(
            stale_medium,
            frozenset(),
            f"Stale entries in medium_trust_grandfathered (please remove): {sorted(stale_medium)}",
        )


if __name__ == "__main__":
    unittest.main()


