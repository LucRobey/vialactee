"""
benchmarks/ground_truth/import_playground_beats.py - Converts playground NPZ beat caches to frozen .beats.txt.
"""

import os
import numpy as np


def import_playground_results():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    playground_dir = os.path.join(root, "playground", "BeatTracking_Evaluation", "librosa results")
    output_dir = os.path.join(root, "benchmarks", "ground_truth", "natural")
    os.makedirs(output_dir, exist_ok=True)

    if not os.path.exists(playground_dir):
        print(f"Playground dir not found: {playground_dir}")
        return

    count = 0
    for f in os.listdir(playground_dir):
        if not f.endswith(".npz"):
            continue
        npz_path = os.path.join(playground_dir, f)
        data = np.load(npz_path)
        if "beats" not in data:
            continue
        beats = data["beats"]

        # Clean filename: "01-Plastic-People.mp3_librosa_beats.npz" -> "01-Plastic-People.beats.txt"
        base = f.replace(".mp3_librosa_beats.npz", "").replace("_librosa_beats.npz", "")
        txt_name = f"{base}.beats.txt"
        txt_path = os.path.join(output_dir, txt_name)

        with open(txt_path, "w", encoding="utf-8") as out:
            out.write(f"# Frozen Reference Beats for {base}\n")
            out.write(f"# Extracted from playground benchmark archive\n")
            for b in beats:
                out.write(f"{float(b):.4f}\n")
        count += 1
        print(f"Imported {txt_name} ({len(beats)} beats)")

    print(f"\nSuccessfully imported {count} reference beat files into {output_dir}")


if __name__ == "__main__":
    import_playground_results()
