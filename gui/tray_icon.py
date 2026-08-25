"""
Velodictum - System Tray Icon & Context Menu
"""
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QActionGroup
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from gui.assets import create_tray_icon
from gui.signals import signals
from config import config
from i18n import tr, get_current_language


class VelodictumTrayIcon(QSystemTrayIcon):
    def __init__(self, main_window, parent=None):
        super().__init__(create_tray_icon(), parent)
        self.main_window = main_window
        self.setToolTip(tr("tray_tooltip"))

        self._create_menu()
        self.activated.connect(self._on_tray_activated)
        signals.language_changed.connect(self._retranslate_tray)

    def _retranslate_tray(self, lang_code=None):
        self.setToolTip(tr("tray_tooltip"))
        self._create_menu()

    def _create_menu(self):
        menu = QMenu()

        # Status Header
        self.status_action = QAction(f"Velodictum: {tr('ready')}", menu)
        self.status_action.setEnabled(False)
        menu.addAction(self.status_action)
        menu.addSeparator()

        # Open Dashboard Action
        open_action = QAction(tr("tray_open_dashboard"), menu)
        open_action.triggered.connect(self.main_window.show_and_activate)
        menu.addAction(open_action)

        menu.addSeparator()

        # Tier 1: Operating Mode (Flow vs Raw)
        op_menu = menu.addMenu(tr("tray_op_mode"))
        op_group = QActionGroup(op_menu)

        act_flow = QAction(tr("tray_mode_flow"), op_menu, checkable=True)
        act_raw = QAction(tr("tray_mode_raw"), op_menu, checkable=True)

        for act, m_key in [(act_flow, "flow"), (act_raw, "raw")]:
            op_group.addAction(act)
            op_menu.addAction(act)
            current_m = getattr(config.formatting, "mode", "flow")
            if current_m not in ("flow", "raw"):
                current_m = "flow"
            if current_m == m_key:
                act.setChecked(True)
            act.triggered.connect(lambda checked, mk=m_key: self._set_dict_mode(mk))

        # Tier 2: Tone & Style Profiles
        tone_menu = menu.addMenu(tr("tray_tone_menu"))
        tone_group = QActionGroup(tone_menu)

        tone_options = [
            (tr("tone_default_title"), "default"),
            (tr("tone_formal_title"), "formal_sie"),
            (tr("tone_informal_title"), "informal_du"),
            (tr("tone_concise_title"), "concise"),
            (tr("tone_academic_title"), "academic"),
            (tr("tone_latex_title"), "latex"),
        ]

        current_t = getattr(config.formatting, "tone", "default")
        for label, t_key in tone_options:
            act = QAction(label, tone_menu, checkable=True)
            tone_group.addAction(act)
            tone_menu.addAction(act)
            if current_t == t_key:
                act.setChecked(True)
            act.triggered.connect(lambda checked, tk=t_key: self._set_tone(tk))

        menu.addSeparator()

        # Language Submenu
        lang_menu = menu.addMenu(tr("tray_dict_lang"))
        lang_group = QActionGroup(lang_menu)

        opt_auto = QAction(tr("tray_lang_auto"), lang_menu, checkable=True)
        opt_de = QAction(tr("tray_lang_de"), lang_menu, checkable=True)
        opt_en = QAction(tr("tray_lang_en"), lang_menu, checkable=True)

        for act, code in [(opt_auto, None), (opt_de, "de"), (opt_en, "en")]:
            lang_group.addAction(act)
            lang_menu.addAction(act)
            if config.whisper.language == code:
                act.setChecked(True)
            act.triggered.connect(lambda checked, c=code: self._set_language(c))

        # Hotkey Mode Submenu (Push-to-Talk vs Toggle)
        mode_menu = menu.addMenu(tr("tray_trigger_mode"))
        mode_group = QActionGroup(mode_menu)
        mode_ptt = QAction(tr("tray_trigger_ptt"), mode_menu, checkable=True)
        mode_toggle = QAction(tr("tray_trigger_toggle"), mode_menu, checkable=True)

        mode_group.addAction(mode_ptt)
        mode_group.addAction(mode_toggle)
        mode_menu.addAction(mode_ptt)
        mode_menu.addAction(mode_toggle)

        if config.hotkey.mode == "push_to_talk":
            mode_ptt.setChecked(True)
        else:
            mode_toggle.setChecked(True)

        mode_ptt.triggered.connect(lambda: self._set_mode("push_to_talk"))
        mode_toggle.triggered.connect(lambda: self._set_mode("toggle"))

        menu.addSeparator()

        # Quit Action
        quit_action = QAction(tr("tray_quit"), menu)
        quit_action.triggered.connect(self.main_window.close_app)
        menu.addAction(quit_action)

        self.setContextMenu(menu)

    def _set_language(self, lang_code):
        config.whisper.language = lang_code
        config.save()
        signals.language_changed.emit(lang_code or "auto")

    def _set_mode(self, mode):
        config.hotkey.mode = mode
        config.save()
        signals.mode_changed.emit(mode)

    def _set_dict_mode(self, mode_key):
        config.formatting.mode = mode_key
        config.save()
        if hasattr(self.main_window, "ai_formatter"):
            self.main_window.ai_formatter.mode = mode_key
        signals.dictation_mode_changed.emit(mode_key)

    def _set_tone(self, tone_key):
        config.formatting.tone = tone_key
        config.save()
        if hasattr(self.main_window, "ai_formatter"):
            self.main_window.ai_formatter.tone = tone_key
        if hasattr(self.main_window, "tone_cards"):
            for tk, card in self.main_window.tone_cards.items():
                card.set_selected(tk == tone_key)
        if tone_key == "latex" and hasattr(self.main_window, "_on_priority_card_clicked"):
            self.main_window._on_priority_card_clicked("quality")

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.main_window.toggle_visibility()


# Backward compatibility alias
VelodictumTrayIconAlias = VelodictumTrayIcon
