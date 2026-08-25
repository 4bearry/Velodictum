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
from gui.theme import apply_window_backdrop
from i18n import tr, get_current_language


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
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # Header Row
        header = QHBoxLayout()
        header.setSpacing(8)

        self.title_lbl = QLabel(tr("scratchpad_header"))
        self.title_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #ffffff;")
        
        tag = QLabel("Scratchpad")
        tag.setStyleSheet(
            "font-size: 9.5px; font-weight: 600; color: #82828e; background-color: rgba(255, 255, 255, 0.05); "
            "padding: 2px 6px; border-radius: 4px;"
        )

        self.lbl_stats = QLabel(tr("scratchpad_stats", words=0, chars=0))
        self.lbl_stats.setStyleSheet("font-size: 11px; color: #686874;")

        header.addWidget(self.title_lbl)
        header.addWidget(tag)
        header.addStretch()
        header.addWidget(self.lbl_stats)
        layout.addLayout(header)

        # Text Editor Area
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText(tr("scratchpad_placeholder"))
        self.text_edit.setStyleSheet(
            "QTextEdit { background-color: #131317; color: #f1f1f4; font-size: 12.5px; line-height: 1.5; "
            "border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 8px; padding: 12px; } "
            "QTextEdit:focus { border: 1px solid rgba(56, 189, 248, 0.4); }"
        )
        self.text_edit.textChanged.connect(self._update_stats)
        layout.addWidget(self.text_edit)

        # Action Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        # 1. Microphone Dictate Button (1-Click Voice Input without Hotkey)
        self.btn_mic = QPushButton(tr("btn_dictate"))
        self.btn_mic.setCursor(Qt.CursorShape.PointingHandCursor)
        self._set_mic_btn_idle()
        self.btn_mic.clicked.connect(self._on_mic_clicked)

        # 2. AI Structuring Button
        self.btn_structure = QPushButton(tr("btn_structure"))
        self.btn_structure.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_structure.setStyleSheet(
            "QPushButton { background-color: rgba(56, 189, 248, 0.08); color: #38bdf8; font-weight: 600; font-size: 11.5px; "
            "border: 1px solid rgba(56, 189, 248, 0.22); border-radius: 5px; padding: 5px 12px; } "
            "QPushButton:hover { background-color: rgba(56, 189, 248, 0.16); border-color: #38bdf8; } "
            "QPushButton:disabled { color: #555562; border-color: rgba(255, 255, 255, 0.05); background-color: transparent; }"
        )
        self.btn_structure.clicked.connect(self._structure_notes)

        # 3. Copy to Clipboard
        self.btn_copy = QPushButton(tr("btn_copy_note"))
        self.btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy.setStyleSheet(
            "QPushButton { background-color: rgba(255, 255, 255, 0.04); color: #eeeeef; font-weight: 500; font-size: 11.5px; "
            "border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 5px; padding: 5px 12px; } "
            "QPushButton:hover { background-color: rgba(255, 255, 255, 0.08); }"
        )
        self.btn_copy.clicked.connect(self._copy_to_clipboard)

        # 4. Clear Scratchpad
        self.btn_clear = QPushButton(tr("btn_clear_note"))
        self.btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear.setStyleSheet(
            "QPushButton { background-color: transparent; color: #787884; font-size: 11px; "
            "border: none; padding: 5px 8px; } "
            "QPushButton:hover { color: #f43f5e; }"
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

    def retranslate_ui(self, lang_code=None):
        self.setWindowTitle(tr("scratchpad_title"))
        if hasattr(self, "title_lbl"):
            self.title_lbl.setText(tr("scratchpad_header"))
        if hasattr(self, "text_edit") and not self.text_edit.toPlainText().strip():
            self.text_edit.setPlaceholderText(tr("scratchpad_placeholder"))
        if hasattr(self, "btn_structure"):
            self.btn_structure.setText(tr("btn_structure"))
        if hasattr(self, "btn_copy"):
            self.btn_copy.setText(tr("btn_copy_note"))
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
            "QPushButton { background-color: #172033; color: #38bdf8; font-weight: 600; font-size: 11.5px; "
            "border: 1px solid rgba(56, 189, 248, 0.35); border-radius: 5px; padding: 5px 14px; } "
            "QPushButton:hover { background-color: #1e293b; border-color: #38bdf8; }"
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
                "QPushButton { background-color: #ef4444; color: #ffffff; font-weight: 600; font-size: 11.5px; "
                "border: 1px solid #f87171; border-radius: 5px; padding: 5px 14px; }"
            )
        else:
            self._recording_active_in_pad = False
            self._set_mic_btn_idle()

    def _on_recording_stopped(self):
        if self._recording_active_in_pad:
            self.btn_mic.setText(tr("btn_dictate_processing"))
            self.btn_mic.setEnabled(False)
            self.btn_mic.setStyleSheet(
                "QPushButton { background-color: #1e3a8a; color: #93c5fd; font-weight: 600; font-size: 11.5px; "
                "border: 1px solid #3b82f6; border-radius: 5px; padding: 5px 14px; }"
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
                QTimer.singleShot(1500, lambda: self.btn_copy.setText(tr("btn_copy_note")))
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
        apply_window_backdrop(int(self.winId()))

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