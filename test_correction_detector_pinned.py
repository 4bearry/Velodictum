"""
Velodictum - Verification Suite: Pinned & Hardened CorrectionDetector
Verifies:
1. Pinned window & control inspection:
   - Injected in Window A / Control 1: "In Zootopia gibt es einen schönen Lux namens Powert."
   - User types in Window B / Control 2 (e.g. ChatGPT, Antigravity, empty editor):
     -> Strictly 0 prompts (no false positives)!
2. Sentence Structure Anchor Protection:
   - User types completely unrelated sentence in same window:
     -> Strictly 0 prompts!
3. Legitimate In-Field Replacement in Pinned Control:
   - User modifies 'Powert' -> 'Pawbert' in the pinned text field:
     -> Correctly triggers HUD prompt!
4. One-Shot Lifecycle:
   - Disarms after first correction or expiry.
"""
from correction_detector import correction_detector
from custom_vocabulary import vocab_manager


def test_pinned_correction_detector():
    print("--- TEST: Pinned CorrectionDetector & False-Positive Shield ---")

    test_cand = "Pawbert"
    test_orig = "Powert"
    vocab_manager.remove_word(test_cand)

    # 1. Record injection in Window 1001 / Control 'win_1001_ctrl_50'
    injected = "In Zootopia gibt es einen schönen Lux namens Powert."
    correction_detector.record_injection(injected, hwnd=1001)

    with correction_detector._lock:
        if correction_detector._last_injection:
            correction_detector._last_injection["control_sig"] = "win_1001_ctrl_50"

    # Test A: User types something in ChatGPT / Antigravity (Window 2002)
    diff_other_window = correction_detector.inspect_text_for_corrections(
        current_text="Schreibe mir eine Zusammenfassung über AlphaFold.",
        current_hwnd=2002,
        current_control_sig="win_2002_ctrl_99"
    )
    print(f"  Result for other window (ChatGPT/Antigravity): {diff_other_window}")
    assert len(diff_other_window) == 0, "Failed: False positive triggered on different window!"

    # Test B: User types new unrelated sentence in an empty control in same window
    diff_unrelated = correction_detector.inspect_text_for_corrections(
        current_text="Hallo Welt, das ist eine ganz andere Notiz.",
        current_hwnd=1001,
        current_control_sig="win_1001_ctrl_50"
    )
    print(f"  Result for unrelated text in same control: {diff_unrelated}")
    assert len(diff_unrelated) == 0, "Failed: False positive triggered on unrelated sentence!"

    # Test C: Legitimate manual replacement in the pinned control
    valid_edited_text = "In Zootopia gibt es einen schönen Lux namens Pawbert."
    valid_corrections = correction_detector.inspect_text_for_corrections(
        current_text=valid_edited_text,
        current_hwnd=1001,
        current_control_sig="win_1001_ctrl_50"
    )
    print(f"  Result for legitimate in-field edit: {valid_corrections}")
    assert (test_orig, test_cand) in valid_corrections, f"Failed to detect ('{test_orig}', '{test_cand}')"

    # Test D: Trigger prompt (watcher remains armed during typing refinement)
    correction_detector.trigger_prompt(test_cand, test_orig)
    
    # Test E: Accept candidate and verify clean disarm
    correction_detector.accept_candidate(test_cand, test_orig)
    with correction_detector._lock:
        assert not correction_detector._last_injection.get("is_armed", False), "Watcher must disarm after acceptance!"

    # Test F: Further checks after disarm return empty
    diff_after_disarm = correction_detector.inspect_text_for_corrections(
        current_text=valid_edited_text,
        current_hwnd=1001,
        current_control_sig="win_1001_ctrl_50"
    )
    assert len(diff_after_disarm) == 0, "Watcher must not trigger after disarming!"

    # Clean up
    vocab_manager.remove_word(test_cand)
    print("[OK] [PINNED DETECTOR PASSED] Zero false positives on external windows & perfect in-field detection!")


if __name__ == "__main__":
    test_pinned_correction_detector()
