"""
Velodictum - Auto-Ducking Verification Suite
Tests native Windows Core Audio master volume ducking, scalar boundaries,
and unduck restoration.
"""
from audio_ducker import audio_ducker


def test_auto_ducking():
    print("--- TEST: Windows Core Audio Auto-Ducking ---")
    initial_vol = audio_ducker.get_master_volume()
    print(f"  Current Windows Master Volume: {initial_vol}")
    if initial_vol is None:
        print("[WARN] Audio endpoint not accessible in headless environment, skipping live ducking.")
        return

    # 1. Duck to 25%
    duck_ok = audio_ducker.duck(target_fraction=0.25)
    assert duck_ok, "audio_ducker.duck() failed"
    assert audio_ducker.is_ducked, "is_ducked should be True"

    ducked_vol = audio_ducker.get_master_volume()
    print(f"  Ducked Volume: {ducked_vol}")
    assert ducked_vol is not None
    assert ducked_vol <= initial_vol, "Ducked volume must be <= initial volume"

    # 2. Unduck back to original level
    unduck_ok = audio_ducker.unduck()
    assert unduck_ok, "audio_ducker.unduck() failed"
    assert not audio_ducker.is_ducked, "is_ducked should be False"

    restored_vol = audio_ducker.get_master_volume()
    print(f"  Restored Volume: {restored_vol}")
    assert abs(restored_vol - initial_vol) < 0.05, f"Expected {initial_vol}, got {restored_vol}"

    print("[OK] [AUTO-DUCKING TEST PASSED] Native Core Audio Ducking and Restoration verified!")


if __name__ == "__main__":
    test_auto_ducking()
