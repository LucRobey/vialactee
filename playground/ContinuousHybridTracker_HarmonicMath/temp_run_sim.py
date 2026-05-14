def class_to_bpm_candidates(bpm_class):
    # Base bpm in the [60, 120] range
    base_bpm = 60.0 * (2 ** bpm_class)
    
    # Standard octave multiples + Polyrhythmic Cousins!
    candidates = [
        base_bpm * 0.5,
        base_bpm * 0.75, # 3/4 time
        base_bpm * 1.0,
        base_bpm * 1.25, # 5/4 time (Cures the 116 -> 145 trap!)
        base_bpm * 1.5,  # 3/2 time
        base_bpm * 2.0
    ]
    return candidates

def run_simulation(y_list):
    print(f"\n🚀 Starting Fast-Scout/Heavy-Judge Simulation with Bass+High Filter...")
    infos = default_infos()
    infos["printAsservmentDetails"] = False 
    infos["useMicrophone"] = True

    SIMULATED_FPS = 60.0
    TIME_PER_FRAME = 1.0 / SIMULATED_FPS
    CHUNK_SIZE_FOR_60FPS = int(44100 / SIMULATED_FPS)

    class MockTime:
        def __init__(self): self.current_time = 0.0
        def time(self): return self.current_time

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

    # Metrics
    history_time = []
    history_raw_bpm = []
    history_pearson = []
    history_class = []
    history_ltm_class = []

    audio_time = 0.0
    playhead_time = 0.0
    frame = 0

    frames_since_sweep = 0
    frames_between_sweep = int(5 * SIMULATED_FPS)

    long_term_class = 0.0
    
    # CUSTOM BASS + HIGH ODF BUFFER
    custom_odf_buffer = np.zeros(300)
    prev_bands = np.zeros(len(listener.ingestion.fft_band_values))

    while mic.pop_chunk(CHUNK_SIZE_FOR_60FPS):
        mic.calculate_fft()
        listener.update()
        
        # Calculate pristine ODF (Dropping Mid frequencies to remove vocal/synth noise)
        current_bands = np.array(listener.ingestion.fft_band_values)
        flux_bands = np.maximum(0, current_bands - prev_bands)
        prev_bands = current_bands
        
        # Bass = 0, 1. High = 5, 6 (or whatever the top two are)
        # Summing just the edges.
        custom_flux = np.sum(flux_bands[0:2]) + np.sum(flux_bands[-2:])
        custom_odf_buffer = np.roll(custom_odf_buffer, -1)
        custom_odf_buffer[-1] = custom_flux
        
        if frames_since_sweep >= frames_between_sweep:
            # 1. RAW SWEEP (The Fast Scout) on CUSTOM PRISTINE ODF
            raw_bpm, raw_phase, raw_score = localized_continuous_phase_sweep(
                custom_odf_buffer, center_bpm=120.0, search_radius=40.0, step=0.5, expected_phase=None, tau_power=0.5)
            
            # 2. CLASS MATH
            current_class = bpm_to_class(raw_bpm)
            
            # 3. ALIGN & SMOOTH
            min_d, aligned_class = harmonic_alignment(current_class, long_term_class)
            
            if playhead_time < 5.0:
                long_term_class = aligned_class
            else:
                diff = (aligned_class - long_term_class + 0.5) % 1.0 - 0.5
                long_term_class = (long_term_class + 0.1 * diff) % 1.0
                
            # 4. CANDIDATES
            candidates = class_to_bpm_candidates(long_term_class)
            
            # 5. FINAL LOCK (The Heavy Judge) on CUSTOM PRISTINE ODF
            bpm_pearson, score_pearson = evaluate_specific_bpms(custom_odf_buffer, candidates)

            # THE FLYWHEEL FIX
            winning_class = bpm_to_class(bpm_pearson)
            min_d_win, aligned_winning_class = harmonic_alignment(winning_class, long_term_class)
            diff_win = (aligned_winning_class - long_term_class + 0.5) % 1.0 - 0.5
            long_term_class = (long_term_class + 0.5 * diff_win) % 1.0 

            listener.analyzer.bpm = bpm_pearson
            frames_since_sweep = 0
            
        frames_since_sweep += 1
        
        if frame % int(SIMULATED_FPS) == 0:
            history_time.append(playhead_time)
            history_raw_bpm.append(raw_bpm if 'raw_bpm' in locals() else 120)
            history_pearson.append(bpm_pearson if 'bpm_pearson' in locals() else 120)
            history_class.append(current_class if 'current_class' in locals() else 0)
            history_ltm_class.append(long_term_class)

        audio_time += TIME_PER_FRAME
        mock_timer.current_time += TIME_PER_FRAME
        playhead_time += TIME_PER_FRAME
        frame += 1

    ListenerModule.time.time = time.time 
    
    print("Simulation Complete!")
    return history_time, history_raw_bpm, history_pearson, history_class, history_ltm_class

