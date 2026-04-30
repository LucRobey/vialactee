import sys
import json
import matplotlib

# Force UTF-8 for print statements in Windows Console
sys.stdout.reconfigure(encoding='utf-8')
# Force headless rendering so plt.show() doesn't hang!
matplotlib.use('Agg')

with open('ContinuousHybridTracker.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

full_code = ""
for cell in nb['cells']:
    if cell['cell_type'] == 'code':
        for line in cell['source']:
            if "clear_output" in line or "display" in line:
               continue
            full_code += line
            if not line.endswith('\n'):
                full_code += '\n'

# Execute it
try:
    exec(full_code)
except Exception as e:
    import traceback
    print(f"Error executing: {e}")
    traceback.print_exc()
