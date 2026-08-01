from PyQt6.QtGui import QColor, QPalette, QFont
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
from database.db import get_setting, set_setting


# ─────────────────────────────────────────────
#  RUFUS-STYLE NATIVE COLORS
# ─────────────────────────────────────────────
LIGHT = {
    "bg_primary":      "#f0f0f0",   # Rufus window bg
    "bg_secondary":    "#ffffff",
    "bg_card":         "#ffffff",
    "bg_input":        "#ffffff",
    "bg_hover":        "#e5f1fb",
    "bg_selected":     "#cce8ff",
    "bg_disabled":     "#f0f0f0",

    "border":          "#adadad",
    "border_light":    "#d4d4d4",
    "border_focus":    "#0078d4",

    "text_primary":    "#000000",
    "text_secondary":  "#454545",
    "text_muted":      "#767676",
    "text_disabled":   "#a0a0a0",

    "accent":          "#0078d4",   # Windows blue
    "accent_hover":    "#106ebe",
    "accent_pressed":  "#005a9e",

    "success":         "#107c10",
    "warning":         "#ca5010",
    "error":           "#a80000",
    "info":            "#0078d4",

    "sidebar_bg":      "#f0f0f0",
    "sidebar_text":    "#000000",
    "sidebar_active":  "#0078d4",
    "sidebar_active_bg": "#cce8ff",

    "btn_primary_bg":     "#e1e1e1",
    "btn_primary_hover":  "#e5f1fb",
    "btn_primary_text":   "#000000",
    "btn_primary_border": "#adadad",

    "btn_accent_bg":      "#0078d4",
    "btn_accent_text":    "#ffffff",

    "btn_danger_bg":      "#e1e1e1",
    "btn_danger_text":    "#a80000",
    "btn_danger_border":  "#adadad",
}

DARK = {
    "bg_primary":      "#202020",
    "bg_secondary":    "#2b2b2b",
    "bg_card":         "#2b2b2b",
    "bg_input":        "#333333",
    "bg_hover":        "#3e3e3e",
    "bg_selected":     "#0e4a72",
    "bg_disabled":     "#2b2b2b",

    "border":          "#555555",
    "border_light":    "#3d3d3d",
    "border_focus":    "#4cc2ff",

    "text_primary":    "#ffffff",
    "text_secondary":  "#d0d0d0",
    "text_muted":      "#a0a0a0",
    "text_disabled":   "#6d6d6d",

    "accent":          "#4cc2ff",
    "accent_hover":    "#6ccfff",
    "accent_pressed":  "#2b96d1",

    "success":         "#6ccb5f",
    "warning":         "#fce100",
    "error":           "#ff5252",
    "info":            "#4cc2ff",

    "sidebar_bg":      "#202020",
    "sidebar_text":    "#ffffff",
    "sidebar_active":  "#4cc2ff",
    "sidebar_active_bg": "#0e4a72",

    "btn_primary_bg":     "#333333",
    "btn_primary_hover":  "#3e3e3e",
    "btn_primary_text":   "#ffffff",
    "btn_primary_border": "#555555",

    "btn_accent_bg":      "#4cc2ff",
    "btn_accent_text":    "#000000",

    "btn_danger_bg":      "#333333",
    "btn_danger_text":    "#ff5252",
    "btn_danger_border":  "#555555",
}


class ThemeManager:
    _current: str = "light"
    _colors: dict = LIGHT
    _listeners: list = []

    @classmethod
    def load(cls):
        saved = get_setting("theme", "light")
        cls._current = saved
        cls._colors  = LIGHT if saved == "light" else DARK

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
    def get(cls, key: str, fallback: str = "#000000") -> str:
        return cls._colors.get(key, fallback)

    @classmethod
    def toggle(cls):
        cls._current = "dark" if cls._current == "light" else "light"
        cls._colors  = LIGHT if cls._current == "light" else DARK
        set_setting("theme", cls._current)
        cls._notify()

    @classmethod
    def set_theme(cls, theme: str):
        if theme not in ("dark", "light"):
            return
        cls._current = theme
        cls._colors  = LIGHT if theme == "light" else DARK
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


def apply_palette(app: QApplication):
    """Native Windows palette"""
    c = ThemeManager.colors()
    palette = QPalette()

    bg     = QColor(c['bg_primary'])
    bg_in  = QColor(c['bg_input'])
    text   = QColor(c['text_primary'])
    accent = QColor(c['accent'])
    disabled = QColor(c['text_disabled'])

    palette.setColor(QPalette.ColorRole.Window, bg)
    palette.setColor(QPalette.ColorRole.WindowText, text)
    palette.setColor(QPalette.ColorRole.Base, bg_in)
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(c['bg_secondary']))
    palette.setColor(QPalette.ColorRole.Text, text)
    palette.setColor(QPalette.ColorRole.Button, QColor(c['btn_primary_bg']))
    palette.setColor(QPalette.ColorRole.ButtonText, text)
    palette.setColor(QPalette.ColorRole.Highlight, accent)
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(c['bg_secondary']))
    palette.setColor(QPalette.ColorRole.ToolTipText, text)
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(c['text_muted']))

    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.WindowText, disabled
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.Text, disabled
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.ButtonText, disabled
    )

    app.setPalette(palette)


def build_stylesheet() -> str:
    c = ThemeManager.colors()
    return f"""
    /* GLOBAL */
    * {{
        outline: 0;
    }}

    QWidget {{
        background-color: {c['bg_primary']};
        color: {c['text_primary']};
        font-family: "Segoe UI";
        font-size: 12px;
    }}

    QMainWindow {{
        background-color: {c['bg_primary']};
    }}

    /* LABELS — NO BORDERS */
    QLabel {{
        background: transparent;
        color: {c['text_primary']};
        border: 0px;
        padding: 0px;
    }}

    /* FRAMES */
    QFrame {{
        background: transparent;
        border: 0px;
    }}

    QFrame[class="group"] {{
        background-color: {c['bg_primary']};
        border: 1px solid {c['border']};
        border-radius: 0px;
    }}

    QFrame[class="sidebar"] {{
        background-color: {c['sidebar_bg']};
        border: 0px;
        border-right: 1px solid {c['border']};
    }}

    QFrame[class="divider"] {{
        background-color: {c['border']};
        max-height: 1px;
        min-height: 1px;
        border: 0px;
    }}

    /* SCROLL AREA */
    QScrollArea {{
        background: transparent;
        border: 0px;
    }}
    QScrollArea > QWidget > QWidget {{
        background: transparent;
    }}
    QScrollBar:vertical {{
        background: {c['bg_primary']};
        width: 14px;
        border: 0px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background: {c['border']};
        min-height: 20px;
        border-radius: 0px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {c['text_muted']};
    }}
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0px;
        border: 0px;
    }}
    QScrollBar:horizontal {{
        background: {c['bg_primary']};
        height: 14px;
        border: 0px;
    }}
    QScrollBar::handle:horizontal {{
        background: {c['border']};
        min-width: 20px;
    }}
    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal {{
        width: 0px;
        border: 0px;
    }}

    /* BUTTONS — Native Windows style */
    QPushButton {{
        background-color: {c['btn_primary_bg']};
        color: {c['btn_primary_text']};
        border: 1px solid {c['btn_primary_border']};
        border-radius: 0px;
        padding: 6px 16px;
        font-size: 12px;
        min-height: 22px;
    }}
    QPushButton:hover {{
        background-color: {c['btn_primary_hover']};
        border: 1px solid {c['accent']};
    }}
    QPushButton:pressed {{
        background-color: {c['bg_selected']};
    }}
    QPushButton:disabled {{
        background-color: {c['bg_disabled']};
        color: {c['text_disabled']};
        border: 1px solid {c['border_light']};
    }}
    QPushButton:default {{
        border: 1px solid {c['accent']};
    }}

    QPushButton[class="accent"] {{
        background-color: {c['btn_accent_bg']};
        color: {c['btn_accent_text']};
        border: 1px solid {c['btn_accent_bg']};
        font-weight: 600;
    }}
    QPushButton[class="accent"]:hover {{
        background-color: {c['accent_hover']};
        border: 1px solid {c['accent_hover']};
    }}
    QPushButton[class="accent"]:pressed {{
        background-color: {c['accent_pressed']};
    }}

    QPushButton[class="danger"] {{
        color: {c['error']};
    }}
    QPushButton[class="danger"]:hover {{
        border: 1px solid {c['error']};
    }}

    /* LINE EDIT */
    QLineEdit {{
        background-color: {c['bg_input']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 0px;
        padding: 4px 6px;
        selection-background-color: {c['accent']};
        selection-color: #ffffff;
        min-height: 20px;
    }}
    QLineEdit:focus {{
        border: 1px solid {c['border_focus']};
    }}
    QLineEdit:disabled {{
        background-color: {c['bg_disabled']};
        color: {c['text_disabled']};
    }}

    QTextEdit, QPlainTextEdit {{
        background-color: {c['bg_input']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 0px;
        padding: 4px;
        selection-background-color: {c['accent']};
        selection-color: #ffffff;
    }}
    QTextEdit:focus, QPlainTextEdit:focus {{
        border: 1px solid {c['border_focus']};
    }}

    /* COMBO BOX */
    QComboBox {{
        background-color: {c['bg_input']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 0px;
        padding: 4px 6px;
        min-height: 20px;
    }}
    QComboBox:focus {{
        border: 1px solid {c['border_focus']};
    }}
    QComboBox:hover {{
        border: 1px solid {c['accent']};
    }}
    QComboBox::drop-down {{
        border: 0px;
        border-left: 1px solid {c['border']};
        width: 20px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {c['bg_input']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        selection-background-color: {c['bg_selected']};
        selection-color: {c['text_primary']};
        outline: 0;
    }}

    /* SLIDER */
    QSlider {{
        background: transparent;
        border: 0px;
    }}
    QSlider::groove:horizontal {{
        background: {c['border_light']};
        height: 4px;
        border: 1px solid {c['border']};
    }}
    QSlider::handle:horizontal {{
        background: {c['bg_input']};
        width: 12px;
        height: 16px;
        margin: -7px 0;
        border: 1px solid {c['border']};
    }}
    QSlider::handle:horizontal:hover {{
        background: {c['bg_hover']};
        border: 1px solid {c['accent']};
    }}
    QSlider::sub-page:horizontal {{
        background: {c['accent']};
        border: 1px solid {c['accent']};
    }}

    /* PROGRESS BAR */
    QProgressBar {{
        background-color: {c['bg_input']};
        border: 1px solid {c['border']};
        border-radius: 0px;
        height: 18px;
        text-align: center;
        color: {c['text_primary']};
    }}
    QProgressBar::chunk {{
        background-color: {c['accent']};
    }}

    /* TABLE */
    QTableWidget, QTableView {{
        background-color: {c['bg_input']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        gridline-color: {c['border_light']};
        selection-background-color: {c['bg_selected']};
        selection-color: {c['text_primary']};
        alternate-background-color: {c['bg_primary']};
    }}
    QTableWidget::item, QTableView::item {{
        padding: 4px;
        border: 0px;
    }}
    QTableWidget::item:selected, QTableView::item:selected {{
        background-color: {c['bg_selected']};
        color: {c['text_primary']};
    }}
    QHeaderView {{
        background-color: {c['bg_primary']};
        border: 0px;
    }}
    QHeaderView::section {{
        background-color: {c['bg_primary']};
        color: {c['text_primary']};
        font-weight: 600;
        padding: 4px;
        border: 0px;
        border-right: 1px solid {c['border_light']};
        border-bottom: 1px solid {c['border']};
    }}
    QTableCornerButton::section {{
        background-color: {c['bg_primary']};
        border: 0px;
        border-right: 1px solid {c['border']};
        border-bottom: 1px solid {c['border']};
    }}

    /* CHECKBOX / RADIO */
    QCheckBox {{
        color: {c['text_primary']};
        spacing: 6px;
        background: transparent;
        border: 0px;
    }}
    QCheckBox::indicator {{
        width: 14px;
        height: 14px;
        border: 1px solid {c['border']};
        background: {c['bg_input']};
    }}
    QCheckBox::indicator:checked {{
        background: {c['accent']};
        border: 1px solid {c['accent']};
    }}
    QCheckBox::indicator:hover {{
        border: 1px solid {c['accent']};
    }}

    QRadioButton {{
        color: {c['text_primary']};
        spacing: 6px;
        background: transparent;
        border: 0px;
    }}
    QRadioButton::indicator {{
        width: 14px;
        height: 14px;
        border: 1px solid {c['border']};
        border-radius: 7px;
        background: {c['bg_input']};
    }}
    QRadioButton::indicator:checked {{
        background: {c['accent']};
        border: 1px solid {c['accent']};
    }}
    QRadioButton::indicator:hover {{
        border: 1px solid {c['accent']};
    }}

    /* GROUP BOX (for Rufus-style panels) */
    QGroupBox {{
        background-color: transparent;
        border: 1px solid {c['border']};
        border-radius: 0px;
        margin-top: 12px;
        padding-top: 10px;
        font-weight: 600;
        color: {c['text_primary']};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 8px;
        padding: 0 4px;
        color: {c['text_primary']};
    }}

    /* TOOLTIP */
    QToolTip {{
        background-color: {c['bg_secondary']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        padding: 4px 6px;
    }}

    /* DIALOG / MESSAGE BOX */
    QMessageBox, QDialog {{
        background-color: {c['bg_primary']};
        color: {c['text_primary']};
    }}
    QMessageBox QLabel, QDialog QLabel {{
        color: {c['text_primary']};
        background: transparent;
        border: 0px;
    }}

    /* TAB WIDGET */
    QTabWidget::pane {{
        border: 1px solid {c['border']};
        background: {c['bg_primary']};
    }}
    QTabBar::tab {{
        background: {c['bg_primary']};
        color: {c['text_primary']};
        padding: 6px 14px;
        border: 1px solid {c['border']};
        border-bottom: 0px;
        margin-right: 2px;
    }}
    QTabBar::tab:selected {{
        background: {c['bg_input']};
        border-bottom: 1px solid {c['bg_input']};
    }}
    QTabBar::tab:hover {{
        background: {c['bg_hover']};
    }}

    /* SPLITTER */
    QSplitter::handle {{
        background-color: {c['border']};
    }}
    QSplitter::handle:horizontal {{
        width: 1px;
    }}
    QSplitter::handle:vertical {{
        height: 1px;
    }}

    /* STACKED WIDGET */
    QStackedWidget {{
        background-color: {c['bg_primary']};
        border: 0px;
    }}
    """


def apply_theme(app: QApplication):
    ThemeManager.load()
    app.setStyle("Fusion")
    apply_palette(app)
    app.setStyleSheet(build_stylesheet())


def refresh_theme(app: QApplication):
    apply_palette(app)
    app.setStyleSheet(build_stylesheet())