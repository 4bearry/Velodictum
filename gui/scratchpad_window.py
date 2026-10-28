from typing import Optional
from PyQt6.QtCore import Qt, QPoint, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit, QPushButton, QFrame, QApplication
)
import pyperclip
from config import config
from gui.signals import signals
from gui.assets import create_app_icon
from gui.theme import (
    ThemeColors,
    ThemeMetrics,
    ThemeTypography,
    apply_window_backdrop,
)
from i18n import tr, get_current_language, set_current_language


class ScratchpadWindow(QMainWindow):
    structuring_completed = pyqtSignal(str)
    structuring_failed = pyqtSignal(str)

    def __init__(self, ai_formatter, parent=None):
        super().__init__(parent)
        self.ai_formatter = ai_formatter
        self._recording_active_in_pad = False
        self._recording_triggered_by_pad = False

        self.setWindowTitle(tr("scratchpad_title"))
        self.setWindowIcon(create_app_icon(32))
        self.resize(480, 500)
        self.setMinimumSize(420, 380)

        # Make floating always-on-top window with custom styling
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowStaysOnTopHint
        )

        central = QWidget(self)
        central.setStyleSheet(f"QWidget {{ background-color: {ThemeColors.BG_DIALOG}; }}")
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        # Header Row
        header = QHBoxLayout()
        header.setSpacing(10)

        self.title_lbl = QLabel(tr("scratchpad_header"))
        self.title_lbl.setStyleSheet(
            f"QLabel {{ "
            f"    font-family: {ThemeTypography.FONT_FAMILY_PRIMARY}; "
            f"    font-size: {ThemeTypography.SIZE_SECTION_TITLE}; "
            f"    font-weight: {ThemeTypography.WEIGHT_BOLD}; "
            f"    color: {ThemeColors.TEXT_PRIMARY}; "
            f"    background: transparent; "
            f"}}"
        )
        
        tag = QLabel("Scratchpad")
        tag.setStyleSheet(
            f"QLabel {{ "
            f"    font-family: {ThemeTypography.FONT_FAMILY_PRIMARY}; "
            f"    font-size: {ThemeTypography.SIZE_BADGE}; "
            f"    font-weight: {ThemeTypography.WEIGHT_SEMIBOLD}; "
            f"    color: {ThemeColors.ACCENT_INDIGO_TEXT}; "
            f"    background-color: {ThemeColors.ACCENT_INDIGO_MUTED}; "
            f"    padding: 3px 9px; "
            f"    border-radius: {ThemeMetrics.RADIUS_BADGE}; "
            f"    border: 1px solid {ThemeColors.ACCENT_INDIGO_BORDER}; "
            f"}}"
        )

        self.lbl_stats = QLabel(tr("scratchpad_stats", words=0, chars=0))
        self.lbl_stats.setStyleSheet(
            f"QLabel {{ "
            f"    font-family: {ThemeTypography.FONT_FAMILY_PRIMARY}; "
            f"    font-size: {ThemeTypography.SIZE_CAPTION}; "
            f"    color: {ThemeColors.TEXT_MUTED}; "
            f"    background: transparent; "
            f"}}"
        )

        header.addWidget(self.title_lbl)
        header.addWidget(tag)
        header.addStretch()
        header.addWidget(self.lbl_stats)
        layout.addLayout(header)

        # Sunken Neomorphic Text Editor Area
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText(tr("scratchpad_placeholder"))
        self.text_edit.setStyleSheet(
            f"QTextEdit {{ "
            f"    background-color: {ThemeColors.BG_SUNKEN}; "
            f"    color: {ThemeColors.TEXT_PRIMARY}; "
            f"    font-family: {ThemeTypography.FONT_FAMILY_PRIMARY}; "
            f"    font-size: {ThemeTypography.SIZE_BODY_LARGE}; "
            f"    line-height: {ThemeTypography.LINE_HEIGHT_RELAXED}; "
            f"    border-top: 1px solid {ThemeColors.BORDER_SUNKEN_TOP}; "
            f"    border-left: 1px solid {ThemeColors.BORDER_SUNKEN_LEFT}; "
            f"    border-bottom: 1px solid {ThemeColors.BORDER_SUNKEN_BOTTOM}; "
            f"    border-right: 1px solid {ThemeColors.BORDER_SUNKEN_RIGHT}; "
            f"    border-radius: {ThemeMetrics.RADIUS_CARD}; "
            f"    padding: 14px; "
            f"}} "
            f"QTextEdit:hover {{ "
            f"    border-color: {ThemeColors.BORDER_HOVER}; "
            f"}} "
            f"QTextEdit:focus {{ "
            f"    border: 2px solid {ThemeColors.BORDER_FOCUS}; "
            f"    background-color: {ThemeColors.BG_INPUT_FOCUS}; "
            f"}}"
        )
        self.text_edit.textChanged.connect(self._update_stats)
        layout.addWidget(self.text_edit)

        # Action Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        # 1. Microphone Dictate Button (1-Click Voice Input without Hotkey - Coral Primary CTA)
        self.btn_mic = QPushButton(tr("btn_dictate"))
        self.btn_mic.setCursor(Qt.CursorShape.PointingHandCursor)
        self._set_mic_btn_idle()
        self.btn_mic.clicked.connect(self._on_mic_clicked)

        # 2. AI Structuring Button (Muted Indigo Secondary Accent)
        self.btn_structure = QPushButton(tr("btn_structure"))
        self.btn_structure.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_structure.setStyleSheet(
            f"QPushButton {{ "
            f"    background-color: {ThemeColors.ACCENT_INDIGO_MUTED}; "
            f"    color: {ThemeColors.ACCENT_INDIGO_TEXT}; "
            f"    font-family: {ThemeTypography.FONT_FAMILY_PRIMARY}; "
            f"    font-size: 12px; "
            f"    font-weight: {ThemeTypography.WEIGHT_SEMIBOLD}; "
            f"    border: 1px solid {ThemeColors.ACCENT_INDIGO_BORDER}; "
            f"    border-radius: {ThemeMetrics.RADIUS_CONTROL}; "
            f"    padding: {ThemeMetrics.PADDING_BUTTON}; "
            f"}} "
            f"QPushButton:hover {{ "
            f"    background-color: {ThemeColors.ACCENT_INDIGO_SURFACE}; "
            f"    border-color: {ThemeColors.ACCENT_INDIGO_BRIGHT}; "
            f"    color: {ThemeColors.TEXT_PRIMARY}; "
            f"}} "
            f"QPushButton:pressed {{ "
            f"    background-color: {ThemeColors.ACCENT_INDIGO}; "
            f"}} "
            f"QPushButton:focus {{ "
            f"    border: 2px solid {ThemeColors.BORDER_FOCUS}; "
            f"}} "
            f"QPushButton:disabled {{ "
            f"    color: {ThemeColors.TEXT_DISABLED}; "
            f"    border-color: {ThemeColors.BORDER_SUBTLE}; "
            f"    background-color: {ThemeColors.BG_SUNKEN}; "
            f"}}"
        )
        self.btn_structure.clicked.connect(self._structure_notes)

        # 3. Copy to Clipboard (Raised Neomorphic Control)
        self.btn_copy = QPushButton(tr("btn_copy_note"))
        self.btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy.setStyleSheet(
            f"QPushButton {{ "
            f"    background-color: {ThemeColors.BG_ELEVATED}; "
            f"    color: {ThemeColors.TEXT_SECONDARY}; "
            f"    font-family: {ThemeTypography.FONT_FAMILY_PRIMARY}; "
            f"    font-size: 12px; "
            f"    font-weight: {ThemeTypography.WEIGHT_SEMIBOLD}; "
            f"    border-top: 1px solid {ThemeColors.BORDER_SPECULAR_TOP}; "
            f"    border-left: 1px solid {ThemeColors.BORDER_SUBTLE}; "
            f"    border-bottom: 1px solid {ThemeColors.BORDER_BOTTOM}; "
            f"    border-right: 1px solid {ThemeColors.BORDER_BOTTOM}; "
            f"    border-radius: {ThemeMetrics.RADIUS_CONTROL}; "
            f"    padding: {ThemeMetrics.PADDING_BUTTON}; "
            f"}} "
            f"QPushButton:hover {{ "
            f"    background-color: {ThemeColors.BG_CARD_HOVER}; "
            f"    border-color: {ThemeColors.BORDER_HOVER}; "
            f"    color: {ThemeColors.TEXT_PRIMARY}; "
            f"}} "
            f"QPushButton:pressed {{ "
            f"    background-color: {ThemeColors.BG_SUNKEN}; "
            f"}} "
            f"QPushButton:focus {{ "
            f"    border: 2px solid {ThemeColors.BORDER_FOCUS}; "
            f"}}"
        )
        self.btn_copy.clicked.connect(self._copy_to_clipboard)

        # 4. Clear Scratchpad
        self.btn_clear = QPushButton(tr("btn_clear_note"))
        self.btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear.setStyleSheet(
            f"QPushButton {{ "
            f"    background-color: transparent; "
            f"    color: {ThemeColors.TEXT_MUTED}; "
            f"    font-family: {ThemeTypography.FONT_FAMILY_PRIMARY}; "
            f"    font-size: {ThemeTypography.SIZE_CAPTION}; "
            f"    font-weight: {ThemeTypography.WEIGHT_MEDIUM}; "
            f"    border: 1px solid {ThemeColors.BORDER_SUBTLE}; "
            f"    border-radius: {ThemeMetrics.RADIUS_CONTROL}; "
            f"    padding: {ThemeMetrics.PADDING_BUTTON_SM}; "
            f"}} "
            f"QPushButton:hover {{ "
            f"    color: {ThemeColors.ERROR}; "
            f"    background-color: {ThemeColors.ERROR_MUTED}; "
            f"    border-color: {ThemeColors.ERROR_BORDER}; "
            f"}} "
            f"QPushButton:pressed {{ "
            f"    background-color: rgba(239, 68, 68, 0.25); "
            f"}} "
            f"QPushButton:focus {{ "
            f"    border: 2px solid {ThemeColors.BORDER_FOCUS}; "
            f"}}"
        )
        self.btn_clear.clicked.connect(self.text_edit.clear)

        toolbar.addWidget(self.btn_mic)
        toolbar.addWidget(self.btn_structure)
        toolbar.addWidget(self.btn_copy)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_clear)
        layout.addLayout(toolbar)

        # Connect event bus signals
        signals.scratchpad_toggle_requested.connect(self.toggle_visibility)
        signals.recording_started.connect(self._on_recording_started)
        signals.recording_stopped.connect(self._on_recording_stopped)
        signals.transcription_started.connect(self._on_transcribing)
        signals.formatting_started.connect(self._on_formatting)
        signals.transcription_completed.connect(self._on_transcribe_done)
        signals.transcription_failed.connect(self._on_transcribe_done)
        signals.language_changed.connect(self.retranslate_ui)

        # Connect internal thread-safe signals
        self.structuring_completed.connect(self._on_structuring_completed)
        self.structuring_failed.connect(self._on_structuring_failed)

    def retranslate_ui(self, lang_code: Optional[str] = None):
        if lang_code and isinstance(lang_code, str) and lang_code in ("en", "de"):
            set_current_language(lang_code)
        self.setWindowTitle(tr("scratchpad_title"))
        if hasattr(self, "title_lbl"):
            self.title_lbl.setText(tr("scratchpad_header"))
        if hasattr(self, "text_edit") and not self.text_edit.toPlainText().strip():
            self.text_edit.setPlaceholderText(tr("scratchpad_placeholder"))
        if hasattr(self, "btn_structure"):
            self.btn_structure.setText(tr("btn_structure"))
        if hasattr(self, "btn_copy"):
            copy_text = tr("btn_copy_note")
            if get_current_language() == "de":
                if "notiz" not in copy_text.lower() or "Kopieren" not in copy_text:
                    copy_text = "Notiz Kopieren"
            self.btn_copy.setText(copy_text)
        if hasattr(self, "btn_clear"):
            self.btn_clear.setText(tr("btn_clear_note"))
        self._set_mic_btn_idle()
        self._update_stats()

    def _is_scratchpad_focused(self) -> bool:
        """Check if Scratchpad is active, has focus, or triggered the recording."""
        if getattr(self, "_recording_triggered_by_pad", False):
            return True
        if self.isActiveWindow() or self.text_edit.hasFocus():
            return True
        try:
            import ctypes
            active_hwnd = ctypes.windll.user32.GetForegroundWindow()
            if active_hwnd == int(self.winId()):
                return True
        except Exception:
            pass
        return False

    def _set_mic_btn_idle(self):
        self.btn_mic.setText(tr("btn_dictate"))
        self.btn_mic.setEnabled(True)
        self.btn_mic.setStyleSheet(
            f"QPushButton {{ "
            f"    background-color: {ThemeColors.ACCENT_CORAL}; "
            f"    color: #ffffff; "
            f"    font-family: {ThemeTypography.FONT_FAMILY_PRIMARY}; "
            f"    font-size: 12px; "
            f"    font-weight: {ThemeTypography.WEIGHT_BOLD}; "
            f"    border-top: 1px solid #f89073; "
            f"    border-left: 1px solid #f0643b; "
            f"    border-bottom: 1px solid #b53d1e; "
            f"    border-right: 1px solid #b53d1e; "
            f"    border-radius: {ThemeMetrics.RADIUS_CONTROL}; "
            f"    padding: {ThemeMetrics.PADDING_BUTTON}; "
            f"}} "
            f"QPushButton:hover {{ "
            f"    background-color: {ThemeColors.ACCENT_CORAL_HOVER}; "
            f"    border-top: 1px solid #fca58d; "
            f"}} "
            f"QPushButton:pressed {{ "
            f"    background-color: {ThemeColors.ACCENT_CORAL_PRESSED}; "
            f"}} "
            f"QPushButton:focus {{ "
            f"    border: 2px solid {ThemeColors.BORDER_FOCUS}; "
            f"}}"
        )

    def _on_mic_clicked(self):
        """Trigger voice dictation directly from the scratchpad without needing a hotkey."""
        self._recording_triggered_by_pad = True
        self.raise_()
        self.activateWindow()
        self.text_edit.setFocus()
        signals.dictation_toggle_requested.emit()

    def _on_recording_started(self):
        if self._is_scratchpad_focused():
            self._recording_active_in_pad = True
            self.btn_mic.setText(tr("btn_dictate_recording"))
            self.btn_mic.setEnabled(True)
            self.btn_mic.setStyleSheet(
                f"QPushButton {{ "
                f"    background-color: {ThemeColors.ERROR}; "
                f"    color: {ThemeColors.TEXT_PRIMARY}; "
                f"    font-family: {ThemeTypography.FONT_FAMILY_PRIMARY}; "
                f"    font-size: 12px; "
                f"    font-weight: {ThemeTypography.WEIGHT_BOLD}; "
                f"    border: 1.5px solid {ThemeColors.ERROR_BORDER}; "
                f"    border-radius: {ThemeMetrics.RADIUS_CONTROL}; "
                f"    padding: {ThemeMetrics.PADDING_BUTTON}; "
                f"}} "
                f"QPushButton:hover {{ "
                f"    background-color: #dc2626; "
                f"}}"
            )
        else:
            self._recording_active_in_pad = False
            self._set_mic_btn_idle()

    def _on_recording_stopped(self):
        if self._recording_active_in_pad:
            self.btn_mic.setText(tr("btn_dictate_processing"))
            self.btn_mic.setEnabled(False)
            self.btn_mic.setStyleSheet(
                f"QPushButton {{ "
                f"    background-color: {ThemeColors.ACCENT_INDIGO_MUTED}; "
                f"    color: {ThemeColors.ACCENT_INDIGO_TEXT}; "
                f"    font-family: {ThemeTypography.FONT_FAMILY_PRIMARY}; "
                f"    font-size: 12px; "
                f"    font-weight: {ThemeTypography.WEIGHT_SEMIBOLD}; "
                f"    border: 1px solid {ThemeColors.ACCENT_INDIGO_BORDER}; "
                f"    border-radius: {ThemeMetrics.RADIUS_CONTROL}; "
                f"    padding: {ThemeMetrics.PADDING_BUTTON}; "
                f"}}"
            )

    def _on_transcribing(self):
        if self._recording_active_in_pad:
            self.btn_mic.setText(tr("processing"))
            self.btn_mic.setEnabled(False)

    def _on_formatting(self):
        if self._recording_active_in_pad:
            self.btn_mic.setText(tr("formatting"))
            self.btn_mic.setEnabled(False)

    def _on_transcribe_done(self, *args):
        self._recording_active_in_pad = False
        self._recording_triggered_by_pad = False
        self._set_mic_btn_idle()

    def _update_stats(self):
        text = self.text_edit.toPlainText().strip()
        if not text:
            self.lbl_stats.setText(tr("scratchpad_stats", words=0, chars=0))
            return
        words = len(text.split())
        chars = len(text)
        self.lbl_stats.setText(tr("scratchpad_stats", words=words, chars=chars))

    def _copy_to_clipboard(self):
        text = self.text_edit.toPlainText().strip()
        if text:
            try:
                pyperclip.copy(text)
                self.btn_copy.setText(tr("copied"))
                def _restore_copy_label():
                    copy_text = tr("btn_copy_note")
                    if get_current_language() == "de":
                        if "notiz" not in copy_text.lower() or "Kopieren" not in copy_text:
                            copy_text = "Notiz Kopieren"
                    self.btn_copy.setText(copy_text)
                QTimer.singleShot(1500, _restore_copy_label)
            except Exception:
                pass

    def _structure_notes(self):
        """Restructure and clean up raw notes/thoughts into organized Markdown."""
        text = self.text_edit.toPlainText().strip()
        if not text:
            return
        self.btn_structure.setText(tr("btn_structuring"))
        self.btn_structure.setEnabled(False)

        import threading

        def _worker():
            try:
                cur_lang = get_current_language()
                if hasattr(self.ai_formatter, "structure_notes"):
                    structured = self.ai_formatter.structure_notes(text, language=cur_lang)
                else:
                    res = self.ai_formatter.format_text(text, language=cur_lang)
                    structured = res.get("text", text)
                self.structuring_completed.emit(structured)
            except Exception as e:
                print(f"[Scratchpad] Structuring error: {e}")
                self.structuring_failed.emit(str(e))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_structuring_completed(self, structured: str):
        if structured and structured.strip():
            self.text_edit.setPlainText(structured.strip())
        self.btn_structure.setText(tr("btn_structure"))
        self.btn_structure.setEnabled(True)

    def _on_structuring_failed(self, err_msg: str):
        self.btn_structure.setText(tr("btn_structure"))
        self.btn_structure.setEnabled(True)

    def showEvent(self, event):
        super().showEvent(event)
        apply_window_backdrop(self)

    def toggle_visibility(self):
        def _exec_toggle():
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.raise_()
                self.activateWindow()
                self.text_edit.setFocus()

        QTimer.singleShot(0, _exec_toggle)