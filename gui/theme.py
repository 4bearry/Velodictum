"""
Velodictum - Minimalist Studio Design System (Liquid Glass Edition)
High-end, calm, distraction-free desktop aesthetic for Windows with native Acrylic backdrop and specular highlights.
"""

import sys
import ctypes
from ctypes import c_int

VELODICTUM_STYLESHEET = """
/* Global Window & Base Palette - Liquid Glass (Translucent Acrylic) */
QWidget {
    background-color: transparent;
    color: #eeeeef;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', Roboto, sans-serif;
    font-size: 12px;
    selection-background-color: rgba(56, 189, 248, 0.25);
    selection-color: #ffffff;
    outline: none;
}

QMainWindow, QDialog {
    background-color: rgba(14, 14, 18, 0.72);
}

/* Seamless Scroll Areas */
QScrollArea {
    border: none;
    background-color: transparent;
}

QScrollArea > QWidget > QWidget {
    background-color: transparent;
}

/* Elevated Frosted Glass Cards (Specular light edge on top) */
QFrame#card {
    background-color: rgba(255, 255, 255, 0.032);
    border-top: 1px solid rgba(255, 255, 255, 0.12);
    border-bottom: 1px solid rgba(255, 255, 255, 0.025);
    border-left: 1px solid rgba(255, 255, 255, 0.05);
    border-right: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 9px;
}

QFrame#hero_card {
    background-color: rgba(255, 255, 255, 0.045);
    border-top: 1px solid rgba(255, 255, 255, 0.16);
    border-bottom: 1px solid rgba(255, 255, 255, 0.03);
    border-left: 1px solid rgba(255, 255, 255, 0.07);
    border-right: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 9px;
}

/* Section & Group Headers */
QLabel#brand_title {
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 0.3px;
    color: #ffffff;
}

QLabel#brand_tag {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.4px;
    color: #93c5fd;
    background-color: rgba(56, 189, 248, 0.1);
    padding: 2px 6px;
    border-radius: 4px;
    border: 1px solid rgba(56, 189, 248, 0.2);
}

QLabel#section_title {
    font-size: 10.5px;
    font-weight: 700;
    letter-spacing: 0.8px;
    color: #94a3b8;
    text-transform: uppercase;
}

/* Sleek Segmented Tab Navigation */
QTabWidget::pane {
    border: none;
    background-color: transparent;
}

QTabBar {
    background-color: rgba(20, 20, 26, 0.6);
    border-radius: 7px;
    padding: 2px;
    border: 1px solid rgba(255, 255, 255, 0.05);
}

QTabBar::tab {
    background-color: transparent;
    color: #94a3b8;
    font-weight: 600;
    font-size: 11.5px;
    letter-spacing: 0.2px;
    padding: 5px 14px;
    border-radius: 5px;
    border: none;
    margin: 0 1px;
}

QTabBar::tab:selected {
    background-color: rgba(255, 255, 255, 0.09);
    color: #ffffff;
    border-top: 1px solid rgba(255, 255, 255, 0.15);
}

QTabBar::tab:hover:!selected {
    color: #e2e8f0;
    background-color: rgba(255, 255, 255, 0.04);
}

/* Clean Form Controls (Translucent glass) */
QComboBox {
    background-color: rgba(255, 255, 255, 0.04);
    color: #f1f1f4;
    border-top: 1px solid rgba(255, 255, 255, 0.12);
    border-bottom: 1px solid rgba(255, 255, 255, 0.04);
    border-left: 1px solid rgba(255, 255, 255, 0.06);
    border-right: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 6px;
    padding: 6px 10px;
    min-height: 18px;
    font-size: 12px;
}

QComboBox:hover {
    background-color: rgba(255, 255, 255, 0.07);
    border-color: rgba(255, 255, 255, 0.18);
}

QComboBox:focus {
    border-color: rgba(56, 189, 248, 0.55);
    background-color: rgba(255, 255, 255, 0.06);
}

QComboBox::drop-down {
    border: none;
    padding-right: 6px;
}

QComboBox QAbstractItemView {
    background-color: #15151c;
    color: #eeeeef;
    border: 1px solid rgba(255, 255, 255, 0.1);
    selection-background-color: rgba(56, 189, 248, 0.2);
    selection-color: #ffffff;
    border-radius: 6px;
    outline: none;
    padding: 4px;
}

QLineEdit {
    background-color: rgba(255, 255, 255, 0.04);
    color: #f1f1f4;
    border-top: 1px solid rgba(255, 255, 255, 0.12);
    border-bottom: 1px solid rgba(255, 255, 255, 0.04);
    border-left: 1px solid rgba(255, 255, 255, 0.06);
    border-right: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}

QLineEdit:hover {
    background-color: rgba(255, 255, 255, 0.07);
    border-color: rgba(255, 255, 255, 0.18);
}

QLineEdit:focus {
    border-color: rgba(56, 189, 248, 0.55);
    background-color: rgba(255, 255, 255, 0.06);
}

/* Precision Glass Buttons */
QPushButton {
    background-color: rgba(255, 255, 255, 0.045);
    color: #e2e8f0;
    font-weight: 500;
    font-size: 12px;
    border-top: 1px solid rgba(255, 255, 255, 0.14);
    border-bottom: 1px solid rgba(255, 255, 255, 0.03);
    border-left: 1px solid rgba(255, 255, 255, 0.07);
    border-right: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 6px;
    padding: 5px 12px;
    min-height: 18px;
}

QPushButton:hover {
    background-color: rgba(255, 255, 255, 0.09);
    border-color: rgba(255, 255, 255, 0.22);
    color: #ffffff;
}

QPushButton#btn_primary {
    background-color: rgba(29, 78, 216, 0.4);
    color: #bae6fd;
    font-weight: 600;
    border: 1px solid rgba(56, 189, 248, 0.45);
    border-radius: 6px;
}

QPushButton#btn_primary:hover {
    background-color: rgba(37, 99, 235, 0.6);
    border-color: rgba(56, 189, 248, 0.7);
    color: #ffffff;
}

QPushButton#btn_secondary {
    background-color: transparent;
    color: #94a3b8;
    font-weight: 500;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 5px;
    padding: 3px 8px;
}

QPushButton#btn_secondary:hover {
    background-color: rgba(255, 255, 255, 0.06);
    color: #f1f5f9;
    border-color: rgba(255, 255, 255, 0.16);
}

/* Glass Checkboxes */
QCheckBox {
    spacing: 8px;
    color: #cbd5e1;
    font-size: 12px;
}

QCheckBox:hover {
    color: #ffffff;
}

QCheckBox::indicator {
    width: 15px;
    height: 15px;
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 3.5px;
    background-color: rgba(20, 20, 26, 0.6);
}

QCheckBox::indicator:hover {
    border-color: rgba(255, 255, 255, 0.35);
    background-color: rgba(30, 30, 38, 0.8);
}

QCheckBox::indicator:checked {
    background-color: #2563eb;
    border-color: #38bdf8;
}

/* Minimalist Scrollbars */
QScrollBar:vertical {
    background-color: transparent;
    width: 4px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: rgba(255, 255, 255, 0.12);
    min-height: 20px;
    border-radius: 2px;
}

QScrollBar::handle:vertical:hover {
    background-color: rgba(255, 255, 255, 0.25);
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""

# Aliases for backward compatibility
LIQUID_GLASS_STYLESHEET = VELODICTUM_STYLESHEET
DARK_STYLESHEET = VELODICTUM_STYLESHEET


def get_stylesheet(liquid_glass: bool = True) -> str:
    """Returns the unified Velodictum Liquid Glass stylesheet."""
    return VELODICTUM_STYLESHEET


def apply_window_backdrop(win_id: int, enable_liquid_glass: bool = True) -> bool:
    """
    Applies Windows 11 Acrylic / DWM Blur to a window hwnd.
    Returns True if successfully applied, False on unsupported platforms.
    """
    if sys.platform != "win32":
        return False

    try:
        # DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        # DWMWA_SYSTEMBACKDROP_TYPE = 38 (3 = Acrylic)
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        DWMWA_SYSTEMBACKDROP_TYPE = 38

        dark_mode = c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            win_id,
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(dark_mode),
            ctypes.sizeof(dark_mode),
        )

        backdrop_val = c_int(3)
        res = ctypes.windll.dwmapi.DwmSetWindowAttribute(
            win_id,
            DWMWA_SYSTEMBACKDROP_TYPE,
            ctypes.byref(backdrop_val),
            ctypes.sizeof(backdrop_val),
        )
        return res == 0
    except Exception:
        return False
