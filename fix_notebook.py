import json

def fix_notebook():
    file_path = 'ContinuousHybridTracker.ipynb'
    with open(file_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
        
    new_source = [
        "stm_power_arr = np.array(history_stm_power)\n",
        "ltm_power_arr = np.array(history_ltm_power)\n",
        "timbral_nov_arr = np.array(history_timbral_nov)\n",
        "power_nov_arr = np.array(history_power_nov)\n",
        "combined_nov_arr = np.array(history_combined_nov)\n",
        "nov_lm_arr = np.array(history_novelty_lm)\n",
        "nov_gm_arr = np.array(history_novelty_gm)\n",
        "asserved_nov_arr = np.array(history_asserved_nov)\n",
        "\n",
        "fig, (ax1, ax2, ax3, ax4) = plt.subplots(4, 1, figsize=(15, 18), sharex=True)\n",
        "\n",
        "### GROUP 1: RAW AUDIO SIGNALS ###\n",
        "\n",
        "# PLOT 1: Power Comparison\n",
        "ax1.plot(time_arr, stm_power_arr, color='dodgerblue', alpha=0.8, linewidth=1.5, label='Short-Term Power (STM)')\n",
        "ax1.plot(time_arr, ltm_power_arr, color='darkorange', alpha=0.8, linewidth=2.0, label='Long-Term Power (LTM)')\n",
        "ax1.set_title(\"Signal Group: Power Dynamics (STM vs LTM)\")\n",
        "ax1.set_ylabel(\"Total Smoothed Power\")\n",
        "ax1.legend(loc=\"upper right\")\n",
        "ax1.grid(alpha=0.3)\n",
        "\n",
        "# PLOT 2: Vocal Detection\n",
        "ax2.plot(time_arr, vocal_arr, color='magenta', linewidth=1.5, label='Vocal Flux')\n",
        "vocal_max = np.max(vocal_arr) if len(vocal_arr) > 0 else 100\n",
        "ax2.fill_between(time_arr, 0, vocal_max, where=vocals_present_arr, color='purple', alpha=0.2, label='Vocals Present Area')\n",
        "ax2.set_title(\"Signal Group: Vocal Flux & Acapella Detection\")\n",
        "ax2.set_ylabel(\"Vocal Flux Energy\")\n",
        "ax2.legend(loc=\"upper right\")\n",
        "ax2.grid(alpha=0.3)\n",
        "\n",
        "### GROUP 2: STRUCTURAL NOVELTY ###\n",
        "\n",
        "# PLOT 3: Raw Novelty vs LM & GM Envelopes\n",
        "ax3.plot(time_arr, combined_nov_arr, color='red', linewidth=1.5, label='Combined Novelty Score')\n",
        "ax3.plot(time_arr[:len(nov_lm_arr)], nov_lm_arr, color=\"grey\", linestyle=\":\", label=\"Local Max Envelope\")\n",
        "ax3.plot(time_arr[:len(nov_gm_arr)], nov_gm_arr, color=\"black\", linewidth=2.0, alpha=0.6, label=\"Global Max Envelope\")\n",
        "ax3.set_title(\"Structural Tracking Group: Raw Novelty vs Asserved Envelopes\")\n",
        "ax3.set_ylabel(\"Novelty Score\")\n",
        "ax3.legend(loc=\"upper right\")\n",
        "ax3.grid(alpha=0.3)\n",
        "\n",
        "# PLOT 4: Asserved Normalized Novelty & Triggers\n",
        "ax4.plot(time_arr[:len(asserved_nov_arr)], asserved_nov_arr, color='teal', linewidth=2.0, label='Asserved Normalized Novelty')\n",
        "ax4.axhline(1.0, color=\"green\", linestyle=\":\", label=\"Absolute Normalized Peak\")\n",
        "ax4.axhline(0.8, color=\"black\", linestyle=\"--\", linewidth=2.0, label=\"Song Change Threshold (0.8)\")\n",
        "ax4.axhline(0.6, color=\"red\", linestyle=\":\", linewidth=2.0, label=\"Verse/Chorus Threshold (0.6)\")\n",
        "ax4.set_title(\"Structural Tracking Group: Fully Asserved Normalization Signal\")\n",
        "ax4.set_xlabel(\"Time (seconds)\")\n",
        "ax4.set_ylabel(\"Asserved value (0-1)\")\n",
        "ax4.legend(loc=\"upper right\")\n",
        "ax4.grid(alpha=0.3)\n",
        "\n",
        "### ADD GLOBAL MARKERS TO ALL APPROPRIATE PLOTS ###\n",
        "\n",
        "y=0\n",
        "for k in range(len(y_list)):\n",
        "    y_k = y_list[k]\n",
        "    y+= len(y_k)\n",
        "    for ax in [ax3, ax4]:\n",
        "        ax.axvline(y/sr, color='purple', linestyle='-', linewidth=2, label=f'Real song change {k}' if k==0 else \"\")\n",
        "\n",
        "# Add algorithmic song structures\n",
        "for sid, s_time in enumerate(structural_changes):\n",
        "    ax1.axvline(s_time, color='red', linestyle='--', linewidth=2)\n",
        "    ax3.axvline(s_time, color='red', linestyle='--', linewidth=2, label='Verse/Chorus Boundary' if sid == 0 else \"\")\n",
        "    ax4.axvline(s_time, color='red', linestyle='--', linewidth=2)\n",
        "\n",
        "for sid, s_time in enumerate(song_changes):\n",
        "    ax1.axvline(s_time, color='black', linestyle='-', linewidth=3)\n",
        "    ax3.axvline(s_time, color='black', linestyle='-', linewidth=2, alpha=0.4,label='Song Change' if sid == 0 else \"\")\n",
        "    ax4.axvline(s_time, color='black', linestyle='-', linewidth=2)\n",
        "\n",
        "for ev_i, ev in enumerate(acapella_events):\n",
        "    ax2.axvline(x=ev, color='orange', linestyle='-', linewidth=3, alpha=0.8, label='Acapella Event' if ev_i == 0 else \"\")\n",
        "    \n",
        "plt.tight_layout()\n",
        "plt.savefig('novelty_boundaries_plot.png')\n",
        "plt.show()\n"
    ]
        
    for cell in nb['cells']:
        if cell['cell_type'] == 'code' and any('plt.subplots(4, 1' in line for line in cell['source']):
            cell['source'] = new_source
            break
            
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1)

if __name__ == '__main__':
    fix_notebook()
