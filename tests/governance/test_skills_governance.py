"""
tests/governance/test_skills_governance.py
Automated mechanical governance test for the .agents/skills/ ecosystem.

Verifies:
1. Frontmatter validity (YAML parse, name matches directory, non-empty description).
2. Axiom harmony: no skill mentions "60 FPS" for visual LED rendering (AXIOM-01: 30 FPS).
3. Relative link integrity: all referenced local markdown files exist.
4. Size budget: no SKILL.md exceeds 20 KB (forces modular references).
"""
import os
import re
import unittest

try:
    import yaml  # type: ignore
except ImportError:
    class _MinimalYaml:
        @staticmethod
        def safe_load(text: str):
            data = {}
            for raw_line in text.splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if ":" not in line:
                    raise ValueError(f"Invalid YAML frontmatter line: {raw_line!r}")
                key, val = line.split(":", 1)
                val = val.strip()
                if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
                    val = val[1:-1]
                data[key.strip()] = val
            return data

    yaml = _MinimalYaml()


class TestSkillsGovernance(unittest.TestCase):
    def setUp(self):
        self.repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.skills_dir = os.path.join(self.repo_root, ".agents", "skills")
        self.expected_skills = [
            "vialactee-dsp-engine",
            "vialactee-mode-creator",
            "vialactee-project",
            "vialactee-research-manager",
            "vialactee-researcher",
        ]

    def test_expected_active_skills_present(self):
        """Verify the exact lean portfolio of active skills exists."""
        active_dirs = sorted([
            d for d in os.listdir(self.skills_dir)
            if os.path.isdir(os.path.join(self.skills_dir, d))
        ])
        self.assertEqual(
            active_dirs,
            sorted(self.expected_skills),
            f"Active skills mismatch. Found: {active_dirs}, Expected: {self.expected_skills}"
        )

    def test_skill_frontmatter_validity(self):
        """Verify that every SKILL.md has valid YAML frontmatter, matching name, and valid description."""
        for skill_name in self.expected_skills:
            skill_md_path = os.path.join(self.skills_dir, skill_name, "SKILL.md")
            self.assertTrue(os.path.exists(skill_md_path), f"Missing SKILL.md in {skill_name}")

            with open(skill_md_path, "r", encoding="utf-8") as f:
                content = f.read()

            self.assertTrue(content.startswith("---"), f"{skill_name}/SKILL.md must start with YAML frontmatter delimiter '---'")
            parts = content.split("---", 2)
            self.assertGreaterEqual(len(parts), 3, f"{skill_name}/SKILL.md must have opening and closing '---' delimiters")

            yaml_str = parts[1]
            try:
                frontmatter = yaml.safe_load(yaml_str)
            except Exception as e:
                self.fail(f"YAML frontmatter parse failed for {skill_name}/SKILL.md: {e}")

            self.assertIsInstance(frontmatter, dict, f"Frontmatter in {skill_name}/SKILL.md must be a dictionary")
            self.assertEqual(frontmatter.get("name"), skill_name, f"Frontmatter 'name' must match folder name '{skill_name}'")
            self.assertIn("description", frontmatter, f"Frontmatter in {skill_name}/SKILL.md must contain 'description'")
            desc = frontmatter.get("description")
            self.assertIsInstance(desc, str, f"'description' in {skill_name}/SKILL.md must be a string")
            self.assertGreater(len(desc.strip()), 10, f"'description' in {skill_name}/SKILL.md is too short")
            self.assertLess(len(desc), 1000, f"'description' in {skill_name}/SKILL.md exceeds 1000 characters")

    def test_axiom_01_frame_budget_harmony(self):
        """Verify no skill claims 60 FPS for LED rendering (AXIOM-01: 30 FPS rendering, 60 Hz audio ticks)."""
        for skill_name in self.expected_skills:
            skill_folder = os.path.join(self.skills_dir, skill_name)
            for root, _, files in os.walk(skill_folder):
                for file in files:
                    if not file.endswith(".md"):
                        continue
                    fp = os.path.join(root, file)
                    with open(fp, "r", encoding="utf-8") as f:
                        text = f.read()

                    # Find occurrences of '60 FPS' or '60fps'
                    matches = re.findall(r"(?:maintain|render|display|budget)\s*(?:at\s*)?60\s*fps", text, re.IGNORECASE)
                    self.assertEqual(
                        matches, [],
                        f"Found prohibited 60 FPS rendering claim in {os.path.relpath(fp, self.repo_root)}: {matches}. (AXIOM-01: 30 FPS rendering)."
                    )

    def test_skill_size_budgets(self):
        """Verify no SKILL.md exceeds 20 KB (forces modular reference files)."""
        for skill_name in self.expected_skills:
            skill_md_path = os.path.join(self.skills_dir, skill_name, "SKILL.md")
            size_kb = os.path.getsize(skill_md_path) / 1024.0
            self.assertLessEqual(
                size_kb, 20.0,
                f"{skill_name}/SKILL.md is {size_kb:.1f} KB, exceeding the 20.0 KB size budget."
            )

    def test_relative_links_integrity(self):
        """Verify all local markdown links in SKILL.md point to real existing files."""
        link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
        import urllib.parse
        for skill_name in self.expected_skills:
            skill_md_path = os.path.join(self.skills_dir, skill_name, "SKILL.md")
            skill_dir = os.path.dirname(skill_md_path)
            with open(skill_md_path, "r", encoding="utf-8") as f:
                content = f.read()

            for match in link_pattern.finditer(content):
                target = match.group(2)
                # Ignore web URLs, anchors, or mailto
                if target.startswith("http") or target.startswith("#") or target.startswith("mailto:"):
                    continue
                # Unquote URL encoding (%C3%A9 -> é)
                target_decoded = urllib.parse.unquote(target)
                if target_decoded.startswith("file:///"):
                    target_path = target_decoded.replace("file:///", "").replace("/", os.sep)
                else:
                    target_path = os.path.normpath(os.path.join(skill_dir, target_decoded))

                # Strip anchor tags like #section
                target_clean = target_path.split("#")[0]
                self.assertTrue(
                    os.path.exists(target_clean),
                    f"Broken link in {skill_name}/SKILL.md: '{target}' resolved to non-existent '{target_clean}'"
                )


if __name__ == "__main__":
    unittest.main()
