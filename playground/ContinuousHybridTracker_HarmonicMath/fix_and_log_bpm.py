import json

nb_path = 'ContinuousHybridTracker_HarmonicMath.ipynb'
with open(nb_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# ── 1. Fix Palladium BPM: 145 → 172.2 ───────────────────────────────────────
fixed = False
for cell in nb['cells']:
    if cell['cell_type'] != 'code':
        continue
    src = "".join(cell['source'])
    if "'Palladium'" in src and 'SONGS' in src:
        new_source = []
        for line in cell['source']:
            if "'Palladium'" in line and ('145' in line or '172' in line):
                line = "    ('Palladium',                                     172.2),\n"
                fixed = True
            new_source.append(line)
        cell['source'] = new_source
        break

print(f"Palladium BPM fixed: {fixed}")

# ── 2. Remove any existing log-BPM cells so we don't duplicate ───────────────
nb['cells'] = [
    c for c in nb['cells']
    if not ('log_bpm_curves' in "".join(c.get('source', [])) or
            'Log BPM Class' in "".join(c.get('source', [])))
]

# ── 3. Append new log-BPM class plot cell ────────────────────────────────────
log_bpm_cell_source = [
    "import matplotlib.pyplot as plt\n",
    "import numpy as np\n",
    "\n",
    "# BPM → class helper (needed here in case kernel was partially run)\n",
    "def _bpm_to_class(bpm):\n",
    "    return np.log2(float(bpm) / 60.0) % 1.0\n",
    "\n",
    "def _circular_dist(a, b):\n",
    "    d = np.abs(np.asarray(a, float) - float(b))\n",
    "    return np.minimum(d, 1.0 - d)\n",
    "\n",
    "n_songs = len(results)\n",
    "ncols = 2\n",
    "nrows = (n_songs + 1) // ncols\n",
    "\n",
    "fig, axes = plt.subplots(nrows, ncols, figsize=(16, nrows * 4))\n",
    "fig.patch.set_facecolor('#0d0d0d')\n",
    "axes = axes.flatten()\n",
    "\n",
    "for idx, res in enumerate(results):\n",
    "    ax = axes[idx]\n",
    "    ax.set_facecolor('#1a1a1a')\n",
    "    ax.tick_params(colors='white')\n",
    "    ax.xaxis.label.set_color('white')\n",
    "    ax.yaxis.label.set_color('white')\n",
    "    ax.title.set_color('white')\n",
    "    for sp in ax.spines.values(): sp.set_edgecolor('#444')\n",
    "\n",
    "    t           = np.array(res['h_time'])\n",
    "    ltm_class   = np.array(res['h_ltm_class'])     # Flywheel (smoothed)\n",
    "    scout_class = np.array(res['h_class'])          # Raw Fast Scout class\n",
    "    target      = res['target_bpm']\n",
    "    name        = res['name']\n",
    "\n",
    "    # Target class — and its harmonic aliases\n",
    "    tc      = _bpm_to_class(target)\n",
    "    tc_half = _bpm_to_class(target * 0.5)\n",
    "    tc_dbl  = _bpm_to_class(target * 2.0)\n",
    "\n",
    "    ax.scatter(t, scout_class, s=2, color='#555555', alpha=0.4, label='Fast Scout class')\n",
    "    ax.plot(t, ltm_class, color='#69f0ae', linewidth=2.0, label='Flywheel LTM class')\n",
    "\n",
    "    # Target class lines\n",
    "    ax.axhline(tc,      color='#ffeb3b', linestyle='--', linewidth=1.5,\n",
    "               label=f'Target class {tc:.3f}  ({target:.1f} BPM)')\n",
    "    ax.axhline(tc_half, color='#ff8f00', linestyle=':',  linewidth=1.0, alpha=0.7,\n",
    "               label=f'x0.5 class  {tc_half:.3f}  ({target*0.5:.1f} BPM)')\n",
    "    ax.axhline(tc_dbl,  color='#ff8f00', linestyle=':',  linewidth=1.0, alpha=0.7,\n",
    "               label=f'x2   class  {tc_dbl:.3f}  ({target*2.0:.1f} BPM)')\n",
    "\n",
    "    # Compute median class error (harmonic-aware)\n",
    "    mid = len(ltm_class) // 2\n",
    "    late_ltm = ltm_class[mid:]\n",
    "    class_err = np.minimum(\n",
    "        _circular_dist(late_ltm, tc),\n",
    "        np.minimum(\n",
    "            _circular_dist(late_ltm, tc_half),\n",
    "            _circular_dist(late_ltm, tc_dbl)\n",
    "        )\n",
    "    )\n",
    "    med_class_err = float(np.median(class_err))\n",
    "    err_color = '#69f0ae' if med_class_err < 0.05 else '#ffa726' if med_class_err < 0.15 else '#ef5350'\n",
    "\n",
    "    ax.set_title(\n",
    "        f'{name[:42]}\\n'\n",
    "        f'Target class={tc:.3f}  |  Median class err={med_class_err:.4f}',\n",
    "        fontsize=9, fontweight='bold', color=err_color\n",
    "    )\n",
    "    ax.set_xlabel('Time (s)')\n",
    "    ax.set_ylabel('BPM Class  [0, 1)')\n",
    "    ax.set_ylim(-0.02, 1.02)\n",
    "    ax.grid(True, alpha=0.12)\n",
    "    ax.legend(fontsize=7, facecolor='#222', labelcolor='white', loc='lower right')\n",
    "\n",
    "for idx in range(n_songs, len(axes)):\n",
    "    axes[idx].set_visible(False)\n",
    "\n",
    "fig.suptitle(\n",
    "    'Log BPM Class Tracking  (circular [0, 1) space)\\n'\n",
    "    'Yellow = target class | Orange dotted = harmonic aliases',\n",
    "    fontsize=13, fontweight='bold', color='white', y=1.01\n",
    ")\n",
    "plt.tight_layout(pad=2.0)\n",
    "plt.savefig('log_bpm_class_curves.png', dpi=110, facecolor='#0d0d0d', bbox_inches='tight')\n",
    "plt.show()\n",
    "print('Saved: log_bpm_class_curves.png')\n",
]

nb['cells'].append({
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": log_bpm_cell_source
})

with open(nb_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1)

print("Done! Palladium fixed to 172.2 BPM + log-BPM class cell appended.")
