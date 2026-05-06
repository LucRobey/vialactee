import numpy as np
import matplotlib.pyplot as plt

# Generate phase fractions from 0 to 1
norm_phi = np.linspace(0, 1.0, 1000)
abs_phi = np.abs(norm_phi - 0.5)

# Calculate template values
template_vals = np.full_like(norm_phi, -0.2)
template_vals[abs_phi >= 0.45] = 1.0
template_vals[abs_phi <= 0.05] = 0.6
template_vals[((abs_phi >= 0.22) & (abs_phi <= 0.28))] = 0.0

# Plotting on a dark theme
plt.style.use('dark_background')
plt.figure(figsize=(10, 5))

# Main function line
plt.plot(norm_phi, template_vals, color='cyan', linewidth=2.5)
plt.axhline(0, color='white', linestyle='-', linewidth=1.5, alpha=0.5)

# Fills
plt.fill_between(norm_phi, template_vals, 0, where=(template_vals>0), color='cyan', alpha=0.3)
plt.fill_between(norm_phi, template_vals, 0, where=(template_vals<0), color='red', alpha=0.3)

# Annotations
plt.title('Sub-Beat Sweep Template Weight Function', fontsize=14, pad=20)
plt.xlabel('Normalized Phase (0.0 to 1.0 = One Beat)', fontsize=12)
plt.ylabel('Reward / Penalty Weight', fontsize=12)

# Text labels for key regions
plt.text(0.02, 1.05, 'Downbeat (1.0)', ha='left', color='cyan', fontweight='bold')
plt.text(0.98, 1.05, 'Downbeat (1.0)', ha='right', color='cyan', fontweight='bold')
plt.text(0.5, 0.65, 'Upbeat (0.6)', ha='center', color='cyan', fontweight='bold')
plt.text(0.25, 0.05, '16th Note (0.0)', ha='center', color='lightgray', backgroundcolor='black')
plt.text(0.75, 0.05, '16th Note (0.0)', ha='center', color='lightgray', backgroundcolor='black')

# Additional grid aesthetics
plt.grid(True, alpha=0.15, linestyle='--')
plt.tight_layout()

# Save out to artifacts
save_path = r'C:\Users\Users\.gemini\antigravity\brain\822c0acb-4c71-4554-a824-b81bc38b3929\template_plot.png'
plt.savefig(save_path, dpi=200, transparent=False)
