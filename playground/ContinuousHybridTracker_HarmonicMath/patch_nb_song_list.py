import json

nb_path = 'ContinuousHybridTracker_HarmonicMath.ipynb'
with open(nb_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

new_song_list_source = [
    "import librosa\n",
    "import numpy as np\n",
    "import os\n",
    "import json\n",
    "\n",
    "root        = '../../assets/musics/mp3_files/'\n",
    "DB_PATH     = os.path.join(root, 'bpm_database.json')\n",
    "\n",
    "# Load the BPM database\n",
    "with open(DB_PATH, 'r', encoding='utf-8') as _f:\n",
    "    _bpm_db = json.load(_f)\n",
    "\n",
    "# Select songs to test — edit this list freely.\n",
    "# Only names that exist in bpm_database.json will work.\n",
    "TEST_SONGS = [\n",
    "    'Palladium',\n",
    "    'Pumped Up Kicks',\n",
    "    'Nobody Rules the Streets',\n",
    "    'Another One Bites The Dust - Remastered 2011',\n",
    "    \"Stayin' Alive - From _Saturday Night Fever_ Soundtrack\",\n",
    "    'Boogie Wonderland',\n",
    "    'Roxanne - Remastered 2003',\n",
    "    'September',\n",
    "]\n",
    "\n",
    "SONGS      = [(name, _bpm_db[name]['bpm']) for name in TEST_SONGS if name in _bpm_db]\n",
    "song_files = [root + name + '.mp3' for name, _ in SONGS]\n",
    "real_bpms  = [bpm for _, bpm in SONGS]\n",
    "song_names = [name for name, _ in SONGS]\n",
    "\n",
    "librosa_dir = os.path.join(root, 'librosa')\n",
    "os.makedirs(librosa_dir, exist_ok=True)\n",
    "\n",
    "y_list = []\n",
    "for f in song_files:\n",
    "    basename  = os.path.basename(f)\n",
    "    save_path = os.path.join(librosa_dir, f'{basename}.npz')\n",
    "    if os.path.exists(save_path):\n",
    "        data = np.load(save_path, allow_pickle=True)\n",
    "        y = data['y']\n",
    "    else:\n",
    "        y, _ = librosa.load(f, sr=44100)\n",
    "        np.savez(save_path, y=y, sr=44100)\n",
    "    y_list.append(y)\n",
    "\n",
    "print(f'BPM database: {len(_bpm_db)} songs total')\n",
    "print(f'Testing {len(y_list)} songs:')\n",
    "for i, (name, bpm) in enumerate(SONGS):\n",
    "    src = _bpm_db[name].get('source', '?')\n",
    "    dur = len(y_list[i]) / 44100.0\n",
    "    print(f'  [{i+1}] {name[:50]:50s}  {dur:.1f}s  {bpm} BPM  [{src}]')\n",
]

patched = False
for cell in nb['cells']:
    if cell['cell_type'] == 'code':
        src = "".join(cell['source'])
        if "'Palladium'" in src and 'SONGS' in src and 'run_simulation' not in src:
            cell['source'] = new_song_list_source
            patched = True
            break

print(f"Song list cell patched: {patched}")

with open(nb_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1)

print("Done!")
