from PyQt6.QtGui import QColor, QPalette, QFont
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
from database.db import get_setting, set_setting


# ─────────────────────────────────────────────
#  COLOR TOKENS
# ─────────────────────────────────────────────
DARK = {
    "bg_primary":      "#1a1a2e",
    "bg_secondary":    "#16213e",
    "bg_card":         "#0f3460",
    "bg_input":        "#1e2a45",
    "bg_hover":        "#1e3a5f",
    "bg_selected":     "#0f3460",
    "border":          "#2a3f6f",
    "border_light":    "#1e3a5f",
    "text_primary":    "#e8eaf6",
    "text_secondary":  "#9aa5c4",
    "text_muted":      "#7986cb",
    "text_disabled":   "#3d4f7c",
    "accent":          "#4A9EFF",
    "accent_hover":    "#6cb4ff",
    "accent_pressed":  "#2980d9",
    "success":         "#4caf50",
    "warning":         "#ff9800",
    "error":           "#f44336",
    "info":            "#2196f3",
    "sim_high":        "#FF4C4C",
    "sim_medium":      "#FFA500",
    "sim_low":         "#FFD700",
    "sim_base":        "#4A9EFF",
    "sidebar_bg":      "#0d1b2a",
    "sidebar_text":    "#8892b0",
    "sidebar_active":  "#4A9EFF",
    "sidebar_active_bg": "#1a2744",
    "scrollbar_bg":    "#1a1a2e",
    "scrollbar_handle":"#2a3f6f",
    "btn_primary_bg":  "#4A9EFF",
    "btn_primary_text":"#ffffff",
    "btn_danger_bg":   "#f44336",
    "btn_ghost_bg":    "transparent",
    "btn_ghost_text":  "#4A9EFF",
}

LIGHT = {
    "bg_primary":      "#f5f6fa",
    "bg_secondary":    "#ffffff",
    "bg_card":         "#ffffff",
    "bg_input":        "#f0f2f5",
    "bg_hover":        "#e8ecf5",
    "bg_selected":     "#dce8ff",
    "border":          "#dde1ec",
    "border_light":    "#eef0f7",
    "text_primary":    "#1a1a2e",
    "text_secondary":  "#4a5568",
    "text_muted":      "#718096",
    "text_disabled":   "#a0aec0",
    "accent":          "#2563eb",
    "accent_hover":    "#1d4ed8",
    "accent_pressed":  "#1e40af",
    "success":         "#16a34a",
    "warning":         "#d97706",
    "error":           "#dc2626",
    "info":            "#2563eb",
    "sim_high":        "#dc2626",
    "sim_medium":      "#d97706",
    "sim_low":         "#ca8a04",
    "sim_base":        "#2563eb",
    "sidebar_bg":      "#1a1a2e",
    "sidebar_text":    "#8892b0",
    "sidebar_active":  "#4A9EFF",
    "sidebar_active_bg": "#1a2744",
    "scrollbar_bg":    "#f0f2f5",
    "scrollbar_handle":"#cbd5e0",
    "btn_primary_bg":  "#2563eb",
    "btn_primary_text":"#ffffff",
    "btn_danger_bg":   "#dc2626",
    "btn_ghost_bg":    "transparent",
    "btn_ghost_text":  "#2563eb",
}


class ThemeManager:
    _current: str = "dark"
    _colors: dict = DARK
    _listeners: list = []

    @classmethod
    def load(cls):
        saved = get_setting("theme", "dark")
        cls._current = saved
        cls._colors  = DARK if saved == "dark" else LIGHT

    @classmethod
    def current(cls) -> str:
        return cls._current

    @classmethod
    def is_dark(cls) -> bool:
        return cls._current == "dark"

    @classmethod
    def colors(cls) -> dict:
        return cls._colors

    @classmethod
    def get(cls, key: str, fallback: str = "#ffffff") -> str:
        return cls._colors.get(key, fallback)

    @classmethod
    def toggle(cls):
        cls._current = "light" if cls._current == "dark" else "dark"
        cls._colors  = DARK if cls._current == "dark" else LIGHT
        set_setting("theme", cls._current)
        cls._notify()

    @classmethod
    def set_theme(cls, theme: str):
        if theme not in ("dark", "light"):
            return
        cls._current = theme
        cls._colors  = DARK if theme == "dark" else LIGHT
        set_setting("theme", theme)
        cls._notify()

    @classmethod
    def add_listener(cls, callback):
        if callback not in cls._listeners:
            cls._listeners.append(callback)

    @classmethod
    def remove_listener(cls, callback):
        if callback in cls._listeners:
            cls._listeners.remove(callback)

    @classmethod
    def _notify(cls):
        for cb in cls._listeners:
            try:
                cb()
            except Exception:
                pass


def build_stylesheet() -> str:
    c = ThemeManager.colors()
    return f"""
    /* ── GLOBAL RESET — NO BORDERS ON DEFAULT WIDGETS ── */
    * {{
        outline: none;
    }}
    QWidget {{
        background-color: {c['bg_primary']};
        color: {c['text_primary']};
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 13px;
    }}

    /* ── QLabel — CRITICAL: NO BORDER ── */
    QLabel {{
        background: transparent;
        color: {c['text_primary']};
        border: none;
        padding: 0px;
    }}

    QMainWindow {{
        background-color: {c['bg_primary']};
    }}

    /* ── Scroll Area ── */
    QScrollArea {{
        background-color: transparent;
        border: none;
    }}
    QScrollArea > QWidget > QWidget {{
        background-color: transparent;
    }}
    QScrollBar:vertical {{
        background: {c['scrollbar_bg']};
        width: 8px;
        border: none;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical {{
        background: {c['scrollbar_handle']};
        border-radius: 4px;
        min-height: 30px;
    }}
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0px;
        border: none;
    }}
    QScrollBar:horizontal {{
        background: {c['scrollbar_bg']};
        height: 8px;
        border: none;
        border-radius: 4px;
    }}
    QScrollBar::handle:horizontal {{
        background: {c['scrollbar_handle']};
        border-radius: 4px;
        min-width: 30px;
    }}
    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal {{
        width: 0px;
        border: none;
    }}

    /* ── Push Buttons ── */
    QPushButton {{
        background-color: {c['btn_primary_bg']};
        color: {c['btn_primary_text']};
        border: none;
        border-radius: 6px;
        padding: 8px 18px;
        font-size: 13px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        background-color: {c['accent_hover']};
    }}
    QPushButton:pressed {{
        background-color: {c['accent_pressed']};
    }}
    QPushButton:disabled {{
        background-color: {c['text_disabled']};
        color: {c['bg_primary']};
    }}
    QPushButton[class="danger"] {{
        background-color: {c['btn_danger_bg']};
        color: #ffffff;
    }}
    QPushButton[class="danger"]:hover {{
        background-color: #ff6659;
    }}
    QPushButton[class="ghost"] {{
        background-color: transparent;
        color: {c['btn_ghost_text']};
        border: 1.5px solid {c['accent']};
    }}
    QPushButton[class="ghost"]:hover {{
        background-color: {c['bg_hover']};
    }}

    /* ── Line Edit ── */
    QLineEdit {{
        background-color: {c['bg_input']};
        color: {c['text_primary']};
        border: 1.5px solid {c['border']};
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 13px;
    }}
    QLineEdit:focus {{
        border-color: {c['accent']};
    }}
    QLineEdit:disabled {{
        color: {c['text_disabled']};
    }}

    /* ── Text Edit ── */
    QTextEdit, QPlainTextEdit {{
        background-color: {c['bg_input']};
        color: {c['text_primary']};
        border: 1.5px solid {c['border']};
        border-radius: 6px;
        padding: 8px;
        font-size: 13px;
    }}
    QTextEdit:focus, QPlainTextEdit:focus {{
        border-color: {c['accent']};
    }}

    /* ── Combo Box ── */
    QComboBox {{
        background-color: {c['bg_input']};
        color: {c['text_primary']};
        border: 1.5px solid {c['border']};
        border-radius: 6px;
        padding: 7px 12px;
        font-size: 13px;
    }}
    QComboBox:focus {{
        border-color: {c['accent']};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {c['bg_card']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        selection-background-color: {c['bg_selected']};
        padding: 4px;
    }}

    /* ── Slider ── */
    QSlider::groove:horizontal {{
        background: {c['border']};
        height: 4px;
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background: {c['accent']};
        width: 16px;
        height: 16px;
        margin: -6px 0;
        border-radius: 8px;
    }}
    QSlider::sub-page:horizontal {{
        background: {c['accent']};
        border-radius: 2px;
    }}

    /* ── Progress Bar ── */
    QProgressBar {{
        background-color: {c['bg_input']};
        border: none;
        border-radius: 4px;
        height: 8px;
        text-align: center;
        color: transparent;
    }}
    QProgressBar::chunk {{
        background-color: {c['accent']};
        border-radius: 4px;
    }}

    /* ── Table Widget ── */
    QTableWidget {{
        background-color: {c['bg_card']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        gridline-color: {c['border_light']};
        selection-background-color: {c['bg_selected']};
    }}
    QTableWidget::item {{
        padding: 8px;
        border: none;
    }}
    QTableWidget::item:selected {{
        background-color: {c['bg_selected']};
        color: {c['text_primary']};
    }}
    QHeaderView::section {{
        background-color: {c['bg_input']};
        color: {c['text_secondary']};
        font-weight: 600;
        font-size: 12px;
        padding: 8px;
        border: none;
        border-bottom: 1px solid {c['border']};
    }}

    /* ── Check Box ── */
    QCheckBox {{
        color: {c['text_primary']};
        spacing: 8px;
        background: transparent;
        border: none;
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border: 2px solid {c['border']};
        border-radius: 4px;
        background: {c['bg_input']};
    }}
    QCheckBox::indicator:checked {{
        background: {c['accent']};
        border-color: {c['accent']};
    }}

    /* ── Radio Button ── */
    QRadioButton {{
        color: {c['text_primary']};
        spacing: 8px;
        background: transparent;
        border: none;
    }}
    QRadioButton::indicator {{
        width: 16px;
        height: 16px;
        border: 2px solid {c['border']};
        border-radius: 8px;
        background: {c['bg_input']};
    }}
    QRadioButton::indicator:checked {{
        background: {c['accent']};
        border-color: {c['accent']};
    }}

    /* ── Tooltip ── */
    QToolTip {{
        background-color: {c['bg_card']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 4px;
        padding: 4px 8px;
        font-size: 12px;
    }}

    /* ── Message Box ── */
    QMessageBox {{
        background-color: {c['bg_primary']};
        color: {c['text_primary']};
    }}
    QMessageBox QLabel {{
        color: {c['text_primary']};
        background: transparent;
        border: none;
    }}

    /* ── Dialog ── */
    QDialog {{
        background-color: {c['bg_primary']};
        color: {c['text_primary']};
    }}
    QDialog QLabel {{
        color: {c['text_primary']};
        background: transparent;
        border: none;
    }}

    /* ── Splitter ── */
    QSplitter::handle {{
        background-color: {c['border']};
    }}
    QSplitter::handle:horizontal {{
        width: 2px;
    }}
    QSplitter::handle:vertical {{
        height: 2px;
    }}

    /* ── Frame classes ── */
    QFrame[class="card"] {{
        background-color: {c['bg_card']};
        border: 1px solid {c['border']};
        border-radius: 10px;
    }}
    QFrame[class="sidebar"] {{
        background-color: {c['sidebar_bg']};
        border: none;
    }}
    QFrame[class="divider"] {{
        background-color: {c['border']};
        max-height: 1px;
        min-height: 1px;
        border: none;
    }}
    """


def apply_theme(app: QApplication):
    ThemeManager.load()
    app.setStyle("Fusion")
    app.setStyleSheet(build_stylesheet())


def refresh_theme(app: QApplication):
    app.setStyleSheet(build_stylesheet())