"""
tests/test_code_governance.py - Enforces Constitution Law 3 (500-Line Rule & Ratchet)
"""
import os
import unittest


class TestCodeGovernance(unittest.TestCase):
    """
    Enforces Article II, Law 3: Agent-Native Navigability
    - No new or modified production file may exceed 500 lines.
    - Legacy core files are grandfathered under a strict ratchet: they may shrink, never expand.
    """

    GRANDFATHERED_RATCHET = {
        os.path.normpath("core/AudioAnalyzer.py"): 598,
        os.path.normpath("core/Mode_master.py"): 613,
        os.path.normpath("core/MultiBandOnsetAudioAnalyzer.py"): 621,
        os.path.normpath("core/Transition_Engine.py"): 548,
    }

    PRODUCTION_DIRS = ["core", "hardware", "modes", "config", "connectors"]
    PRODUCTION_ROOT_FILES = ["Main.py"]

    def test_file_line_counts_and_ratchet(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        violations = []

        # Check root production files
        for root_file in self.PRODUCTION_ROOT_FILES:
            full_path = os.path.join(repo_root, root_file)
            if not os.path.isfile(full_path):
                continue
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                line_count = len(f.readlines())
            if line_count > 500:
                violations.append(
                    f"Production file {root_file} exceeds 500-line cap: "
                    f"{line_count} > 500 lines"
                )

        for prod_dir in self.PRODUCTION_DIRS:
            dir_path = os.path.join(repo_root, prod_dir)
            if not os.path.isdir(dir_path):
                continue

            for root, _, files in os.walk(dir_path):
                for file_name in files:
                    if not file_name.endswith(".py"):
                        continue

                    full_path = os.path.join(root, file_name)
                    rel_path = os.path.normpath(os.path.relpath(full_path, repo_root))

                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        line_count = len(f.readlines())

                    if rel_path in self.GRANDFATHERED_RATCHET:
                        ratchet_limit = self.GRANDFATHERED_RATCHET[rel_path]
                        if line_count > ratchet_limit:
                            violations.append(
                                f"Grandfathered file {rel_path} expanded beyond ratchet limit: "
                                f"{line_count} > {ratchet_limit}"
                            )
                    else:
                        if line_count > 500:
                            violations.append(
                                f"Production file {rel_path} exceeds 500-line cap: "
                                f"{line_count} > 500 lines"
                            )

        self.assertEqual(violations, [], "Line count / ratchet violations found:\n" + "\n".join(violations))


if __name__ == "__main__":
    unittest.main()
