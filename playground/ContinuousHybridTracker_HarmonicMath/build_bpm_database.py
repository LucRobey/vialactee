"""
build_bpm_database.py
─────────────────────
1. Loads any already-known BPMs from bpm_database.json
2. For every .mp3 in the library that is NOT yet in the database,
   uses librosa to estimate the BPM (fast, no full load needed)
3. Saves everything back to bpm_database.json

Run this once, then manually correct wrong values in the JSON.
The notebook will read from that file automatically.
"""

import os
import json
import librosa
import numpy as np

MP3_DIR  = '../../assets/musics/mp3_files'
DB_PATH  = os.path.join(MP3_DIR, 'bpm_database.json')

# ── 1. Seed with manually verified BPMs from the notebook ────────────────────
VERIFIED = {
    'Palladium':                                                    172.2,
    'Pumped Up Kicks':                                              128.0,
    'Nobody Rules the Streets':                                     128.0,
    'Another One Bites The Dust - Remastered 2011':                110.0,
    "Stayin' Alive - From _Saturday Night Fever_ Soundtrack":       104.0,
    'Boogie Wonderland':                                            132.0,
    'Roxanne - Remastered 2003':                                    134.0,
    'September':                                                    125.0,
}

# ── 2. Load existing database (if any) ───────────────────────────────────────
if os.path.exists(DB_PATH):
    with open(DB_PATH, 'r', encoding='utf-8') as f:
        db = json.load(f)
    print(f"Loaded existing database: {len(db)} entries")
else:
    db = {}
    print("No existing database found — starting fresh")

# Merge verified values (verified always win)
for name, bpm in VERIFIED.items():
    db[name] = {'bpm': bpm, 'source': 'verified'}

# ── 3. Auto-estimate BPM for every unknown MP3 ───────────────────────────────
mp3_files = sorted(
    f for f in os.listdir(MP3_DIR)
    if f.lower().endswith('.mp3')
)

print(f"\nFound {len(mp3_files)} MP3 files in library.")
print("Estimating BPM for unknown songs (this will take a few minutes)...\n")

for mp3_file in mp3_files:
    name = mp3_file[:-4]  # strip .mp3

    if name in db:
        src = db[name].get('source', 'unknown')
        print(f"  SKIP  {name[:55]:55s}  {db[name]['bpm']:.1f} BPM  [{src}]")
        continue

    full_path = os.path.join(MP3_DIR, mp3_file)
    try:
        # Load only first 60 seconds for speed
        y, sr = librosa.load(full_path, sr=22050, duration=60.0)
        # onset_envelope-based beat tracking (faster than default)
        onset_env = librosa.onset.onset_strength(y=y, sr=sr, aggregate=np.median)
        tempo, _ = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
        bpm_val = float(np.round(tempo, 1))

        db[name] = {'bpm': bpm_val, 'source': 'librosa_estimate'}
        print(f"  AUTO  {name[:55]:55s}  {bpm_val:.1f} BPM  [librosa_estimate]")

    except Exception as e:
        print(f"  ERR   {name[:55]:55s}  ERROR: {e}")
        db[name] = {'bpm': None, 'source': 'error'}

# ── 4. Save ───────────────────────────────────────────────────────────────────
# Sort alphabetically for readability
db_sorted = dict(sorted(db.items(), key=lambda x: x[0].lower()))

with open(DB_PATH, 'w', encoding='utf-8') as f:
    json.dump(db_sorted, f, indent=2, ensure_ascii=False)

print(f"\nSaved {len(db_sorted)} entries to: {DB_PATH}")
print("\nVerified entries:")
for name, entry in db_sorted.items():
    if entry.get('source') == 'verified':
        print(f"  {name[:55]:55s}  {entry['bpm']} BPM")
