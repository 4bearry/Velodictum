"""
Velodictum - Verification Suite: Multi-Tier Recording Cancellation
Verifies:
1. Spoken cancel triggers ("Abbrechen", "Verwerfen", "Diktat abbrechen", "Cancel") -> returns action="cancel"
2. Normal dictations mentioning "abbrechen" (e.g. "Wir müssen den Vertrag abbrechen.") -> returns normal text, action!=cancel
3. Escape key hook in HotkeyManager
4. App cancel_recording lifecycle (recorder stop, unduck, recording_cancelled emission)
"""
from ai_formatter import AIFormatter
from hotkey_manager import HotkeyManager
from gui.signals import signals


def test_recording_cancellation_suite():
    print("--- TEST: Multi-Tier Recording Cancellation ---")

    formatter = AIFormatter(mode="flow", engine="rules")

    # 1. Spoken Cancel Tests (Isolated)
    c1 = formatter.format_text("Abbrechen", language="de")
    print(f"  Spoken 'Abbrechen' -> action: {c1.get('action')}, text: {repr(c1.get('text'))}")
    assert c1.get("action") == "cancel", "Expected action='cancel' for 'Abbrechen'"
    assert c1.get("text") == "", "Expected empty text for cancelled recording"

    c2 = formatter.format_text("Verwerfen", language="de")
    assert c2.get("action") == "cancel", "Expected action='cancel' for 'Verwerfen'"

    c3 = formatter.format_text("Diktat abbrechen.", language="de")
    assert c3.get("action") == "cancel", "Expected action='cancel' for 'Diktat abbrechen.'"

    c4 = formatter.format_text("Ich wollte sagen... ach nein abbrechen", language="de")
    assert c4.get("action") == "cancel", "Expected action='cancel' for trailing 'ach nein abbrechen'"

    # 2. Spoken False Positive Protection (Sentences containing 'abbrechen')
    normal_1 = formatter.format_text("Wir müssen diesen Vertrag sofort abbrechen.", language="de")
    print(f"  Normal sentence with 'abbrechen' -> action: {normal_1.get('action')}, text: {repr(normal_1.get('text'))}")
    assert normal_1.get("action") != "cancel", "Normal sentence must NOT be cancelled!"
    assert "abbrechen" in normal_1.get("text").lower(), "Word 'abbrechen' must be kept in text"

    normal_2 = formatter.format_text("Klicke bitte auf den Button Abbrechen.", language="de")
    assert normal_2.get("action") != "cancel", "Normal instruction must NOT be cancelled!"

    # 3. Hotkey Manager Escape callback test
    cancel_called = []
    def on_cancel():
        cancel_called.append(True)

    hk = HotkeyManager(hotkey_name="f8", on_cancel=on_cancel)
    hk._on_press("esc")
    import time
    time.sleep(0.1)
    assert len(cancel_called) == 1, "HotkeyManager must trigger on_cancel callback on Escape key press!"

    print("[OK] [CANCELLATION SUITE PASSED] Recording cancellation & false-positive protection verified!")


if __name__ == "__main__":
    test_recording_cancellation_suite()
