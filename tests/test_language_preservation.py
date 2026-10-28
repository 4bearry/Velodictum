import pytest
from ai_formatter import AIFormatter

def test_ai_formatter_prompt_english_directive():
    formatter = AIFormatter()
    
    # Test that prompts strictly enforce zero-translation and output in spoken language
    prompt_en = formatter._build_system_prompt(language="en", window_context=None)
    assert "ZERO TRANSLATION" in prompt_en
    assert "ABSOLUTE SPRACHTREUE" in prompt_en
    assert "NIEMALS ins Deutsche übersetzen" in prompt_en
    assert "Can you please review the latest pull request" in prompt_en

    prompt_de = formatter._build_system_prompt(language="de", window_context=None)
    assert "ZERO TRANSLATION" in prompt_de
    assert "ABSOLUTE SPRACHTREUE" in prompt_de

def test_ai_formatter_user_message_format():
    formatter = AIFormatter()
    user_msg = formatter._build_user_message("This is a test transcription.")
    assert "<diktat>" in user_msg
    assert "This is a test transcription." in user_msg
    assert "Originalsprache" in user_msg

def test_structure_notes_language_preservation():
    formatter = AIFormatter()
    notes_en = "Project sync notes. Action item one: update dependencies. Action item two: write documentation."
    structured = formatter._structure_with_rules(notes_en)
    assert "Project sync notes" in structured
