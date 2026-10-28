#!/usr/bin/env python3
"""
M3 Iteration 2 Empirical Challenger Stress-Test Suite
=====================================================
Adversarial stress testing of gui/dashboard_window.py:
1. Zero-width and whitespace edge cases:
   - Unicode whitespace categories (Zs, Zl, Zp)
   - Zero-width and invisible control characters (\u200b, \u200c, \u200d, \ufeff, \u2060)
   - Flanking whitespace and non-whitespace invisible tokens
2. Recursive progressive disclosure auto-expansion:
   - "bridge" / "lan" -> sub_mob_bridge (in card_audio)
   - "storage" / "speicher" -> model_storage_frame (in card_stt)
   - "catalog" / "katalog" -> custom_catalog_frame (in card_fmt)
   - "opacity" / "transparenz" -> hud_sliders_frame (in card_hud)
   - "scale" / "skalierung" -> hud_sliders_frame (in card_hud)
   - "cache" / "zwischenspeicher" -> dev_options_frame (in card_adv)
   - "markdown" / "filler" -> adv_formatting_frame (in card_fmt)
3. Rapid sequential search bursts, tab switches, and expand/collapse cycles.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock

os.environ["QT_QPA_PLATFORM"] = "offscreen"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE_DIR = os.path.join(BASE_DIR, "core")
if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(1, BASE_DIR)

from PyQt6.QtWidgets import QApplication
from i18n import tr, set_current_language
from gui.dashboard_window import DashboardWindow


def get_qapp():
    app = QApplication.instance()
    if not app:
        app = QApplication(["--platform", "offscreen"])
    return app


class TestM3R2AdversarialStress(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = get_qapp()

    def setUp(self):
        self.mock_rec = MagicMock()
        self.mock_rec.list_devices.return_value = [{'id': 0, 'name': 'Mikrofon'}]
        self.mock_stt = MagicMock()
        self.mock_stt.model_size = 'de_max'
        self.mock_fmt = MagicMock()
        self.mock_fmt.engine = 'universal'
        self.dash = DashboardWindow(self.mock_rec, self.mock_stt, self.mock_fmt)

    def tearDown(self):
        if hasattr(self.dash, "waveform_widget") and hasattr(self.dash.waveform_widget, "anim_timer"):
            self.dash.waveform_widget.anim_timer.stop()
        if hasattr(self.dash, "gpu_timer"):
            self.dash.gpu_timer.stop()
        self.dash.close()
        self.app.processEvents()

    # =========================================================================
    # 1. Whitespace & Zero-Width Edge Cases
    # =========================================================================
    def test_pure_whitespace_variants_unhide_all_cards(self):
        """
        Verify that all variations of Unicode whitespace (Zs, Zl, Zp) unhide all cards,
        collapse non-audio cards, and keep card_audio expanded.
        """
        whitespace_samples = [
            "",
            " ",
            "   \t   \n  \r\n   ",
            "\u00a0",              # NO-BREAK SPACE
            "\u1680",              # OGHAM SPACE MARK
            "\u2000",              # EN QUAD
            "\u2001",              # EM QUAD
            "\u2002",              # EN SPACE
            "\u2003",              # EM SPACE
            "\u2004",              # THREE-PER-EM SPACE
            "\u2005",              # FOUR-PER-EM SPACE
            "\u2006",              # SIX-PER-EM SPACE
            "\u2007",              # FIGURE SPACE
            "\u2008",              # PUNCTUATION SPACE
            "\u2009",              # THIN SPACE
            "\u200a",              # HAIR SPACE
            "\u2028",              # LINE SEPARATOR
            "\u2029",              # PARAGRAPH SEPARATOR
            "\u202f",              # NARROW NO-BREAK SPACE
            "\u205f",              # MEDIUM MATHEMATICAL SPACE
            "\u3000",              # IDEOGRAPHIC SPACE
            "  \u00a0 \u2003 \u3000  ",
        ]

        for ws in whitespace_samples:
            self.dash._on_settings_search_changed(ws)
            self.app.processEvents()

            # All 7 cards must be unhidden
            for card in self.dash.all_settings_cards:
                self.assertFalse(
                    card.isHidden(),
                    f"Card {card.lbl_title.text()} unexpectedly hidden on whitespace: {repr(ws)}"
                )

            # card_audio must be expanded by default on empty/whitespace search
            self.assertTrue(
                self.dash.card_audio.is_expanded,
                f"card_audio must be expanded by default on whitespace: {repr(ws)}"
            )

            # All 6 disclosure sections must be collapsed on empty/whitespace search
            for disc in self.dash.all_disclosure_sections:
                self.assertFalse(
                    disc.is_expanded,
                    f"Disclosure {disc.lbl_title.text()} unexpectedly expanded on whitespace: {repr(ws)}"
                )

    def test_invisible_non_whitespace_unicode_hides_all_cards(self):
        """
        Verify that invisible non-whitespace tokens (e.g. U+200B zero-width space,
        U+200C ZWNJ, U+200D ZWJ, U+FEFF BOM) are treated as unmatched search queries
        (hiding all cards, zero crashes).
        """
        invisible_tokens = [
            "\u200b",              # ZERO WIDTH SPACE (Cf)
            "\u200c",              # ZERO WIDTH NON-JOINER (Cf)
            "\u200d",              # ZERO WIDTH JOINER (Cf)
            "\ufeff",              # ZERO WIDTH NO-BREAK SPACE / BOM (Cf)
            "\u2060",              # WORD JOINER (Cf)
            "  \u200b  ",          # with surrounding whitespace
            "  \u200c  ",
            "  \ufeff  ",
            "\u200b\u200c\ufeff",  # composite invisible string
        ]

        for token in invisible_tokens:
            self.dash._on_settings_search_changed(token)
            self.app.processEvents()

            visible_cards = [c for c in self.dash.all_settings_cards if not c.isHidden()]
            self.assertEqual(
                len(visible_cards), 0,
                f"Expected 0 visible cards for non-matching invisible token {repr(token)}, found {len(visible_cards)}"
            )

            # Clean recovery with empty search
            self.dash._on_settings_search_changed("")
            self.app.processEvents()
            for card in self.dash.all_settings_cards:
                self.assertFalse(card.isHidden())

    def test_flanking_invisible_tokens_around_matching_terms(self):
        """
        Verify that searching terms containing invisible characters or unicode spaces
        does not crash and gracefully matches via substring tokenization.
        """
        queries = [
            "  bridge  ",
            "lan \u00a0",
            "\u00a0 storage \u00a0",
            "catalog\u00a0",
            "\u200bbridge",       # contains "bridge"
            "lan\ufeff",          # contains "lan"
        ]

        for q in queries:
            self.dash._on_settings_search_changed(q)
            self.app.processEvents()
            # Must not crash
            self.dash._on_settings_search_changed("")
            self.app.processEvents()

    # =========================================================================
    # 2. Recursive Progressive Disclosure Auto-Expansion
    # =========================================================================
    def test_auto_expansion_bridge_and_lan(self):
        """
        'bridge' and 'lan' must unhide card_audio, expand card_audio,
        and auto-expand sub_mob_bridge.
        """
        for term in ["bridge", "lan", "BRIDGE", "LAN", "  bridge  "]:
            self.dash._collapse_all_settings()
            self.dash._on_settings_search_changed(term)
            self.app.processEvents()

            self.assertFalse(self.dash.card_audio.isHidden(), f"card_audio should be visible for '{term}'")
            self.assertTrue(self.dash.card_audio.is_expanded, f"card_audio should be expanded for '{term}'")
            self.assertTrue(self.dash.sub_mob_bridge.is_expanded, f"sub_mob_bridge should be expanded for '{term}'")

    def test_auto_expansion_storage_and_speicher(self):
        """
        'storage' and 'speicher' must unhide card_stt, expand card_stt,
        and auto-expand model_storage_frame.
        """
        for term in ["storage", "speicher", "STORAGE", "Speicher"]:
            self.dash._collapse_all_settings()
            self.dash._on_settings_search_changed(term)
            self.app.processEvents()

            self.assertFalse(self.dash.card_stt.isHidden(), f"card_stt should be visible for '{term}'")
            self.assertTrue(self.dash.card_stt.is_expanded, f"card_stt should be expanded for '{term}'")
            self.assertTrue(self.dash.model_storage_frame.is_expanded, f"model_storage_frame should be expanded for '{term}'")

    def test_auto_expansion_catalog_and_katalog(self):
        """
        'catalog' and 'katalog' must unhide card_fmt, expand card_fmt,
        and auto-expand custom_catalog_frame.
        """
        for term in ["catalog", "katalog", "CATALOG", "Katalog"]:
            self.dash._collapse_all_settings()
            self.dash._on_settings_search_changed(term)
            self.app.processEvents()

            self.assertFalse(self.dash.card_fmt.isHidden(), f"card_fmt should be visible for '{term}'")
            self.assertTrue(self.dash.card_fmt.is_expanded, f"card_fmt should be expanded for '{term}'")
            self.assertTrue(self.dash.custom_catalog_frame.is_expanded, f"custom_catalog_frame should be expanded for '{term}'")

    def test_auto_expansion_opacity_and_transparenz(self):
        """
        'opacity', 'transparenz', and 'deckkraft' must unhide card_hud, expand card_hud,
        and auto-expand hud_sliders_frame.
        """
        for term in ["opacity", "transparenz", "deckkraft", "OPACITY", "Transparenz"]:
            self.dash._collapse_all_settings()
            self.dash._on_settings_search_changed(term)
            self.app.processEvents()

            self.assertFalse(self.dash.card_hud.isHidden(), f"card_hud should be visible for '{term}'")
            self.assertTrue(self.dash.card_hud.is_expanded, f"card_hud should be expanded for '{term}'")
            self.assertTrue(self.dash.hud_sliders_frame.is_expanded, f"hud_sliders_frame should be expanded for '{term}'")

    def test_auto_expansion_scale_and_skalierung(self):
        """
        'scale' and 'skalierung' must unhide card_hud, expand card_hud,
        and auto-expand hud_sliders_frame.
        """
        for term in ["scale", "skalierung", "SCALE", "Skalierung"]:
            self.dash._collapse_all_settings()
            self.dash._on_settings_search_changed(term)
            self.app.processEvents()

            self.assertFalse(self.dash.card_hud.isHidden(), f"card_hud should be visible for '{term}'")
            self.assertTrue(self.dash.card_hud.is_expanded, f"card_hud should be expanded for '{term}'")
            self.assertTrue(self.dash.hud_sliders_frame.is_expanded, f"hud_sliders_frame should be expanded for '{term}'")

    def test_auto_expansion_cache_and_zwischenspeicher(self):
        """
        'cache' and 'zwischenspeicher' must unhide card_adv, expand card_adv,
        and auto-expand dev_options_frame.
        """
        for term in ["cache", "zwischenspeicher", "CACHE", "Zwischenspeicher"]:
            self.dash._collapse_all_settings()
            self.dash._on_settings_search_changed(term)
            self.app.processEvents()

            self.assertFalse(self.dash.card_adv.isHidden(), f"card_adv should be visible for '{term}'")
            self.assertTrue(self.dash.card_adv.is_expanded, f"card_adv should be expanded for '{term}'")
            self.assertTrue(self.dash.dev_options_frame.is_expanded, f"dev_options_frame should be expanded for '{term}'")

    def test_auto_expansion_adv_formatting(self):
        """
        'markdown' and 'filler' must unhide card_fmt, expand card_fmt,
        and auto-expand adv_formatting_frame.
        """
        for term in ["markdown", "filler", "füllwörter", "seeding"]:
            self.dash._collapse_all_settings()
            self.dash._on_settings_search_changed(term)
            self.app.processEvents()

            self.assertFalse(self.dash.card_fmt.isHidden(), f"card_fmt should be visible for '{term}'")
            self.assertTrue(self.dash.card_fmt.is_expanded, f"card_fmt should be expanded for '{term}'")
            self.assertTrue(self.dash.adv_formatting_frame.is_expanded, f"adv_formatting_frame should be expanded for '{term}'")

    # =========================================================================
    # 3. Rapid Sequential Bursts, Tab Switching, and Expand/Collapse Cycles
    # =========================================================================
    def test_rapid_sequential_search_burst_stress(self):
        """
        Stress test: 120 alternating queries switching between disclosures, empty,
        and non-matching queries.
        """
        queries = [
            "bridge", "", "storage", "   ", "catalog", "\u200b", "opacity",
            "scale", "cache", "nonexistent_token_999", "zwischenspeicher",
            "lan", "skalierung", "transparenz", "speicher", "katalog", "filler"
        ] * 7  # 119 queries

        for q in queries:
            self.dash._on_settings_search_changed(q)

        # Final reset
        self.dash._on_settings_search_changed("")
        self.app.processEvents()
        for card in self.dash.all_settings_cards:
            self.assertFalse(card.isHidden())
        self.assertTrue(self.dash.card_audio.is_expanded)

    def test_tab_switching_under_active_filter(self):
        """
        Verify that switching tabs while a search filter is active does not corrupt
        the settings card states or crash.
        """
        self.dash._on_settings_search_changed("bridge")
        self.app.processEvents()
        self.assertFalse(self.dash.card_audio.isHidden())
        self.assertTrue(self.dash.sub_mob_bridge.is_expanded)

        # Switch across tabs 0 -> 1 -> 2 -> 3 -> 1
        for tab_idx in [0, 1, 2, 3, 1]:
            self.dash.tabs.setCurrentIndex(tab_idx)
            self.app.processEvents()

        # Returning to settings tab (index 1) maintains the filtered state
        self.assertFalse(self.dash.card_audio.isHidden())
        self.assertTrue(self.dash.sub_mob_bridge.is_expanded)

        # Clear search
        self.dash._on_settings_search_changed("")
        self.app.processEvents()
        for card in self.dash.all_settings_cards:
            self.assertFalse(card.isHidden())

    def test_expand_all_collapse_all_repeated_cycles(self):
        """
        Verify that _expand_all_settings() and _collapse_all_settings()
        can be called 30 times in alternating sequence with 100% state consistency.
        """
        for i in range(30):
            if i % 2 == 0:
                self.dash._expand_all_settings()
                for card in self.dash.all_settings_cards:
                    self.assertTrue(card.is_expanded, f"Card should be expanded on iteration {i}")
                for disc in self.dash.all_disclosure_sections:
                    self.assertTrue(disc.is_expanded, f"Disclosure should be expanded on iteration {i}")
            else:
                self.dash._collapse_all_settings()
                for card in self.dash.all_settings_cards:
                    self.assertFalse(card.is_expanded, f"Card should be collapsed on iteration {i}")
                for disc in self.dash.all_disclosure_sections:
                    self.assertFalse(disc.is_expanded, f"Disclosure should be collapsed on iteration {i}")


if __name__ == "__main__":
    unittest.main()
