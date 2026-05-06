import ast
import os
import sys
import pkgutil

def get_imports(path):
    imports = set()
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith('.py'):
                try:
                    with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                        tree = ast.parse(f.read())
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for n in node.names:
                                imports.add(n.name.split('.')[0])
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                imports.add(node.module.split('.')[0])
                except Exception:
                    pass
    return imports

stdlib = {m.name for m in pkgutil.iter_modules() if m.ispkg == False}
stdlib.update(sys.builtin_module_names)
stdlib.update(['os', 'sys', 'math', 'time', 'json', 'random', 'asyncio', 'logging', 'datetime', 'threading', 'colorsys', 'socket', 'csv', 'struct', 'typing', 'urllib', 'traceback'])

imports = get_imports('.')
internal = ['core', 'connectors', 'modes', 'hardware', 'Mode_Globaux', 'config', 'data', 'calculations', 'old_system', 'test zone', 'BTrack', 'Python-BTrack', 'patch_silero']
external = [m for m in imports if m not in stdlib and m not in internal]
print(external)
