"""
Velodictum - Functional Test Suite
Verifies:
1. Spoken Language Preservation (English stays English, German stays German)
2. Zero Unwanted Translation (Flow Layer never translates without Transform)
3. Anti-Answering & Meta-Prompt Protection
4. Spoken Markdown & Self-Correction Resolution
5. Deep Cursor Context & Case Adaptation
"""
import sys
import os

# Ensure project root & core in path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))
sys.path.insert(1, os.path.join(os.path.dirname(__file__), ".."))

from ai_formatter import AIFormatter

def run_functional_tests():
    print("=" * 65)
    print(" VELODICTUM - FUNCTIONAL FLOW LAYER & ZERO-TRANSLATION TESTS")
    print("=" * 65)

    formatter = AIFormatter(mode="auto_adaptive", engine="rules")

    # -------------------------------------------------------------
    # Test 1: Spoken Language Preservation in System Prompt
    # -------------------------------------------------------------
    print("\n[TEST 1] Verifying System Prompt Language & Zero-Translation Directives...")
    prompt_en = formatter._build_system_prompt("en", None)
    prompt_de = formatter._build_system_prompt("de", None)

    assert "ZERO TRANSLATION" in prompt_en, "System prompt must contain ZERO TRANSLATION directive"
    assert "ABSOLUTE SPRACHTREUE" in prompt_en, "System prompt must contain ABSOLUTE SPRACHTREUE rule"
    assert "NIEMALS ins Deutsche übersetzen" in prompt_en, "System prompt must explicitly forbid German translation on English input"
    assert "ZERO TRANSLATION" in prompt_de, "German prompt must also enforce ZERO TRANSLATION"
    print("  -> PASSED: Strict Zero-Translation directives verified in system prompts.")

    # -------------------------------------------------------------
    # Test 2: User Message Delimiter Framing
    # -------------------------------------------------------------
    print("\n[TEST 2] Verifying User Message XML Framing & Output Instruction...")
    user_msg_en = formatter._build_user_message("Can you please review this code?")
    assert "<diktat>" in user_msg_en and "</diktat>" in user_msg_en, "XML task delimiter tags missing"
    assert "Can you please review this code?" in user_msg_en
    assert "Originalsprache" in user_msg_en, "User message must remind model of original spoken language"
    print("  -> PASSED: XML framing and language-preservation output trailer verified.")

    # -------------------------------------------------------------
    # Test 3: English Spoken Diktat Formatting (Rule Engine Fallback)
    # -------------------------------------------------------------
    print("\n[TEST 3] Testing English Spoken Diktat & Spoken Markdown Formatting...")
    raw_en_md = "heading 2 Project Status. new line. checkbox pending implement audio ducking."
    res_en_md = formatter.format_text(raw_en_md, language="en")
    print(f"  Input:  '{raw_en_md}'")
    print(f"  Output:\n{res_en_md['text']}")
    assert "## Project Status" in res_en_md["text"], "Heading 2 markdown failed"
    assert "- [ ]" in res_en_md["text"], "Checkbox pending markdown failed"
    assert "implement audio ducking" in res_en_md["text"], "English wording must remain in English"
    print("  -> PASSED: English spoken markdown correctly formatted in English.")

    # -------------------------------------------------------------
    # Test 4: English Spoken Self-Correction
    # -------------------------------------------------------------
    print("\n[TEST 4] Testing English Self-Correction Resolution...")
    raw_en_corr = "We will release on Friday, actually no, on next Monday."
    res_en_corr = formatter.format_text(raw_en_corr, language="en")
    print(f"  Input:  '{raw_en_corr}'")
    print(f"  Output: '{res_en_corr['text']}'")
    assert "actually no" not in res_en_corr["text"].lower(), "Self-correction signal not stripped"
    assert "on next Monday" in res_en_corr["text"], "Target corrected phrase missing"
    print("  -> PASSED: English self-correction resolved without translation.")

    # -------------------------------------------------------------
    # Test 5: German Spoken Diktat with English Tech Terminology
    # -------------------------------------------------------------
    print("\n[TEST 5] Testing German Diktat with English Developer Terminology...")
    raw_de_tech = "Erstelle einen neuen Pull Request und deploye das Backend auf AWS."
    res_de_tech = formatter.format_text(raw_de_tech, language="de")
    print(f"  Input:  '{raw_de_tech}'")
    print(f"  Output: '{res_de_tech['text']}'")
    assert "Pull Request" in res_de_tech["text"] or "pull request" in res_de_tech["text"].lower()
    assert "Backend" in res_de_tech["text"] or "backend" in res_de_tech["text"].lower()
    assert "deploy" in res_de_tech["text"].lower()
    print("  -> PASSED: Technical English keywords preserved in German context.")

    # -------------------------------------------------------------
    # Test 6: Deep Cursor Context & Mid-Sentence Lowercase Continuation
    # -------------------------------------------------------------
    print("\n[TEST 6] Testing Deep Context Mid-Sentence Continuation...")
    cursor_ctx = {
        "preceding_text": "We noticed that ",
        "is_sentence_start": False,
        "is_clause_continuation": True,
        "category": "code",
    }
    raw_continuation = "the latency increases after five minutes"
    res_cont = formatter.format_text(raw_continuation, language="en", window_context=cursor_ctx)
    print(f"  Preceding: '{cursor_ctx['preceding_text']}'")
    print(f"  Input:     '{raw_continuation}'")
    print(f"  Output:    '{res_cont['text']}'")
    assert res_cont["text"].startswith("the"), "Mid-sentence continuation must remain lowercase"
    print("  -> PASSED: Cursor context respected seamlessly.")

    # -------------------------------------------------------------
    # Test 7: Dedicated Note & Memo Structuring Language Preservation
    # -------------------------------------------------------------
    print("\n[TEST 7] Testing Scratchpad / Diktierbuch Note Structuring...")
    raw_notes_en = "Sprint goals. Todo: run benchmarks. Todo: update release notes."
    res_notes_en = formatter.structure_notes(raw_notes_en, language="en")
    print(f"  Input:  '{raw_notes_en}'")
    print(f"  Output:\n{res_notes_en}")
    assert "Sprint goals" in res_notes_en
    assert "- Todo: update release notes" in res_notes_en or "- run benchmarks" in res_notes_en or "update release notes" in res_notes_en
    print("  -> PASSED: Scratchpad note structuring preserves input language.")

    print("\n" + "=" * 65)
    print(" ALL 7 FUNCTIONAL TESTS PASSED SUCCESSFULLY (100% GREEN)!")
    print("=" * 65)

if __name__ == "__main__":
    run_functional_tests()
