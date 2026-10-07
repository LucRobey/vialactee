"""
AXIOM governance: the transition sector is a sealed room.

1. Nothing inside transitions/ may import project code (core, modes, connectors, hardware,
   config, utils, tools, ...). Only the standard library, numpy, PIL and transitions itself.
2. Nothing outside transitions/ may import its internals; production code may import only
   `transitions.api`. (Tests are exempt so they can unit-test the internals.)
"""
import ast
import os
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ROOM = "transitions"
SKIP_DIRS = {".git", "__pycache__", "node_modules", "wabb-interface", "archive", "scratch",
             ".temp_scratch", "research", "tests", ".agents", "playground", ".pytest_cache"}


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


class TestTransitionIsolation(unittest.TestCase):
    def test_room_imports_no_project_code(self):
        forbidden = _project_roots()
        violations = []
        for path in _py_files(os.path.join(REPO_ROOT, ROOM), {"__pycache__"}):
            for module, _ in _imports(path):
                if module.split(".")[0] in forbidden:
                    violations.append(f"{os.path.relpath(path, REPO_ROOT)} imports {module}")
        self.assertEqual(violations, [], "The transition sector reached outside its wall:\n" + "\n".join(violations))

    def test_outside_code_uses_only_the_front_door(self):
        violations = []
        for path in _py_files(REPO_ROOT, SKIP_DIRS | {ROOM}):
            rel = os.path.relpath(path, REPO_ROOT)
            for module, names in _imports(path):
                parts = module.split(".")
                if parts[0] != ROOM:
                    continue
                if len(parts) == 1:
                    # `from transitions import x` : only api is allowed
                    bad = [n for n in names if n != "api"]
                    if bad or not names:
                        violations.append(f"{rel} imports {module} ({', '.join(names) or 'whole package'})")
                elif parts[1] != "api":
                    violations.append(f"{rel} imports {module}")
        self.assertEqual(violations, [], "Code outside the sector used its internals:\n" + "\n".join(violations))

    def test_wall_check_detects_violations(self):
        """Guard the guard: the checker itself must flag a synthetic violation."""
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write("from core.Segment import Segment\nimport numpy\n")
        self.addCleanup(os.unlink, f.name)
        modules = [m for m, _ in _imports(f.name)]
        self.assertIn("core.Segment", modules)
        self.assertIn("core", _project_roots())


if __name__ == "__main__":
    unittest.main()
