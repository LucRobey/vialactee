import json
import re
import sys

def parse_nb():
    with open('BeatTracking_Evaluation_Test.ipynb', encoding='utf-8') as f:
        nb = json.load(f)
    
    with open('metrics_output.txt', 'w', encoding='utf-8') as out:
        for c in nb.get('cells', []):
            if 'outputs' in c:
                for o in c['outputs']:
                    if o.get('output_type') == 'stream':
                        text = ''.join(o.get('text', []))
                        out.write(text)

if __name__ == "__main__":
    parse_nb()
