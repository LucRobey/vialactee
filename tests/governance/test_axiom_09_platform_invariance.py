"""
tests/governance/test_axiom_09_platform_invariance.py
Enforces AXIOM-09: Scoped DSP Math & Processing Invariance
- Zero platform/OS checks in modes/
- Zero platform/OS checks in core/ (outside isolated hardware thread offload)
"""
import ast
import os
import unittest


class PlatformCheckVisitor(ast.NodeVisitor):
    def __init__(self, filename):
        self.filename = filename
        self.violations = []

    def visit_Attribute(self, node):
        # Detect sys.platform or os.name
        if isinstance(node.value, ast.Name):
            if node.value.id == "sys" and node.attr == "platform":
                self.violations.append(f"{self.filename}:{node.lineno} uses sys.platform")
            elif node.value.id == "os" and node.attr == "name":
                self.violations.append(f"{self.filename}:{node.lineno} uses os.name")
        self.generic_visit(node)

    def visit_Call(self, node):
        # Detect platform.system()
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "platform":
                self.violations.append(f"{self.filename}:{node.lineno} calls platform.{node.func.attr}()")
        self.generic_visit(node)


class TestAxiom09PlatformInvariance(unittest.TestCase):
    def setUp(self):
        self.repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    def test_modes_have_zero_platform_checks(self):
        """Verify no file in modes/ inspects sys.platform or os.name."""
        modes_dir = os.path.join(self.repo_root, "modes")
        violations = []

        for root, _, files in os.walk(modes_dir):
            for file_name in files:
                if not file_name.endswith(".py"):
                    continue
                file_path = os.path.join(root, file_name)
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    try:
                        tree = ast.parse(f.read(), filename=file_name)
                    except SyntaxError:
                        continue
                visitor = PlatformCheckVisitor(file_name)
                visitor.visit(tree)
                violations.extend(visitor.violations)

        self.assertEqual(violations, [], "Platform branching found in modes/:\n" + "\n".join(violations))

    def test_core_dsp_has_zero_platform_checks(self):
        """Verify core/ DSP modules have zero platform checks."""
        core_dir = os.path.join(self.repo_root, "core")
        violations = []

        for root, _, files in os.walk(core_dir):
            for file_name in files:
                if not file_name.endswith(".py"):
                    continue
                file_path = os.path.join(root, file_name)
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    try:
                        tree = ast.parse(f.read(), filename=file_name)
                    except SyntaxError:
                        continue
                visitor = PlatformCheckVisitor(file_name)
                visitor.visit(tree)
                violations.extend(visitor.violations)

        self.assertEqual(violations, [], "Platform branching found in core/:\n" + "\n".join(violations))


if __name__ == "__main__":
    unittest.main()
