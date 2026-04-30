import json
import re
import subprocess

with open("ContinuousHybridTracker.ipynb", "r", encoding="utf-8") as f:
    nb = json.load(f)

code_cells = ["import sys\nsys.stdout.reconfigure(encoding='utf-8')\n"]
for c in nb["cells"]:
    if c["cell_type"] == "code":
        source = "".join(c.get("source", []))
        # Strip cell magics
        source = re.sub(r'^\s*%.*$', '', source, flags=re.MULTILINE)
        code_cells.append(source)

full_code = "\n".join(code_cells)

with open("temp_eval.py", "w", encoding="utf-8") as f:
    f.write(full_code)

try:
    result = subprocess.run(["python", "temp_eval.py"], capture_output=True, text=True, encoding='utf-8')
    print("STDOUT:")
    print(result.stdout)
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
except Exception as e:
    print(f"Error: {e}")
