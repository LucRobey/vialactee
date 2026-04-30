import json
import sys

with open(sys.argv[1], 'r', encoding='utf-8') as f:
    nb = json.load(f)

for cell in nb['cells']:
    if cell['cell_type'] == 'code':
        source = "".join(cell['source'])
        
        target_str = '''# template_vals[((abs_phi >= 0.22) & (abs_phi <= 0.28))] = 0.3 # Sub-sub-beats ignored!'''
        replacement_str = '''template_vals[((abs_phi >= 0.22) & (abs_phi <= 0.28))] = 0.0 # Sub-sub-beats get neutral weight (0.0)'''
        
        if target_str in source:
            source = source.replace(target_str, replacement_str)
            
        lines = [line + '\n' for line in source.split('\n')]
        if len(lines) > 0:
            lines[-1] = lines[-1][:-1]
        cell['source'] = lines

with open(sys.argv[1], 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1)
