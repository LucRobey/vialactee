"""
AXIOM governance: the music analysis sector is a sealed room.

1. Nothing inside music/ may import project code outside music/ (core, modes, connectors,
   hardware, config, transitions, mood, utils, tools, ...). Only the standard library,
   numpy and music itself.
2. Production code outside music/ may import only `music.api`. (Tests, research, and
   developer tools/scripts are exempt so they can inspect and benchmark internals.)
3. None of the 10 music modules may remain in core/ as shims.
"""
import ast
import os
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ROOM = "music"
SKIP_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    "wabb-interface",
    "archive",
    "scratch",
    ".temp_scratch",
    "research",
    "tests",
    "tools",
    "scripts",
    ".agents",
    "playground",
    ".pytest_cache",
    ".venv",
}

MOVED_MUSIC_FILES = (
    "AudioIngestion.py",
    "BaseAudioAnalyzer.py",
    "AudioAnalyzer.py",
    "MultiBandOnsetAudioAnalyzer.py",
    "DyadicMetricalAudioAnalyzer.py",
    "comb_kernels.py",
    "StructuralNoveltyDetector.py",
    "RhythmConfig.py",
    "MusicalContextEngine.py",
    "Listener.py",
)


def _project_roots():
    """Top-level project packages/modules (everything that is project code, minus the room)."""
    roots = set()
    for name in os.listdir(REPO_ROOT):
        path = os.path.join(REPO_ROOT, name)
        if os.path.isdir(path) and name not in SKIP_DIRS and not name.startswith("."):
            roots.add(name)
        elif name.endswith(".py"):
            roots.add(name[:-3])
    roots.discard(ROOM)
    return roots


def _imports(path):
    """Yields (module, names) for each import in the file. names is () for plain `import x`."""
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        tree = ast.parse(f.read(), filename=path)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name, ()
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.module, tuple(a.name for a in node.names)


def _py_files(base, skip_dirs):
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for name in files:
            if name.endswith(".py"):
                yield os.path.join(root, name)


class TestMusicIsolation(unittest.TestCase):
    def test_room_imports_no_project_code(self):
        forbidden = _project_roots()
        violations = []
        for path in _py_files(os.path.join(REPO_ROOT, ROOM), {"__pycache__"}):
            for module, _ in _imports(path):
                if module.split(".")[0] in forbidden:
                    violations.append(f"{os.path.relpath(path, REPO_ROOT)} imports {module}")
        self.assertEqual(violations, [], "The music sector reached outside its wall:\n" + "\n".join(violations))

    def test_outside_code_uses_only_the_front_door(self):
        violations = []
        for path in _py_files(REPO_ROOT, SKIP_DIRS | {ROOM}):
            rel = os.path.relpath(path, REPO_ROOT)
            for module, names in _imports(path):
                parts = module.split(".")
                if parts[0] != ROOM:
                    continue
                if len(parts) == 1:
                    # `from music import x` : only api is allowed
                    bad = [n for n in names if n != "api"]
                    if bad or not names:
                        violations.append(f"{rel} imports {module} ({', '.join(names) or 'whole package'})")
                elif parts[1] != "api":
                    violations.append(f"{rel} imports {module}")
        self.assertEqual(violations, [], "Production code outside music/ used its internals:\n" + "\n".join(violations))

    def test_no_shims_remain_in_core(self):
        core_dir = os.path.join(REPO_ROOT, "core")
        music_dir = os.path.join(REPO_ROOT, "music")
        lingering = [fn for fn in MOVED_MUSIC_FILES if os.path.exists(os.path.join(core_dir, fn))]
        missing = [fn for fn in MOVED_MUSIC_FILES if not os.path.isfile(os.path.join(music_dir, fn))]
        self.assertEqual(lingering, [], f"Music shims or files still present in core/: {lingering}")
        self.assertEqual(missing, [], f"Moved music files missing from music/: {missing}")

    def test_wall_check_detects_violations(self):
        """Guard the guard: the checker itself must flag a synthetic violation."""
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write("from core.Segment import Segment\nimport numpy\n")
        self.addCleanup(os.unlink, f.name)
        modules = [m for m, _ in _imports(f.name)]
        self.assertIn("core.Segment", modules)
        self.assertIn("core", _project_roots())
        self.assertIn("transitions", _project_roots())
        self.assertIn("mood", _project_roots())


if __name__ == "__main__":
    unittest.main()
