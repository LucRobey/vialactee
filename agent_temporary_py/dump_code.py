import json

with open("ContinuousHybridTracker.ipynb", "r", encoding="utf-8") as f:
    nb = json.load(f)

with open("temp_code.py", "w", encoding="utf-8") as f:
    for c in nb["cells"]:
        if c["cell_type"] == "code":
            f.write("".join(c["source"]))
            f.write("\n\n")
