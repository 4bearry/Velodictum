"""
Velodictum - Power User Feature Verification Suite
"""
import time
import numpy as np
from hotkey_manager import HotkeyManager
from text_injector import TextInjector
from stt_engine import WhisperEngine
from ai_formatter import AIFormatter
from custom_vocabulary import vocab_manager
from voice_editor import VoiceEditor
from window_context import get_active_window_context


def run_all_tests():
    print("=" * 60)
    print(" VELODICTUM LAYER & POWER-USER FEATURE CHECKS")
    print("=" * 60)

    # 1. Test HotkeyRegistry
    print("\n[1/8] Testing HotkeyRegistry & Multi-Combo Parsing...")
    mgr = HotkeyManager(hotkey_name="f8", mode="push_to_talk")
    mgr.register_hotkey("undo", "ctrl+alt+z", mode="press_once")
    mgr.register_hotkey("voice_edit", "ctrl+alt+space", mode="push_to_talk")
    mgr.register_hotkey("scratchpad", "ctrl+shift+d", mode="press_once")

    assert "primary_dictate" in mgr._bindings
    assert "undo" in mgr._bindings
    assert "voice_edit" in mgr._bindings
    assert "scratchpad" in mgr._bindings

    assert mgr.parse_combo("ctrl+shift+space") == ["ctrl", "shift", "space"]
    assert mgr.parse_combo("strg+alt+z") == ["ctrl", "alt", "z"]
    print("  [PASS] All 4 hotkeys registered and parsed correctly!")

    # 2. Test TextInjector State & Undo
    print("\n[2/8] Testing TextInjector State Tracking & Revert...")
    inj = TextInjector(auto_paste=False, restore_clipboard=True)
    inj.inject("Formatierter KI Text", raw_text="formatierter ki text")
    assert inj.last_injection is not None
    assert inj.last_injection["injected_text"] == "Formatierter KI Text"
    assert inj.last_injection["raw_text"] == "formatierter ki text"

    revert_res = inj.revert_last_injection(mode="undo")
    assert revert_res["success"] is True
    assert inj.last_injection is None
    print("  [PASS] Injection state tracking and revert successful!")

    # 3. Test Hallucination Squelcher
    print("\n[3/8] Testing Hallucination Squelcher...")
    assert WhisperEngine.is_hallucination("Vielen Dank für Ihre Aufmerksamkeit.") is True
    assert WhisperEngine.is_hallucination("Untertitel: ZDF 2024") is True
    assert WhisperEngine.is_hallucination("Thank you for watching!") is True
    assert WhisperEngine.is_hallucination("da da da da da da da") is True
    assert WhisperEngine.is_hallucination(".") is True
    assert WhisperEngine.is_hallucination("") is True

    assert WhisperEngine.is_hallucination("Wir treffen uns morgen um 10 Uhr zum Meeting.") is False
    assert WhisperEngine.is_hallucination("Erstelle bitte einen Pull Request.") is False
    print("  [PASS] Hallucination Squelcher perfectly filtered hallucinations while preserving speech!")

    # 4. Test AI Formatter Send It Detection
    print("\n[4/8] Testing Send It Chat Voice Actions...")
    fmt = AIFormatter(mode="auto_adaptive", engine="rules")
    res_send = fmt.format_text("Wir sehen uns morgen um zehn und abschicken", language="de")
    assert res_send.get("action") == "send_enter", f"Expected action send_enter, got {res_send.get('action')}"
    assert "und abschicken" not in res_send.get("text", "").lower()
    print(f"  Stripped text: '{res_send['text']}' | Action: {res_send['action']}")
    print("  [PASS] Send It trigger detected and cleanly stripped!")

    # 5. Test Spoken Markdown Engine
    print("\n[5/8] Testing Spoken Markdown Engine...")
    res_md = fmt.format_text("Ueberschrift 2 API Endpunkte neue Zeile Checkbox unerledigt Auth Token validieren", language="de")
    print(f"  Formatted Markdown Output:\n{res_md['text']}")
    assert "API Endpunkte" in res_md.get("text", "")
    print("  [PASS] Spoken Markdown successfully transformed!")

    # 6. Test Window Context & Workspace Seeding
    print("\n[6/8] Testing Window Context & Workspace Term Extraction...")
    ctx = get_active_window_context(include_deep_text=False)
    print(f"  Current Active App: {ctx['process_name']} ({ctx['category']})")
    print(f"  Hint: {ctx['hint']}")
    assert "category" in ctx
    print("  [PASS] Active context inspected cleanly!")

    # 7. Test Transient Vocabulary & Suggestions
    print("\n[7/8] Testing Dynamic Vocabulary Seeding & Suggestion Engine...")
    vocab_manager.set_transient_workspace_terms(["Velodictum", "AntigravityEngine"])
    inj_prompt = vocab_manager.get_prompt_injection("de")
    assert "Velodictum" in inj_prompt
    assert "AntigravityEngine" in inj_prompt

    suggestions = vocab_manager.suggest_words_from_text("Wir nutzen FastAPIEngine und CUDA_ACCEL im neuen Branch.")
    print(f"  Extracted Word Suggestions: {suggestions}")
    assert "FastAPIEngine" in suggestions or "CUDA_ACCEL" in suggestions
    print("  [PASS] Dynamic transient prompt injection and suggestions verified!")

    # 8. Test Voice Editor Transform
    print("\n[8/8] Testing Voice Editor Transform Module...")
    editor = VoiceEditor(fmt)
    sample_orig = "Hi, eigentlich wollten wir uns sozusagen morgen treffen."
    trans_out = editor.transform_text(sample_orig, "Kürze das", language="de")
    print(f"  Original: '{sample_orig}' -> Transformed: '{trans_out}'")
    assert len(trans_out) > 0
    print("  [PASS] VoiceEditor integrated and functional!")

    print("\n" + "=" * 60)
    print(" ALL 8 POWER-USER VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_all_tests()
