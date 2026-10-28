#!/usr/bin/env python3
"""
M3 Empirical Challenger Stress-Test Suite
=========================================
Adversarial verification of Milestone 3:
1. Search Filtering Adversarial & Pathological Edge Cases:
   - Regex meta-characters and unclosed syntax tokens: [, (, *, +, ?, ^, $, \\, (?=), etc.
   - Unicode, multi-byte glyphs, CJK, Cyrillic, RTL Arabic/Hebrew, and emojis (single & ZWJ).
   - Whitespace, empty, and zero-width spaces.
   - Bilingual cross-language query matching (DE query in EN mode, EN query in DE mode).
   - Deep recursive auto-expansion of child disclosure sections on matching contents.
   - Rapid sequential search query bursts.
2. Progressive Disclosure Section Lifecycle & Synchronization:
   - Invariant contract: Exactly 6 disclosure sections registered in all_disclosure_sections.
   - Bidirectional synchronization between legacy toggle buttons and disclosure sections.
   - Repeated rapid toggle stress cycles (50+ iterations).
   - _expand_all_settings() and _collapse_all_settings() propagation to sub-accordions.
3. Retranslation and State Stability:
   - Preserving expansion state across bilingual retranslation (de <-> en).
   - Retranslation during active search filtering.
   - Resilient handling of invalid/None/empty language codes.
4. Architectural Invariants:
   - Widget count (>= 263), 7 canonical cards, 4 backward compatibility aliases, 6 engine containers.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock

# Offscreen headless platform configuration
os.environ["QT_QPA_PLATFORM"] = "offscreen"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE_DIR = os.path.join(BASE_DIR, "core")
if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(1, BASE_DIR)

from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt

from config import config
from i18n import tr, set_current_language
from gui.dashboard_window import (
    DashboardWindow,
    SettingsDisclosureSection,
    CollapsibleSettingsCard,
)


def get_qapp():
    app = QApplication.instance()
    if not app:
        app = QApplication(["--platform", "offscreen"])
    return app


class TestM3SearchFilteringAdversarial(unittest.TestCase):
    """
    Adversarial stress testing for live settings search filtering.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = get_qapp()

    def setUp(self):
        self.mock_rec = MagicMock()
        self.mock_rec.list_devices.return_value = [{'id': 0, 'name': 'Standard-Mikrofon'}]
        self.mock_stt = MagicMock()
        self.mock_stt.model_size = 'de_max'
        self.mock_fmt = MagicMock()
        self.mock_fmt.engine = 'universal'

        self.dash = DashboardWindow(self.mock_rec, self.mock_stt, self.mock_fmt)

    def tearDown(self):
        if self.dash:
            if hasattr(self.dash, "waveform_widget") and hasattr(self.dash.waveform_widget, "anim_timer"):
                self.dash.waveform_widget.anim_timer.stop()
            self.dash.close()
        self.app.processEvents()

    def test_regex_metacharacters_and_pathological_patterns(self):
        """
        Adversarial test: Ensure unescaped regex meta-characters, unbalanced tokens,
        and malformed expressions never trigger re.error or runtime crashes.
        """
        pathological_tokens = [
            "[", "]", "(", ")", "{", "}", "*", "+", "?", "^", "$", "\\", "|", ".",
            "*(.*?)+", "[[[", "(((", "\\\\\\\\", "(?=", "(?<=", "(?P<name>.*)",
            "[a-z]+(\\d+)", ".*?", "{1,1000}", "\\x00\\xff", "(?i)", "(?-i)",
            "++", "**", "??", "][", ")(", "/\\*.*\\*/", "^.*$", "\\b\\w+\\b"
        ]
        for token in pathological_tokens:
            try:
                self.dash._on_settings_search_changed(token)
            except Exception as exc:
                self.fail(f"Search filtering crashed on pathological regex token '{token}': {exc}")

        # Ensure UI recovers cleanly after pathological inputs
        self.dash._on_settings_search_changed("")
        for card in self.dash.all_settings_cards:
            self.assertFalse(card.isHidden(), "All cards must be visible after clearing search.")

    def test_unicode_multilingual_and_emoji_queries(self):
        """
        Adversarial test: Ensure search handles non-ASCII, accents, Cyrillic, CJK,
        RTL scripts, zero-width characters, and composite ZWJ emojis without crash.
        """
        complex_queries = [
            # German umlauts and sharp S
            "Übertragung", "rückgängig", "Lautstärke", "Schlüssel", "groß", "äöüß",
            # Accented romance characters
            "paramètres", "configuración", "opções", "èéêë",
            # Cyrillic
            "микрофон", "настройки", "голосовой",
            # CJK scripts
            "麦克风", "マイク", "설정", "음성 인식",
            # RTL scripts
            "ميكروفون", "إعدادات", "מיקרופון", "הגדרות",
            # Emojis and composite sequences
            "🎤", "⚙️", "🔍", "🚀", "🔊", "💡", "👨‍👩‍👧‍👦", "🏳️‍🌈",
            # Zero-width spaces and control escapes
            "\u200b", "\ufeff", "\u00a0"
        ]
        for query in complex_queries:
            try:
                self.dash._on_settings_search_changed(query)
            except Exception as exc:
                self.fail(f"Search filtering crashed on complex query '{query}': {exc}")

        # Verify clean reset
        self.dash._on_settings_search_changed("")
        for card in self.dash.all_settings_cards:
            self.assertFalse(card.isHidden())

    def test_whitespace_and_empty_edge_cases(self):
        """
        Verify that empty, pure whitespace, tab, and newline queries unhide all cards
        and maintain default audio expansion.
        """
        whitespace_variations = [
            "",
            " ",
            "   ",
            "\t",
            "\n",
            "\r\n",
            "   \t\r\n   ",
            "  \u00a0  "  # non-breaking space is categorized as Zs whitespace in python
        ]
        for ws in whitespace_variations:
            self.dash._on_settings_search_changed(ws)
            for card in self.dash.all_settings_cards:
                self.assertFalse(card.isHidden(), f"Card hidden unexpectedly on whitespace input: repr({repr(ws)})")
            self.assertTrue(self.dash.card_audio.is_expanded, "card_audio should be default expanded on empty search")

    def test_nonmatching_invisible_unicode_characters(self):
        """
        Verify that non-whitespace invisible Unicode tokens (like zero-width space U+200B)
        act as non-matching queries, hiding cards rather than crashing.
        """
        self.dash._on_settings_search_changed("\u200b")
        visible_cards = [c for c in self.dash.all_settings_cards if not c.isHidden()]
        self.assertEqual(len(visible_cards), 0, "Zero-width space should safely act as non-matching query")
        # Ensure clean recovery
        self.dash._on_settings_search_changed("")
        for card in self.dash.all_settings_cards:
            self.assertFalse(card.isHidden())
    def test_bilingual_cross_language_queries(self):
        """
        Adversarial test: Ensure German search terms match in English UI mode,
        and English search terms match in German UI mode.
        """
        # --- Mode 1: UI in ENGLISH ---
        set_current_language("en")
        self.dash.retranslate_ui("en")

        # German query: "mikrofon" -> card_audio must match
        self.dash._on_settings_search_changed("mikrofon")
        self.assertFalse(self.dash.card_audio.isHidden(), "DE query 'mikrofon' failed to find card_audio in EN mode")

        # German query: "tastenkürzel" -> card_hk must match
        self.dash._on_settings_search_changed("tastenkürzel")
        self.assertFalse(self.dash.card_hk.isHidden(), "DE query 'tastenkürzel' failed to find card_hk in EN mode")

        # German query: "lautstärke" -> card_audio must match
        self.dash._on_settings_search_changed("lautstärke")
        self.assertFalse(self.dash.card_audio.isHidden(), "DE query 'lautstärke' failed to find card_audio in EN mode")

        # German query: "spracherkennung" -> card_stt must match
        self.dash._on_settings_search_changed("spracherkennung")
        self.assertFalse(self.dash.card_stt.isHidden(), "DE query 'spracherkennung' failed to find card_stt in EN mode")

        # German query: "formatierung" -> card_fmt must match
        self.dash._on_settings_search_changed("formatierung")
        self.assertFalse(self.dash.card_fmt.isHidden(), "DE query 'formatierung' failed to find card_fmt in EN mode")

        # --- Mode 2: UI in GERMAN ---
        set_current_language("de")
        self.dash.retranslate_ui("de")

        # English query: "microphone" -> card_audio must match
        self.dash._on_settings_search_changed("microphone")
        self.assertFalse(self.dash.card_audio.isHidden(), "EN query 'microphone' failed to find card_audio in DE mode")

        # English query: "hotkey" -> card_hk must match
        self.dash._on_settings_search_changed("hotkey")
        self.assertFalse(self.dash.card_hk.isHidden(), "EN query 'hotkey' failed to find card_hk in DE mode")

        # English query: "volume" -> card_audio must match
        self.dash._on_settings_search_changed("volume")
        self.assertFalse(self.dash.card_audio.isHidden(), "EN query 'volume' failed to find card_audio in DE mode")

        # English query: "speech" -> card_stt must match
        self.dash._on_settings_search_changed("speech")
        self.assertFalse(self.dash.card_stt.isHidden(), "EN query 'speech' failed to find card_stt in DE mode")

        # English query: "formatting" -> card_fmt must match
        self.dash._on_settings_search_changed("formatting")
        self.assertFalse(self.dash.card_fmt.isHidden(), "EN query 'formatting' failed to find card_fmt in DE mode")

        # English query: "hud" -> card_hud must match
        self.dash._on_settings_search_changed("hud")
        self.assertFalse(self.dash.card_hud.isHidden(), "Query 'hud' failed to find card_hud in DE mode")

    def test_deep_disclosure_section_auto_expansion(self):
        """
        Verify that searching for terms located inside nested disclosure sections
        automatically unhides the parent card AND auto-expands the matching disclosure section.
        """
        # Collapse all first
        self.dash._collapse_all_settings()
        for disc in self.dash.all_disclosure_sections:
            self.assertFalse(disc.is_expanded)

        # 1. Search for "8765" or "server" (located in sub_mob_bridge title & URL)
        self.dash._on_settings_search_changed("8765")
        self.assertFalse(self.dash.card_audio.isHidden(), "Parent card_audio should be visible for '8765'")
        self.assertTrue(self.dash.card_audio.is_expanded, "Parent card_audio should be expanded for '8765'")
        self.assertTrue(self.dash.sub_mob_bridge.is_expanded, "Child disclosure section sub_mob_bridge should auto-expand")

        # Clear search: all disclosure sections should collapse back
        self.dash._on_settings_search_changed("")
        self.assertFalse(self.dash.sub_mob_bridge.is_expanded, "sub_mob_bridge should collapse on search clear")

        # 2. Search for "routing" (shared token in custom_catalog_frame in both languages)
        self.dash._collapse_all_settings()
        self.dash._on_settings_search_changed("routing")
        self.assertFalse(self.dash.card_fmt.isHidden(), "Parent card_fmt should be visible for 'routing'")
        self.assertTrue(self.dash.card_fmt.is_expanded, "Parent card_fmt should be expanded for 'routing'")
        self.assertTrue(self.dash.custom_catalog_frame.is_expanded, "Child custom_catalog_frame should auto-expand for 'routing'")

        # Clear search
        self.dash._on_settings_search_changed("")
        self.assertFalse(self.dash.custom_catalog_frame.is_expanded, "custom_catalog_frame should collapse on search clear")

        # 3. Test localized catalog in English mode
        self.dash.retranslate_ui("en")
        self.dash._collapse_all_settings()
        self.dash._on_settings_search_changed("catalog")
        self.assertFalse(self.dash.card_fmt.isHidden(), "Parent card_fmt should be visible for 'catalog' in EN mode")
        self.assertTrue(self.dash.custom_catalog_frame.is_expanded, "custom_catalog_frame should auto-expand for 'catalog' in EN mode")

        # 4. Test localized katalog in German mode
        self.dash.retranslate_ui("de")
        self.dash._collapse_all_settings()
        self.dash._on_settings_search_changed("katalog")
        self.assertFalse(self.dash.card_fmt.isHidden(), "Parent card_fmt should be visible for 'katalog' in DE mode")
        self.assertTrue(self.dash.custom_catalog_frame.is_expanded, "custom_catalog_frame should auto-expand for 'katalog' in DE mode")

        # Clear search again
        self.dash._on_settings_search_changed("")
        self.assertFalse(self.dash.custom_catalog_frame.is_expanded, "custom_catalog_frame should collapse on search clear")

    def test_rapid_sequential_search_burst(self):
        """
        Stress test: Execute 100 alternating queries in rapid succession without UI freeze.
        """
        burst_queries = [
            "audio", "hotkey", "nonexistent_token_123", "", "whisper",
            "format", "[a-z]", "microphone", "tastenkürzel", " ",
            "ollama", "gemini", "groq", "hud", "system",
            "äöü", "🎤", "bridge", "gain", "backup"
        ] * 5  # 100 queries total

        for q in burst_queries:
            self.dash._on_settings_search_changed(q)

        # Ensure final state resets cleanly
        self.dash._on_settings_search_changed("")
        for card in self.dash.all_settings_cards:
            self.assertFalse(card.isHidden())


class TestM3DisclosureSectionLifecycle(unittest.TestCase):
    """
    Empirical testing of disclosure section invariants, synchronization, and lifecycle.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = get_qapp()

    def setUp(self):
        self.mock_rec = MagicMock()
        self.mock_rec.list_devices.return_value = [{'id': 0, 'name': 'Standard-Mikrofon'}]
        self.mock_stt = MagicMock()
        self.mock_stt.model_size = 'de_max'
        self.mock_fmt = MagicMock()
        self.mock_fmt.engine = 'universal'

        self.dash = DashboardWindow(self.mock_rec, self.mock_stt, self.mock_fmt)

    def tearDown(self):
        if self.dash:
            if hasattr(self.dash, "waveform_widget") and hasattr(self.dash.waveform_widget, "anim_timer"):
                self.dash.waveform_widget.anim_timer.stop()
            self.dash.close()
        self.app.processEvents()

    def test_disclosure_section_registration_and_invariants(self):
        """
        Contract verification: Exactly 6 progressive disclosure sections must be registered.
        """
        self.assertTrue(hasattr(self.dash, "all_disclosure_sections"))
        disclosures = self.dash.all_disclosure_sections
        self.assertEqual(len(disclosures), 6, f"Expected exactly 6 disclosure sections, found {len(disclosures)}")

        # Verify expected sections
        expected_sections = [
            self.dash.sub_mob_bridge,
            self.dash.model_storage_frame,
            self.dash.custom_catalog_frame,
            self.dash.adv_formatting_frame,
            self.dash.hud_sliders_frame,
            self.dash.dev_options_frame
        ]
        for sec in expected_sections:
            self.assertIn(sec, disclosures)
            self.assertIsInstance(sec, SettingsDisclosureSection)
            self.assertTrue(hasattr(sec, "is_expanded"))
            self.assertTrue(hasattr(sec, "toggle"))
            self.assertTrue(hasattr(sec, "set_expanded"))

    def test_legacy_toggle_button_bidirectional_synchronization(self):
        """
        Verify bidirectional synchronization between legacy buttons and disclosure sections.
        """
        # Test Custom Catalog toggle
        custom_cat = self.dash.custom_catalog_frame
        btn_cat = self.dash.btn_toggle_custom_catalog

        # Initial state: collapsed
        custom_cat.set_expanded(False)
        self.assertFalse(custom_cat.is_expanded)

        # Trigger via legacy method
        self.dash._toggle_custom_catalog()
        self.assertTrue(custom_cat.is_expanded)

        self.dash._toggle_custom_catalog()
        self.assertFalse(custom_cat.is_expanded)

        # Test Advanced Formatting toggle
        adv_fmt = self.dash.adv_formatting_frame
        btn_fmt = self.dash.btn_toggle_adv_formatting

        adv_fmt.set_expanded(False)
        self.dash._toggle_advanced_formatting()
        self.assertTrue(adv_fmt.is_expanded)

        self.dash._toggle_advanced_formatting()
        self.assertFalse(adv_fmt.is_expanded)

    def test_stress_repeated_toggling_cycles(self):
        """
        Stress test: Rapidly toggle all disclosure sections 50 times to check for leaks or desync.
        """
        for _ in range(50):
            for disc in self.dash.all_disclosure_sections:
                disc.toggle()

        # End in fully collapsed state
        self.dash._collapse_all_settings()
        for disc in self.dash.all_disclosure_sections:
            self.assertFalse(disc.is_expanded)

    def test_expand_all_and_collapse_all_propagation(self):
        """
        Verify that _expand_all_settings and _collapse_all_settings operate
        on both top-level cards and nested disclosure sections.
        """
        # 1. Expand all
        self.dash._expand_all_settings()
        for card in self.dash.all_settings_cards:
            self.assertTrue(card.is_expanded, f"Card {card} not expanded")
        for disc in self.dash.all_disclosure_sections:
            self.assertTrue(disc.is_expanded, f"Disclosure {disc} not expanded")

        # 2. Collapse all
        self.dash._collapse_all_settings()
        for card in self.dash.all_settings_cards:
            self.assertFalse(card.is_expanded, f"Card {card} not collapsed")
        for disc in self.dash.all_disclosure_sections:
            self.assertFalse(disc.is_expanded, f"Disclosure {disc} not collapsed")


class TestM3RetranslationAndStateStability(unittest.TestCase):
    """
    Stress testing retranslation robustness under active state combinations.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = get_qapp()

    def setUp(self):
        self.mock_rec = MagicMock()
        self.mock_rec.list_devices.return_value = [{'id': 0, 'name': 'Standard-Mikrofon'}]
        self.mock_stt = MagicMock()
        self.mock_stt.model_size = 'de_max'
        self.mock_fmt = MagicMock()
        self.mock_fmt.engine = 'universal'

        self.dash = DashboardWindow(self.mock_rec, self.mock_stt, self.mock_fmt)

    def tearDown(self):
        if self.dash:
            if hasattr(self.dash, "waveform_widget") and hasattr(self.dash.waveform_widget, "anim_timer"):
                self.dash.waveform_widget.anim_timer.stop()
            self.dash.close()
        self.app.processEvents()

    def test_retranslation_preserves_expansion_states(self):
        """
        Verify that switching languages does not collapse already-expanded cards or disclosure sections.
        """
        # Expand specific card and disclosure section
        self.dash.card_fmt.set_expanded(True)
        self.dash.custom_catalog_frame.set_expanded(True)

        # Switch to German
        set_current_language("de")
        self.dash.retranslate_ui("de")
        self.assertTrue(self.dash.card_fmt.is_expanded, "card_fmt lost expansion state on DE retranslate")
        self.assertTrue(self.dash.custom_catalog_frame.is_expanded, "custom_catalog lost expansion state on DE retranslate")

        # Switch to English
        set_current_language("en")
        self.dash.retranslate_ui("en")
        self.assertTrue(self.dash.card_fmt.is_expanded, "card_fmt lost expansion state on EN retranslate")
        self.assertTrue(self.dash.custom_catalog_frame.is_expanded, "custom_catalog lost expansion state on EN retranslate")

    def test_retranslation_during_active_search_filter(self):
        """
        Verify that retranslating the UI while a search filter is active does not throw or corrupt widgets.
        """
        self.dash._on_settings_search_changed("mikrofon")
        self.assertFalse(self.dash.card_audio.isHidden())

        # Retranslate while filtered
        self.dash.retranslate_ui("de")
        self.dash.retranslate_ui("en")
        self.dash.retranslate_ui("de")

        # Clear filter
        self.dash._on_settings_search_changed("")
        for card in self.dash.all_settings_cards:
            self.assertFalse(card.isHidden())

    def test_retranslation_with_invalid_language_codes_zero_crashes(self):
        """
        Adversarial test: Ensure passing invalid, None, empty, or numeric values
        to retranslate_ui does not crash DashboardWindow.
        """
        invalid_codes = ["invalid_code", None, "", 12345, [], {}, "es-419", "zh_CN_EXTRA"]
        for code in invalid_codes:
            try:
                self.dash.retranslate_ui(code)
            except Exception as exc:
                self.fail(f"DashboardWindow.retranslate_ui crashed on invalid code '{code}': {exc}")

        # Recover cleanly
        self.dash.retranslate_ui("de")
        self.assertIn("Einstellungen", self.dash.tabs.tabText(2))


class TestM3ArchitecturalInvariantsAndCompatibility(unittest.TestCase):
    """
    Verification of architectural invariants, backward compatibility aliases, and widget counts.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = get_qapp()

    def setUp(self):
        self.mock_rec = MagicMock()
        self.mock_rec.list_devices.return_value = [{'id': 0, 'name': 'Standard-Mikrofon'}]
        self.mock_stt = MagicMock()
        self.mock_stt.model_size = 'de_max'
        self.mock_fmt = MagicMock()
        self.mock_fmt.engine = 'universal'

        self.dash = DashboardWindow(self.mock_rec, self.mock_stt, self.mock_fmt)

    def tearDown(self):
        if self.dash:
            if hasattr(self.dash, "waveform_widget") and hasattr(self.dash.waveform_widget, "anim_timer"):
                self.dash.waveform_widget.anim_timer.stop()
            self.dash.close()
        self.app.processEvents()

    def test_widget_count_baseline(self):
        """
        Verify that bound QWidget attributes meet or exceed the 263 invariant baseline.
        """
        attrs = [a for a in dir(self.dash) if isinstance(getattr(self.dash, a, None), QWidget)]
        self.assertGreaterEqual(len(attrs), 263, f"Widget count {len(attrs)} is below invariant baseline 263")

    def test_backward_compatibility_aliases_identity(self):
        """
        Verify exact identity (is) for the 4 backward compatibility aliases.
        """
        self.assertIs(self.dash.card_llm, self.dash.card_fmt, "card_llm is not card_fmt")
        self.assertIs(self.dash.card_sound, self.dash.card_gen, "card_sound is not card_gen")
        self.assertIs(self.dash.card_mob, self.dash.card_audio, "card_mob is not card_audio")
        self.assertIs(self.dash.card_sys, self.dash.card_adv, "card_sys is not card_adv")

    def test_engine_switching_containers_presence(self):
        """
        Verify that all 6 engine switching containers exist as QWidgets.
        """
        engine_containers = [
            "universal_container",
            "rules_container",
            "ollama_container",
            "openai_container",
            "groq_container",
            "gemini_container"
        ]
        for name in engine_containers:
            self.assertTrue(hasattr(self.dash, name), f"Missing engine container: {name}")
            widget = getattr(self.dash, name)
            self.assertIsInstance(widget, QWidget, f"{name} is not a QWidget")


class TestM3WidgetInteractionsAndGUIEvents(unittest.TestCase):
    """
    Adversarial testing of actual Qt GUI events, mouse clicks, and widget signals.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = get_qapp()

    def setUp(self):
        self.mock_rec = MagicMock()
        self.mock_rec.list_devices.return_value = [{'id': 0, 'name': 'Standard-Mikrofon'}]
        self.mock_stt = MagicMock()
        self.mock_stt.model_size = 'de_max'
        self.mock_fmt = MagicMock()
        self.mock_fmt.engine = 'universal'

        self.dash = DashboardWindow(self.mock_rec, self.mock_stt, self.mock_fmt)

    def tearDown(self):
        if self.dash:
            if hasattr(self.dash, "waveform_widget") and hasattr(self.dash.waveform_widget, "anim_timer"):
                self.dash.waveform_widget.anim_timer.stop()
            self.dash.close()
        self.app.processEvents()

    def test_search_input_widget_signals_and_clear_button(self):
        """
        Verify that typing into input_settings_search triggers filtering via Qt signal
        and calling input_settings_search.clear() restores all cards.
        """
        self.dash.input_settings_search.setText("hotkey")
        self.app.processEvents()

        self.assertFalse(self.dash.card_hk.isHidden())
        self.assertTrue(self.dash.card_audio.isHidden())

        # Clear search via line edit clear
        self.dash.input_settings_search.clear()
        self.app.processEvents()

        self.assertEqual(self.dash.input_settings_search.text(), "")
        for card in self.dash.all_settings_cards:
            self.assertFalse(card.isHidden(), f"Card {card} remained hidden after search clear")

    def test_header_mouse_click_event_delivery(self):
        """
        Simulate mouse click event on header_widget of CollapsibleSettingsCard and SettingsDisclosureSection.
        """
        from PyQt6.QtGui import QMouseEvent
        from PyQt6.QtCore import QPointF

        # 1. Test Card header click
        card = self.dash.card_audio
        initial_expanded = card.is_expanded

        # Synthesize mouse click
        press_event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(10, 10),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        card._on_header_clicked(press_event)
        self.assertNotEqual(card.is_expanded, initial_expanded, "Card expansion failed to toggle on mouse click")

        # Toggle back
        card._on_header_clicked(press_event)
        self.assertEqual(card.is_expanded, initial_expanded)

        # 2. Test Disclosure Section header click
        disc = self.dash.sub_mob_bridge
        initial_disc_exp = disc.is_expanded
        disc._on_header_clicked(press_event)
        self.assertNotEqual(disc.is_expanded, initial_disc_exp, "Disclosure expansion failed to toggle on mouse click")

        disc._on_header_clicked(press_event)
        self.assertEqual(disc.is_expanded, initial_disc_exp)

    def test_cross_tab_switching_under_active_filter(self):
        """
        Verify tab switching (Studio -> Library -> Settings -> Logs -> Settings)
        while a search filter is active does not cause crashes or state corruption.
        """
        self.dash.input_settings_search.setText("whisper")
        self.app.processEvents()

        # Switch across all 4 tabs
        for idx in [0, 1, 3, 2, 0, 2]:
            self.dash.tabs.setCurrentIndex(idx)
            self.app.processEvents()

        # In Settings tab, card_stt should still be visible and match
        self.assertFalse(self.dash.card_stt.isHidden())
        self.assertTrue(self.dash.card_stt.is_expanded)

        # Clear
        self.dash.input_settings_search.clear()
        self.app.processEvents()
        for card in self.dash.all_settings_cards:
            self.assertFalse(card.isHidden())

    def test_expand_all_collapse_all_buttons_interactivity(self):
        """
        Verify clicking btn_expand_all and btn_collapse_all buttons in UI.
        """
        self.dash.btn_expand_all.click()
        self.app.processEvents()
        for card in self.dash.all_settings_cards:
            self.assertTrue(card.is_expanded)
        for disc in self.dash.all_disclosure_sections:
            self.assertTrue(disc.is_expanded)

        self.dash.btn_collapse_all.click()
        self.app.processEvents()
        for card in self.dash.all_settings_cards:
            self.assertFalse(card.is_expanded)
        for disc in self.dash.all_disclosure_sections:
            self.assertFalse(disc.is_expanded)


if __name__ == "__main__":
    unittest.main()

