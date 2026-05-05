import os

def update_file_contents(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    new_content = content.replace('from utils ', 'from utils ')
    new_content = new_content.replace('import utils.', 'import utils.')
    new_content = new_content.replace('utils.rgb_hsv', 'utils.rgb_hsv')
    new_content = new_content.replace('utils.colors', 'utils.colors')

    new_content = new_content.replace('from geometry ', 'from geometry ')
    new_content = new_content.replace('import geometry.', 'import geometry.')
    new_content = new_content.replace('geometry.', 'geometry.')

    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated {filepath}")

for root, dirs, files in os.walk('.'):
    if '.git' in root or 'node_modules' in root or '__pycache__' in root:
        continue
    for file in files:
        if file.endswith('.py') or file.endswith('.md'):
            update_file_contents(os.path.join(root, file))

print("Done updating contents for folders.")
