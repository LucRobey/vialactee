import json

def modify():
    with open('ContinuousHybridTracker.ipynb', 'r', encoding='utf-8') as f:
        nb = json.load(f)
        
    for cell in nb.get('cells', []):
        if cell.get('cell_type') != 'code':
            continue
            
        source = "".join(cell['source'])
        
        if "plt.show()" in source and "Rhythm Tracking Over Full Audio Duration" in source:
            source = source.replace("plt.show()", "plt.savefig('traking_plot.png')\nplt.show()")
            
            lines = []
            parts = source.split('\n')
            for i, part in enumerate(parts):
                if i < len(parts) - 1:
                    lines.append(part + '\n')
                else:
                    if part:
                        lines.append(part)
            cell['source'] = lines

    with open('ContinuousHybridTracker.ipynb', 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1)

if __name__ == '__main__':
    modify()
    print("Notebook modified successfully.")
