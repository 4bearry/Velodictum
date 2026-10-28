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
from gui.theme import (
    apply_window_backdrop,
    ThemeColors,
    ThemeTypography,
    ThemeMetrics,
)
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
        self.lbl_title.setStyleSheet(
            f"font-family: {ThemeTypography.FONT_FAMILY_PRIMARY}; "
            f"font-size: {ThemeTypography.SIZE_SECTION_TITLE}; "
            f"font-weight: {ThemeTypography.WEIGHT_BOLD}; "
            f"color: {ThemeColors.TEXT_PRIMARY}; background: transparent;"
        )
        row_top.addWidget(self.lbl_title)

        if badge:
            self.lbl_badge = QLabel(badge)
            self.lbl_badge.setStyleSheet(
                f"background-color: {ThemeColors.ACCENT_INDIGO_MUTED}; "
                f"color: {ThemeColors.ACCENT_INDIGO_TEXT}; "
                f"font-size: {ThemeTypography.SIZE_BADGE}; "
                f"font-weight: {ThemeTypography.WEIGHT_BOLD}; "
                f"letter-spacing: 0.4px; "
                f"padding: 2px 8px; "
                f"border-radius: {ThemeMetrics.RADIUS_BADGE}; "
                f"border: 1px solid {ThemeColors.ACCENT_INDIGO_BORDER};"
            )
            row_top.addWidget(self.lbl_badge)

        row_top.addStretch(1)
        layout.addLayout(row_top)

        self.lbl_desc = QLabel(subtitle)
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setStyleSheet(
            f"font-family: {ThemeTypography.FONT_FAMILY_PRIMARY}; "
            f"font-size: {ThemeTypography.SIZE_CAPTION}; "
            f"color: {ThemeColors.TEXT_MUTED}; "
            f"line-height: {ThemeTypography.LINE_HEIGHT_NORMAL}; "
            f"background: transparent;"
        )
        layout.addWidget(self.lbl_desc)

        self._update_style()

    def set_selected(self, selected: bool):
        self.selected = selected
        self._update_style()

    def _update_style(self):
        if self.selected:
            self.setStyleSheet(
                f"QFrame#LanguageOptionCard {{ background-color: {ThemeColors.BG_CARD_ACTIVE}; "
                f"border: 1.5px solid {ThemeColors.ACCENT_INDIGO_BRIGHT}; "
                f"border-radius: {ThemeMetrics.RADIUS_CARD}; }} "
                "QLabel { background: transparent; }"
            )
        else:
            self.setStyleSheet(
                f"QFrame#LanguageOptionCard {{ background-color: {ThemeColors.BG_CARD}; "
                f"border-top: 1px solid {ThemeColors.BORDER_SPECULAR_TOP}; "
                f"border-left: 1px solid {ThemeColors.BORDER_SUBTLE}; "
                f"border-bottom: 1px solid {ThemeColors.BORDER_BOTTOM}; "
                f"border-right: 1px solid {ThemeColors.BORDER_BOTTOM}; "
                f"border-radius: {ThemeMetrics.RADIUS_CARD}; }} "
                f"QFrame#LanguageOptionCard:hover {{ background-color: {ThemeColors.BG_CARD_HOVER}; "
                f"border-top: 1px solid {ThemeColors.BORDER_SPECULAR_TOP_HOVER}; "
                f"border-left: 1px solid {ThemeColors.BORDER_HOVER}; "
                f"border-right: 1px solid {ThemeColors.BORDER_HOVER}; "
                f"border-bottom: 1px solid {ThemeColors.BORDER_BOTTOM}; }} "
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
        self.setStyleSheet(
            f"QDialog {{ background-color: {ThemeColors.BG_DIALOG}; color: {ThemeColors.TEXT_SECONDARY}; }} "
            f"QLabel {{ background: transparent; }}"
        )
        apply_window_backdrop(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 24)
        layout.setSpacing(14)

        # Title & Subtitle
        lbl_welcome = QLabel("Welcome to Velodictum")
        lbl_welcome.setStyleSheet(
            f"font-family: {ThemeTypography.FONT_FAMILY_DISPLAY}; "
            f"font-size: 20px; font-weight: {ThemeTypography.WEIGHT_BOLD}; "
            f"color: {ThemeColors.TEXT_PRIMARY}; letter-spacing: -0.3px; background: transparent;"
        )
        layout.addWidget(lbl_welcome)

        lbl_sub = QLabel("Please choose your preferred interface language to continue:")
        lbl_sub.setStyleSheet(
            f"font-family: {ThemeTypography.FONT_FAMILY_PRIMARY}; "
            f"font-size: {ThemeTypography.SIZE_BODY_LARGE}; color: {ThemeColors.TEXT_MUTED}; background: transparent;"
        )
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
            f"QPushButton {{ background-color: {ThemeColors.ACCENT_CORAL}; color: #ffffff; "
            f"font-weight: {ThemeTypography.WEIGHT_BOLD}; font-size: 13px; "
            f"padding: 9px 26px; border-radius: {ThemeMetrics.RADIUS_CONTROL}; "
            f"border-top: 1px solid #f89073; border-bottom: 1px solid #b53d1e; }} "
            f"QPushButton:hover {{ background-color: {ThemeColors.ACCENT_CORAL_HOVER}; }} "
            f"QPushButton:pressed {{ background-color: {ThemeColors.ACCENT_CORAL_PRESSED}; }} "
            f"QPushButton:focus {{ border: 2px solid {ThemeColors.BORDER_FOCUS}; }}"
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
