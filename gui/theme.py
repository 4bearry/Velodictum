"""
Velodictum - Dark Neomorphism 2.0 Design System & Theme Engine
Tactile, calm, high-contrast dark desktop aesthetic with raised & recessed graphite surfaces,
Coral/Orange primary CTA, Muted Indigo/Violet selection accents, and Mint/Green system readiness.
"""

import sys
import re
import ctypes
from ctypes import c_int, byref, sizeof
from typing import Union, Any, Optional
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import QWidget, QGraphicsDropShadowEffect


# =========================================================================
# 1. Centralized Theme Color Tokens (Dark Neomorphism 2.0)
# =========================================================================

class ThemeColors:
    """Dark Neomorphism 2.0 Color Palette & Surface Materiality Tokens."""

    # Level 0: Deep Blue-Black Canvas & Window Backing
    BG_WINDOW = "#0b0d14"
    BG_CANVAS = "#0b0d14"
    BG_BASE = "#0b0d14"
    BG_SIDEBAR = "#111520"
    BG_DIALOG = "#111520"
    BG_POPOVER = "#151a28"
    BG_TOOLTIP = "#171c2b"

    # Level 1: Raised Neomorphic Cards & Panels (Graphite / Deep Slate)
    BG_CARD = "#131722"
    BG_CARD_HOVER = "#181d2b"
    BG_CARD_PRESSED = "#0e111a"
    BG_CARD_ACTIVE = "rgba(99, 102, 241, 0.16)"
    BG_HERO_CARD = "#141926"
    BG_HERO_CARD_HOVER = "#191f2e"

    # Level 2: Elevated Interactive Controls & Recessed (Sunken) Wells
    BG_ELEVATED = "#1a2030"
    BG_ELEVATED_HOVER = "#22293d"
    BG_ELEVATED_PRESSED = "#10141f"
    BG_SUNKEN = "#0c0f17"          # Sunken well for text outputs, inputs, ring sockets
    BG_SUNKEN_DEEP = "#090b11"     # Deepest inset socket
    BG_INPUT_FOCUS = "#101420"     # Focused input surface
    BG_STATUS_BAR = "#111520"

    # Neomorphic Dual Borders (Light Top/Left Edge + Dark Bottom/Right Shadow Edge)
    BORDER_SPECULAR = "rgba(255, 255, 255, 0.08)"
    BORDER_SPECULAR_TOP = "rgba(255, 255, 255, 0.09)"
    BORDER_SPECULAR_TOP_HERO = "rgba(255, 255, 255, 0.11)"
    BORDER_SPECULAR_TOP_HOVER = "rgba(255, 255, 255, 0.16)"
    BORDER_SUBTLE = "rgba(255, 255, 255, 0.05)"
    BORDER_BOTTOM = "rgba(3, 5, 10, 0.88)"
    BORDER_SHADOW_DARK = "rgba(2, 4, 9, 0.92)"

    # Sunken / Recessed Well Borders (Inverted Light: Dark Top/Left, Subtle Light Bottom/Right)
    BORDER_SUNKEN_TOP = "rgba(2, 4, 9, 0.92)"
    BORDER_SUNKEN_LEFT = "rgba(4, 6, 12, 0.80)"
    BORDER_SUNKEN_BOTTOM = "rgba(255, 255, 255, 0.06)"
    BORDER_SUNKEN_RIGHT = "rgba(255, 255, 255, 0.04)"

    # Interactive & Accessibility Borders (WCAG 2.2 AA)
    BORDER_HOVER = "rgba(129, 140, 248, 0.38)"
    BORDER_ACTIVE = "#6366f1"
    BORDER_FOCUS = "#818cf8"       # Visible 2px keyboard focus ring

    # Text Hierarchy (Bright Cool White + Legible Blue-Gray Secondary)
    TEXT_PRIMARY = "#f8fafc"       # Cool white for primary headings & active labels
    TEXT_SECONDARY = "#e2e8f0"     # High-legibility body text & controls
    TEXT_MUTED = "#94a3b8"         # Legible blue-gray secondary text (WCAG AA compliant)
    TEXT_DIM = "#64748b"           # Captions, timestamps, inactive hints
    TEXT_DISABLED = "#64748b"      # Disabled controls text
    TEXT_ACCENT = "#818cf8"        # Muted Indigo accent text
    TEXT_CORAL = "#f26b46"         # Coral/Orange highlight text
    TEXT_ON_ACCENT = "#ffffff"

    # Primary Action Token: Coral / Orange ("Diktat starten")
    ACCENT_CORAL = "#eb5e38"
    ACCENT_CORAL_HOVER = "#f46d48"
    ACCENT_CORAL_PRESSED = "#d14b27"
    ACCENT_CORAL_MUTED = "rgba(235, 94, 56, 0.16)"
    ACCENT_CORAL_BORDER = "rgba(244, 109, 72, 0.55)"
    ACCENT_CORAL_GLOW = "rgba(235, 94, 56, 0.32)"

    # Selection & Secondary Accents: Muted Indigo / Violet
    ACCENT_INDIGO = "#5861b5"
    ACCENT_INDIGO_BRIGHT = "#7c83e0"
    ACCENT_INDIGO_TEXT = "#a5b4fc"
    ACCENT_INDIGO_SURFACE = "#3d448a"
    ACCENT_INDIGO_HOVER = "#4b53a6"
    ACCENT_INDIGO_PRESSED = "#313773"
    ACCENT_INDIGO_MUTED = "rgba(99, 102, 241, 0.16)"
    ACCENT_INDIGO_BORDER = "rgba(129, 140, 248, 0.48)"

    # Mapped Core Accent Tokens (Indigo selection + Coral primary compatibility)
    ACCENT_PRIMARY = "#7c83e0"
    ACCENT_PRIMARY_HOVER = "#6366f1"
    ACCENT_PRIMARY_PRESSED = "#4f46e5"
    ACCENT_PRIMARY_MUTED = "rgba(124, 131, 224, 0.16)"
    ACCENT_PRIMARY_GLOW = "rgba(124, 131, 224, 0.30)"

    ACCENT_BLUE = "#5861b5"
    ACCENT_BLUE_HOVER = "#6366f1"
    ACCENT_BLUE_PRESSED = "#4338ca"
    ACCENT_BLUE_MUTED = "rgba(88, 97, 181, 0.25)"

    # Positive System States: Mint / Green ("Bereit")
    SUCCESS = "#34d399"
    SUCCESS_MUTED = "rgba(52, 211, 153, 0.14)"
    SUCCESS_BORDER = "rgba(52, 211, 153, 0.42)"

    WARNING = "#f59e0b"
    WARNING_MUTED = "rgba(245, 158, 11, 0.15)"
    WARNING_BORDER = "rgba(245, 158, 11, 0.42)"

    ERROR = "#ef4444"
    ERROR_MUTED = "rgba(239, 68, 68, 0.16)"
    ERROR_BORDER = "rgba(239, 68, 68, 0.45)"

    PURPLE = "#818cf8"
    PURPLE_MUTED = "rgba(129, 140, 248, 0.16)"
    PURPLE_BORDER = "rgba(129, 140, 248, 0.42)"

    # Form Controls & Sunken Input Surfaces
    INPUT_BG = "#0d1018"
    INPUT_BG_HOVER = "#111520"
    INPUT_BG_FOCUS = "#0f131d"

    DROPDOWN_MENU_BG = "#141824"
    BORDER_DROPDOWN = "rgba(255, 255, 255, 0.10)"
    DROPDOWN_MENU_BORDER = f"1px solid {BORDER_DROPDOWN}"

    # Chip & Keycap Specific Tokens
    CHIP_BG_SELECTED = "#282e5c"
    CHIP_BG_SELECTED_HOVER = "#343b75"
    CHIP_TEXT_UNSELECTED = "#94a3b8"
    KEYCAP_BG = "#1b2030"
    KEYCAP_BORDER_TOP = "rgba(255, 255, 255, 0.12)"
    KEYCAP_BORDER_BOTTOM = "rgba(3, 5, 10, 0.90)"

    SCROLLBAR_HANDLE = "rgba(148, 163, 184, 0.18)"
    SCROLLBAR_HANDLE_HOVER = "rgba(148, 163, 184, 0.34)"

    SLIDER_TRACK = "#0c0f17"
    SLIDER_SUBPAGE = "#6366f1"
    SLIDER_HANDLE = "#f8fafc"

    SELECTION_BG = "rgba(99, 102, 241, 0.32)"
    SELECTION_TEXT = "#ffffff"


# =========================================================================
# 2. Centralized Typography Tokens & Factory
# =========================================================================

class ThemeTypography:
    """Dark Neomorphism 2.0 Typography Hierarchy and Font Constructors."""

    FONT_FAMILY = "'Segoe UI Variable Text', 'Segoe UI Variable', 'Segoe UI', system-ui, -apple-system, sans-serif"
    FONT_FAMILY_PRIMARY = "'Segoe UI Variable Text', 'Segoe UI Variable', 'Segoe UI', system-ui, -apple-system, sans-serif"
    FONT_FAMILY_DISPLAY = "'Segoe UI Variable Display', 'Segoe UI Variable', 'Segoe UI', system-ui, -apple-system, sans-serif"
    FONT_FAMILY_SMALL = "'Segoe UI Variable Small', 'Segoe UI Variable', 'Segoe UI', system-ui, -apple-system, sans-serif"
    FONT_FAMILY_MONO = "'Cascadia Code', 'Consolas', 'Courier New', monospace"

    WEIGHT_LIGHT = "300"
    WEIGHT_REGULAR = "400"
    WEIGHT_MEDIUM = "500"
    WEIGHT_SEMIBOLD = "600"
    WEIGHT_BOLD = "700"
    WEIGHT_BLACK = "800"

    SIZE_HERO = "22px"
    SIZE_PAGE_TITLE = "18px"
    SIZE_SECTION_TITLE = "14px"
    SIZE_CARD_TITLE = "13px"
    SIZE_BODY = "12px"
    SIZE_BODY_LARGE = "13px"
    SIZE_CAPTION = "11px"
    SIZE_BADGE = "9.5px"
    SIZE_MICRO = "8px"

    PT_HERO = 22
    PT_PAGE_TITLE = 18
    PT_SECTION_TITLE = 14
    PT_CARD_TITLE = 13
    PT_BODY = 12
    PT_BODY_LARGE = 13
    PT_CAPTION = 11
    PT_BADGE = 9
    PT_MICRO = 8

    LINE_HEIGHT_TIGHT = "1.2"
    LINE_HEIGHT_NORMAL = "1.45"
    LINE_HEIGHT_RELAXED = "1.55"

    @staticmethod
    def get_qfont(
        size: int = 12,
        weight: Union[QFont.Weight, int, str] = QFont.Weight.Normal,
        mono: bool = False,
        small_variant: bool = False,
        display_variant: bool = False,
        italic: bool = False,
        pixel_size: bool = False,
    ) -> QFont:
        """Creates a QFont instance adhering to Windows 11 Segoe UI Variable typography."""
        if mono:
            primary = "Cascadia Code"
            families = ["Cascadia Code", "Consolas", "Courier New", "monospace"]
            hint = QFont.StyleHint.Monospace
        elif display_variant or size >= 18:
            primary = "Segoe UI Variable Display"
            families = ["Segoe UI Variable Display", "Segoe UI Variable", "Segoe UI", "sans-serif"]
            hint = QFont.StyleHint.SansSerif
        elif small_variant or size <= 9:
            primary = "Segoe UI Variable Small"
            families = ["Segoe UI Variable Small", "Segoe UI Variable", "Segoe UI", "sans-serif"]
            hint = QFont.StyleHint.SansSerif
        else:
            primary = "Segoe UI Variable Text"
            families = ["Segoe UI Variable Text", "Segoe UI Variable", "Segoe UI", "sans-serif"]
            hint = QFont.StyleHint.SansSerif

        font = QFont(primary)
        if pixel_size:
            font.setPixelSize(size)
        else:
            font.setPointSize(size)

        font.setFamilies(families)
        font.setStyleHint(hint)

        if isinstance(weight, str):
            try:
                parsed_w = int(weight)
                font.setWeight(QFont.Weight(parsed_w))
            except (ValueError, TypeError):
                font.setWeight(QFont.Weight.Normal)
        elif isinstance(weight, int):
            try:
                font.setWeight(QFont.Weight(weight))
            except (ValueError, TypeError):
                font.setWeight(QFont.Weight.Normal)
        elif isinstance(weight, QFont.Weight):
            font.setWeight(weight)
        else:
            font.setWeight(QFont.Weight.Normal)

        if italic:
            font.setItalic(True)

        return font


# =========================================================================
# 3. Centralized Geometry & Metrics Tokens
# =========================================================================

class ThemeMetrics:
    """Dark Neomorphism 2.0 Geometry, Radius, Depth, and Spacing Constants."""

    # Border Radii (QSS Strings)
    RADIUS_CARD = "14px"           # Standard neomorphic cards
    RADIUS_CARD_LARGE = "18px"     # Hero stage, sidebar, primary panels
    RADIUS_CONTROL = "10px"        # Buttons, ComboBox, LineEdit, Nav buttons
    RADIUS_SUNKEN = "12px"         # Recessed wells & text editors
    RADIUS_KEYCAP = "7px"          # Tactile shortcut keycaps
    RADIUS_PILL = "18px"           # Floating HUD, pill badges
    RADIUS_BADGE = "6px"           # Inline tags
    RADIUS_CHECKBOX = "5px"        # Checkbox indicator square
    RADIUS_SCROLLBAR = "3px"       # Scrollbar handle

    # Border Radii (Integers for QPainter & native PyQt methods)
    RADIUS_CARD_INT = 14
    RADIUS_CARD_LARGE_INT = 18
    RADIUS_CONTROL_INT = 10
    RADIUS_SUNKEN_INT = 12
    RADIUS_KEYCAP_INT = 7
    RADIUS_PILL_INT = 18
    RADIUS_BADGE_INT = 6
    RADIUS_CHECKBOX_INT = 5
    RADIUS_SCROLLBAR_INT = 3

    # Generous Spacing Tokens (QSS Strings)
    SPACING_XS = "6px"
    SPACING_SM = "10px"
    SPACING_MD = "16px"
    SPACING_LG = "22px"
    SPACING_XL = "30px"

    # Padding Tokens (QSS Strings)
    PADDING_CARD = "18px 20px"
    PADDING_CARD_COMPACT = "12px 16px"
    PADDING_CONTROL = "7px 12px"
    PADDING_BUTTON = "7px 16px"
    PADDING_BUTTON_SM = "5px 12px"


# =========================================================================
# 4. Accessibility & Neomorphic Surface Helpers
# =========================================================================

_OS_REDUCED_MOTION_CACHE: Optional[bool] = None
_OS_HIGH_CONTRAST_CACHE: Optional[bool] = None


def is_reduced_motion(config_obj: Any = None) -> bool:
    """
    Returns True if animations should be minimized/disabled based on user config
    (`hud.fluid_animations == False`) or Windows OS ClientAreaAnimation setting.
    """
    global _OS_REDUCED_MOTION_CACHE
    try:
        if config_obj is not None:
            hud_cfg = getattr(config_obj, "hud", None)
            if hud_cfg is not None:
                if getattr(hud_cfg, "fluid_animations", True) is False:
                    return True
            elif isinstance(config_obj, dict):
                hud_dict = config_obj.get("hud")
                if isinstance(hud_dict, dict) and hud_dict.get("fluid_animations") is False:
                    return True
    except Exception:
        pass

    if _OS_REDUCED_MOTION_CACHE is not None:
        return _OS_REDUCED_MOTION_CACHE

    if sys.platform == "win32":
        try:
            SPI_GETCLIENTAREAANIMATION = 0x1042
            anim_enabled = c_int(1)
            if ctypes.windll.user32.SystemParametersInfoW(
                SPI_GETCLIENTAREAANIMATION, 0, byref(anim_enabled), 0
            ):
                _OS_REDUCED_MOTION_CACHE = (anim_enabled.value == 0)
                return _OS_REDUCED_MOTION_CACHE
        except Exception:
            pass
    _OS_REDUCED_MOTION_CACHE = False
    return False


def is_high_contrast() -> bool:
    """Returns True if the OS High Contrast accessibility mode is active."""
    global _OS_HIGH_CONTRAST_CACHE
    if _OS_HIGH_CONTRAST_CACHE is not None:
        return _OS_HIGH_CONTRAST_CACHE

    if sys.platform == "win32":
        try:
            class HIGHCONTRASTW(ctypes.Structure):
                _fields_ = [
                    ("cbSize", ctypes.c_uint),
                    ("dwFlags", ctypes.c_uint),
                    ("lpszDefaultScheme", ctypes.c_wchar_p),
                ]
            SPI_GETHIGHCONTRAST = 0x0042
            HCF_HIGHCONTRASTON = 0x00000001
            hc = HIGHCONTRASTW()
            hc.cbSize = sizeof(HIGHCONTRASTW)
            if ctypes.windll.user32.SystemParametersInfoW(
                SPI_GETHIGHCONTRAST, hc.cbSize, byref(hc), 0
            ):
                _OS_HIGH_CONTRAST_CACHE = bool(hc.dwFlags & HCF_HIGHCONTRASTON)
                return _OS_HIGH_CONTRAST_CACHE
        except Exception:
            pass
    _OS_HIGH_CONTRAST_CACHE = False
    return False


def apply_neomorphic_shadow(
    widget: QWidget,
    blur_radius: float = 24.0,
    offset_x: float = 4.0,
    offset_y: float = 8.0,
    alpha: int = 125,
) -> Optional[QGraphicsDropShadowEffect]:
    """
    Attaches a soft Dark Neomorphism 2.0 drop shadow to a raised surface widget.
    Safe in offscreen/headless environments.
    """
    if widget is None:
        return None
    try:
        shadow = QGraphicsDropShadowEffect(widget)
        shadow.setBlurRadius(blur_radius)
        shadow.setOffset(offset_x, offset_y)
        shadow.setColor(QColor(2, 4, 10, max(0, min(255, int(alpha)))))
        widget.setGraphicsEffect(shadow)
        return shadow
    except Exception:
        return None


def _color_to_rgba(color_str: str, alpha: Union[str, float]) -> str:
    """
    Converts a hex string (#RGB, #RRGGBB) or rgb(...) string into an rgba(r, g, b, alpha) string.
    Falls back gracefully to rgba(255, 255, 255, alpha) if parsing fails.
    """
    alpha_str = str(alpha).strip()
    color = color_str.strip()
    if color.startswith("#"):
        c = color.lstrip("#")
        if len(c) == 6:
            try:
                r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
                return f"rgba({r}, {g}, {b}, {alpha_str})"
            except ValueError:
                pass
        elif len(c) == 3:
            try:
                r, g, b = int(c[0] * 2, 16), int(c[1] * 2, 16), int(c[2] * 2, 16)
                return f"rgba({r}, {g}, {b}, {alpha_str})"
            except ValueError:
                pass
    m = re.match(r"rgba?\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", color)
    if m:
        r, g, b = m.group(1), m.group(2), m.group(3)
        return f"rgba({r}, {g}, {b}, {alpha_str})"
    return f"rgba(255, 255, 255, {alpha_str})"


def get_card_qss(
    selected: bool = False,
    hoverable: bool = True,
    radius: Optional[str] = None,
    widget_class: str = "QFrame",
    card_type: str = "standard",  # "standard", "hero", "elevated", "sunken"
    accent_color: str = ThemeColors.ACCENT_PRIMARY,
    active_bg: Optional[str] = None,
    padding: Optional[str] = None,
) -> str:
    """
    Returns Dark Neomorphism 2.0 QSS for raised or sunken card surfaces.
    Uses directional dual bevel borders (fine light top/left edge, deep dark bottom/right edge)
    and explicit active/hover/focus borders so controls are never identified by shadow alone.
    """
    if card_type == "sunken":
        r = radius or ThemeMetrics.RADIUS_SUNKEN
        padding_rule = f"        padding: {padding};\n" if padding else ""
        return f"""
        {widget_class} {{
            background-color: {ThemeColors.BG_SUNKEN};
            border-top: 1px solid {ThemeColors.BORDER_SUNKEN_TOP};
            border-left: 1px solid {ThemeColors.BORDER_SUNKEN_LEFT};
            border-bottom: 1px solid {ThemeColors.BORDER_SUNKEN_BOTTOM};
            border-right: 1px solid {ThemeColors.BORDER_SUNKEN_RIGHT};
            border-radius: {r};
{padding_rule}        }}
        """

    if card_type == "hero":
        r = radius or ThemeMetrics.RADIUS_CARD_LARGE
        bg_base = ThemeColors.BG_HERO_CARD
        bg_hover = ThemeColors.BG_HERO_CARD_HOVER
        border_specular = ThemeColors.BORDER_SPECULAR_TOP_HERO
    elif card_type == "elevated":
        r = radius or ThemeMetrics.RADIUS_CARD
        bg_base = ThemeColors.BG_ELEVATED
        bg_hover = ThemeColors.BG_ELEVATED_HOVER
        border_specular = ThemeColors.BORDER_SPECULAR_TOP
    else:
        r = radius or ThemeMetrics.RADIUS_CARD
        bg_base = ThemeColors.BG_CARD
        bg_hover = ThemeColors.BG_CARD_HOVER
        border_specular = ThemeColors.BORDER_SPECULAR_TOP

    padding_rule = f"        padding: {padding};\n" if padding else ""

    if selected:
        act_bg = active_bg or _color_to_rgba(accent_color, "0.14")
        return f"""
        {widget_class} {{
            background-color: {act_bg};
            border: 1.5px solid {accent_color};
            border-radius: {r};
{padding_rule}        }}
        """

    hover_qss = f"""
        {widget_class}:hover {{
            background-color: {bg_hover};
            border-top: 1px solid {ThemeColors.BORDER_SPECULAR_TOP_HOVER};
            border-left: 1px solid {ThemeColors.BORDER_HOVER};
            border-right: 1px solid {ThemeColors.BORDER_HOVER};
            border-bottom: 1px solid {ThemeColors.BORDER_BOTTOM};
        }}
    """ if hoverable else ""

    return f"""
    {widget_class} {{
        background-color: {bg_base};
        border-top: 1px solid {border_specular};
        border-left: 1px solid {ThemeColors.BORDER_SUBTLE};
        border-right: 1px solid {ThemeColors.BORDER_BOTTOM};
        border-bottom: 1px solid {ThemeColors.BORDER_BOTTOM};
        border-radius: {r};
{padding_rule}    }}
    {hover_qss}
    """


def get_sunken_qss(
    radius: str = ThemeMetrics.RADIUS_SUNKEN,
    widget_class: str = "QFrame",
    padding: Optional[str] = None,
) -> str:
    """Returns QSS for a recessed (inset) neomorphic well."""
    return get_card_qss(
        selected=False,
        hoverable=False,
        radius=radius,
        widget_class=widget_class,
        card_type="sunken",
        padding=padding,
    )


def get_keycap_qss(widget_class: str = "QLabel") -> str:
    """Returns tactile Dark Neomorphism 2.0 physical keycap badge styling."""
    return f"""
    {widget_class} {{
        background-color: {ThemeColors.KEYCAP_BG};
        color: {ThemeColors.TEXT_SECONDARY};
        font-family: {ThemeTypography.FONT_FAMILY_PRIMARY};
        font-size: 11px;
        font-weight: 600;
        padding: 4px 10px;
        border-radius: {ThemeMetrics.RADIUS_KEYCAP};
        border-top: 1px solid {ThemeColors.KEYCAP_BORDER_TOP};
        border-left: 1px solid rgba(255, 255, 255, 0.07);
        border-right: 1px solid {ThemeColors.KEYCAP_BORDER_BOTTOM};
        border-bottom: 2px solid {ThemeColors.KEYCAP_BORDER_BOTTOM};
    }}
    """


def get_chip_qss(
    selected: bool = False,
    radius: str = "8px",
    widget_class: str = "QPushButton",
    accent_color: str = ThemeColors.ACCENT_PRIMARY,
    selected_bg: str = ThemeColors.CHIP_BG_SELECTED,
    selected_hover_bg: str = ThemeColors.CHIP_BG_SELECTED_HOVER,
    unselected_text: str = ThemeColors.CHIP_TEXT_UNSELECTED,
    font_size: str = "11px",
    padding: str = "4px 12px",
) -> str:
    """
    Returns neomorphic pill/chip styling for model sub-chips and filter tabs.
    Selected chips use Muted Indigo fill and clear 1.5px border; unselected chips are recessed/raised with visible borders.
    """
    if selected:
        return f"""
        {widget_class} {{
            background-color: {selected_bg};
            color: {ThemeColors.TEXT_PRIMARY};
            border: 1.5px solid {accent_color};
            border-radius: {radius};
            font-size: {font_size};
            font-weight: 600;
            padding: {padding};
        }}
        {widget_class}:hover {{
            background-color: {selected_hover_bg};
        }}
        {widget_class}:focus {{
            border: 2px solid {ThemeColors.BORDER_FOCUS};
        }}
        """
    return f"""
    {widget_class} {{
        background-color: {ThemeColors.BG_ELEVATED};
        color: {unselected_text};
        border-top: 1px solid {ThemeColors.BORDER_SPECULAR_TOP};
        border-left: 1px solid {ThemeColors.BORDER_SUBTLE};
        border-right: 1px solid {ThemeColors.BORDER_BOTTOM};
        border-bottom: 1px solid {ThemeColors.BORDER_BOTTOM};
        border-radius: {radius};
        font-size: {font_size};
        font-weight: 500;
        padding: {padding};
    }}
    {widget_class}:hover {{
        background-color: {ThemeColors.BG_ELEVATED_HOVER};
        color: {ThemeColors.TEXT_PRIMARY};
        border-color: {ThemeColors.BORDER_HOVER};
    }}
    {widget_class}:focus {{
        border: 2px solid {ThemeColors.BORDER_FOCUS};
    }}
    """


def get_badge_qss(
    accent_color: str = ThemeColors.ACCENT_PRIMARY,
    bg_alpha: Union[str, float] = "0.16",
    border_alpha: Union[str, float] = "0.38",
    radius: str = ThemeMetrics.RADIUS_BADGE,
    widget_class: str = "QLabel",
    bg_color: Optional[str] = None,
    border_color: Optional[str] = None,
    font_size: str = "9.5px",
    padding: str = "2px 7px",
) -> str:
    """Returns styling for inline status badges and tags."""
    resolved_bg = bg_color or _color_to_rgba(accent_color, bg_alpha)
    resolved_border = border_color or _color_to_rgba(accent_color, border_alpha)

    return f"""
    {widget_class} {{
        background-color: {resolved_bg};
        color: {accent_color};
        font-size: {font_size};
        font-weight: 700;
        letter-spacing: 0.3px;
        padding: {padding};
        border-radius: {radius};
        border: 1px solid {resolved_border};
    }}
    """


# =========================================================================
# 5. Comprehensive Dark Neomorphism 2.0 QSS Engine
# =========================================================================

def build_stylesheet() -> str:
    """
    Generates the unified Dark Neomorphism 2.0 QSS.
    No glassmorphism, no neon aesthetics — purely tactile deep blue-black & graphite surfaces,
    recessed input wells, Coral primary CTAs, Muted Indigo selections, and Mint readiness states.
    """
    return f"""
/* =========================================================================
   1. Global Base & Window Styling (Deep Blue-Black & Graphite)
   ========================================================================= */
QWidget {{
    background-color: transparent;
    color: {ThemeColors.TEXT_SECONDARY};
    font-family: {ThemeTypography.FONT_FAMILY};
    font-size: {ThemeTypography.SIZE_BODY};
    selection-background-color: {ThemeColors.SELECTION_BG};
    selection-color: {ThemeColors.SELECTION_TEXT};
    outline: none;
}}

QMainWindow, QDialog {{
    background-color: {ThemeColors.BG_WINDOW};
}}

/* Seamless Scroll Areas */
QScrollArea {{
    border: none;
    background-color: transparent;
}}

QScrollArea > QWidget > QWidget {{
    background-color: transparent;
}}

/* =========================================================================
   2. Dark Neomorphism 2.0 Surface Cards (Raised & Recessed)
   ========================================================================= */
QFrame#card {{
    background-color: {ThemeColors.BG_CARD};
    border-top: 1px solid {ThemeColors.BORDER_SPECULAR_TOP};
    border-left: 1px solid {ThemeColors.BORDER_SUBTLE};
    border-right: 1px solid {ThemeColors.BORDER_BOTTOM};
    border-bottom: 1px solid {ThemeColors.BORDER_BOTTOM};
    border-radius: {ThemeMetrics.RADIUS_CARD};
}}

QFrame#card:hover {{
    background-color: {ThemeColors.BG_CARD_HOVER};
    border-top: 1px solid {ThemeColors.BORDER_SPECULAR_TOP_HOVER};
}}

QFrame#hero_card {{
    background-color: {ThemeColors.BG_HERO_CARD};
    border-top: 1px solid {ThemeColors.BORDER_SPECULAR_TOP_HERO};
    border-left: 1px solid rgba(255, 255, 255, 0.06);
    border-right: 1px solid {ThemeColors.BORDER_SHADOW_DARK};
    border-bottom: 2px solid {ThemeColors.BORDER_SHADOW_DARK};
    border-radius: {ThemeMetrics.RADIUS_CARD_LARGE};
}}

QFrame#sunken_well {{
    background-color: {ThemeColors.BG_SUNKEN};
    border-top: 1px solid {ThemeColors.BORDER_SUNKEN_TOP};
    border-left: 1px solid {ThemeColors.BORDER_SUNKEN_LEFT};
    border-bottom: 1px solid {ThemeColors.BORDER_SUNKEN_BOTTOM};
    border-right: 1px solid {ThemeColors.BORDER_SUNKEN_RIGHT};
    border-radius: {ThemeMetrics.RADIUS_SUNKEN};
}}

/* =========================================================================
   3. Brand, Section & Typography Headers
   ========================================================================= */
QLabel#brand_title {{
    font-family: {ThemeTypography.FONT_FAMILY_DISPLAY};
    font-size: 16px;
    font-weight: 700;
    letter-spacing: -0.2px;
    color: {ThemeColors.TEXT_PRIMARY};
}}

QLabel#brand_tag {{
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.4px;
    color: {ThemeColors.ACCENT_INDIGO_BRIGHT};
    background-color: {ThemeColors.ACCENT_INDIGO_MUTED};
    padding: 2px 7px;
    border-radius: {ThemeMetrics.RADIUS_BADGE};
    border: 1px solid {ThemeColors.ACCENT_INDIGO_BORDER};
}}

QLabel#section_title {{
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.8px;
    color: {ThemeColors.TEXT_MUTED};
    text-transform: uppercase;
}}

/* =========================================================================
   4. Neomorphic Navigation & Tabs
   ========================================================================= */
QTabWidget::pane {{
    border: none;
    background-color: transparent;
}}

QTabBar {{
    background-color: {ThemeColors.BG_SUNKEN};
    border-radius: {ThemeMetrics.RADIUS_CONTROL};
    padding: 3px;
    border-top: 1px solid {ThemeColors.BORDER_SUNKEN_TOP};
    border-bottom: 1px solid {ThemeColors.BORDER_SUNKEN_BOTTOM};
}}

QTabBar::tab {{
    background-color: transparent;
    color: {ThemeColors.TEXT_MUTED};
    font-weight: 600;
    font-size: 12px;
    letter-spacing: 0.2px;
    padding: 6px 16px;
    border-radius: 7px;
    border: 1px solid transparent;
    margin: 0 1px;
}}

QTabBar::tab:selected {{
    background-color: {ThemeColors.ACCENT_INDIGO_SURFACE};
    color: {ThemeColors.TEXT_PRIMARY};
    border-top: 1px solid rgba(255, 255, 255, 0.18);
    border-bottom: 1px solid {ThemeColors.BORDER_BOTTOM};
}}

QTabBar::tab:hover:!selected {{
    color: {ThemeColors.TEXT_PRIMARY};
    background-color: {ThemeColors.BG_ELEVATED};
}}

/* =========================================================================
   5. Recessed Form Controls (Inputs, ComboBox, Editors)
   ========================================================================= */
QComboBox {{
    background-color: {ThemeColors.INPUT_BG};
    color: {ThemeColors.TEXT_PRIMARY};
    border-top: 1px solid {ThemeColors.BORDER_SUNKEN_TOP};
    border-left: 1px solid {ThemeColors.BORDER_SUNKEN_LEFT};
    border-bottom: 1px solid {ThemeColors.BORDER_SUNKEN_BOTTOM};
    border-right: 1px solid {ThemeColors.BORDER_SUNKEN_RIGHT};
    border-radius: {ThemeMetrics.RADIUS_CONTROL};
    padding: 6px 12px;
    min-height: 22px;
    font-size: 12px;
}}

QComboBox:hover {{
    background-color: {ThemeColors.INPUT_BG_HOVER};
    border-color: {ThemeColors.BORDER_HOVER};
}}

QComboBox:focus {{
    border: 2px solid {ThemeColors.BORDER_FOCUS};
    background-color: {ThemeColors.INPUT_BG_FOCUS};
}}

QComboBox:disabled {{
    background-color: #090b10;
    color: {ThemeColors.TEXT_DIM};
    border-color: rgba(255, 255, 255, 0.03);
}}

QComboBox::drop-down {{
    border: none;
    padding-right: 10px;
}}

QComboBox QAbstractItemView {{
    background-color: {ThemeColors.DROPDOWN_MENU_BG};
    color: {ThemeColors.TEXT_SECONDARY};
    border: {ThemeColors.DROPDOWN_MENU_BORDER};
    selection-background-color: {ThemeColors.ACCENT_INDIGO_SURFACE};
    selection-color: {ThemeColors.TEXT_PRIMARY};
    border-radius: {ThemeMetrics.RADIUS_CONTROL};
    outline: none;
    padding: 4px;
}}

QLineEdit {{
    background-color: {ThemeColors.INPUT_BG};
    color: {ThemeColors.TEXT_PRIMARY};
    border-top: 1px solid {ThemeColors.BORDER_SUNKEN_TOP};
    border-left: 1px solid {ThemeColors.BORDER_SUNKEN_LEFT};
    border-bottom: 1px solid {ThemeColors.BORDER_SUNKEN_BOTTOM};
    border-right: 1px solid {ThemeColors.BORDER_SUNKEN_RIGHT};
    border-radius: {ThemeMetrics.RADIUS_CONTROL};
    padding: 7px 12px;
    font-size: 12px;
}}

QLineEdit:hover {{
    background-color: {ThemeColors.INPUT_BG_HOVER};
    border-color: {ThemeColors.BORDER_HOVER};
}}

QLineEdit:focus {{
    border: 2px solid {ThemeColors.BORDER_FOCUS};
    background-color: {ThemeColors.INPUT_BG_FOCUS};
}}

QLineEdit:disabled {{
    background-color: #090b10;
    color: {ThemeColors.TEXT_DIM};
    border-color: rgba(255, 255, 255, 0.03);
}}

QTextEdit, QPlainTextEdit {{
    background-color: {ThemeColors.BG_SUNKEN};
    color: {ThemeColors.TEXT_PRIMARY};
    font-size: 13px;
    line-height: {ThemeTypography.LINE_HEIGHT_RELAXED};
    border-top: 1px solid {ThemeColors.BORDER_SUNKEN_TOP};
    border-left: 1px solid {ThemeColors.BORDER_SUNKEN_LEFT};
    border-bottom: 1px solid {ThemeColors.BORDER_SUNKEN_BOTTOM};
    border-right: 1px solid {ThemeColors.BORDER_SUNKEN_RIGHT};
    border-radius: {ThemeMetrics.RADIUS_SUNKEN};
    padding: 12px;
}}

QTextEdit:hover, QPlainTextEdit:hover {{
    border-color: {ThemeColors.BORDER_HOVER};
}}

QTextEdit:focus, QPlainTextEdit:focus {{
    border: 2px solid {ThemeColors.BORDER_FOCUS};
}}

/* =========================================================================
   6. Tactile Neomorphic Buttons & Keyboard Focus Rings
   ========================================================================= */
QPushButton {{
    background-color: {ThemeColors.BG_ELEVATED};
    color: {ThemeColors.TEXT_SECONDARY};
    font-weight: 600;
    font-size: 12px;
    border-top: 1px solid {ThemeColors.BORDER_SPECULAR_TOP};
    border-left: 1px solid rgba(255, 255, 255, 0.06);
    border-right: 1px solid {ThemeColors.BORDER_BOTTOM};
    border-bottom: 2px solid {ThemeColors.BORDER_BOTTOM};
    border-radius: {ThemeMetrics.RADIUS_CONTROL};
    padding: 6px 14px;
    min-height: 22px;
}}

QPushButton:hover {{
    background-color: {ThemeColors.BG_ELEVATED_HOVER};
    border-top: 1px solid {ThemeColors.BORDER_SPECULAR_TOP_HOVER};
    border-left: 1px solid {ThemeColors.BORDER_HOVER};
    border-right: 1px solid {ThemeColors.BORDER_HOVER};
    color: {ThemeColors.TEXT_PRIMARY};
}}

QPushButton:pressed {{
    background-color: {ThemeColors.BG_ELEVATED_PRESSED};
    border-top: 1px solid {ThemeColors.BORDER_SUNKEN_TOP};
    border-bottom: 1px solid {ThemeColors.BORDER_SUNKEN_BOTTOM};
}}

QPushButton:focus {{
    border: 2px solid {ThemeColors.BORDER_FOCUS};
}}

QPushButton:disabled {{
    background-color: #10131c;
    color: {ThemeColors.TEXT_DIM};
    border: 1px solid rgba(255, 255, 255, 0.03);
}}

/* Primary Action CTA (Coral / Orange) */
QPushButton#btn_primary_coral {{
    background-color: {ThemeColors.ACCENT_CORAL};
    color: #ffffff;
    font-weight: 700;
    border-top: 1px solid rgba(255, 255, 255, 0.28);
    border-left: 1px solid rgba(255, 255, 255, 0.14);
    border-right: 1px solid #9e3316;
    border-bottom: 2px solid #85280f;
    border-radius: {ThemeMetrics.RADIUS_CONTROL};
}}

QPushButton#btn_primary_coral:hover {{
    background-color: {ThemeColors.ACCENT_CORAL_HOVER};
    color: #ffffff;
}}

QPushButton#btn_primary_coral:pressed {{
    background-color: {ThemeColors.ACCENT_CORAL_PRESSED};
}}

/* Secondary / Selection Action (Muted Indigo) */
QPushButton#btn_primary {{
    background-color: {ThemeColors.ACCENT_INDIGO_SURFACE};
    color: {ThemeColors.TEXT_PRIMARY};
    font-weight: 600;
    border-top: 1px solid rgba(255, 255, 255, 0.20);
    border-left: 1px solid {ThemeColors.ACCENT_INDIGO_BORDER};
    border-right: 1px solid {ThemeColors.BORDER_BOTTOM};
    border-bottom: 2px solid {ThemeColors.BORDER_BOTTOM};
    border-radius: {ThemeMetrics.RADIUS_CONTROL};
}}

QPushButton#btn_primary:hover {{
    background-color: {ThemeColors.ACCENT_INDIGO_HOVER};
    border-color: {ThemeColors.ACCENT_INDIGO_BRIGHT};
    color: {ThemeColors.TEXT_PRIMARY};
}}

QPushButton#btn_primary:pressed {{
    background-color: {ThemeColors.ACCENT_INDIGO_PRESSED};
}}

QPushButton#btn_secondary {{
    background-color: {ThemeColors.BG_CARD};
    color: {ThemeColors.TEXT_MUTED};
    font-weight: 600;
    border-top: 1px solid {ThemeColors.BORDER_SPECULAR_TOP};
    border-left: 1px solid {ThemeColors.BORDER_SUBTLE};
    border-right: 1px solid {ThemeColors.BORDER_BOTTOM};
    border-bottom: 1px solid {ThemeColors.BORDER_BOTTOM};
    border-radius: 8px;
    padding: 5px 12px;
}}

QPushButton#btn_secondary:hover {{
    background-color: {ThemeColors.BG_ELEVATED};
    color: {ThemeColors.TEXT_PRIMARY};
    border-color: {ThemeColors.BORDER_HOVER};
}}

/* =========================================================================
   7. Checkboxes & Radio Buttons (Recessed Indicators + Indigo Checked Fill)
   ========================================================================= */
QCheckBox {{
    spacing: 10px;
    color: {ThemeColors.TEXT_SECONDARY};
    font-size: 12px;
}}

QCheckBox:hover {{
    color: {ThemeColors.TEXT_PRIMARY};
}}

QCheckBox::indicator {{
    width: 17px;
    height: 17px;
    border-top: 1px solid {ThemeColors.BORDER_SUNKEN_TOP};
    border-left: 1px solid {ThemeColors.BORDER_SUNKEN_LEFT};
    border-bottom: 1px solid rgba(255, 255, 255, 0.14);
    border-right: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: {ThemeMetrics.RADIUS_CHECKBOX};
    background-color: {ThemeColors.BG_SUNKEN};
}}

QCheckBox::indicator:hover {{
    border-color: {ThemeColors.ACCENT_INDIGO_BRIGHT};
    background-color: {ThemeColors.BG_ELEVATED};
}}

QCheckBox::indicator:checked {{
    background-color: {ThemeColors.ACCENT_INDIGO};
    border: 1.5px solid {ThemeColors.ACCENT_INDIGO_BRIGHT};
}}

QCheckBox:focus {{
    color: {ThemeColors.TEXT_PRIMARY};
}}

QRadioButton {{
    spacing: 10px;
    color: {ThemeColors.TEXT_SECONDARY};
    font-size: 12px;
}}

QRadioButton:hover {{
    color: {ThemeColors.TEXT_PRIMARY};
}}

QRadioButton::indicator {{
    width: 17px;
    height: 17px;
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 9px;
    background-color: {ThemeColors.BG_SUNKEN};
}}

QRadioButton::indicator:hover {{
    border-color: {ThemeColors.ACCENT_INDIGO_BRIGHT};
}}

QRadioButton::indicator:checked {{
    background-color: {ThemeColors.ACCENT_INDIGO_BRIGHT};
    border: 4px solid {ThemeColors.BG_CARD};
}}

/* =========================================================================
   8. Sliders (Sunken Groove + Indigo Sub-page + Raised Handle)
   ========================================================================= */
QSlider:horizontal {{
    min-height: 24px;
}}

QSlider::groove:horizontal {{
    height: 6px;
    background: {ThemeColors.SLIDER_TRACK};
    border-top: 1px solid {ThemeColors.BORDER_SUNKEN_TOP};
    border-bottom: 1px solid {ThemeColors.BORDER_SUNKEN_BOTTOM};
    border-radius: 3px;
}}

QSlider::sub-page:horizontal {{
    height: 6px;
    background: {ThemeColors.SLIDER_SUBPAGE};
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    background: {ThemeColors.SLIDER_HANDLE};
    border: 2px solid {ThemeColors.ACCENT_INDIGO};
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}

QSlider::handle:horizontal:hover {{
    background: #ffffff;
    border-color: {ThemeColors.ACCENT_CORAL};
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
}}

QSlider:vertical {{
    min-width: 24px;
}}

QSlider::groove:vertical {{
    width: 6px;
    background: {ThemeColors.SLIDER_TRACK};
    border-radius: 3px;
}}

QSlider::sub-page:vertical {{
    width: 6px;
    background: {ThemeColors.SLIDER_SUBPAGE};
    border-radius: 3px;
}}

QSlider::handle:vertical {{
    background: {ThemeColors.SLIDER_HANDLE};
    border: 2px solid {ThemeColors.ACCENT_INDIGO};
    width: 14px;
    height: 14px;
    margin: 0 -5px;
    border-radius: 7px;
}}

/* =========================================================================
   9. Scrollbars (Vertical & Horizontal)
   ========================================================================= */
QScrollBar:vertical {{
    background-color: transparent;
    width: 7px;
    margin: 2px 0;
}}

QScrollBar::handle:vertical {{
    background-color: {ThemeColors.SCROLLBAR_HANDLE};
    min-height: 28px;
    border-radius: {ThemeMetrics.RADIUS_SCROLLBAR};
}}

QScrollBar::handle:vertical:hover {{
    background-color: {ThemeColors.SCROLLBAR_HANDLE_HOVER};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background-color: transparent;
    height: 7px;
    margin: 0 2px;
}}

QScrollBar::handle:horizontal {{
    background-color: {ThemeColors.SCROLLBAR_HANDLE};
    min-width: 28px;
    border-radius: {ThemeMetrics.RADIUS_SCROLLBAR};
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {ThemeColors.SCROLLBAR_HANDLE_HOVER};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* =========================================================================
   10. Menus, Popovers & Context Menus
   ========================================================================= */
QMenu {{
    background-color: {ThemeColors.BG_POPOVER};
    color: {ThemeColors.TEXT_SECONDARY};
    border-top: 1px solid {ThemeColors.BORDER_SPECULAR_TOP};
    border-left: 1px solid {ThemeColors.BORDER_SUBTLE};
    border-right: 1px solid {ThemeColors.BORDER_BOTTOM};
    border-bottom: 2px solid {ThemeColors.BORDER_BOTTOM};
    border-radius: {ThemeMetrics.RADIUS_CONTROL};
    padding: 6px 2px;
}}

QMenu::item {{
    padding: 7px 22px;
    font-size: 12px;
    border-radius: 6px;
    margin: 1px 5px;
}}

QMenu::item:selected {{
    background-color: {ThemeColors.ACCENT_INDIGO_SURFACE};
    color: {ThemeColors.TEXT_PRIMARY};
}}

QMenu::separator {{
    height: 1px;
    background: rgba(255, 255, 255, 0.07);
    margin: 5px 10px;
}}

/* =========================================================================
   11. Tooltips & Progress Indicators
   ========================================================================= */
QToolTip {{
    background-color: {ThemeColors.BG_TOOLTIP};
    color: {ThemeColors.TEXT_PRIMARY};
    border: 1px solid {ThemeColors.ACCENT_INDIGO_BORDER};
    border-radius: 7px;
    padding: 6px 10px;
    font-size: 11px;
}}

QProgressBar {{
    background-color: {ThemeColors.BG_SUNKEN};
    border-top: 1px solid {ThemeColors.BORDER_SUNKEN_TOP};
    border-bottom: 1px solid {ThemeColors.BORDER_SUNKEN_BOTTOM};
    border-radius: 4px;
    height: 7px;
    text-align: center;
}}

QProgressBar::chunk {{
    background-color: {ThemeColors.ACCENT_INDIGO_BRIGHT};
    border-radius: 3px;
}}
"""


# =========================================================================
# 6. Backward Compatibility Export Signatures
# =========================================================================

VELODICTUM_STYLESHEET: str = build_stylesheet()
LIQUID_GLASS_STYLESHEET: str = VELODICTUM_STYLESHEET
DARK_STYLESHEET: str = VELODICTUM_STYLESHEET


def get_stylesheet(liquid_glass: bool = True) -> str:
    """Returns the unified Velodictum Dark Neomorphism 2.0 stylesheet."""
    return VELODICTUM_STYLESHEET


# =========================================================================
# 7. Polymorphic Platform Backdrop Integration (Windows 11 Immersive Dark Mode)
# =========================================================================

def apply_window_backdrop(
    target: Union[int, Any] = None,
    enable_liquid_glass: bool = True,
    backdrop_type: str = "none",
    *,
    win_id: Optional[Union[int, Any]] = None,
    **kwargs,
) -> bool:
    """
    Applies Windows 11 Immersive Dark Mode titlebar and solid opaque Dark Neomorphism 2.0
    surface framing (disabling translucent glassmorphism bleed while preserving full DWM contract).

    Polymorphically accepts:
    - win_id: int (Win32 HWND integer)
    - target: QWidget / QWindow / QDialog / QMainWindow instance with a winId() method
    - Keyword arguments: target=... or win_id=... for 100% backward compatibility
    """
    if sys.platform != "win32":
        return False

    hwnd_input = target if target is not None else (win_id if win_id is not None else kwargs.get("win_id"))
    if hwnd_input is None or isinstance(hwnd_input, bool):
        return False

    try:
        if hasattr(hwnd_input, "winId") and callable(getattr(hwnd_input, "winId")):
            actual_win_id = int(hwnd_input.winId())
        else:
            actual_win_id = int(hwnd_input)
    except Exception:
        return False

    if actual_win_id <= 0:
        return False

    success = False
    try:
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1 = 19

        dark_mode = c_int(1)
        res_dark = ctypes.windll.dwmapi.DwmSetWindowAttribute(
            actual_win_id,
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            byref(dark_mode),
            sizeof(dark_mode),
        )
        if res_dark != 0:
            res_dark = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                actual_win_id,
                DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1,
                byref(dark_mode),
                sizeof(dark_mode),
            )
        if res_dark == 0:
            success = True

        # Set caption color to deep blue-black (#0b0d14 -> COLORREF 0x00140d0b) on Windows 11
        DWMWA_CAPTION_COLOR = 35
        caption_color = c_int(0x00140D0B)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            actual_win_id,
            DWMWA_CAPTION_COLOR,
            byref(caption_color),
            sizeof(caption_color),
        )
    except Exception:
        return False

    return success
