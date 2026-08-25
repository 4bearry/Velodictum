"""
Velodictum - First-Run Language Selection Dialog
Liquid Glass modal welcoming users and configuring the primary interface language.
"""
from typing import Optional
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QWidget,
)

from config import config
from gui.theme import apply_window_backdrop
from gui.signals import signals
import i18n


class LanguageOptionCard(QFrame):
    clicked = pyqtSignal(str)

    def __init__(self, lang_code: str, title: str, subtitle: str, badge: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.lang_code = lang_code
        self.selected = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("LanguageOptionCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(6)

        row_top = QHBoxLayout()
        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #f4f4f6; background: transparent;")
        row_top.addWidget(self.lbl_title)

        if badge:
            self.lbl_badge = QLabel(badge)
            self.lbl_badge.setStyleSheet(
                "background-color: rgba(56, 189, 248, 0.15); color: #38bdf8; "
                "font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 4px;"
            )
            row_top.addWidget(self.lbl_badge)

        row_top.addStretch(1)
        layout.addLayout(row_top)

        self.lbl_desc = QLabel(subtitle)
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setStyleSheet("font-size: 11.5px; color: #9d9da8; line-height: 1.3; background: transparent;")
        layout.addWidget(self.lbl_desc)

        self._update_style()

    def set_selected(self, selected: bool):
        self.selected = selected
        self._update_style()

    def _update_style(self):
        if self.selected:
            self.setStyleSheet(
                "QFrame#LanguageOptionCard { background-color: #172033; border: 1.5px solid #38bdf8; border-radius: 8px; } "
                "QLabel { background: transparent; }"
            )
        else:
            self.setStyleSheet(
                "QFrame#LanguageOptionCard { background-color: rgba(255, 255, 255, 0.025); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 8px; } "
                "QFrame#LanguageOptionCard:hover { background-color: rgba(255, 255, 255, 0.05); border-color: rgba(255, 255, 255, 0.12); } "
                "QLabel { background: transparent; }"
            )

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.lang_code)
        super().mousePressEvent(event)


class LanguageSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_lang = getattr(config.system, "ui_language", "en")
        self.setWindowTitle("Velodictum - Language Selection")
        self.setFixedSize(540, 390)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        self.setStyleSheet("QDialog { background-color: #0c0c0f; color: #f1f1f4; } QLabel { background: transparent; }")
        apply_window_backdrop(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 24)
        layout.setSpacing(14)

        # Title & Subtitle
        lbl_welcome = QLabel("Welcome to Velodictum")
        lbl_welcome.setStyleSheet("font-size: 20px; font-weight: 800; color: #ffffff; letter-spacing: -0.3px; background: transparent;")
        layout.addWidget(lbl_welcome)

        lbl_sub = QLabel("Please choose your preferred interface language to continue:")
        lbl_sub.setStyleSheet("font-size: 12.5px; color: #8e8e98; background: transparent;")
        layout.addWidget(lbl_sub)

        layout.addSpacing(6)

        # Options Container
        self.card_en = LanguageOptionCard(
            lang_code="en",
            title="English",
            subtitle="Full English user interface with international transcription presets.",
            badge="DEFAULT",
            parent=self,
        )
        self.card_en.clicked.connect(self._select_lang)
        layout.addWidget(self.card_en)

        self.card_de = LanguageOptionCard(
            lang_code="de",
            title="Deutsch (German)",
            subtitle="Deutsche Benutzeroberfläche mit optimierten Diktierprofilen für Deutsch.",
            badge="DEUTSCH",
            parent=self,
        )
        self.card_de.clicked.connect(self._select_lang)
        layout.addWidget(self.card_de)

        layout.addSpacing(10)

        # Bottom Button Row
        row_btn = QHBoxLayout()
        row_btn.addStretch(1)

        self.btn_confirm = QPushButton("Continue / Fortfahren")
        self.btn_confirm.setStyleSheet(
            "QPushButton { background-color: #0284c7; color: #ffffff; font-weight: 700; font-size: 13px; "
            "padding: 8px 24px; border-radius: 6px; border: none; } "
            "QPushButton:hover { background-color: #0369a1; } "
            "QPushButton:pressed { background-color: #075985; }"
        )
        self.btn_confirm.clicked.connect(self._confirm)
        row_btn.addWidget(self.btn_confirm)

        layout.addLayout(row_btn)

        self._update_cards()

    def _select_lang(self, lang_code: str):
        self.selected_lang = lang_code
        self._update_cards()

    def _update_cards(self):
        self.card_en.set_selected(self.selected_lang == "en")
        self.card_de.set_selected(self.selected_lang == "de")

    def _confirm(self):
        config.system.ui_language = self.selected_lang
        config.system.first_run_completed = True
        i18n.set_current_language(self.selected_lang)
        config.save()
        signals.language_changed.emit(self.selected_lang)
        self.accept()
