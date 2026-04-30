import numpy as np
import matplotlib.pyplot as plt

tau_val = 100
p_max = int(np.ceil(tau_val))
p_arr = np.arange(p_max)
norm_phi = p_arr / tau_val 
abs_phi = np.abs(norm_phi - 0.5)

template_vals = np.full(p_max, -0.2)
template_vals[abs_phi >= 0.45] = 1.5
template_vals[abs_phi <= 0.04] = 0.6
template_vals[((abs_phi >= 0.22) & (abs_phi <= 0.28))] = 0.0 

plt.figure(figsize=(10, 4))
plt.plot(norm_phi, template_vals, drawstyle='steps-mid', linewidth=2, color='coral')
plt.axhline(0, color='black', linewidth=1, linestyle='--')

plt.title('Sweep Algorithm Phase Template')
plt.xlabel('Normalized Phase (0.0 to 1.0, where 0.0 is Main Beat)')
plt.ylabel('Template Weight')
plt.grid(True, alpha=0.3)

# Annotate
plt.annotate('Main Beat\n(1.5)', xy=(0.0, 1.5), xytext=(0.05, 1.0),
             arrowprops=dict(facecolor='black', shrink=0.05, width=1, headwidth=5))
plt.annotate('Main Beat\n(1.5)', xy=(1.0, 1.5), xytext=(0.85, 1.0),
             arrowprops=dict(facecolor='black', shrink=0.05, width=1, headwidth=5))
plt.annotate('Sub-Beat\n(0.6)', xy=(0.5, 0.6), xytext=(0.5, 1.0), ha='center',
             arrowprops=dict(facecolor='black', shrink=0.05, width=1, headwidth=5))
plt.annotate('Sub-sub-beat\n(0.0)', xy=(0.25, 0.0), xytext=(0.25, 0.4), ha='center',
             arrowprops=dict(facecolor='black', shrink=0.05, width=1, headwidth=5))
plt.annotate('Sub-sub-beat\n(0.0)', xy=(0.75, 0.0), xytext=(0.75, 0.4), ha='center',
             arrowprops=dict(facecolor='black', shrink=0.05, width=1, headwidth=5))

plt.tight_layout()
plt.savefig(r'C:\Users\Users\.gemini\antigravity\brain\822c0acb-4c71-4554-a824-b81bc38b3929\artifacts\template_plot_new.png', dpi=150)
print('Plot saved.')
