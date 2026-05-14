import json
import os

nb_path = 'ContinuousHybridTracker_HarmonicMath.ipynb'
with open(nb_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# The new TemplateBank and optimized Judge cell
new_judge_cell_source = [
    "# THE TEMPLATE BANK (O(1) Precomputed Pearson Correlation)\n",
    "class FastTemplateBank:\n",
    "    def __init__(self, btrack_fps=60.0, odf_size=300):\n",
    "        self.btrack_fps = btrack_fps\n",
    "        self.odf_size = odf_size\n",
    "        self.templates = {}\n",
    "        \n",
    "        buffer_indices = np.arange(self.odf_size)\n",
    "        self.const_part = buffer_indices - (self.odf_size - 1)\n",
    "        \n",
    "    def get_template(self, bpm_val):\n",
    "        if bpm_val in self.templates:\n",
    "            return self.templates[bpm_val]\n",
    "            \n",
    "        tau_val = 60.0 * self.btrack_fps / bpm_val\n",
    "        p_max = int(np.ceil(tau_val))\n",
    "        \n",
    "        p_arr = np.arange(p_max)[:, None]\n",
    "        phase_float = (self.const_part[None, :] + p_arr) % tau_val\n",
    "        norm_phi = phase_float / tau_val \n",
    "        \n",
    "        # Sharp Triangle Pulse\n",
    "        beat_dist = np.minimum(norm_phi, 1.0 - norm_phi)\n",
    "        template_vals = np.full((p_max, self.odf_size), -1.0)\n",
    "        mask_beat = beat_dist < 0.1\n",
    "        template_vals[mask_beat] = 1.0 - (beat_dist[mask_beat] / 0.1)\n",
    "        \n",
    "        template_mean = np.mean(template_vals, axis=1, keepdims=True)\n",
    "        template_centered = template_vals - template_mean\n",
    "        template_std = np.sqrt(np.sum(template_centered**2, axis=1)) + 1e-6\n",
    "        \n",
    "        # Pre-normalized template for rapid matrix multiplication\n",
    "        normalized_template = template_centered / template_std[:, None]\n",
    "        self.templates[bpm_val] = normalized_template\n",
    "        return normalized_template\n",
    "\n",
    "# Global Bank Instance\n",
    "template_bank = FastTemplateBank()\n",
    "\n",
    "# THE CANDIDATE EVALUATOR (HEAVY JUDGE)\n",
    "def evaluate_specific_bpms(odf_buffer, candidate_bpms, **kwargs):\n",
    "    odf_size = len(odf_buffer)\n",
    "    decay_curve = np.exp(-1.5 * np.linspace(1.0, 0.0, odf_size))\n",
    "    weighted_buffer = odf_buffer * decay_curve\n",
    "    \n",
    "    # Pre-compute zero-mean buffer for Pearson\n",
    "    buffer_mean = np.mean(weighted_buffer)\n",
    "    buffer_centered = weighted_buffer - buffer_mean\n",
    "    buffer_std = np.sqrt(np.sum(buffer_centered**2)) + 1e-6\n",
    "    \n",
    "    best_score_pearson = -float('inf')\n",
    "    best_bpm_pearson = candidate_bpms[0]\n",
    "    \n",
    "    for bpm_val in candidate_bpms:\n",
    "        if not (40.0 <= bpm_val <= 190.0):\n",
    "            continue\n",
    "            \n",
    "        normalized_template = template_bank.get_template(bpm_val)\n",
    "        \n",
    "        # O(1) Vectorized Pearson Correlation via Dot Product\n",
    "        p_scores_pearson = (normalized_template @ buffer_centered) / buffer_std\n",
    "        \n",
    "        # --- HUMAN PERCEPTION PRIOR (Gaussian weighting) ---\n",
    "        human_prior = 0.5 + 0.5 * np.exp(-0.5 * ((bpm_val - 125.0) / 40.0)**2)\n",
    "        weighted_score = np.max(p_scores_pearson) * human_prior\n",
    "        \n",
    "        if weighted_score > best_score_pearson:\n",
    "            best_score_pearson = weighted_score\n",
    "            best_bpm_pearson = bpm_val\n",
    "            \n",
    "    return best_bpm_pearson, best_score_pearson\n"
]

new_scout_cell_source = [
    "# THE INITIAL SWEEP (FAST SCOUT) - TRUE PEARSON O(1)\n",
    "def class_based_phase_sweep(odf_buffer, class_evals, **kwargs):\n",
    "    odf_size = len(odf_buffer)\n",
    "    decay_curve = np.exp(-1.5 * np.linspace(1.0, 0.0, odf_size))\n",
    "    weighted_buffer = odf_buffer * decay_curve\n",
    "    \n",
    "    buffer_mean = np.mean(weighted_buffer)\n",
    "    buffer_centered = weighted_buffer - buffer_mean\n",
    "    buffer_std = np.sqrt(np.sum(buffer_centered**2)) + 1e-6\n",
    "    \n",
    "    best_overall_score = -float('inf')\n",
    "    best_overall_class = class_evals[0] % 1.0\n",
    "    \n",
    "    for class_val in class_evals:\n",
    "        c = class_val % 1.0\n",
    "        base_bpm = 60.0 * (2 ** c)\n",
    "        eval_bpm = base_bpm if base_bpm >= 90.0 else base_bpm * 2.0\n",
    "        \n",
    "        normalized_template = template_bank.get_template(eval_bpm)\n",
    "        \n",
    "        # O(1) Vectorized Pearson Correlation via Dot Product\n",
    "        p_scores = (normalized_template @ buffer_centered) / buffer_std\n",
    "        \n",
    "        tau_max_score = np.max(p_scores)\n",
    "        \n",
    "        if tau_max_score > best_overall_score:\n",
    "            best_overall_score = tau_max_score\n",
    "            best_overall_class = c\n",
    "            \n",
    "    return best_overall_class, best_overall_score\n"
]

for cell in nb['cells']:
    if cell['cell_type'] == 'code':
        source = "".join(cell['source'])
        if "def evaluate_specific_bpms" in source:
            cell['source'] = new_judge_cell_source
        elif "def class_based_phase_sweep" in source:
            cell['source'] = new_scout_cell_source

with open(nb_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1)
