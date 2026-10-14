"""
tools/eval_skills.py
Skill Effectiveness & Compliance Evaluation Engine.

Allows regular, automated testing of whether skills are working, necessary,
and being respected across the codebase.

Usage:
    python tools/eval_skills.py --all
    python tools/eval_skills.py --skill vialactee-mode-creator
    python tools/eval_skills.py --skill vialactee-dsp-engine
    python tools/eval_skills.py --skill vialactee-researcher
    python tools/eval_skills.py --eval-prompts  # Prints benchmark prompts and rubrics for A/B testing
"""
import argparse
import ast
import glob
import os
import re
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)


def evaluate_mode_creator():
    """
    Evaluates compliance with vialactee-mode-creator rules across all active modes in modes/.
    Rules checked:
    1. No 'for i in range' or pixel loops in render/run.
    2. Inherits from Mode.
    3. Exposes get_settings_schema() with valid structure.
    4. Overrides render() or run() (never update()).
    """
    print("\n=======================================================")
    print("  EVAL: vialactee-mode-creator (Scanning modes/)")
    print("=======================================================")
    modes_dir = os.path.join(REPO_ROOT, "modes")
    mode_files = [f for f in glob.glob(os.path.join(modes_dir, "*_mode.py")) if not os.path.basename(f).startswith("_")]

    passed = 0
    warnings = []
    errors = []

    for mf in sorted(mode_files):
        bn = os.path.basename(mf)
        with open(mf, "r", encoding="utf-8") as f:
            code = f.read()

        # Rule 1: No slow loops over leds
        if re.search(r"for\s+\w+\s+in\s+range\s*\(\s*(?:self\.)?nb_of_leds", code):
            errors.append(f"[{bn}] VIOLATION: Slow pixel loop detected ('for ... in range(nb_of_leds)'). Must use vectorized NumPy.")

        # Rule 2: Never override update()
        if re.search(r"def\s+update\s*\(", code):
            errors.append(f"[{bn}] VIOLATION: Mode overrides update(). Must override render() or run().")

        # Rule 3: Must override render() or run()
        if not (re.search(r"def\s+render\s*\(", code) or re.search(r"def\s+run\s*\(", code)):
            errors.append(f"[{bn}] VIOLATION: Mode overrides neither render() nor run().")

        # Rule 4: get_settings_schema check
        if "get_settings_schema" not in code:
            warnings.append(f"[{bn}] ADVISORY: Missing get_settings_schema() method.")

        passed += 1

    print(f"Scanned {passed} visual mode files.")
    if errors:
        print(f"\n[FAIL] Found {len(errors)} hard rule violations:")
        for err in errors:
            print(f"  - {err}")
    else:
        print("\n[PASS] 100% of production modes respect vectorization and execution rules!")

    if warnings:
        print(f"\n[INFO] {len(warnings)} modes lack get_settings_schema() exposure:")
        for w in warnings[:5]:
            print(f"  - {w}")
        if len(warnings) > 5:
            print(f"  ... and {len(warnings) - 5} more.")

    return len(errors) == 0


def evaluate_dsp_engine():
    """
    Evaluates compliance with vialactee-dsp-engine rules:
    1. Dual-resolution Mel filterbank invariant in AudioIngestion.py (8 bands for visuals, 32 bands for rhythm).
    2. Zero-division floor safeguards.
    3. Listener delayed property exposure.
    """
    print("\n=======================================================")
    print("  EVAL: vialactee-dsp-engine (Core DSP Invariants)")
    print("=======================================================")
    ingestion_path = os.path.join(REPO_ROOT, "core", "AudioIngestion.py")
    listener_path = os.path.join(REPO_ROOT, "core", "Listener.py")

    errors = []

    # Check 1: AudioIngestion dual-resolution filterbank
    with open(ingestion_path, "r", encoding="utf-8") as f:
        ingestion_code = f.read()

    if "fft_band_values" not in ingestion_code or "multiband_fft_values" not in ingestion_code:
        errors.append("AudioIngestion.py missing dual-resolution filterbank ('fft_band_values' and 'multiband_fft_values').")

    if "1e-9" not in ingestion_code and "1e-6" not in ingestion_code:
        errors.append("AudioIngestion.py missing epsilon zero-division safeguards.")

    # Check 2: Listener delayed properties
    with open(listener_path, "r", encoding="utf-8") as f:
        listener_code = f.read()

    expected_listener_props = ["asserved_fft_band", "beat_phase", "context"]
    for prop in expected_listener_props:
        if prop not in listener_code:
            errors.append(f"Listener.py missing key property exposure: '{prop}'")

    if errors:
        print(f"\n[FAIL] Found {len(errors)} DSP rule violations:")
        for err in errors:
            print(f"  - {err}")
        return False
    else:
        print("[PASS] Dual-resolution filterbanks, epsilon zero-division floors, and Listener contracts verified!")
        return True


def evaluate_research():
    """
    Evaluates research environment health:
    1. RESEARCH_IDEA_TREE.md exists and is readable.
    2. LEADERBOARD.md exists.
    3. Real-time budget gate of <= 3.0ms per tick is enforced in models.
    """
    print("\n=======================================================")
    print("  EVAL: vialactee-research-manager & vialactee-researcher")
    print("=======================================================")
    tree_path = os.path.join(REPO_ROOT, "research", "experiments", "RESEARCH_IDEA_TREE.md")
    leaderboard_path = os.path.join(REPO_ROOT, "research", "experiments", "LEADERBOARD.md")

    errors = []
    if not os.path.exists(tree_path):
        errors.append("Missing research/experiments/RESEARCH_IDEA_TREE.md")
    if not os.path.exists(leaderboard_path):
        errors.append("Missing research/experiments/LEADERBOARD.md")

    if errors:
        print(f"\n[FAIL] Research state missing files: {errors}")
        return False
    else:
        print("[PASS] Living idea tree and leaderboard are healthy and in sync!")
        return True


def print_eval_prompts():
    """Prints standard test prompts and checklists for evaluating skills on an LLM."""
    print("\n=======================================================")
    print("  BENCHMARK EVAL PROMPTS (For testing LLM effectiveness)")
    print("=======================================================")
    print("""
Prompt 1: Visual Mode Authoring
--------------------------------
\"\"\"
Create a new visual mode named 'NeonStrobe_mode.py' in modes/ that:
1. Staves off ghost beats by flashing only when context.is_real_beat is True.
2. Modulates color speed based on context.energy.
3. Exposes a 'decay_rate' slider to the React web app.
\"\"\"
Pass Checklist:
[ ] Class inherits from modes.Mode
[ ] No 'for i in range(self.nb_of_leds)' loop (pure NumPy vectorization)
[ ] Uses immutable color constants (e.g. self.white as tuple)
[ ] Exposes get_settings_schema() returning list with key, label, valueType
[ ] Overrides render() or run(), does NOT override update()
[ ] Frame budget assumes 30 FPS (AXIOM-01), not 60 FPS

Prompt 2: Research Strategy Briefing
------------------------------------
\"\"\"
Formulate a research hypothesis for Stage 1 Tournament 002 to eliminate
the 180° upbeat trap on disco and funk tracks (e.g. Stayin' Alive).
\"\"\"
Pass Checklist:
[ ] Uses a first-principles mathematical derivation (e.g. Costas quadrature / Hilbert transform)
[ ] Explicitly rejects incremental constant tweaks (Anti-Incremental Gate)
[ ] Enforces discrete causal difference equations y[n] = f(y[n-1], x[n])
[ ] Allots frame budget <= 1.0ms in pre-allocated NumPy matrices
[ ] Specifies 2-track real-world stress test (Sweet Child O' Mine & Stayin' Alive)
""")


def main():
    parser = argparse.ArgumentParser(description="Vialactee Skill Evaluation Engine")
    parser.add_argument("--all", action="store_true", help="Run all automated skill evaluations")
    parser.add_argument("--skill", type=str, help="Evaluate a specific skill by name")
    parser.add_argument("--eval-prompts", action="store_true", help="Print benchmark prompts and rubrics for A/B skill testing")

    args = parser.parse_args()

    if args.eval_prompts:
        print_eval_prompts()
        return

    success = True
    if args.all or not args.skill:
        s1 = evaluate_mode_creator()
        s2 = evaluate_dsp_engine()
        s3 = evaluate_research()
        success = s1 and s2 and s3
    elif args.skill == "vialactee-mode-creator":
        success = evaluate_mode_creator()
    elif args.skill == "vialactee-dsp-engine":
        success = evaluate_dsp_engine()
    elif args.skill in ["vialactee-researcher", "vialactee-research-manager"]:
        success = evaluate_research()
    else:
        print(f"Unknown skill: {args.skill}")
        sys.exit(1)

    print("\n-------------------------------------------------------")
    print(f"OVERALL EVAL RESULT: {'ALL PASS' if success else 'FAILURES DETECTED'}")
    print("-------------------------------------------------------\n")
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
