from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt


LIGHT = {
    "window":          "#F0F0F0",
    "window_text":     "#000000",
    "base":            "#FFFFFF",
    "alt_base":        "#F7F7F7",
    "text":            "#000000",
    "button":          "#E1E1E1",
    "button_text":     "#000000",
    "highlight":       "#0078D4",
    "highlight_text":  "#FFFFFF",
    "border":          "#ADADAD",
    "sidebar_bg":      "#F0F0F0",
    "sidebar_text":    "#000000",
    "sidebar_active":  "#0078D4",
    "card_bg":         "#FFFFFF",
    "accent":          "#0078D4",
    "danger":          "#C42B1C",
    "success":         "#0F7B0F",
    "warning":         "#9D5D00",
}

DARK = {
    "window":          "#202020",
    "window_text":     "#FFFFFF",
    "base":            "#2B2B2B",
    "alt_base":        "#252525",
    "text":            "#FFFFFF",
    "button":          "#3C3C3C",
    "button_text":     "#FFFFFF",
    "highlight":       "#0078D4",
    "highlight_text":  "#FFFFFF",
    "border":          "#555555",
    "sidebar_bg":      "#1C1C1C",
    "sidebar_text":    "#CCCCCC",
    "sidebar_active":  "#0078D4",
    "card_bg":         "#2B2B2B",
    "accent":          "#0078D4",
    "danger":          "#F04747",
    "success":         "#43B581",
    "warning":         "#FAA61A",
}

_current_theme = "light"


def get_colors() -> dict:
    return LIGHT if _current_theme == "light" else DARK


def apply_theme(app: QApplication, theme: str = "light"):
    global _current_theme
    _current_theme = theme
    c = get_colors()

    app.setStyle("Fusion")
    _apply_palette(app, c)
    app.setStyleSheet(_build_stylesheet(c))


def _apply_palette(app: QApplication, c: dict):
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window,          QColor(c["window"]))
    palette.setColor(QPalette.ColorRole.WindowText,      QColor(c["window_text"]))
    palette.setColor(QPalette.ColorRole.Base,            QColor(c["base"]))
    palette.setColor(QPalette.ColorRole.AlternateBase,   QColor(c["alt_base"]))
    palette.setColor(QPalette.ColorRole.Text,            QColor(c["text"]))
    palette.setColor(QPalette.ColorRole.ButtonText,      QColor(c["button_text"]))
    palette.setColor(QPalette.ColorRole.Button,          QColor(c["button"]))
    palette.setColor(QPalette.ColorRole.Highlight,       QColor(c["highlight"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(c["highlight_text"]))
    app.setPalette(palette)


def _build_stylesheet(c: dict) -> str:
    return f"""
        QMainWindow, QDialog, QWidget {{
            background-color: {c["window"]};
            color: {c["window_text"]};
            font-family: "Segoe UI";
            font-size: 9pt;
        }}

        /* ── Sidebar ── */
        QWidget#sidebar {{
            background-color: {c["sidebar_bg"]};
            border-right: 1px solid {c["border"]};
        }}

        QPushButton#nav_btn {{
            background-color: transparent;
            color: {c["sidebar_text"]};
            border: none;
            border-radius: 0px;
            text-align: left;
            padding: 8px 16px;
            font-size: 9pt;
        }}
        QPushButton#nav_btn:hover {{
            background-color: {c["highlight"]};
            color: #FFFFFF;
        }}
        QPushButton#nav_btn[active="true"] {{
            background-color: {c["highlight"]};
            color: #FFFFFF;
            font-weight: bold;
        }}

        /* ── Buttons ── */
        QPushButton {{
            background-color: {c["button"]};
            color: {c["button_text"]};
            border: 1px solid {c["border"]};
            border-radius: 0px;
            padding: 5px 12px;
            font-size: 9pt;
        }}
        QPushButton:hover {{
            background-color: {c["highlight"]};
            color: #FFFFFF;
            border-color: {c["highlight"]};
        }}
        QPushButton:pressed {{
            background-color: #005A9E;
            color: #FFFFFF;
        }}
        QPushButton:disabled {{
            background-color: {c["alt_base"]};
            color: #888888;
            border-color: {c["border"]};
        }}

        QPushButton#primary_btn {{
            background-color: {c["highlight"]};
            color: #FFFFFF;
            border: 1px solid {c["highlight"]};
            font-weight: bold;
        }}
        QPushButton#primary_btn:hover {{
            background-color: #005A9E;
        }}

        QPushButton#danger_btn {{
            background-color: {c["danger"]};
            color: #FFFFFF;
            border: 1px solid {c["danger"]};
        }}
        QPushButton#danger_btn:hover {{
            background-color: #A82315;
        }}

        /* ── Inputs ── */
        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: {c["base"]};
            color: {c["text"]};
            border: 1px solid {c["border"]};
            border-radius: 0px;
            padding: 4px 6px;
            font-size: 9pt;
            selection-background-color: {c["highlight"]};
        }}
        QLineEdit:focus, QTextEdit:focus {{
            border-color: {c["highlight"]};
        }}

        /* ── ComboBox ── */
        QComboBox {{
            background-color: {c["base"]};
            color: {c["text"]};
            border: 1px solid {c["border"]};
            border-radius: 0px;
            padding: 4px 6px;
            font-size: 9pt;
        }}
        QComboBox:hover {{
            border-color: {c["highlight"]};
        }}
        QComboBox QAbstractItemView {{
            background-color: {c["base"]};
            color: {c["text"]};
            border: 1px solid {c["border"]};
            selection-background-color: {c["highlight"]};
            selection-color: #FFFFFF;
        }}

        /* ── GroupBox ── */
        QGroupBox {{
            border: 1px solid {c["border"]};
            border-radius: 0px;
            margin-top: 8px;
            padding-top: 8px;
            font-size: 9pt;
            font-weight: bold;
            color: {c["window_text"]};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 4px;
            left: 8px;
        }}

        /* ── Tables ── */
        QTableWidget, QTableView {{
            background-color: {c["base"]};
            color: {c["text"]};
            border: 1px solid {c["border"]};
            border-radius: 0px;
            gridline-color: {c["border"]};
            font-size: 9pt;
            selection-background-color: {c["highlight"]};
            selection-color: #FFFFFF;
        }}
        QHeaderView::section {{
            background-color: {c["button"]};
            color: {c["button_text"]};
            border: 1px solid {c["border"]};
            padding: 4px 8px;
            font-weight: bold;
            font-size: 9pt;
        }}

        /* ── Progress Bar ── */
        QProgressBar {{
            background-color: {c["base"]};
            border: 1px solid {c["border"]};
            border-radius: 0px;
            text-align: center;
            color: {c["text"]};
            font-size: 9pt;
        }}
        QProgressBar::chunk {{
            background-color: {c["highlight"]};
        }}

        /* ── Scroll Bars ── */
        QScrollBar:vertical {{
            background: {c["alt_base"]};
            width: 14px;
            border: none;
        }}
        QScrollBar::handle:vertical {{
            background: {c["border"]};
            min-height: 20px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {c["highlight"]};
        }}
        QScrollBar:horizontal {{
            background: {c["alt_base"]};
            height: 14px;
            border: none;
        }}
        QScrollBar::handle:horizontal {{
            background: {c["border"]};
            min-width: 20px;
        }}

        /* ── Labels ── */
        QLabel {{
            color: {c["window_text"]};
            border: none;
            background: transparent;
            font-size: 9pt;
        }}

        /* ── Frames ── */
        QFrame {{
            border: none;
        }}

        /* ── Tab Widget ── */
        QTabWidget::pane {{
            border: 1px solid {c["border"]};
        }}
        QTabBar::tab {{
            background-color: {c["button"]};
            color: {c["button_text"]};
            border: 1px solid {c["border"]};
            padding: 6px 14px;
            font-size: 9pt;
        }}
        QTabBar::tab:selected {{
            background-color: {c["highlight"]};
            color: #FFFFFF;
        }}

        /* ── Spin Box ── */
        QSpinBox, QDoubleSpinBox {{
            background-color: {c["base"]};
            color: {c["text"]};
            border: 1px solid {c["border"]};
            border-radius: 0px;
            padding: 3px 6px;
            font-size: 9pt;
        }}

        /* ── Slider ── */
        QSlider::groove:horizontal {{
            height: 4px;
            background: {c["border"]};
        }}
        QSlider::handle:horizontal {{
            background: {c["highlight"]};
            width: 14px;
            height: 14px;
            margin: -5px 0;
        }}

        /* ── Status Bar ── */
        QStatusBar {{
            background-color: {c["button"]};
            color: {c["button_text"]};
            border-top: 1px solid {c["border"]};
            font-size: 8pt;
        }}

        /* ── Tooltips ── */
        QToolTip {{
            background-color: {c["base"]};
            color: {c["text"]};
            border: 1px solid {c["border"]};
            font-size: 8pt;
        }}

        /* ── Radio / Check ── */
        QRadioButton, QCheckBox {{
            color: {c["window_text"]};
            font-size: 9pt;
            background: transparent;
        }}

        /* ── Splitter ── */
        QSplitter::handle {{
            background-color: {c["border"]};
        }}
    """