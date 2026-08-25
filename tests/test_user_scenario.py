"""
Velodictum - Exact User Scenario Verification Suite
Scenario:
- Velodictum injects: "In Zootopia gibt es zum Beispiel einen Lux namens Powert."
- User manually changes "Powert" -> "Pawbert" in their text field.
- Detector identifies ("Powert" -> "Pawbert") and triggers the prompt!
"""
from correction_detector import correction_detector
from custom_vocabulary import vocab_manager


def test_user_powert_to_pawbert_scenario():
    print("--- TEST: User Scenario 'Powert' -> 'Pawbert' ---")

    # 1. Clear any prior test state
    vocab_manager.remove_word("Pawbert")
    correction_detector._prompted_timestamps.clear()

    # 2. Simulate injection
    injected = "In Zootopia gibt es zum Beispiel einen Lux namens Powert."
    correction_detector.record_injection(injected)

    # 3. Simulate user in text field editing 'Powert' to 'Pawbert'
    user_edited = "In Zootopia gibt es zum Beispiel einen Lux namens Pawbert."
    corrections = correction_detector.inspect_text_for_corrections(user_edited)
    print(f"  Detected In-Field corrections: {corrections}")

    assert ("Powert", "Pawbert") in corrections, f"Failed to detect ('Powert', 'Pawbert'). Got: {corrections}"

    # 4. Accept candidate
    ok = correction_detector.accept_candidate("Pawbert", "Powert")
    assert ok, "Failed to accept candidate"

    # 5. Verify Prompt Injection
    prompt = vocab_manager.get_prompt_injection("de")
    print(f"  Updated Whisper Prompt Injection: {prompt}")
    assert "Pawbert" in prompt

    print("[OK] [USER SCENARIO PASSED] 'Powert' -> 'Pawbert' live correction detection verified!")


if __name__ == "__main__":
    test_user_powert_to_pawbert_scenario()
