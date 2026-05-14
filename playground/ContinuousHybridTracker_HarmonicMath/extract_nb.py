import json
import traceback

try:
    with open('ContinuousHybridTracker_HarmonicMath.ipynb', 'r', encoding='utf-8') as f:
        nb = json.load(f)
    
    # We will assemble all code cells into one big script and execute it
    code_lines = []
    for cell in nb['cells']:
        if cell['cell_type'] == 'code':
            for line in cell['source']:
                # Skip plotting and %matplotlib to prevent GUI blocking
                if line.startswith('%matplotlib') or 'matplotlib' in line or 'plt.' in line:
                    continue
                code_lines.append(line)
                
    full_script = "".join(code_lines)
    
    with open('temp_run.py', 'w', encoding='utf-8') as f:
        f.write(full_script)
        
except Exception as e:
    print(f"Error parsing notebook: {e}")
