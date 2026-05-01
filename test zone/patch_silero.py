import nbformat

def patch_notebook():
    path = 'continuousVoiceTracking.ipynb'
    with open(path, 'r', encoding='utf-8') as f:
        nb = nbformat.read(f, as_version=4)

    # Find the data loading cell
    for cell in nb.cells:
        if "y_full = " in cell.source and "song_files =" in cell.source:
            if "target_sr=16000" not in cell.source:
                cell.source += "\nprint('Resampling audio to 16kHz for Silero VAD...')\ny_full_16k = librosa.resample(y_full, orig_sr=44100, target_sr=16000)\nprint(f'✅ Resampled to 16kHz! Total 16k frames: {len(y_full_16k)}')\n"

    # Find the main simulation loop cell
    sim_cell = None
    for cell in nb.cells:
        if "mic = Robust_Simulated_Microphone" in cell.source and "while mic.pop_chunk" in cell.source:
            sim_cell = cell
            break

    if sim_cell:
        new_code = '''import torch
model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad', force_reload=False, trust_repo=True)
model.eval() # ensure evaluation mode

infos = default_infos()

SIMULATED_FPS = 60.0
TIME_PER_FRAME = 1.0 / SIMULATED_FPS
CHUNK_SIZE_FOR_60FPS = int(44100 / SIMULATED_FPS)

mic = Robust_Simulated_Microphone(y_full, np.zeros(8, dtype=int), infos)

history_time = []
history_vocals_present = []
history_vocal_score = []
history_complexity = []
history_variance = []
acapella_events = []
last_acapella_frame = -9999
ACAPELLA_COOLDOWN_FRAMES = int(5.0 * SIMULATED_FPS)

audio_time = 0.0
playhead_time = 0.0
frame = 0

smooth_suppression = 50.0
smooth_vocal = 0.0
ema_complexity = 0.0
COMPLEXITY_ALPHA = 0.1
asserved_bass_energy = 0.0
asserved_treble_energy = 0.0
asserved_bass_flux = 0.0
asserved_treble_flux = 0.0
EMA_ALPHA = 0.0066  # Approximates a 5-second moving average at 60 FPS

acapella_state = False
hangover_frames = 0
DILATION_FRAMES = int(0.5 * SIMULATED_FPS)

# Silero VAD Tracking
current_16k_pos = 0
vad_buffer = []
current_voice_prob = 0.0

print("🚀 Starting Voice Tracking Simulation with Silero VAD...")

while mic.pop_chunk(CHUNK_SIZE_FOR_60FPS):
    mic.calculate_fft()
    
    vocal_energy = mic.vocal_energy
    bass_energy = mic.bass_energy
    treble_energy = mic.treble_energy
    
    # 16kHz audio buffer integration for VAD processing
    next_16k_pos = int((audio_time + TIME_PER_FRAME) * 16000)
    if next_16k_pos > current_16k_pos:
        new_16k_samples = y_full_16k[current_16k_pos:next_16k_pos]
        vad_buffer.extend(new_16k_samples)
        current_16k_pos = next_16k_pos
        
    # Process EXACTLY 512 frames at a time
    while len(vad_buffer) >= 512:
        chunk = vad_buffer[:512]
        vad_buffer = vad_buffer[512:]
        tensor_chunk = torch.tensor(chunk, dtype=torch.float32)
        with torch.no_grad():
            current_voice_prob = model(tensor_chunk, 16000).item()
            
    # Exponential moving averages for baseline audio
    asserved_bass_energy = asserved_bass_energy * (1 - EMA_ALPHA) + bass_energy * EMA_ALPHA
    asserved_treble_energy = asserved_treble_energy * (1 - EMA_ALPHA) + treble_energy * EMA_ALPHA
    asserved_bass_flux = asserved_bass_flux * (1 - EMA_ALPHA) + mic.bass_flux * EMA_ALPHA
    asserved_treble_flux = asserved_treble_flux * (1 - EMA_ALPHA) + mic.treble_flux * EMA_ALPHA

    # We map the voice prob directly to vocal_score for plotting and bounds logic
    # scaling it so it behaves identically on a scale with the old metrics (0.0 - 1.5+)
    vocal_score = current_voice_prob * 1.5 
    
    # VAD Detection logic incorporating some track safety checks
    score_high_threshold = 0.5 * 1.5  # > 0.5 strict probability
    score_low_threshold = 0.3 * 1.5
    
    if not acapella_state:
        # Add minor constraint on bass/treble flux to prevent electronic drop triggers
        if vocal_score > score_high_threshold and mic.bass_flux < (asserved_bass_flux * 0.8 + 10.0):
            acapella_state = True
            hangover_frames = DILATION_FRAMES
    else:
        if vocal_score > score_low_threshold:
            hangover_frames = DILATION_FRAMES
        else:
            hangover_frames -= 1
            if hangover_frames <= 0:
                acapella_state = False

    vocals_present = acapella_state
    
    # Event cooldown system
    if mic.bass_flux < 5.0 and acapella_state:
        if (frame - last_acapella_frame) > ACAPELLA_COOLDOWN_FRAMES:
            acapella_events.append(playhead_time)
            last_acapella_frame = frame

    history_time.append(playhead_time)
    ema_complexity = ema_complexity * (1 - COMPLEXITY_ALPHA) + mic.spectral_complexity * COMPLEXITY_ALPHA
    
    history_complexity.append(ema_complexity*0.5+history_complexity[-1]*0.95) if len(history_complexity)>0 else history_complexity.append(ema_complexity)
    diff = ema_complexity - history_complexity[-1]
    history_variance .append(0.9 * history_variance[-1] + 0.1 * diff * diff) if len(history_variance)>0 else history_variance.append(diff*diff)
    history_vocals_present.append(vocals_present)
    history_vocal_score.append(vocal_score)
    
    playhead_time += TIME_PER_FRAME
    audio_time += TIME_PER_FRAME
    frame += 1
    
    if frame % 1800 == 0:
        print(f"Processed audio time {audio_time:.1f}s...")

print(f"✅ Simulation Complete! Detected {len(acapella_events)} distinct acapella events.")
'''
        sim_cell.source = new_code

    with open(path, 'w', encoding='utf-8') as f:
        nbformat.write(nb, f)
        print("Notebook successfully patched for Silero VAD!")

if __name__ == '__main__':
    patch_notebook()
