import json

def extract_code():
    with open('ContinuousHybridTracker.ipynb', 'r', encoding='utf-8') as f:
        nb = json.load(f)
        
    with open('run_sim.py', 'w', encoding='utf-8') as f:
        for cell in nb.get('cells', []):
            if cell.get('cell_type') == 'code':
                source = "".join(cell['source'])
                
                # filter out magics if any
                lines = []
                for line in source.split('\n'):
                    if not line.startswith('%'):
                        lines.append(line)
                
                f.write('\n'.join(lines))
                f.write('\n\n')

if __name__ == '__main__':
    extract_code()
    print("Extraction done.")
