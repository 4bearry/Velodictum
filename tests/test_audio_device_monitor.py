"""
Velodictum - Audio Device Fallback & Monitor Test Suite
Verifies:
1. Audio input device enumeration.
2. System default input device retrieval.
3. Graceful stream fallback when an invalid device index is supplied.
"""
from audio_device_monitor import audio_device_monitor
from audio_recorder import AudioRecorder


def test_audio_device_monitor():
    print("--- TEST: Audio Device Fallback & Monitor ---")

    # 1. Query Devices
    devices = audio_device_monitor.get_input_devices()
    print(f"  Detected Input Devices: {len(devices)}")
    default_dev = audio_device_monitor.get_default_input_device()
    print(f"  Default Input Device: {default_dev}")

    # 2. Test AudioRecorder start() with an invalid device index (9999) to verify automatic fallback
    rec = AudioRecorder(device=9999)
    started = rec.start()
    print(f"  Recorder start with invalid device 9999 -> started: {started}, fallback device: {rec.device}")
    assert started, "AudioRecorder should successfully start using fallback device"
    assert rec.is_recording, "AudioRecorder should be recording"

    # Stop recording
    rec.stop()
    assert not rec.is_recording, "AudioRecorder should be stopped"

    print("[OK] [DEVICE MONITOR TEST PASSED] Device querying and graceful stream fallback verified!")


if __name__ == "__main__":
    test_audio_device_monitor()
