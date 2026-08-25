"""
Velodictum - Verification Suite: Audio Pre-Amplification Gain & Anti-Clipping Soft Limiter
Verifies:
1. Gain multiplier scaling on PCM audio arrays
2. Anti-clipping limiter (signal strictly clamped to [-0.99, 0.99])
3. AudioRecorder callback gain integration
"""
import numpy as np
from config import config
from audio_recorder import AudioRecorder


def test_gain_and_anti_clipping():
    print("--- TEST: Audio Gain & Anti-Clipping Soft Limiter ---")

    # 1. Test normal scaling
    config.audio.input_gain = 2.0  # +6 dB
    rec = AudioRecorder()
    rec._is_recording = True

    # Low amplitude input
    low_signal = np.array([[0.1], [0.2], [-0.15], [0.05]], dtype=np.float32)
    rec._audio_callback(low_signal, len(low_signal), None, 0)

    chunk = rec._frames[-1]
    expected = low_signal * 2.0
    np.testing.assert_allclose(chunk, expected, rtol=1e-5)
    print("  Gain scaling test passed: signal accurately amplified by 2.0x")

    # 2. Test Anti-Clipping Limiter (high input that would exceed 1.0)
    hot_signal = np.array([[0.8], [0.9], [-0.95], [1.2]], dtype=np.float32)
    rec._audio_callback(hot_signal, len(hot_signal), None, 0)

    hot_chunk = rec._frames[-1]
    max_val = np.max(np.abs(hot_chunk))
    print(f"  Hot chunk max amplitude after 2.0x gain: {max_val:.4f}")
    assert max_val <= 0.99, f"Anti-clipping limiter failed: max amplitude {max_val} > 0.99"

    # 3. Test Microphone Test Mode (Level callback without accumulating frames)
    level_updates = []
    def on_level(rms):
        level_updates.append(rms)

    rec_test = AudioRecorder(on_level_update=on_level)
    rec_test._is_testing = True

    test_signal = np.array([[0.2], [0.3], [-0.25], [0.1]], dtype=np.float32)
    rec_test._audio_callback(test_signal, len(test_signal), None, 0)

    assert len(rec_test._frames) == 0, "Test mode must not accumulate frames into recorder buffer!"
    assert len(level_updates) == 1, "Test mode must trigger on_level_update for calibration meter!"
    assert level_updates[0] > 0.0, "RMS value must be positive"

    rec_test.stop_test()
    assert not rec_test.is_testing
    assert level_updates[-1] == 0.0, "stop_test must reset level meter to 0.0"

    # Reset config
    config.audio.input_gain = 1.0
    rec.stop()
    print("[OK] [GAIN & LIMITER PASSED] Software pre-amplification, anti-clipping, and mic test mode verified!")


if __name__ == "__main__":
    test_gain_and_anti_clipping()
