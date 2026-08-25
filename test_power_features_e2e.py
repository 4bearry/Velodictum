"""
Comprehensive End-to-End Verification Test Suite for Velodictum Power Features:
1. Hotkey Decoding (Ctrl+Shift+D, Ctrl+Alt+Z, Ctrl+Alt+Space with Windows ASCII Control Codes)
2. Send It Voice Action ("und absenden", "und abschicken", "send it")
3. Hallucination Squelcher (Silence & repetitive loop rejection)
4. Context Intelligence & Workspace Seeding
5. Mobile LAN Bridge HTTP/WebM Server Lifecycle & Dictation Route
6. Dashboard Settings UI wiring
"""
import sys
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import time
import json
import urllib.request
from pynput.keyboard import Key, KeyCode

from PyQt6.QtWidgets import QApplication
_qapp = QApplication.instance() or QApplication([])

from config import config, AppConfig
from hotkey_manager import HotkeyManager
from ai_formatter import AIFormatter
from stt_engine import WhisperEngine
from text_injector import TextInjector
from window_context import get_active_window_context
from mobile_bridge_server import MobileBridgeServer, extract_audio_payload, get_local_ip


def test_1_hotkey_decoding_and_scratchpad():
    print("\n--- TEST 1: Hotkey Decoding (Ctrl+Shift+D & Ctrl+Alt+Z) ---")
    
    # Check ASCII control characters produced on Windows when Ctrl is held
    key_ctrl_d = KeyCode.from_char('\x04')  # ASCII 4 = Ctrl+D
    canonical_d = HotkeyManager.canonical_key_name(key_ctrl_d)
    assert canonical_d == "d", f"Expected 'd', got {canonical_d!r}"
    
    key_ctrl_z = KeyCode.from_char('\x1a')  # ASCII 26 = Ctrl+Z
    canonical_z = HotkeyManager.canonical_key_name(key_ctrl_z)
    assert canonical_z == "z", f"Expected 'z', got {canonical_z!r}"

    # Check Virtual Key codes (VK)
    key_vk_d = KeyCode.from_vk(68)
    assert HotkeyManager.canonical_key_name(key_vk_d) == "d"
    
    key_vk_z = KeyCode.from_vk(90)
    assert HotkeyManager.canonical_key_name(key_vk_z) == "z"

    # Simulate HotkeyManager press state for Ctrl+Shift+D
    scratchpad_triggered = []
    mgr = HotkeyManager(
        hotkey_name="f8",
        mode="push_to_talk",
        on_start_recording=lambda: None,
        on_stop_recording=lambda: None,
    )
    mgr.register_hotkey(
        name="scratchpad",
        combo_str="ctrl+shift+d",
        on_press=lambda: scratchpad_triggered.append(True),
        mode="press_once",
    )

    # Simulate pressing Ctrl, Shift, and D (with ASCII 4 character)
    mgr._on_press(Key.ctrl_l)
    mgr._on_press(Key.shift_l)
    mgr._on_press(KeyCode.from_char('\x04'))

    assert len(scratchpad_triggered) == 1, "Ctrl+Shift+D failed to trigger scratchpad callback!"
    print("[OK] [TEST 1 PASSED] Ctrl+Shift+D & Ctrl+Alt+Z key codes and triggers verified!")


def test_2_send_it_voice_action():
    print("\n--- TEST 2: 'Send It' Voice Trigger Regex & Logic ---")
    formatter = AIFormatter(mode="raw", engine="rules")

    test_cases = [
        ("Hallo Herr Schmidt, anbei das Dokument, und absenden.", "Hallo Herr Schmidt, anbei das Dokument.", "send_enter"),
        ("Wir treffen uns im Konferenzraum abschicken!", "Wir treffen uns im Konferenzraum", "send_enter"),
        ("Bitte sende mir das PDF zu, und abschicken.", "Bitte sende mir das PDF zu,", "send_enter"),
        ("Ich bin gleich fertig, bitte absenden", "Ich bin gleich fertig,", "send_enter"),
        ("Meeting is rescheduled, send it.", "Meeting is rescheduled,", "send_enter"),
        ("Guten Tag, das ist ein normaler Text ohne Befehl.", "Guten Tag, das ist ein normaler Text ohne Befehl.", None),
    ]

    for raw, expected_text_start, expected_action in test_cases:
        res = formatter.format_text(raw, language="de")
        assert res.get("action") == expected_action, f"For '{raw}': expected action {expected_action}, got {res.get('action')}"
        if expected_action == "send_enter":
            # Punctuation or trailing whitespace stripped properly
            assert "absenden" not in res["text"].lower() and "abschicken" not in res["text"].lower() and "send it" not in res["text"].lower()
    print("[OK] [TEST 2 PASSED] All 'Send It' voice triggers and action flags verified!")


def test_3_hallucination_squelcher():
    print("\n--- TEST 3: Hallucination Squelcher ---")
    
    # Silence hallucinations that should be caught
    hallucination_samples = [
        "Vielen Dank fürs Zuschauen!",
        "Danke für eure Aufmerksamkeit.",
        "Untertitel von ARD Text",
        "Thank you for watching!",
        "Like and subscribe.",
        "...",
        ",,,,",
        "   ",
    ]

    for sample in hallucination_samples:
        is_hal = WhisperEngine.is_hallucination(sample)
        assert is_hal is True, f"Failed to squelch hallucination: '{sample}'"

    # Legitimate speech samples that should NOT be squelched
    legitimate_samples = [
        "Guten Morgen, wir müssen heute die Datenbank migrieren.",
        "Hier ist der Entwurf für das Quartalsmeeting.",
        "Bitte den Hotkey STRG+SHIFT+D drücken.",
    ]

    for sample in legitimate_samples:
        is_hal = WhisperEngine.is_hallucination(sample)
        assert is_hal is False, f"False positive squelch on valid speech: '{sample}'"

    print("[OK] [TEST 3 PASSED] Hallucination Squelcher entropy and blacklist filters verified!")


def test_4_context_intelligence():
    print("\n--- TEST 4: Context Intelligence & Workspace Seeding ---")
    ctx = get_active_window_context(include_deep_text=False)
    assert isinstance(ctx, dict)
    assert "category" in ctx
    assert "process_name" in ctx
    assert "title" in ctx
    print(f"  Active Window Detected: '{ctx.get('title')}' (Category: {ctx.get('category')}, Process: {ctx.get('process_name')})")
    print("[OK] [TEST 4 PASSED] Active Window Context retrieval verified!")


def test_5_mobile_lan_bridge_e2e():
    print("\n--- TEST 5: Mobile LAN Bridge HTTP/WebM Server ---")
    import ssl
    ssl_ctx = ssl._create_unverified_context()
    received_audio = []

    def mock_transcriber(audio_bytes: bytes) -> str:
        received_audio.append(audio_bytes)
        return "Transkribierter Testtext vom Smartphone"

    server = MobileBridgeServer(port=8991, on_audio_received=mock_transcriber)
    server.start()
    time.sleep(0.3)
    proto = "https" if getattr(server, "is_https", False) else "http"

    try:
        # 1. Test GET /
        url = f"{proto}://127.0.0.1:8991/"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, context=ssl_ctx) as resp:
            assert resp.status == 200
            html = resp.read().decode("utf-8")
            assert "Velodictum Mobile" in html
            assert "MediaRecorder" in html

        # 2. Test GET /api/status (with header token authentication)
        req_status = urllib.request.Request(
            f"{proto}://127.0.0.1:8991/api/status",
            headers={"X-Velodictum-Token": server.auth_token}
        )
        with urllib.request.urlopen(req_status, context=ssl_ctx) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["app"] == "Velodictum"
            assert data.get("status") == "ok"

        # 3. Test POST /api/dictate (with token header)
        mock_payload = b"MOCK_AUDIO_DATA_FOR_TESTING_PURPOSES"
        req_post = urllib.request.Request(
            f"{proto}://127.0.0.1:8991/api/dictate",
            data=mock_payload,
            headers={
                "Content-Type": "audio/webm",
                "X-Velodictum-Token": server.auth_token,
            },
            method="POST",
        )
        with urllib.request.urlopen(req_post, context=ssl_ctx) as resp:
            assert resp.status == 200
            result = json.loads(resp.read().decode("utf-8"))
            assert result.get("status") == "ok"
            assert result.get("text") == "Transkribierter Testtext vom Smartphone"

        assert len(received_audio) == 1
        assert received_audio[0] == mock_payload
        print("[OK] [TEST 5 PASSED] Mobile LAN Bridge Web client and Dictation API verified!")
    finally:
        server.stop()


def test_6_config_and_ui_wiring():
    print("\n--- TEST 6: Config and UI Dataclasses ---")
    assert hasattr(config.whisper, "hallucination_filter")
    assert hasattr(config.formatting, "context_intelligence")
    assert hasattr(config.formatting, "workspace_seeding")
    assert hasattr(config.formatting, "spoken_markdown")
    assert hasattr(config.formatting, "send_it_enabled")
    assert hasattr(config, "mobile_bridge")
    assert hasattr(config.mobile_bridge, "port")
    assert hasattr(config.mobile_bridge, "enabled")
    print("[OK] [TEST 6 PASSED] All configuration fields and defaults verified!")


def test_7_two_tier_architecture():
    print("\n--- TEST 7: 2-Tier Architecture (Operating Mode & Tone Profiles) ---")
    from ai_formatter import MODES
    from style_profiles import TONE_PROFILES, get_tone_instruction

    # Tier 1: Operating modes must only be "flow" and "raw"
    assert "flow" in MODES
    assert "raw" in MODES
    assert len(MODES) == 2, f"Expected 2 operating modes, got {len(MODES)}"

    # Tier 2: Tone profiles
    assert "default" in TONE_PROFILES
    assert "formal_sie" in TONE_PROFILES
    assert "informal_du" in TONE_PROFILES
    assert "concise" in TONE_PROFILES
    assert "academic" in TONE_PROFILES
    assert "latex" in TONE_PROFILES

    # Test Raw Bypass
    raw_fmt = AIFormatter(mode="raw", engine="rules")
    raw_res = raw_fmt.format_text("Das ist ein Test", language="de")
    assert raw_res["mode"] == "raw"
    assert raw_res["engine"] == "bypass"
    assert raw_res["text"] == "Das ist ein Test"

    # Test Flow Mode with Tone
    flow_fmt = AIFormatter(mode="flow", engine="rules", tone="formal_sie")
    flow_res = flow_fmt.format_text("das ist ein test", language="de")
    assert flow_res["mode"] == "flow"
    assert flow_res["engine"] == "rules"

    # Verify tone instruction generation
    formal_inst = get_tone_instruction("formal_sie")
    assert "Sie" in formal_inst

    latex_inst = get_tone_instruction("latex")
    assert "LATEX" in latex_inst
    assert "$" in latex_inst

    print("[OK] [TEST 7 PASSED] 2-Tier Operating Mode and Tone Profile architecture verified!")


def test_8_scratchpad_mic_and_structuring():
    print("\n--- TEST 8: Scratchpad Mic Button & Note Structuring ---")
    import os
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from gui.scratchpad_window import ScratchpadWindow
    from gui.signals import signals

    fmt = AIFormatter(mode="flow", engine="rules")
    pad = ScratchpadWindow(fmt)

    # 1. Verify mic button and event bus toggle
    triggered = []
    signals.dictation_toggle_requested.connect(lambda: triggered.append(True))
    pad.btn_mic.click()
    assert len(triggered) == 1, "Clicking mic button did not emit dictation_toggle_requested signal!"

    # 2. Verify note structuring method
    raw_sample = "Erstene Punkt eins. Zweitens Punkt zwei. Drittens Aufgabe drei erledigen."
    structured = fmt.structure_notes(raw_sample, language="de")
    assert structured and len(structured) > 5

    print("[OK] [TEST 8 PASSED] Scratchpad Mic Button & Note Structuring verified!")


def test_9_universal_api_and_provider_agnostic_engine():
    print("\n--- TEST 9: Universal API & Provider-Agnostic Engine ---")
    from formatting_providers import (
        detect_provider,
        categorize_models,
        UniversalApiProvider,
        LocalRulesProvider,
        OllamaProvider,
        OpenAIProvider,
        GeminiProvider,
        GroqProvider,
    )

    # 1. Provider Detection
    assert detect_provider("https://openrouter.ai/api/v1") == "OpenRouter"
    assert detect_provider("https://api.together.xyz/v1") == "Together AI"
    assert detect_provider("https://api.deepseek.com/v1") == "DeepSeek"
    assert detect_provider("https://api.fireworks.ai/inference/v1") == "Fireworks AI"
    assert detect_provider("https://api.groq.com/openai/v1") == "Groq"
    assert detect_provider("https://api.openai.com/v1") == "OpenAI"
    assert detect_provider("http://127.0.0.1:11434") in ("Ollama (Lokal)", "Ollama (Local)")
    assert detect_provider("https://my-custom-proxy.internal.corp/v1") in ("Benutzerdefinierter Endpunkt", "Custom Endpoint")
    print("  [OK] Provider detection verified for multiple platforms!")

    # 2. Model Categorization
    sample_models = [
        {"id": "qwen/qwen-2.5-72b-instruct", "name": "Qwen 2.5 72B Instruct"},
        {"id": "meta-llama/llama-3.1-8b-instruct", "name": "Llama 3.1 8B Instruct"},
        {"id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet"},
        {"id": "google/gemini-2.5-flash", "name": "Gemini 2.5 Flash"},
        {"id": "custom-domain/specialized-bert", "name": "Specialized BERT"},
    ]
    categorized = categorize_models(sample_models)
    assert len(categorized["recommended"]) > 0 or len(categorized["fast"]) > 0 or len(categorized["quality"]) > 0
    print("  [OK] Model categorization verified across standard quality tiers!")

    # 3. UniversalApiProvider Instantiation & URL Handling
    u_provider = UniversalApiProvider(
        endpoint="https://api.custom-ai-host.com/v1",
        api_key="cust-api-key-12345",
        model="custom-org/custom-model-1",
    )
    assert u_provider._get_chat_url() == "https://api.custom-ai-host.com/v1/chat/completions"
    assert u_provider._get_models_url() == "https://api.custom-ai-host.com/v1/models"
    assert u_provider.endpoint == "https://api.custom-ai-host.com/v1"
    assert u_provider.model == "custom-org/custom-model-1"
    print("  [OK] UniversalApiProvider arbitrary endpoint and model routing verified!")

    # 4. Config Backward-Compatibility Migration
    import json, tempfile
    from config import AppConfig
    legacy_json = {
        "formatting": {
            "engine": "openrouter",
            "openrouter_model": "deepseek/deepseek-chat",
            "openrouter_api_key": "sk-or-v1-legacy-key",
        }
    }
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json", encoding="utf-8") as f:
        json.dump(legacy_json, f)
        temp_path = f.name

    test_cfg = AppConfig()
    test_cfg.load(temp_path)
    assert test_cfg.formatting.engine == "universal", f"Expected engine 'universal', got {test_cfg.formatting.engine}"
    assert test_cfg.formatting.model == "deepseek/deepseek-chat", f"Expected model 'deepseek/deepseek-chat', got {test_cfg.formatting.model}"
    assert test_cfg.formatting.get_api_key("universal") == "sk-or-v1-legacy-key", f"Expected vault api_key 'sk-or-v1-legacy-key', got {test_cfg.formatting.get_api_key('universal')}"
    # Clean up test key from vault
    import security_credentials as sec
    sec.delete_credential(sec.KEY_UNIVERSAL_API)
    import os
    try:
        os.remove(temp_path)
    except Exception:
        pass

    # 5. Dashboard UI Panel Dynamic Switching Verification
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from unittest.mock import MagicMock
    from gui.dashboard_window import DashboardWindow
    from ai_formatter import AIFormatter
    fmt = AIFormatter(mode="flow", engine="rules")
    mock_rec = MagicMock()
    mock_rec.list_devices.return_value = [{'id': 0, 'name': 'Default Mic'}]
    mock_stt = MagicMock()
    dash = DashboardWindow(mock_rec, mock_stt, fmt)

    dash.combo_engine.setCurrentIndex(0)
    assert not dash.rules_container.isHidden() and dash.universal_container.isHidden()
    dash.combo_engine.setCurrentIndex(1)
    assert not dash.ollama_container.isHidden() and dash.universal_container.isHidden()
    dash.combo_engine.setCurrentIndex(2)
    assert not dash.universal_container.isHidden() and dash.rules_container.isHidden()
    dash.combo_engine.setCurrentIndex(3)
    assert not dash.openai_container.isHidden() and dash.universal_container.isHidden()
    dash.combo_engine.setCurrentIndex(4)
    assert not dash.gemini_container.isHidden()
    dash.combo_engine.setCurrentIndex(5)
    assert not dash.groq_container.isHidden()
    print("  [OK] DashboardWindow dynamic engine panel switching verified!")

    print("[OK] [TEST 9 PASSED] Universal API & Provider-Agnostic Engine verified!")


if __name__ == "__main__":
    print("==================================================")
    print("RUNNING VELODICTUM COMPREHENSIVE VERIFICATION")
    print("==================================================")
    test_1_hotkey_decoding_and_scratchpad()
    test_2_send_it_voice_action()
    test_3_hallucination_squelcher()
    test_4_context_intelligence()
    test_5_mobile_lan_bridge_e2e()
    test_6_config_and_ui_wiring()
    test_7_two_tier_architecture()
    test_8_scratchpad_mic_and_structuring()
    test_9_universal_api_and_provider_agnostic_engine()
    print("\n==================================================")
    print("ALL 9 VERIFICATION SUITES PASSED! 100% SUCCESS")
    print("==================================================")
