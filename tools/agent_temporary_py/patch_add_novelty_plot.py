import json

def patch_add_novelty_plot():
    with open('ContinuousHybridTracker.ipynb', 'r', encoding='utf-8') as f:
        nb = json.load(f)

    for cell in nb['cells']:
        if cell['cell_type'] == 'code':
            source = "".join(cell['source'])

            # 1. Initialize novel arrays
            init_old = """history_time = []
history_bpm = []
history_bass = []
history_treble = []
history_trust = []"""
            
            init_new = """history_time = []
history_bpm = []
history_bass = []
history_treble = []
history_trust = []
history_stm_power = []
history_ltm_power = []
history_timbral_nov = []
history_power_nov = []
history_combined_nov = []"""
            if init_old in source:
                source = source.replace(init_old, init_new)

            # 2. Append in the main loop
            append_old = """    history_treble.append(present.get('treble_flux', 0.0))
    history_trust.append(ltm_trust)"""
            
            append_new = """    history_treble.append(present.get('treble_flux', 0.0))
    history_trust.append(ltm_trust)
    history_stm_power.append(stm_power)
    history_ltm_power.append(ltm_power)
    history_timbral_nov.append(timbral_novelty)
    history_power_nov.append(power_novelty)
    history_combined_nov.append(combined_novelty)"""
            if append_old in source:
                source = source.replace(append_old, append_new)

            # Assign back
            if "\n" in source:
                lines = source.split('\n')
                cell['source'] = [line + '\n' for line in lines[:-1]] + [lines[-1]] if lines else []
            else:
                cell['source'] = [source]

    # Create the new plotting cell
    new_cell = {
      "cell_type": "code",
      "execution_count": None,
      "metadata": {},
      "outputs": [],
      "source": [
        "stm_power_arr = np.array(history_stm_power)\n",
        "ltm_power_arr = np.array(history_ltm_power)\n",
        "timbral_nov_arr = np.array(history_timbral_nov)\n",
        "power_nov_arr = np.array(history_power_nov)\n",
        "combined_nov_arr = np.array(history_combined_nov)\n",
        "\n",
        "fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), sharex=True)\n",
        "\n",
        "# TOP PLOT: Power Comparison\n",
        "ax1.plot(time_arr, stm_power_arr, color='dodgerblue', alpha=0.8, linewidth=1.5, label='Short-Term Power (STM)')\n",
        "ax1.plot(time_arr, ltm_power_arr, color='darkorange', alpha=0.8, linewidth=2.0, label='Long-Term Power (LTM)')\n",
        "ax1.set_title(\"Power Dynamics (STM vs LTM)\")\n",
        "ax1.set_ylabel(\"Total Smoothed Power\")\n",
        "ax1.legend(loc=\"upper right\")\n",
        "ax1.grid(alpha=0.3)\n",
        "\n",
        "for sid, s_time in enumerate(structural_changes):\n",
        "    ax1.axvline(s_time, color='red', linestyle='--', linewidth=2)\n",
        "for sid, s_time in enumerate(song_changes):\n",
        "    ax1.axvline(s_time, color='black', linestyle='-', linewidth=3)\n",
        "\n",
        "# BOTTOM PLOT: Novelty & Boundaries\n",
        "ax2.plot(time_arr, timbral_nov_arr, color='purple', alpha=0.5, label='Timbral Novelty')\n",
        "ax2.plot(time_arr, power_nov_arr, color='orange', alpha=0.5, label='Power Novelty (relative)')\n",
        "ax2.plot(time_arr, combined_nov_arr, color='red', linewidth=2.0, label='Combined Novelty Score')\n",
        "ax2.axhline(0.15, color=\"black\", linestyle=\":\", label=\"Threshold (0.15)\")\n",
        "ax2.set_title(\"Structural Novelty & Segmentation Boundaries\")\n",
        "ax2.set_xlabel(\"Time (seconds)\")\n",
        "ax2.set_ylabel(\"Novelty Score\")\n",
        "ax2.legend(loc=\"upper right\")\n",
        "ax2.grid(alpha=0.3)\n",
        "\n",
        "# Plot the Boundaries\n",
        "for sid, s_time in enumerate(structural_changes):\n",
        "    ax2.axvline(s_time, color='red', linestyle='--', linewidth=2, label='Verse/Chorus Boundary' if sid == 0 else \"\")\n",
        "for sid, s_time in enumerate(song_changes):\n",
        "    ax2.axvline(s_time, color='black', linestyle='-', linewidth=3, label='Song Change' if sid == 0 else \"\")\n",
        "\n",
        "plt.tight_layout()\n",
        "plt.savefig('novelty_boundaries_plot.png')\n",
        "plt.show()"
      ]
    }
    nb['cells'].append(new_cell)

    with open('ContinuousHybridTracker.ipynb', 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1)

if __name__ == '__main__':
    patch_add_novelty_plot()
    print("Notebook perfectly plotted to user's specs.")
