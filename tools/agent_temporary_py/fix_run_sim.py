def fix_run_sim():
    with open('run_sim.py', 'r', encoding='utf-8') as f:
        src = f.read()

    # Fix indentation errors
    src = src.replace('    history_bass = []', 'history_bass = []')
    src = src.replace('    history_treble = []', 'history_treble = []')
    
    src = src.replace("        history_bass.append(present.get('bass_flux', 0.0))", "    history_bass.append(present.get('bass_flux', 0.0))")
    src = src.replace("        history_treble.append(present.get('treble_flux', 0.0))", "    history_treble.append(present.get('treble_flux', 0.0))")

    src = src.replace('    bass_arr = np.array(history_bass)', 'bass_arr = np.array(history_bass)')
    src = src.replace('    treble_arr = np.array(history_treble)', 'treble_arr = np.array(history_treble)')
    
    src = src.replace('    # Scale bass/treble to fit on the BPM axis for visualization\n    plt.plot', '# Scale bass/treble to fit on the BPM axis for visualization\nplt.plot')
    src = src.replace('    plt.plot(time_arr, treble_arr', 'plt.plot(time_arr, treble_arr')

    # Add the bass and treble curves to the last plot as well
    # The last plot plots onset_env_full[mask]. Let's also plot the flux arrays.
    last_plot_add = """
plt.plot(time_arr, bass_arr, label='Bass Flux', color='blue', alpha=0.8)
plt.plot(time_arr, treble_arr, label='Treble Flux', color='orange', alpha=0.8)
plt.savefig('last_plot.png')
"""
    src = src.replace('plt.show()', last_plot_add + '\nplt.show()')

    with open('run_sim.py', 'w', encoding='utf-8') as f:
        f.write(src)

if __name__ == '__main__':
    fix_run_sim()
    print("Fixed run_sim.py")
