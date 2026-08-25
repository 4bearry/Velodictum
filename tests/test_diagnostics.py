"""
Velodictum - Diagnostic Test Script
Verifies GPU acceleration, audio devices, and text injection.
"""
import sys
import time
import numpy as np

def run_diagnostics():
    print("=" * 60)
    print(" VELODICTUM - SYSTEM DIAGNOSTICS")
    print("=" * 60)

    # 1. Test Audio Devices
    print("\n[1/4] Checking Audio Input Devices...")
    from audio_recorder import AudioRecorder
    devices = AudioRecorder.list_devices()
    print(f"Found {len(devices)} input device(s):")
    for d in devices:
        print(f"  - [{d['id']}] {d['name']} (Channels: {d['channels']}, Rate: {d['default_samplerate']} Hz)")
    print(f"Default mic: {AudioRecorder.get_default_device_name()}")

    # 2. Test CUDA & Whisper Engine
    from gpu_monitor import GPUMonitor
    gpu = GPUMonitor()
    print(f"\n[2/4] Testing STT Engine (faster-whisper on {gpu.short_name})...")
    from stt_engine import WhisperEngine
    stt = WhisperEngine(model_size="small", device="cuda" if gpu.backend != "cpu" else "cpu")
    start_load = time.perf_counter()
    stt.load()
    print(f"Model loaded in {time.perf_counter() - start_load:.2f}s")
    
    # 3. Test Inference Latency on synthetic speech audio
    print("\n[3/4] Benchmarking STT Inference Latency...")
    # Generate 3 seconds of dummy audio (16kHz float32)
    t = np.linspace(0, 3, 16000 * 3, dtype=np.float32)
    synthetic_audio = 0.5 * np.sin(2 * np.pi * 440 * t) # 440Hz tone
    
    result = stt.transcribe(synthetic_audio)
    print(f"Audio Duration: {result['duration']:.2f}s")
    print(f"Inference Latency: {result['latency']*1000:.1f}ms")
    print(f"Real-Time Factor: {result['rtf']:.4f}x (lower is faster; <1.0 is real-time)")

    # 4. Test Text Injector & Clipboard Preservation
    print("\n[4/6] Testing Clipboard Preservation & Text Injector...")
    import pyperclip
    from text_injector import TextInjector
    
    test_original_clip = "Velodictum_Test_Original_Clipboard_Content"
    pyperclip.copy(test_original_clip)
    
    injector = TextInjector(auto_paste=False, restore_clipboard=True, restore_delay=0.1)
    injector.inject("Dictated sample text")
    
    time.sleep(0.2)
    restored_clip = pyperclip.paste()
    assert restored_clip == test_original_clip, f"Expected '{test_original_clip}', got '{restored_clip}'"
    print("Clipboard preservation test PASSED!")

    # 5. Test Autostart & UI Automation Context
    print("\n[5/6] Testing Windows Autostart & UI Automation Caret Context...")
    import autostart_manager
    autostart_state = autostart_manager.is_autostart_enabled()
    print(f"Windows Autostart registered: {autostart_state}")
    
    import ui_automation_context
    caret_pos = ui_automation_context.get_caret_screen_position()
    preceding = ui_automation_context.get_preceding_text_context()
    print(f"Active Caret Screen Position: {caret_pos}")
    print(f"Preceding Text Context: {preceding}")

    # 6. Test Flow Layer Translation & Style Profiles
    print("\n[6/6] Testing Flow Layer Translation & Style Tone Profiles...")
    from ai_formatter import AIFormatter
    from style_profiles import get_tone_instruction
    
    tone_instr = get_tone_instruction("formal_sie", "Verwende klare Fachsprache")
    print(f"Tone Prompt Instruction (formal_sie):\n  {tone_instr}")

    formatter = AIFormatter(mode="auto_adaptive", engine="rules", tone="formal_sie")
    formatted = formatter.format_text("Hallo Herr Richter, ich brauche Butter und Brot. Viele Grüße Müller")
    print(f"Rule Engine Sample Output:\n  {formatted['text']}")

    print("\n" + "=" * 60)
    print(" ALL DIAGNOSTIC CHECKS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_diagnostics()
