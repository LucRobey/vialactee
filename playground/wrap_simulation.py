import json

target_path = r"c:\Users\Users\Desktop\vialactée\vialactee\playground\ContinuousHybridTracker_OptionsTest.ipynb"

with open(target_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

new_sim_code = """import json

def run_simulation(ACTIVE_OPTION, y_list):
    print(f"\\n🚀 Starting Simulation for OPTION {ACTIVE_OPTION}...")
    infos = default_infos()
    infos["printAsservmentDetails"] = False 
    infos["useMicrophone"] = True

    SIMULATED_FPS = 60.0
    TIME_PER_FRAME = 1.0 / SIMULATED_FPS
    CHUNK_SIZE_FOR_60FPS = int(44100 / SIMULATED_FPS)

    class MockTime:
        def __init__(self):
            self.current_time = 0.0
        def time(self):
            return self.current_time

    mock_timer = MockTime()
    ListenerModule.time.time = mock_timer.time

    listener = ListenerModule.Listener(infos)
    listener.ingestion.momentum_multiplier = 0.01
    listener.dynamic_audio_latency = 0

    y_full = np.concatenate(y_list)
    mic = Robust_Simulated_Microphone(y_full, listener.ingestion.fft_band_values, infos)
    listener.hasBeenSilenceCalibrated = True
    listener.hasBeenBBCalibrated = True
    listener.ingestion.calibrate_silence = lambda fps_ratio: None
    listener.ingestion.calibrate_bb = lambda fps_ratio: None

    lookahead_frames = int(8.5 * SIMULATED_FPS)
    future_queue = deque()

    algorithmic_beats = []
    algorithmic_sub_beats = []
    history_time = []
    history_bpm = []
    history_target_phase = []
    history_bpm_divergence = []
    history_ltm_bpm = []
    jailbreak_times = []
    jailbreak_bpms = []

    track_target_phase = 0.0
    track_bpm_divergence = 0.0

    standalone_phase = 0.0
    standalone_beat_count = 0
    last_standalone_beat_count = 0
    last_standalone_phase = 0.0
    standalone_sub_beat_locked = -1

    audio_time = 0.0
    playhead_time = 0.0
    frame = 0

    frames_since_sweep = 0
    frames_between_sweep = int(5 * SIMULATED_FPS)

    # Structural Novelty Variables
    stm_timbre = np.zeros(8)
    ltm_timbre = np.zeros(8)
    stm_power = 0.0
    ltm_power = 0.0
    stm_weight = 0.02
    ltm_weight = 0.0015

    structural_changes = []
    last_structural_change_frame = -9999
    STRUCTURAL_COOLDOWN_FRAMES = int(20.0 * SIMULATED_FPS)

    novelty_lm = 0.2
    novelty_gm = 0.3
    asserved_novelty = 0.0
    NOVELTY_DECAY_RATE = 0.9999

    power_weight = 0.2
    SONG_NOVELTY_ASSERVED_TH = 0.75

    song_changes = []
    silence_frames = 0
    SILENCE_THRESHOLD_FRAMES = int(1.5 * SIMULATED_FPS)

    long_term_bpm = 120.0
    ltm_trust = 10.0
    bpm_jump_threshold = 8.0
    bpm_trust = 10.0

    while mic.pop_chunk(CHUNK_SIZE_FOR_60FPS):
        mic.calculate_fft()
        listener.update()
        
        current_timbre = listener.band_proportion
        stm_timbre = (1 - stm_weight) * stm_timbre + stm_weight * current_timbre
        ltm_timbre = (1 - ltm_weight) * ltm_timbre + ltm_weight * current_timbre
        
        current_power = listener.smoothed_total_power
        stm_power = (1 - stm_weight) * stm_power + stm_weight * current_power
        ltm_power = (1 - ltm_weight) * ltm_power + ltm_weight * current_power
        
        timbral_novelty = np.linalg.norm(stm_timbre - ltm_timbre)
        power_novelty = np.abs(stm_power - ltm_power) / (ltm_power + 1.0)
        combined_novelty = timbral_novelty + (power_novelty * 0.2)

        if combined_novelty > 0.4:
            combined_novelty = 0.4
        
        if combined_novelty >= novelty_lm:
            novelty_lm = combined_novelty
        else:
            novelty_lm = max(0.15, novelty_lm * NOVELTY_DECAY_RATE)
            
        passed_gm = combined_novelty > novelty_gm
        if combined_novelty >= novelty_gm:
            novelty_gm = 1.01 * combined_novelty
        else:
            novelty_gm *= 1 + 0.005 * ((novelty_lm / novelty_gm) - 0.7)
            
        safe_gm = max(0.01, novelty_gm)
        target_asserved = combined_novelty / safe_gm
        asserved_novelty += 0.4 * (target_asserved - asserved_novelty)
        
        if asserved_novelty > SONG_NOVELTY_ASSERVED_TH:
            if len(song_changes) == 0 or (playhead_time - song_changes[-1]) > 20.0:
                song_changes.append(playhead_time)
                standalone_beat_count = 0
                last_standalone_beat_count = 0
                standalone_sub_beat_locked = -1
                standalone_phase = 0.0
                listener.ingestion.band_means.fill(0.0)
                listener.ingestion.smoothed_fft_band_values.fill(0.0)
                listener.analyzer.odf_buffer.fill(0.0)
                
                novelty_gm = combined_novelty * 1.5 
                asserved_novelty = 0.0
                ltm_timbre = np.copy(stm_timbre)
                ltm_power = stm_power
                
        elif passed_gm:
            if (frame - last_structural_change_frame) > STRUCTURAL_COOLDOWN_FRAMES:
                structural_changes.append(playhead_time)
                last_structural_change_frame = frame
                asserved_novelty = 0.0
                ltm_timbre = np.copy(stm_timbre)
                ltm_power = stm_power

        if listener.smoothed_total_power < 5.0:
            silence_frames += 1
        else:
            silence_frames = 0
            
        if silence_frames > SILENCE_THRESHOLD_FRAMES:
            if len(song_changes) == 0 or (playhead_time - song_changes[-1]) > 5.0:
                song_changes.append(playhead_time)
                standalone_beat_count = 0
                last_standalone_beat_count = 0
                standalone_sub_beat_locked = -1
                standalone_phase = 0.0
                listener.ingestion.band_means.fill(0.0)
                listener.ingestion.smoothed_fft_band_values.fill(0.0)
                listener.analyzer.odf_buffer.fill(0.0)

        if frames_since_sweep >= frames_between_sweep:
            coarse_bpm = listener.bpm if (50 < listener.bpm < 220) else 120.0
            total_latency = listener.dynamic_audio_latency + listener.analyzer.hardware_latency
            latency_phase_shift = (coarse_bpm / 60.0) * total_latency
            expected_p_phase = (standalone_phase - latency_phase_shift + 1.0) % 1.0
            inertia_param = expected_p_phase if standalone_beat_count > 5 else None
            
            jailbreak_flag = False
            
            if ACTIVE_OPTION == 0:
                precise_bpm, precise_phase, bpm_trust = localized_continuous_phase_sweep(
                    listener.analyzer.odf_buffer, center_bpm=coarse_bpm, search_radius=1.5, step=0.5, expected_phase=inertia_param)
            elif ACTIVE_OPTION == 1:
                global_target = listener.analyzer.global_target_bpm if hasattr(listener.analyzer, 'global_target_bpm') else 120.0
                precise_bpm, precise_phase, bpm_trust, jailbreak_flag = option1_global_scout(
                    listener.analyzer.odf_buffer, center_bpm=coarse_bpm, 
                    analyzer_global_bpm=global_target, 
                    analyzer_global_trust=listener.analyzer.binary_trust,
                    search_radius=1.5, step=0.5, expected_phase=inertia_param)
            elif ACTIVE_OPTION == 2:
                precise_bpm, precise_phase, bpm_trust, jailbreak_flag = option2_harmonic_cousins(
                    listener.analyzer.odf_buffer, center_bpm=coarse_bpm, search_radius=1.5, step=0.5, expected_phase=inertia_param)
            elif ACTIVE_OPTION == 3:
                precise_bpm, precise_phase, bpm_trust = option3_tau_normalized_sweep(
                    listener.analyzer.odf_buffer, center_bpm=coarse_bpm, search_radius=1.5, step=0.5, expected_phase=inertia_param)
            
            if jailbreak_flag:
                jailbreak_times.append(audio_time)
                jailbreak_bpms.append(precise_bpm)

            listener.analyzer.bpm = precise_bpm
            
            if playhead_time < 5.0:
                long_term_bpm = precise_bpm
                ltm_trust = listener.analyzer.binary_trust
            else:
                long_term_bpm = 0.8 * long_term_bpm + 0.2 * precise_bpm
                ltm_trust = 0.9 * ltm_trust + 0.1 * listener.analyzer.binary_trust
            
            bpm_divergence = np.abs(precise_bpm - long_term_bpm)
            
            if bpm_divergence > bpm_jump_threshold and listener.analyzer.binary_trust < (ltm_trust * 0.6):
                if len(song_changes) == 0 or (playhead_time - song_changes[-1]) > 5.0:
                    song_changes.append(playhead_time)
                    standalone_beat_count = 0
                    last_standalone_beat_count = 0
                    standalone_sub_beat_locked = -1
                    standalone_phase = 0.0
                    listener.ingestion.band_means.fill(0.0)
                    listener.ingestion.smoothed_fft_band_values.fill(0.0)
                    listener.analyzer.odf_buffer.fill(0.0)
                    long_term_bpm = precise_bpm

            latency_phase_shift_precise = (precise_bpm / 60.0) * total_latency
            target_phase = (precise_phase + latency_phase_shift_precise) % 1.0
            
            track_target_phase = target_phase
            track_bpm_divergence = bpm_divergence
            
            phase_diff = (target_phase - standalone_phase + 0.5) % 1.0 - 0.5
            
            if abs(phase_diff) < 0.15:
                standalone_phase += phase_diff * 1.0  
            else:
                pass
            
            frames_since_sweep = 0
            
        frames_since_sweep += 1
        
        phase_delta = (listener.bpm / 60.0) / SIMULATED_FPS
        standalone_phase += phase_delta
        
        while standalone_phase >= 1.0:
            standalone_phase -= 1.0
            standalone_beat_count += 1
        while standalone_phase < 0.0:
            standalone_phase += 1.0
            standalone_beat_count -= 1
        
        is_beat = False
        is_sub_beat = False
        
        if standalone_beat_count > last_standalone_beat_count:
            is_beat = True
            last_standalone_beat_count = standalone_beat_count
            
        if last_standalone_phase < 0.5 and standalone_phase >= 0.5:
            if standalone_sub_beat_locked < last_standalone_beat_count:
                is_sub_beat = True
                standalone_sub_beat_locked = last_standalone_beat_count
                
        last_standalone_phase = standalone_phase
        
        future_queue.append({
            'time': audio_time,
            'bpm': listener.bpm,
            'is_beat': is_beat,
            'is_sub_beat': is_sub_beat,
            'target_phase': track_target_phase,
            'bpm_divergence': track_bpm_divergence,
            'long_term_bpm': long_term_bpm
        })
        
        while len(future_queue) > 0:
            time_diff = audio_time - future_queue[0]['time']
            if time_diff < 5.0:
                break
                
            present = future_queue.popleft()
            if present.get('is_beat', False):
                algorithmic_beats.append(playhead_time)
            if present.get('is_sub_beat', False):
                algorithmic_sub_beats.append(playhead_time)
                
            history_time.append(playhead_time)
            history_bpm.append(present['bpm'])
            history_target_phase.append(present.get('target_phase', 0.0))
            history_bpm_divergence.append(present.get('bpm_divergence', 0.0))
            history_ltm_bpm.append(present.get('long_term_bpm', 120.0))
            playhead_time += TIME_PER_FRAME
            
        audio_time += TIME_PER_FRAME
        mock_timer.current_time += TIME_PER_FRAME
        frame += 1
        
    ListenerModule.time.time = time.time 

    while future_queue:
        present = future_queue.popleft()
        if present.get('is_beat', False):
            algorithmic_beats.append(playhead_time)
        if present.get('is_sub_beat', False):
            algorithmic_sub_beats.append(playhead_time)
        history_time.append(playhead_time)
        history_bpm.append(present['bpm'])
        history_target_phase.append(present.get('target_phase', 0.0))
        history_bpm_divergence.append(present.get('bpm_divergence', 0.0))
        history_ltm_bpm.append(present.get('long_term_bpm', 120.0))
        playhead_time += TIME_PER_FRAME

    return {
        'history_time': history_time,
        'history_bpm': history_bpm,
        'history_target_phase': history_target_phase,
        'history_bpm_divergence': history_bpm_divergence,
        'history_ltm_bpm': history_ltm_bpm,
        'jailbreak_times': jailbreak_times,
        'jailbreak_bpms': jailbreak_bpms,
        'num_beats': len(algorithmic_beats)
    }

# RUN THE TEST
results_dict = {}
for option_idx in [0, 1, 2, 3]:
    results_dict[f'Option_{option_idx}'] = run_simulation(option_idx, y_list)

print("\\n✅ All options simulated. Saving results to JSON...")

with open('../assets/musics/librosa/jailbreak_options_results.json', 'w') as f:
    json.dump(results_dict, f)

print("Results successfully saved to `../assets/musics/librosa/jailbreak_options_results.json`!")
"""

def split_lines(code_str):
    lines = [line + '\\n' for line in code_str.split('\\n')]
    if lines:
        lines[-1] = lines[-1].rstrip('\\n')
    return lines

for cell in nb['cells']:
    if cell['cell_type'] == 'code' and len(cell['source']) > 0 and 'ACTIVE_OPTION =' in "".join(cell['source']):
        cell['source'] = split_lines(new_sim_code)
        break

with open(target_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1)

print("Cell wrapped in test loop successfully!")
