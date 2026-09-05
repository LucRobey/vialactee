import pytest
import numpy as np
from unittest.mock import patch, MagicMock

import config.Configuration_manager as Configuration_manager
import core.AudioAnalyzer as AudioAnalyzer
import core.Listener as Listener


MOCK_DEVICES_WITH_VBCABLE = [
    {"name": "Mappeur de sons Microsoft - Input", "max_input_channels": 2, "max_output_channels": 0},
    {"name": "Microphone (Realtek(R) Audio)", "max_input_channels": 2, "max_output_channels": 0},
    {"name": "Stereo Mix (Realtek(R) Audio)", "max_input_channels": 2, "max_output_channels": 0},
    {"name": "Speakers (Realtek(R) Audio)", "max_input_channels": 0, "max_output_channels": 2},
    {"name": "CABLE Output (VB-Audio Virtual Cable)", "max_input_channels": 2, "max_output_channels": 0},
    {"name": "CABLE Input (VB-Audio Virtual Cable)", "max_input_channels": 0, "max_output_channels": 2},
]

MOCK_DEVICES_NO_VBCABLE = [
    {"name": "Mappeur de sons Microsoft - Input", "max_input_channels": 2, "max_output_channels": 0},
    {"name": "Microphone (Realtek(R) Audio)", "max_input_channels": 2, "max_output_channels": 0},
    {"name": "Mixage stéréo (Realtek HD Audio Stereo input)", "max_input_channels": 2, "max_output_channels": 0},
    {"name": "Haut-parleur du PC", "max_input_channels": 0, "max_output_channels": 2},
]


def test_resolve_custom_preset():
    infos = {
        "audio_preset": "custom",
        "input_device_id": 99,
        "output_device_id": 88,
        "fakeDelay": 3.2
    }
    resolved = Configuration_manager.resolve_audio_config(infos)
    assert resolved["input_device_id"] == 99
    assert resolved["output_device_id"] == 88
    assert resolved["fakeDelay"] == 3.2


def test_resolve_spotify_preset():
    mock_sd = MagicMock()
    mock_sd.query_devices.return_value = MOCK_DEVICES_WITH_VBCABLE
    mock_sd.default.device = [1, 3]

    with patch.dict("sys.modules", {"sounddevice": mock_sd}):
        infos = {"audio_preset": "spotify"}
        resolved = Configuration_manager.resolve_audio_config(infos)
        assert resolved["input_device_id"] == 4  # CABLE Output
        assert resolved["output_device_id"] == 3  # Speakers
        assert resolved["fakeDelay"] == 5.0


def test_resolve_spotify_preset_fallback():
    mock_sd = MagicMock()
    mock_sd.query_devices.return_value = MOCK_DEVICES_NO_VBCABLE
    mock_sd.default.device = [1, 3]

    with patch.dict("sys.modules", {"sounddevice": mock_sd}):
        infos = {"audio_preset": "spotify"}
        resolved = Configuration_manager.resolve_audio_config(infos)
        assert resolved["input_device_id"] == 1  # Fallback default mic
        assert resolved["output_device_id"] == 3  # Speakers
        assert resolved["fakeDelay"] == 5.0


def test_resolve_spotify_aux_with_vbcable():
    mock_sd = MagicMock()
    mock_sd.query_devices.return_value = MOCK_DEVICES_WITH_VBCABLE
    mock_sd.default.device = [1, 3]

    with patch.dict("sys.modules", {"sounddevice": mock_sd}):
        infos = {"audio_preset": "spotify_aux"}
        resolved = Configuration_manager.resolve_audio_config(infos)
        assert resolved["input_device_id"] == 4  # CABLE Output
        assert resolved["output_device_id"] == 3  # Speakers
        assert resolved["fakeDelay"] == 5.0


def test_resolve_spotify_aux_fallback_when_missing():
    mock_sd = MagicMock()
    mock_sd.query_devices.return_value = MOCK_DEVICES_NO_VBCABLE
    mock_sd.default.device = [1, 3]

    with patch.dict("sys.modules", {"sounddevice": mock_sd}):
        infos = {"audio_preset": "spotify_aux"}
        resolved = Configuration_manager.resolve_audio_config(infos)
        # Should fall back cleanly to default input with 5s delay
        assert resolved["input_device_id"] == 1
        assert resolved["output_device_id"] == 3  # Speakers
        assert resolved["fakeDelay"] == 5.0


def test_resolve_aux_preset():
    mock_sd = MagicMock()
    mock_sd.query_devices.return_value = MOCK_DEVICES_WITH_VBCABLE
    mock_sd.default.device = [1, 3]

    with patch.dict("sys.modules", {"sounddevice": mock_sd}):
        infos = {"audio_preset": "aux"}
        resolved = Configuration_manager.resolve_audio_config(infos)
        assert resolved["input_device_id"] == 1  # Default mic
        assert resolved["output_device_id"] == 3  # Speakers
        assert resolved["fakeDelay"] == 5.0


def test_resolve_mic_preset():
    mock_sd = MagicMock()
    mock_sd.query_devices.return_value = MOCK_DEVICES_WITH_VBCABLE
    mock_sd.default.device = [1, 3]

    with patch.dict("sys.modules", {"sounddevice": mock_sd}):
        infos = {"audio_preset": "mic"}
        resolved = Configuration_manager.resolve_audio_config(infos)
        assert resolved["input_device_id"] == 1
        assert resolved["output_device_id"] is None
        assert resolved["fakeDelay"] == 0.0


def test_audio_analyzer_odf_floor_and_speaker_window_math():
    class DummyIngestion:
        nb_of_fft_band = 8
        nb_of_chroma = 12

    # 1. Test fakeDelay = 0.0: ODF buffer size floored at 300, speaker window checks newest frames
    analyzer_0s = AudioAnalyzer.AudioAnalyzer(DummyIngestion(), {"fakeDelay": 0.0})
    assert analyzer_0s.odf_buffer_size == 300
    assert analyzer_0s.lookahead_seconds == 0.0

    # Put a pulse only at the end (newest frames)
    analyzer_0s.odf_buffer[:] = 0.0
    analyzer_0s.odf_buffer[-1] = 10.0
    analyzer_0s.speaker_phase = 1.05
    analyzer_0s.rolling_flux_baseline = 1.0

    analyzer_0s._advance_flywheel(0.016, 1.0)
    assert analyzer_0s.is_beat is True
    assert analyzer_0s.is_real_beat is True
    assert analyzer_0s.is_dropped_beat is False

    # 2. Test fakeDelay = 5.0: speaker window checks oldest frames (around index 0)
    analyzer_5s = AudioAnalyzer.AudioAnalyzer(DummyIngestion(), {"fakeDelay": 5.0})
    assert analyzer_5s.odf_buffer_size == 300
    analyzer_5s.odf_buffer[:] = 0.0
    analyzer_5s.odf_buffer[0] = 10.0  # Pulse in oldest frames
    analyzer_5s.speaker_phase = 1.05
    analyzer_5s.rolling_flux_baseline = 1.0

    analyzer_5s._advance_flywheel(0.016, 1.0)
    assert analyzer_5s.is_beat is True
    assert analyzer_5s.is_real_beat is True
    assert analyzer_5s.is_dropped_beat is False


def test_listener_ring_capacity_floor():
    listener = Listener.Listener({"fakeDelay": 0.0})
    assert listener._ring_capacity >= 16

    # Verify that raw audio process does not crash and updates smoothly
    audio_chunk = np.zeros(4096)
    listener.process_raw_audio(audio_chunk)
    assert len(listener.fft_band_values) == 8
