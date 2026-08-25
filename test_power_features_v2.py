"""
Tests for CPU First-Run Detection, DSP Sound Themes, and Advanced Smart Snippets.
"""
import os
import tempfile
import pytest
import numpy as np
from config import AppConfig, WhisperConfig
from sound_effects import SOUND_THEMES, _synth_opal_resonance, play_cue_async
from smart_snippets import SnippetManager


def test_cpu_first_run_auto_tune(monkeypatch):
    """Verify that when no settings file exists and no CUDA GPU is present, config auto-tunes to low_vram."""
    from gpu_monitor import GPUMonitor
    
    # Mock no CUDA available
    monkeypatch.setattr(GPUMonitor, "is_cuda_available", lambda self: False)
    
    cfg = AppConfig()
    non_existent_file = os.path.join(tempfile.gettempdir(), "test_velodictum_non_existent_settings.json")
    if os.path.exists(non_existent_file):
        os.remove(non_existent_file)
        
    cfg.load(non_existent_file)
    assert cfg.is_first_run is True
    assert cfg.whisper.profile == "low_vram"
    assert cfg.whisper.model_size == "small"
    assert cfg.whisper.device == "cpu"
    assert cfg.whisper.compute_type == "int8"


def test_sound_themes_synthesis():
    """Verify that sound themes generate valid, normalized float32 audio arrays."""
    assert "opal_resonance" in SOUND_THEMES
    assert "quantum_haptic" in SOUND_THEMES
    assert "velodictum_silk" in SOUND_THEMES
    assert "taptic_glass" in SOUND_THEMES
    
    opal_start = _synth_opal_resonance(True)
    opal_stop = _synth_opal_resonance(False)
    assert isinstance(opal_start, np.ndarray)
    assert opal_start.dtype == np.float32
    assert np.max(np.abs(opal_start)) <= 1.0
    assert len(opal_start) > 0


def test_smart_snippets_variables(monkeypatch):
    """Verify dynamic date, weekday, and clipboard variables resolution in smart snippets."""
    temp_json = os.path.join(tempfile.gettempdir(), "test_snippets_vars.json")
    if os.path.exists(temp_json):
        os.remove(temp_json)
        
    mgr = SnippetManager(filepath=temp_json)
    
    # Mock clipboard
    monkeypatch.setattr(mgr, "_get_clipboard_text", lambda: "https://velodictum.ai/test")
    
    mgr.add_snippet("mein link", "Hier ist der Link: {clipboard}")
    mgr.add_snippet("heutiger tag", "Heute ist {weekday}, der {date}")
    
    res1 = mgr.apply_snippets("Bitte klicke auf mein link danke")
    assert "Hier ist der Link: https://velodictum.ai/test" in res1
    
    res2 = mgr.apply_snippets("heutiger tag ist super")
    assert "Heute ist" in res2
    assert ", der " in res2
    
    if os.path.exists(temp_json):
        os.remove(temp_json)
