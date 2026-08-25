"""
Velodictum - Intelligent Proper-Noun Vocabulary Learning Test Suite
Verifies:
1. Extraction and auto-learning of proper nouns from user corrections (e.g., 'Leon' -> 'Léon').
2. Learning of technical mixed-case / camelCase terms (e.g., 'chatgpt' -> 'ChatGPT').
3. Multi-word phrase name corrections (e.g., 'Herr Muller' -> 'Herr Müller').
4. Prevention of stopword pollution (e.g. 'und', 'aber', 'der').
5. Prompt injection of learned proper nouns into Whisper decoding.
"""
from custom_vocabulary import vocab_manager


def test_proper_noun_learning():
    print("--- TEST: Intelligent Proper-Noun Vocabulary Learning ---")

    # 1. Test accent name correction: 'Leon' -> 'Léon'
    learned = vocab_manager.learn_correction("Hallo Leon wie geht es dir", "Hallo Léon wie geht es dir")
    print(f"  Learned for 'Leon' -> 'Léon': {learned}")
    assert "Léon" in learned, "Failed to learn accented name 'Léon'"

    # 2. Test German umlaut name correction: 'Frau Muller' -> 'Frau Müller'
    learned_umlaut = vocab_manager.learn_correction("Frau Muller kommt morgen", "Frau Müller kommt morgen")
    print(f"  Learned for 'Muller' -> 'Müller': {learned_umlaut}")
    assert "Müller" in learned_umlaut, "Failed to learn umlaut name 'Müller'"

    # 3. Test CamelCase technical name correction: 'chat gpt' -> 'ChatGPT'
    learned_tech = vocab_manager.learn_correction("mit chat gpt und velodictum", "mit ChatGPT und Velodictum")
    print(f"  Learned for tech terms: {learned_tech}")
    assert "ChatGPT" in learned_tech, "Failed to learn 'ChatGPT'"

    # 4. Verify that common German words are NOT learned as proper nouns
    learned_stop = vocab_manager.learn_correction("wir gehen heute", "wir gehen aber heute nicht")
    print(f"  Learned for common words: {learned_stop}")
    assert "aber" not in learned_stop and "nicht" not in learned_stop, "Stopwords must not be learned"

    # 5. Verify Prompt Injection
    inj = vocab_manager.get_prompt_injection("de")
    print(f"  Whisper Prompt Injection: {inj}")
    assert "Léon" in inj, "Learned term 'Léon' must be present in Whisper prompt injection"
    assert "Müller" in inj, "Learned term 'Müller' must be present in Whisper prompt injection"

    # Clean up test terms
    vocab_manager.remove_word("Léon")
    vocab_manager.remove_word("Müller")
    vocab_manager.remove_word("ChatGPT")

    print("[OK] [PROPER-NOUN LEARNING TEST PASSED] Correction learning and Whisper prompt injection verified!")


if __name__ == "__main__":
    test_proper_noun_learning()
