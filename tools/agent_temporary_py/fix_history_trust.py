import json

def fix_history_trust():
    with open('ContinuousHybridTracker.ipynb', 'r', encoding='utf-8') as f:
        nb = json.load(f)

    for cell in nb['cells']:
        if cell['cell_type'] == 'code':
            source = "".join(cell['source'])

            old_str = "history_treble.append(present.get('treble_flux', 0.0))"
            new_str = "history_treble.append(present.get('treble_flux', 0.0))\n        history_trust.append(ltm_trust)"
            
            if old_str in source:
                source = source.replace(old_str, new_str)
            
            if "\n" in source:
                lines = source.split('\n')
                cell['source'] = [line + '\n' for line in lines[:-1]] + [lines[-1]] if lines else []
            else:
                cell['source'] = [source]

    with open('ContinuousHybridTracker.ipynb', 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1)

if __name__ == '__main__':
    fix_history_trust()
    print("Fixed history_trust append logic in the notebook.")
