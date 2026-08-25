import pytest
import i18n
from config import config, AppConfig
from gui.signals import signals


def test_i18n_basic_translations():
    i18n.set_current_language("en")
    assert i18n.get_current_language() == "en"
    assert "Ready" in i18n.tr("ready")
    assert "Velodictum" in i18n.tr("app_title")

    i18n.set_current_language("de")
    assert i18n.get_current_language() == "de"
    assert "Bereit" in i18n.tr("ready")


def test_i18n_formatting_interpolation():
    i18n.set_current_language("en")
    text_en = i18n.tr("hero_sub_ptt", key="F8")
    assert "F8" in text_en
    assert "Hold [F8]" in text_en

    i18n.set_current_language("de")
    text_de = i18n.tr("hero_sub_ptt", key="F8")
    assert "F8" in text_de
    assert "gedrückt halten" in text_de


def test_i18n_fallback_safety():
    i18n.set_current_language("de")
    # Non-existent key should return key itself
    res = i18n.tr("non_existent_key_xyz123")
    assert res == "non_existent_key_xyz123"


def test_i18n_catalog_parity():
    en_keys = set(i18n.TRANSLATIONS.get("en", {}).keys())
    de_keys = set(i18n.TRANSLATIONS.get("de", {}).keys())
    missing_in_de = en_keys - de_keys
    missing_in_en = de_keys - en_keys
    assert not missing_in_de, f"Keys in 'en' missing in 'de': {missing_in_de}"
    assert not missing_in_en, f"Keys in 'de' missing in 'en': {missing_in_en}"


def test_config_ui_language_sync():
    cfg = AppConfig()
    assert hasattr(cfg.system, "ui_language")
    assert hasattr(cfg.system, "first_run_completed")
    assert cfg.system.ui_language in ("en", "de")


def test_dashboard_bilingual_switching():
    import sys
    from PyQt6.QtWidgets import QApplication
    from unittest.mock import MagicMock
    from gui.dashboard_window import DashboardWindow

    app = QApplication.instance() or QApplication(sys.argv)
    mock_rec = MagicMock()
    mock_rec.list_devices.return_value = [{"id": 0, "name": "Test Mic"}]
    mock_stt = MagicMock()
    mock_stt.model_size = "tiny"
    mock_fmt = MagicMock()
    mock_fmt.engine = "universal"

    dash = DashboardWindow(mock_rec, mock_stt, mock_fmt)

    # 1. Switch to English
    dash.retranslate_ui("en")
    assert dash.tabs.tabText(0) == "Studio"
    assert dash.tabs.tabText(2) == "Settings"
    assert "Ready for Dictation" in dash.lbl_hero_action.text()
    assert "Expand all" in dash.btn_expand_all.text()
    assert "Collapse all" in dash.btn_collapse_all.text()
    assert dash.btn_sub_vocab.text() == "Custom Vocabulary"
    assert dash.btn_sub_snippets.text() == "Voice Macros & Snippets"
    assert dash.btn_sub_apps.text() == "App Smart Profiles"
    assert "Search settings" in dash.input_settings_search.placeholderText()
    assert "GENERAL" in dash.card_gen.lbl_title.text()
    assert "AUDIO" in dash.card_audio.lbl_title.text()
    assert "SPEECH RECOGNITION" in dash.card_stt.lbl_title.text()
    assert "FORMATTING" in dash.card_fmt.lbl_title.text()
    assert "SHORTCUTS" in dash.card_hk.lbl_title.text()
    assert "FLOATING HUD" in dash.card_hud.lbl_title.text()
    assert "SYSTEM" in dash.card_adv.lbl_title.text()

    # Verify Card 1 & 2 Specific Controls in EN
    assert "Pre-Amplification" in dash.lbl_gain_title.text()
    assert "Background volume" in dash.lbl_duck_title.text()
    assert "Very quiet" in dash.combo_sound_vol.itemText(0)
    assert "Local" in dash.combo_stt_provider.itemText(0)

    # Verify Card 4 Specific Controls in EN
    assert "Local Rules" in dash.combo_engine.itemText(0)
    assert "Speed Priority" in dash.card_prio_fast.lbl_title.text()
    assert "Input Cost:" in dash.lbl_d_cin_title.text()
    assert "Fetch Models" in dash.btn_u_fetch_models.text()
    assert "Standard" in dash.combo_tone.itemText(0)

    # 2. Switch to German
    dash.retranslate_ui("de")
    assert dash.tabs.tabText(0) == "Studio"
    assert dash.tabs.tabText(2) == "Einstellungen"
    assert "Bereit zum Diktieren" in dash.lbl_hero_action.text()
    assert "Alle aufklappen" in dash.btn_expand_all.text()
    assert "Alle einklappen" in dash.btn_collapse_all.text()
    assert dash.btn_sub_vocab.text() == "Eigenes Wörterbuch"
    assert dash.btn_sub_snippets.text() == "Sprach-Makros & Snippets"
    assert dash.btn_sub_apps.text() == "App-Smart-Profile"
    assert "durchsuchen" in dash.input_settings_search.placeholderText()
    assert "ALLGEMEIN" in dash.card_gen.lbl_title.text()
    assert "AUDIO" in dash.card_audio.lbl_title.text()
    assert "SPRACHERKENNUNG" in dash.card_stt.lbl_title.text()
    assert "FORMATIERUNG" in dash.card_fmt.lbl_title.text()
    assert "SHORTCUTS" in dash.card_hk.lbl_title.text()
    assert "FLOATING HUD" in dash.card_hud.lbl_title.text()
    assert "SYSTEM" in dash.card_adv.lbl_title.text()

    # Verify Card 1 & 2 Specific Controls in DE
    assert "Vorverstärkung:" in dash.lbl_gain_title.text()
    assert "Restlautstärke" in dash.lbl_duck_title.text()
    assert "Sehr leise" in dash.combo_sound_vol.itemText(0)
    assert "Lokal" in dash.combo_stt_provider.itemText(0)

    # Verify Card 4 Specific Controls in DE
    assert "Lokale Regeln" in dash.combo_engine.itemText(0)
    assert "Höchste Schnelligkeit" in dash.card_prio_fast.lbl_title.text()
    assert "Input Kosten:" in dash.lbl_d_cin_title.text()
    assert "Modelle laden" in dash.btn_u_fetch_models.text()
    assert "Standard" in dash.combo_tone.itemText(0)


def test_scratchpad_bilingual_switching():
    import sys
    from PyQt6.QtWidgets import QApplication
    from unittest.mock import MagicMock
    from gui.scratchpad_window import ScratchpadWindow

    app = QApplication.instance() or QApplication(sys.argv)
    mock_fmt = MagicMock()
    pad = ScratchpadWindow(mock_fmt)

    # English
    i18n.set_current_language("en")
    pad.retranslate_ui("en")
    assert "Voice Scratchpad" in pad.windowTitle()
    assert pad.btn_mic.text() == "Dictate"
    assert pad.btn_structure.text() == "Structure with AI"
    assert pad.btn_copy.text() == "Copy Note"
    assert pad.btn_clear.text() == "Clear"

    # German
    i18n.set_current_language("de")
    pad.retranslate_ui("de")
    assert "Diktierbuch" in pad.windowTitle()
    assert pad.btn_mic.text() == "Diktieren"
    assert pad.btn_structure.text() == "Mit KI strukturieren"
    assert pad.btn_copy.text() == "Kopieren"
    assert pad.btn_clear.text() == "Leeren"


def test_formatting_providers_localization():
    import formatting_providers

    # English
    i18n.set_current_language("en")
    assert formatting_providers.detect_provider("http://127.0.0.1:11434") == "Ollama (Local)"
    assert formatting_providers.detect_provider("") == "Not configured"
    tiers_en = formatting_providers.get_model_tiers()
    assert tiers_en["speed"]["title"] == "Speed Priority"
    details_en = formatting_providers.get_model_details("google/gemini-2.5-flash")
    assert "Fast & Budget" in details_en["recommended_for"]

    # German
    i18n.set_current_language("de")
    assert formatting_providers.detect_provider("http://127.0.0.1:11434") == "Ollama (Lokal)"
    assert formatting_providers.detect_provider("") == "Nicht konfiguriert"
    tiers_de = formatting_providers.get_model_tiers()
    assert tiers_de["speed"]["title"] == "Höchste Schnelligkeit"
    details_de = formatting_providers.get_model_details("google/gemini-2.5-flash")
    assert "Schnell & Günstig" in details_de["recommended_for"]


def test_model_manager_and_sound_themes_localization():
    import model_manager
    import sound_effects

    # English
    i18n.set_current_language("en")
    catalog_en = {m["id"]: m for m in model_manager.get_models_catalog()}
    assert catalog_en["tiny"]["speed"] == "Ultra-Fast (<100ms)"
    assert "Extremely lightweight" in catalog_en["tiny"]["desc"]

    themes_en = sound_effects.get_sound_themes()
    assert themes_en["velodictum_silk"]["name"] == "Velodictum Silk Droplet"
    assert "Ultra-smooth" in themes_en["velodictum_silk"]["desc"]

    # German
    i18n.set_current_language("de")
    catalog_de = {m["id"]: m for m in model_manager.get_models_catalog()}
    assert catalog_de["tiny"]["speed"] == "Ultra-Schnell (<100ms)"
    assert "Extrem leichtgewichtig" in catalog_de["tiny"]["desc"]

    themes_de = sound_effects.get_sound_themes()
    assert themes_de["velodictum_silk"]["name"] == "Velodictum Silk Droplet"
    assert "Ultra-weicher" in themes_de["velodictum_silk"]["desc"]


