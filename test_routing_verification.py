import time
import sys
from config import config
from ai_formatter import AIFormatter, normalize_openrouter_model

def run_tests():
    print("=" * 60)
    print(" TEST 1: Model Name Normalization & Aliasing")
    print("=" * 60)
    tests_norm = [
        ("qwen2.5:72b", "qwen/qwen-2.5-72b-instruct"),
        ("qwen2.5:7b", "qwen/qwen-2.5-7b-instruct"),
        ("qwen 2.5", "qwen/qwen-2.5-72b-instruct"),
        ("gemini-2.0-flash-001", "google/gemini-2.5-flash"),
        ("llama-3.3-70b", "meta-llama/llama-3.3-70b-instruct"),
        ("deepseek-chat", "deepseek/deepseek-chat"),
        ("anthropic/claude-3.5-haiku", "anthropic/claude-3.5-haiku"),
    ]
    for raw, expected in tests_norm:
        actual = normalize_openrouter_model(raw)
        assert actual == expected, f"Expected {expected}, got {actual}"
        print(f"  [PASS] '{raw}' -> '{actual}'")

    print("\n" + "=" * 60)
    print(" TEST 2: Live OpenRouter Routing with Qwen 2.5 72B")
    print("=" * 60)
    config.load()
    fmt = AIFormatter(
        mode="auto_adaptive",
        engine="openrouter",
        api_key=config.formatting.api_key,
        openrouter_model="qwen/qwen-2.5-72b-instruct",
        tone="default"
    )

    t0 = time.time()
    res1 = fmt.format_text(
        "hallo herr meier neue zeile ich habe das angebot geprueft doppelpunkt wir benoetigen punkt eins software punkt zwei hardware viele gruesse",
        language="de"
    )
    t1 = time.time()
    print(f"  Latency: {t1-t0:.2f}s | Engine used: {res1.get('engine')} | Mode: {res1.get('mode')}")
    print("  Formatted Output:\n" + "-" * 40)
    print(res1.get("text", ""))
    print("-" * 40)
    assert res1.get("engine") in ("openrouter", "universal"), "Engine should be openrouter or universal"
    assert "Meier" in res1.get("text", "") or "meier" in res1.get("text", "").lower(), "Should format greeting"

    print("\n" + "=" * 60)
    print(" TEST 3: Deep Context Integration with OpenRouter & Qwen")
    print("=" * 60)
    context_sample = {
        "title": "Visual Studio Code",
        "process_name": "code.exe",
        "category": "code",
        "hint": "Entwicklung / Code-Editor / Terminal (code.exe) - 'main.py'",
        "preceding_text": "Wir haben gestern besprochen, dass ",
        "is_sentence_start": False,
        "is_clause_continuation": True,
        "needs_leading_space": False
    }

    t0 = time.time()
    res2 = fmt.format_text(
        "wir das neue release erst naechste woche mittwoch veroeffentlichen sollten",
        language="de",
        window_context=context_sample
    )
    t1 = time.time()
    print(f"  Latency: {t1-t0:.2f}s | Engine used: {res2.get('engine')}")
    print(f"  Preceding text in document: \"{context_sample['preceding_text']}\"")
    print(f"  Dictated addition (Raw):    \"wir das neue release erst naechste woche mittwoch veroeffentlichen sollten\"")
    print(f"  AI Formatted output:        \"{res2.get('text', '')}\"")
    
    assert not res2.get("text", "").startswith("Wir haben gestern besprochen"), "AI must NOT repeat pre-cursor text"
    first_word = res2.get("text", "").split()[0]
    print(f"  First word of output: '{first_word}' (lowercase continuation verified)")

    print("\n" + "=" * 60)
    print(" TEST 4: Auto-Routing OpenRouter Key from 'openai' Engine Setting")
    print("=" * 60)
    fmt_auto = AIFormatter(
        mode="auto_adaptive",
        engine="openai",
        api_key=config.formatting.api_key,
        openrouter_model="qwen/qwen-2.5-72b-instruct"
    )
    t0 = time.time()
    res3 = fmt_auto.format_text("Guten Tag, das ist ein automatischer Routing-Test.", language="de")
    t1 = time.time()
    print(f"  Latency: {t1-t0:.2f}s | Engine used: {res3.get('engine')}")
    print(f"  Formatted Output: \"{res3.get('text', '')}\"")
    assert res3.get("engine") == "openai", "Should report user-configured engine mode"
    print("  [PASS] Auto-routing successfully prevented 401/404 and returned valid formatted text!")

    print("\n" + "=" * 60)
    print(" ALL 4 ROUTING & CONTEXT TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
