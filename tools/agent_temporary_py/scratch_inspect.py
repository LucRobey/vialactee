import json

with open("MusicAnalyzer.ipynb", "r", encoding="utf-8") as f:
    nb = json.load(f)

for i, cell in enumerate(nb["cells"]):
    if cell["cell_type"] == "code":
        source = "".join(cell["source"])
        print(f"--- CELL {i} ---")
        print(source[:200] + "...")
