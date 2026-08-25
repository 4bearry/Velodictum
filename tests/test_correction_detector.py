"""
Velodictum - Strict In-Field Correction Detector Verification Suite
Verifies:
1. In-field manual edit detection:
   - Injected: "In Wonderland there is Bobbert."
   - User edits field to: "In Wonderland there is Bawbert."
   -> Detects ('Bobbert' -> 'Bawbert')
2. Prevents prompts when no word was replaced
3. Interactive prompt trigger & acceptance into vocabulary
4. Ingestion into Whisper Prompt Injection
"""
from correction_detector import correction_detector
from custom_vocabulary import vocab_manager


def test_correction_detector_suite():
    print("--- TEST: Strict In-Field Correction Detector ---")

    test_cand = "Bawbert"
    test_orig = "Bobbert"

    vocab_manager.remove_word(test_cand)

    # 1. In-Field Manual Edit Test
    injected_text = f"In Wonderland there is {test_orig}."
    correction_detector.record_injection(injected_text)
    edited_text = f"In Wonderland there is {test_cand}."
    infield_corrections = correction_detector.inspect_text_for_corrections(edited_text)
    print(f"  In-field detected corrections: {infield_corrections}")
    assert (test_orig, test_cand) in infield_corrections, f"Failed to detect in-field ('{test_orig}', '{test_cand}')"

    # 2. Verify NO prompt when text is unchanged
    same_text = f"In Wonderland there is {test_orig}."
    no_corrections = correction_detector.inspect_text_for_corrections(same_text)
    assert len(no_corrections) == 0, f"Expected no corrections for identical text, got: {no_corrections}"

    # 3. Accept Candidate Word into Dictionary
    accepted = correction_detector.accept_candidate(test_cand, test_orig)
    assert accepted, "Failed to accept candidate word"

    # 4. Verify Whisper Prompt Injection
    prompt_inj = vocab_manager.get_prompt_injection("de")
    print(f"  Whisper Prompt Injection: {prompt_inj}")
    assert test_cand in prompt_inj, f"'{test_cand}' must be in Whisper prompt injection"

    # Clean up test word
    vocab_manager.remove_word(test_cand)

    print("[OK] [CORRECTION SUITE PASSED] Strict in-field correction detection verified!")


if __name__ == "__main__":
    test_correction_detector_suite()
