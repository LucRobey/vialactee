"""
tests/governance/test_lab_isolation.py
The two research labs never import each other.

- The choreography lab (research/choreography/) may not import the music lab's code (research/scoreboard,
  research/experiments, research/benchmarks, research/analyzer_trials), nor the truth builders (research/truth),
  nor the inside of music/ (only the door, music.api).
- The music lab, the truth builders and music/ may not import the choreography lab.

What the labs share is data: the signal contract (config/music_signals.json), the truth files, and recordings
whose columns are the contract's slot names.
"""
import ast
import os
import tempfile
import unittest
from typing import Iterable, List, Tuple

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SKIP_DIRS = {"__pycache__", ".venv", "output", "vendor", "runs"}

CHOREOGRAPHY = ("research/choreography",)
CHOREOGRAPHY_FORBIDDEN = ("research.scoreboard", "research.experiments", "research.benchmarks", "research.analyzer_trials", "research.truth")
MUSIC_SIDE = ("research/scoreboard", "research/experiments", "research/benchmarks", "research/truth", "music")
MUSIC_SIDE_FORBIDDEN = ("research.choreography",)
MUSIC_DOOR = "music.api"


def _python_files(folders: Iterable[str]) -> List[str]:
    out = []
    for folder in folders:
        for root, dirs, files in os.walk(os.path.join(REPO_ROOT, folder)):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            out += [os.path.join(root, f) for f in files if f.endswith(".py")]
    return out


def _imports(path: str) -> List[Tuple[int, str]]:
    with open(path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=path)
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [(node.lineno, alias.name) for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.append((node.lineno, node.module))
    return found


def _is_under(module: str, package: str) -> bool:
    return module == package or module.startswith(package + ".")


def violations(files: Iterable[str], forbidden: Iterable[str], door_only_for_music: bool) -> List[str]:
    out = []
    for path in files:
        for line, module in _imports(path):
            bad = any(_is_under(module, pkg) for pkg in forbidden)
            if door_only_for_music and _is_under(module, "music") and module != MUSIC_DOOR:
                bad = True
            if bad:
                out.append(f"{os.path.relpath(path, REPO_ROOT)}:{line} imports {module}")
    return out


class TestLabIsolation(unittest.TestCase):
    def test_choreography_lab_does_not_import_the_music_lab(self):
        files = _python_files(CHOREOGRAPHY)
        self.assertGreater(len(files), 3, "research/choreography/ not found")
        self.assertEqual(violations(files, CHOREOGRAPHY_FORBIDDEN, door_only_for_music=True), [])

    def test_music_side_does_not_import_the_choreography_lab(self):
        files = _python_files(MUSIC_SIDE)
        self.assertGreater(len(files), 10)
        self.assertEqual(violations(files, MUSIC_SIDE_FORBIDDEN, door_only_for_music=False), [])

    def test_the_check_sees_a_violation(self):
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write("import numpy\nfrom research.scoreboard import grade\nfrom music.Listener import Listener\nfrom music.api import Listener as L\n")
            path = f.name
        try:
            found = violations([path], CHOREOGRAPHY_FORBIDDEN, door_only_for_music=True)
        finally:
            os.unlink(path)
        self.assertEqual(len(found), 2)
        self.assertTrue(any("research.scoreboard" in v for v in found))
        self.assertTrue(any("music.Listener" in v for v in found))


if __name__ == "__main__":
    unittest.main()
