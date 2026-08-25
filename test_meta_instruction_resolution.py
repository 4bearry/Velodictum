"""
Velodictum - Verification Suite: Spoken Meta-Instruction & Sentence Filtering Resolution
Verifies:
1. Spoken filter directives with interjections ("A und streiche jeden Satz...", "Ah und lösche alles...")
2. Isolates and preserves only the target sentence
3. Drops all preamble sentences and the trailing directive itself
"""
from ai_formatter import AIFormatter


def test_meta_instructions():
    print("--- TEST: Spoken Meta-Instruction & Sentence Filtering ---")

    formatter = AIFormatter(mode="flow", engine="rules")

    # Case 1: Exact user test scenario with 'A und streiche...'
    raw_1 = (
        "Ich zeige dir mal jetzt zum Beispiel einen Satz, den ich mir ausgedacht habe, "
        "der sehr gut fürs Testen ist, für die Funktion, die ich gerade habe. "
        "Und zwar in Zootopia gibt es ein Lux namens PopWord. A und streiche jeden Satz außer den mit dem Lux."
    )
    res_1 = formatter.format_text(raw_1, language="de")
    print(f"  Result 1: {repr(res_1['text'])}")
    assert "in Zootopia" in res_1["text"]
    assert "Ich zeige dir mal" not in res_1["text"]
    assert "streiche jeden Satz" not in res_1["text"]

    # Case 2: Variant with 'Ah und lösche alle Sätze außer...'
    raw_2 = (
        "Hier ist der erste Entwurf für die Notiz. "
        "Das Projekt Velodictum läuft auf voller Leistung. "
        "Ah und lösche jeden Satz außer den mit dem Projekt."
    )
    res_2 = formatter.format_text(raw_2, language="de")
    print(f"  Result 2: {repr(res_2['text'])}")
    assert "Velodictum" in res_2["text"]
    assert "erste Entwurf" not in res_2["text"]

    # Case 3: Variant with 'Aber behalte nur den Satz mit...'
    raw_3 = (
        "Das war ein Test. Hier kommt die eigentliche Nachricht an Michael. "
        "Aber behalte nur den Satz mit Michael."
    )
    res_3 = formatter.format_text(raw_3, language="de")
    print(f"  Result 3: {repr(res_3['text'])}")
    assert "Michael" in res_3["text"]
    assert "Test" not in res_3["text"]

    print("[OK] [META-INSTRUCTIONS PASSED] Spoken editing and sentence filtering verified!")


if __name__ == "__main__":
    test_meta_instructions()
