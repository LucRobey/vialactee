import json

nb_path = 'ContinuousHybridTracker_HarmonicMath.ipynb'
with open(nb_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# ── 1. New song list cell source ─────────────────────────────────────────────
new_song_list_source = [
    "import librosa\n",
    "import numpy as np\n",
    "import os\n",
    "\n",
    "root = '../../assets/musics/mp3_files/'\n",
    "\n",
    "# (song_file, real_bpm)\n",
    "SONGS = [\n",
    "    ('Palladium',                                     145),\n",
    "    ('Pumped Up Kicks',                               128),\n",
    "    ('Nobody Rules the Streets',                     128),\n",
    "    ('Another One Bites The Dust - Remastered 2011', 110),\n",
    "    (\"Stayin' Alive - From _Saturday Night Fever_ Soundtrack\", 104),\n",
    "    ('Boogie Wonderland',                             132),\n",
    "    ('Roxanne - Remastered 2003',                     134),\n",
    "    ('September',                                     125),\n",
    "]\n",
    "\n",
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
    "print(f'Loaded {len(y_list)} songs.')\n",
    "for i, (name, bpm) in enumerate(SONGS):\n",
    "    dur = len(y_list[i]) / 44100.0\n",
    "    print(f'  [{i+1}] {name:55s}  {dur:.1f}s  target={bpm} BPM')\n",
]

# ── 2. New per-song runner + ratio-plot cell ──────────────────────────────────
new_plot_cell_source = [
    "import time as _time_module\n",
    "import matplotlib.pyplot as plt\n",
    "\n",
    "# Run each song INDEPENDENTLY and collect per-song metrics\n",
    "results = []  # list of dicts\n",
    "\n",
    "for song_idx, (y, target_bpm, sname) in enumerate(zip(y_list, real_bpms, song_names)):\n",
    "    song_duration = len(y) / 44100.0\n",
    "    t_wall_start  = _time_module.perf_counter()\n",
    "\n",
    "    h_time, h_raw_bpm, h_pearson, h_class, h_ltm_class = run_simulation([y])\n",
    "\n",
    "    t_wall_end   = _time_module.perf_counter()\n",
    "    compile_time = t_wall_end - t_wall_start\n",
    "    ratio        = compile_time / song_duration\n",
    "\n",
    "    # Accuracy: median of last 50% of heavy-judge BPM vs target\n",
    "    mid = len(h_pearson) // 2\n",
    "    median_bpm = float(np.median(h_pearson[mid:]))\n",
    "    error_pct  = abs(median_bpm - target_bpm) / target_bpm * 100.0\n",
    "\n",
    "    results.append({\n",
    "        'name':          sname,\n",
    "        'target_bpm':    target_bpm,\n",
    "        'song_duration': song_duration,\n",
    "        'compile_time':  compile_time,\n",
    "        'ratio':         ratio,\n",
    "        'median_bpm':    median_bpm,\n",
    "        'error_pct':     error_pct,\n",
    "        'h_time':        h_time,\n",
    "        'h_pearson':     h_pearson,\n",
    "        'h_raw_bpm':     h_raw_bpm,\n",
    "        'h_ltm_class':   h_ltm_class,\n",
    "    })\n",
    "    print(f'[{song_idx+1}/{len(y_list)}] {sname[:45]:45s}  '\n",
    "          f'dur={song_duration:.1f}s  '\n",
    "          f'compile={compile_time:.1f}s  '\n",
    "          f'ratio={ratio:.3f}  '\n",
    "          f'median={median_bpm:.1f} BPM  '\n",
    "          f'err={error_pct:.1f}%')\n",
    "\n",
    "# ── PLOT 1: Song duration & compile time (bar chart) ──────────────────────\n",
    "labels        = [r['name'][:28] for r in results]\n",
    "durations     = [r['song_duration']  for r in results]\n",
    "compile_times = [r['compile_time']   for r in results]\n",
    "ratios        = [r['ratio']          for r in results]\n",
    "errors        = [r['error_pct']      for r in results]\n",
    "\n",
    "fig, axes = plt.subplots(3, 1, figsize=(14, 14))\n",
    "fig.patch.set_facecolor('#0d0d0d')\n",
    "for ax in axes:\n",
    "    ax.set_facecolor('#1a1a1a')\n",
    "    ax.tick_params(colors='white')\n",
    "    ax.xaxis.label.set_color('white')\n",
    "    ax.yaxis.label.set_color('white')\n",
    "    ax.title.set_color('white')\n",
    "    for spine in ax.spines.values():\n",
    "        spine.set_edgecolor('#444')\n",
    "\n",
    "x = range(len(results))\n",
    "\n",
    "# -- Bar: durations vs compile time --\n",
    "ax = axes[0]\n",
    "width = 0.35\n",
    "bars1 = ax.bar([i - width/2 for i in x], durations,     width, label='Song Duration (s)',  color='#4fc3f7', alpha=0.85)\n",
    "bars2 = ax.bar([i + width/2 for i in x], compile_times, width, label='Compile Time (s)',   color='#ef5350', alpha=0.85)\n",
    "ax.set_xticks(list(x))\n",
    "ax.set_xticklabels(labels, rotation=25, ha='right', fontsize=9, color='white')\n",
    "ax.set_ylabel('Seconds', color='white')\n",
    "ax.set_title('Song Duration vs Compile Time per Song', fontsize=12, fontweight='bold')\n",
    "ax.legend(facecolor='#222', labelcolor='white')\n",
    "ax.grid(axis='y', alpha=0.2)\n",
    "for bar in bars1: ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.5, f'{bar.get_height():.0f}s', ha='center', va='bottom', color='#4fc3f7', fontsize=8)\n",
    "for bar in bars2: ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.5, f'{bar.get_height():.1f}s', ha='center', va='bottom', color='#ef5350', fontsize=8)\n",
    "\n",
    "# -- Bar: compile_time / song_duration ratio --\n",
    "ax = axes[1]\n",
    "bar_colors = ['#66bb6a' if r < 0.5 else '#ffa726' if r < 1.0 else '#ef5350' for r in ratios]\n",
    "bars = ax.bar(x, ratios, color=bar_colors, alpha=0.9)\n",
    "ax.axhline(1.0, color='white', linestyle='--', linewidth=1.2, label='Real-time limit (ratio=1.0)')\n",
    "ax.axhline(0.5, color='#66bb6a', linestyle=':', linewidth=1.0, label='50% real-time (Raspberry Pi target)')\n",
    "ax.set_xticks(list(x))\n",
    "ax.set_xticklabels(labels, rotation=25, ha='right', fontsize=9, color='white')\n",
    "ax.set_ylabel('Compile Time / Song Duration', color='white')\n",
    "ax.set_title('Processing Ratio  (< 1.0 = faster than real-time)', fontsize=12, fontweight='bold')\n",
    "ax.legend(facecolor='#222', labelcolor='white')\n",
    "ax.grid(axis='y', alpha=0.2)\n",
    "for bar, r in zip(bars, ratios): ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.01, f'{r:.3f}', ha='center', va='bottom', color='white', fontsize=9, fontweight='bold')\n",
    "\n",
    "# -- Bar: accuracy error % per song --\n",
    "ax = axes[2]\n",
    "err_colors = ['#66bb6a' if e < 5 else '#ffa726' if e < 15 else '#ef5350' for e in errors]\n",
    "bars = ax.bar(x, errors, color=err_colors, alpha=0.9)\n",
    "ax.axhline(5.0,  color='#66bb6a', linestyle=':', linewidth=1.0, label='5% error threshold')\n",
    "ax.axhline(15.0, color='#ffa726', linestyle=':', linewidth=1.0, label='15% error threshold')\n",
    "ax.set_xticks(list(x))\n",
    "ax.set_xticklabels(labels, rotation=25, ha='right', fontsize=9, color='white')\n",
    "ax.set_ylabel('Median BPM Error (%)', color='white')\n",
    "ax.set_title('Tracking Accuracy  (median Heavy Judge BPM vs target)', fontsize=12, fontweight='bold')\n",
    "ax.legend(facecolor='#222', labelcolor='white')\n",
    "ax.grid(axis='y', alpha=0.2)\n",
    "for bar, res in zip(bars, results):\n",
    "    ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.3,\n",
    "            f'{res[\"median_bpm\"]:.0f}\\n({res[\"error_pct\"]:.1f}%)',\n",
    "            ha='center', va='bottom', color='white', fontsize=8)\n",
    "\n",
    "plt.tight_layout(pad=2.0)\n",
    "plt.savefig('multi_song_profiling.png', dpi=120, facecolor='#0d0d0d')\n",
    "plt.show()\n",
    "print('Saved: multi_song_profiling.png')\n",
]

# ── 3. Patch the notebook ─────────────────────────────────────────────────────
song_list_cell_idx = None
run_sim_cell_idx   = None
plot_cell_idx      = None

for i, cell in enumerate(nb['cells']):
    if cell['cell_type'] != 'code':
        continue
    src = "".join(cell['source'])
    if "song_files" in src and "real_bpms" in src and "y_list" in src and "run_simulation" not in src:
        song_list_cell_idx = i
    if "def run_simulation(y_list):" in src:
        run_sim_cell_idx = i
    # The old plotting cell that calls run_simulation and plt.savefig
    if "run_simulation(y_list)" in src and "plt.savefig" in src:
        plot_cell_idx = i

print(f"Found: song_list={song_list_cell_idx}, run_sim={run_sim_cell_idx}, plot={plot_cell_idx}")

# Replace song list cell
if song_list_cell_idx is not None:
    nb['cells'][song_list_cell_idx]['source'] = new_song_list_source
else:
    print("WARNING: song_list cell not found — inserting before run_simulation")
    nb['cells'].insert(run_sim_cell_idx, {
        "cell_type": "code", "execution_count": None,
        "metadata": {}, "outputs": [], "source": new_song_list_source
    })
    run_sim_cell_idx += 1
    if plot_cell_idx is not None:
        plot_cell_idx += 1

# Replace or append the plot cell
if plot_cell_idx is not None:
    nb['cells'][plot_cell_idx]['source'] = new_plot_cell_source
else:
    print("Appending new plot cell at end of notebook")
    nb['cells'].append({
        "cell_type": "code", "execution_count": None,
        "metadata": {}, "outputs": [], "source": new_plot_cell_source
    })

with open(nb_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1)

print("Notebook patched successfully!")
