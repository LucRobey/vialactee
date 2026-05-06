import json

with open('ContinuousHybridTracker.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

for cell in nb['cells']:
    if cell['cell_type'] == 'code':
        source = "".join(cell['source'])
        
        # We look for the exact string to replace
        old_cooldown = "STRUCTURAL_COOLDOWN_FRAMES = int(5.0 * SIMULATED_FPS)"
        new_cooldown = "STRUCTURAL_COOLDOWN_FRAMES = int(20.0 * SIMULATED_FPS)"
        
        if old_cooldown in source:
            source = source.replace(old_cooldown, new_cooldown)
            
            # Reconstruct notebook cell format
            if "\n" in source:
                lines = source.split('\n')
                cell['source'] = [line + '\n' for line in lines[:-1]] + [lines[-1]] if lines else []
            else:
                cell['source'] = [source]

with open('ContinuousHybridTracker.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1)

print("Updated verse/chorus cooldown to 20 seconds.")
