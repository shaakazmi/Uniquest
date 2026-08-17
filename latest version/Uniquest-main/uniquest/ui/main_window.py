# import sys
# from ui.search import SearchPage
# from pathlib import Path
# from PyQt6.QtWidgets import (
#     QMainWindow, QWidget, QHBoxLayout,
#     QVBoxLayout, QLabel, QPushButton,
#     QFrame, QStackedWidget, QSizePolicy,
#     QSpacerItem, QApplication,
# )
# from PyQt6.QtCore import (
#     Qt, QSize, pyqtSignal, QTimer
# )
# from PyQt6.QtGui import (
#     QIcon, QPixmap, QFont,
# )

# from utils.theme import ThemeManager, build_stylesheet, refresh_theme
# from ui.dashboard import DashboardPage
# from ui.projects import ProjectsPage
# from ui.analysis import AnalysisPage
# from ui.results import ResultsPage
# from ui.settings import SettingsPage


# def assets_path() -> Path:
#     if getattr(sys, "frozen", False):
#         base = Path(sys._MEIPASS) if hasattr(sys, "_MEIPASS") else Path(sys.executable).parent
#     else:
#         base = Path(__file__).parent.parent
#     return base / "assets"


# # ─────────────────────────────────────────────
# #  SIDEBAR NAV BUTTON
# # ─────────────────────────────────────────────
# class NavButton(QPushButton):
#     def __init__(self, label: str, parent=None):
#         super().__init__(parent)
#         self.label_text = label
#         self._active = False
#         if isinstance(label, tuple):
#           label = label[0] if label else ""
#         self.setText("  " + str(label))
#         self.setFixedHeight(32)
#         self.setCursor(Qt.CursorShape.PointingHandCursor)
#         self._refresh_style()

#     def set_active(self, active: bool):
#         self._active = active
#         self._refresh_style()

#     def _refresh_style(self):
#         c = ThemeManager.colors()
#         if self._active:
#             self.setStyleSheet(f"""
#                 QPushButton {{
#                     background-color: {c['sidebar_active_bg']};
#                     color: {c['sidebar_active']};
#                     border: 0px;
#                     border-left: 3px solid {c['sidebar_active']};
#                     text-align: left;
#                     padding-left: 14px;
#                     font-weight: 600;
#                     font-size: 12px;
#                 }}
#             """)
#         else:
#             self.setStyleSheet(f"""
#                 QPushButton {{
#                     background-color: transparent;
#                     color: {c['sidebar_text']};
#                     border: 0px;
#                     border-left: 3px solid transparent;
#                     text-align: left;
#                     padding-left: 14px;
#                     font-size: 12px;
#                 }}
#                 QPushButton:hover {{
#                     background-color: {c['bg_hover']};
#                 }}
#             """)

#     def apply_theme(self):
#         self._refresh_style()


# # ─────────────────────────────────────────────
# #  SIDEBAR
# # ─────────────────────────────────────────────
# class Sidebar(QFrame):
#     nav_clicked = pyqtSignal(int)

#     NAV_ITEMS = [
#         "Dashboard",
#         "Projects",
#         "Analysis",
#         "Results",
#         ("search",    "Search"),
#         "Settings",
#     ]

#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.setFixedWidth(180)
#         self.setProperty("class", "sidebar")
#         self._buttons = []
#         self._build()
#         ThemeManager.add_listener(self.apply_theme)

#     def _build(self):
#         layout = QVBoxLayout(self)
#         layout.setContentsMargins(0, 0, 0, 0)
#         layout.setSpacing(0)

#         # Logo/title area
#         header = QFrame()
#         header.setFixedHeight(56)
#         h_layout = QHBoxLayout(header)
#         h_layout.setContentsMargins(12, 0, 12, 0)
#         h_layout.setSpacing(8)

#         # Logo
#         logo_path = assets_path() / "logo.ico"
#         self.logo_lbl = QLabel()
#         if logo_path.exists():
#             pix = QPixmap(str(logo_path)).scaled(
#                 24, 24,
#                 Qt.AspectRatioMode.KeepAspectRatio,
#                 Qt.TransformationMode.SmoothTransformation,
#             )
#             self.logo_lbl.setPixmap(pix)
#         self.logo_lbl.setFixedSize(28, 28)

#         self.app_name = QLabel("Uniquest")
#         self.app_name.setStyleSheet(
#             "font-size: 15px; font-weight: 700;"
#             "background: transparent; border: 0px;"
#         )

#         h_layout.addWidget(self.logo_lbl)
#         h_layout.addWidget(self.app_name)
#         h_layout.addStretch()
#         layout.addWidget(header)

#         # Divider
#         div = QFrame()
#         div.setFixedHeight(1)
#         div.setStyleSheet(
#             f"background: {ThemeManager.get('border')}; border: 0px;"
#         )
#         layout.addWidget(div)

#         # Nav buttons
#         layout.addSpacing(8)
#         for i, label in enumerate(self.NAV_ITEMS):
#             btn = NavButton(label)
#             btn.clicked.connect(
#                 lambda checked, idx=i: self._on_nav(idx)
#             )
#             layout.addWidget(btn)
#             self._buttons.append(btn)

#         layout.addStretch()

#         # Divider before theme toggle
#         div2 = QFrame()
#         div2.setFixedHeight(1)
#         div2.setStyleSheet(
#             f"background: {ThemeManager.get('border')}; border: 0px;"
#         )
#         layout.addWidget(div2)

#         # Theme toggle
#         self.theme_btn = QPushButton()
#         self.theme_btn.setFixedHeight(28)
#         self.theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
#         self.theme_btn.clicked.connect(self._toggle_theme)
#         self._update_theme_btn()
#         layout.addWidget(self.theme_btn)

#         # Version
#         ver_lbl = QLabel("v1.0.0")
#         ver_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
#         ver_lbl.setStyleSheet(
#             "font-size: 10px; color: #888888;"
#             "background: transparent; border: 0px; padding: 4px;"
#         )
#         layout.addWidget(ver_lbl)

#         self._set_active(0)

#     def _on_nav(self, index: int):
#         self._set_active(index)
#         self.nav_clicked.emit(index)

#     def _set_active(self, index: int):
#         for i, btn in enumerate(self._buttons):
#             btn.set_active(i == index)

#     def set_page(self, index: int):
#         self._set_active(index)

#     def _toggle_theme(self):
#         ThemeManager.toggle()
#         app = QApplication.instance()
#         if app:
#             refresh_theme(app)
#         self.apply_theme()

#     def _update_theme_btn(self):
#         c = ThemeManager.colors()
#         text = "Switch to Light" if ThemeManager.is_dark() else "Switch to Dark"
#         self.theme_btn.setText(text)
#         self.theme_btn.setStyleSheet(f"""
#             QPushButton {{
#                 background: transparent;
#                 color: {c['sidebar_text']};
#                 border: 0px;
#                 text-align: center;
#                 padding: 4px;
#                 font-size: 11px;
#             }}
#             QPushButton:hover {{
#                 background: {c['bg_hover']};
#                 color: {c['accent']};
#             }}
#         """)

#     def apply_theme(self):
#         c = ThemeManager.colors()
#         self.setStyleSheet(
#             f"background-color: {c['sidebar_bg']};"
#             f"border: 0px; border-right: 1px solid {c['border']};"
#         )
#         self.app_name.setStyleSheet(
#             f"font-size: 15px; font-weight: 700; color: {c['text_primary']};"
#             f"background: transparent; border: 0px;"
#         )
#         self._update_theme_btn()
#         for btn in self._buttons:
#             btn.apply_theme()


# # ─────────────────────────────────────────────
# #  TOP BAR
# # ─────────────────────────────────────────────
# class TopBar(QFrame):
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.setFixedHeight(44)
#         self._build()
#         ThemeManager.add_listener(self.apply_theme)

#     def _build(self):
#         layout = QHBoxLayout(self)
#         layout.setContentsMargins(16, 0, 16, 0)
#         layout.setSpacing(8)

#         self.title_lbl = QLabel("Dashboard")
#         self.title_lbl.setStyleSheet(
#             "font-size: 14px; font-weight: 600;"
#             "background: transparent; border: 0px;"
#         )
#         self.sub_lbl = QLabel("")
#         self.sub_lbl.setStyleSheet(
#             "font-size: 11px; background: transparent; border: 0px;"
#         )

#         col = QVBoxLayout()
#         col.setSpacing(0)
#         col.addWidget(self.title_lbl)
#         col.addWidget(self.sub_lbl)

#         layout.addLayout(col)
#         layout.addStretch()
#         self.apply_theme()

#     def set_title(self, title: str, subtitle: str = ""):
#         self.title_lbl.setText(title)
#         self.sub_lbl.setText(subtitle)
#         self.sub_lbl.setVisible(bool(subtitle))

#     def apply_theme(self):
#         c = ThemeManager.colors()
#         self.setStyleSheet(f"""
#             QFrame {{
#                 background-color: {c['bg_primary']};
#                 border: 0px;
#                 border-bottom: 1px solid {c['border']};
#             }}
#         """)
#         self.title_lbl.setStyleSheet(
#             f"font-size: 14px; font-weight: 600; color: {c['text_primary']};"
#             f"background: transparent; border: 0px;"
#         )
#         self.sub_lbl.setStyleSheet(
#             f"font-size: 11px; color: {c['text_muted']};"
#             f"background: transparent; border: 0px;"
#         )


# # ─────────────────────────────────────────────
# #  STATUS BAR
# # ─────────────────────────────────────────────
# class StatusBar(QFrame):
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.setFixedHeight(22)
#         self._build()
#         ThemeManager.add_listener(self.apply_theme)

#     def _build(self):
#         layout = QHBoxLayout(self)
#         layout.setContentsMargins(10, 0, 10, 0)
#         layout.setSpacing(8)

#         self.status_lbl = QLabel("Ready")
#         self.status_lbl.setStyleSheet(
#             "font-size: 11px; background: transparent; border: 0px;"
#         )
#         layout.addWidget(self.status_lbl)
#         layout.addStretch()

#         self.right_lbl = QLabel("Uniquest v1.0.0")
#         self.right_lbl.setStyleSheet(
#             "font-size: 11px; background: transparent; border: 0px;"
#         )
#         layout.addWidget(self.right_lbl)
#         self.apply_theme()

#     def set_status(self, msg: str):
#         self.status_lbl.setText(msg)

#     def apply_theme(self):
#         c = ThemeManager.colors()
#         self.setStyleSheet(f"""
#             QFrame {{
#                 background-color: {c['bg_primary']};
#                 border: 0px;
#                 border-top: 1px solid {c['border']};
#             }}
#         """)
#         self.status_lbl.setStyleSheet(
#             f"font-size: 11px; color: {c['text_muted']};"
#             f"background: transparent; border: 0px;"
#         )
#         self.right_lbl.setStyleSheet(
#             f"font-size: 11px; color: {c['text_muted']};"
#             f"background: transparent; border: 0px;"
#         )


# # ─────────────────────────────────────────────
# #  MAIN WINDOW
# # ─────────────────────────────────────────────
# class MainWindow(QMainWindow):
#     PAGE_TITLES = [
#         ("Dashboard",  "Overview of your projects"),
#         ("Projects",   "Manage analysis projects"),
#         ("Analysis",   "Import files and run scan"),
#         ("Results",    "View similarity matches"),
#         ("Search",     "Live search across all indexed content"),
#         ("Settings",   "Configure preferences"),
#     ]

#     def __init__(self):
#         super().__init__()
#         self._current_page = 0
#         self._current_project = None
#         self._setup_window()
#         self._build_ui()
#         self._connect_signals()
#         self._go_to_page(0)
#         self._page_search = SearchPage(self)
#         self._stack.addWidget(self._page_search)

#     def _setup_window(self):
#         # Standard Windows title bar with min/max/close
#         self.setWindowFlags(
#             Qt.WindowType.Window
#             | Qt.WindowType.WindowTitleHint
#             | Qt.WindowType.WindowSystemMenuHint
#             | Qt.WindowType.WindowMinMaxButtonsHint
#             | Qt.WindowType.WindowCloseButtonHint
#         )
#         self.setWindowTitle("Uniquest")
#         self.setMinimumSize(900, 600)
#         self.resize(1100, 700)

#         icon_path = assets_path() / "logo.ico"
#         if icon_path.exists():
#             self.setWindowIcon(QIcon(str(icon_path)))

#         screen = QApplication.primaryScreen()
#         if screen:
#             geo = screen.availableGeometry()
#             x = (geo.width() - 1100) // 2
#             y = (geo.height() - 700) // 2
#             self.move(x, y)

#     def _build_ui(self):
#         central = QWidget()
#         self.setCentralWidget(central)

#         root = QHBoxLayout(central)
#         root.setContentsMargins(0, 0, 0, 0)
#         root.setSpacing(0)

#         self.sidebar = Sidebar()
#         root.addWidget(self.sidebar)

#         right = QVBoxLayout()
#         right.setContentsMargins(0, 0, 0, 0)
#         right.setSpacing(0)

#         self.topbar = TopBar()
#         right.addWidget(self.topbar)

#         self.stack = QStackedWidget()
#         self.page_dashboard = DashboardPage()
#         self.page_projects  = ProjectsPage()
#         self.page_analysis  = AnalysisPage()
#         self.page_results   = ResultsPage(self)
#         self.page_settings  = SettingsPage()

#         self.stack.addWidget(self.page_dashboard)
#         self.stack.addWidget(self.page_projects)
#         self.stack.addWidget(self.page_analysis)
#         self.stack.addWidget(self.page_results)
#         self.stack.addWidget(self.page_settings)
#         right.addWidget(self.stack, 1)

#         self.statusbar_custom = StatusBar()
#         right.addWidget(self.statusbar_custom)

#         root.addLayout(right, 1)

#     def _connect_signals(self):
#         self.sidebar.nav_clicked.connect(self._go_to_page)

#         self.page_dashboard.open_project.connect(self._open_project_from_dashboard)
#         self.page_dashboard.go_to_projects.connect(lambda: self._go_to_page(1))
#         self.page_dashboard.go_to_analysis.connect(lambda: self._go_to_page(2))

#         self.page_projects.open_analysis.connect(self._open_project_analysis)
#         self.page_projects.project_created.connect(self._on_project_created)

#         self.page_analysis.analysis_complete.connect(self._on_analysis_complete)
#         self.page_analysis.status_message.connect(self.statusbar_custom.set_status)

#         self.page_settings.theme_changed.connect(self._on_theme_changed)

#         ThemeManager.add_listener(self._apply_theme)

#     def _go_to_page(self, index: int):
#         self._current_page = index
#         self.stack.setCurrentIndex(index)
#         self.sidebar.set_page(index)
#         title, subtitle = self.PAGE_TITLES[index]
#         self.topbar.set_title(title, subtitle)
#         self._refresh_page(index)

#     def _refresh_page(self, index: int):
#         if index == 0:
#             self.page_dashboard.refresh()
#         elif index == 1:
#             self.page_projects.refresh()
#         elif index == 2:
#             self.page_analysis.refresh()
#         elif index == 3:
#             if self._current_project:
#                 self.page_results.load_project(self._current_project)
#         elif index == 4:
#             self.page_settings.refresh()

#     def _open_project_from_dashboard(self, project_id: int):
#         self._current_project = project_id
#         self.page_analysis.set_project(project_id)
#         self._go_to_page(2)

#     def _open_project_analysis(self, project_id: int):
#         self._current_project = project_id
#         self.page_analysis.set_project(project_id)
#         self._go_to_page(2)

#     def _on_project_created(self, project_id: int):
#         self._current_project = project_id
#         self.page_analysis.set_project(project_id)
#         self._go_to_page(2)

#     def _on_analysis_complete(self, project_id, text_found, img_found):
#         self._current_project = project_id
#         self.page_results.load_project(project_id)
#         self.statusbar_custom.set_status(
#             f"Analysis complete - {text_found} text, {img_found} image matches"
#         )
#         self.setWindowState(
#             self.windowState() & ~Qt.WindowState.WindowMinimized
#         )
#         self.raise_()
#         self.activateWindow()
#         self.showNormal()
#         QTimer.singleShot(600, lambda: self._go_to_page(3))

#     def _on_theme_changed(self):
#         app = QApplication.instance()
#         if app:
#             refresh_theme(app)
#         self._apply_theme()

#     def _apply_theme(self):
#         c = ThemeManager.colors()
#         self.centralWidget().setStyleSheet(
#             f"background-color: {c['bg_primary']};"
#         )

#     def closeEvent(self, event):
#         ThemeManager.remove_listener(self._apply_theme)
#         event.accept()








import sys
from pathlib import Path
from ui.ip_registry import RegistryPage
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout,
    QVBoxLayout, QLabel, QPushButton,
    QFrame, QStackedWidget, QSizePolicy,
    QSpacerItem, QApplication,
)
from PyQt6.QtCore import (
    Qt, QSize, pyqtSignal, QTimer
)
from PyQt6.QtGui import (
    QIcon, QPixmap, QFont,
)

from utils.theme import ThemeManager, build_stylesheet, refresh_theme
from ui.dashboard import DashboardPage
from ui.search import SearchPage
from ui.settings import SettingsPage


def assets_path() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS) if hasattr(sys, "_MEIPASS") else Path(sys.executable).parent
    else:
        base = Path(__file__).parent.parent
    return base / "assets"


# ─────────────────────────────────────────────
#  SIDEBAR NAV BUTTON
# ─────────────────────────────────────────────
class NavButton(QPushButton):
    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        if isinstance(label, (tuple, list)):
            label = label[0] if label else ""
        self.label_text = str(label)
        self._active = False
        self.setText("  " + self.label_text)
        self.setFixedHeight(32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._refresh_style()

    def set_active(self, active: bool):
        self._active = active
        self._refresh_style()

    def _refresh_style(self):
        c = ThemeManager.colors()
        if self._active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {c['sidebar_active_bg']};
                    color: {c['sidebar_active']};
                    border: 0px;
                    border-left: 3px solid {c['sidebar_active']};
                    text-align: left;
                    padding-left: 14px;
                    font-weight: 600;
                    font-size: 12px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {c['sidebar_text']};
                    border: 0px;
                    border-left: 3px solid transparent;
                    text-align: left;
                    padding-left: 14px;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background-color: {c['bg_hover']};
                }}
            """)

    def apply_theme(self):
        self._refresh_style()


# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────
class Sidebar(QFrame):
    nav_clicked = pyqtSignal(int)

    NAV_ITEMS = [
        "Dashboard",
        "Search",
        "Registry",
        "Settings",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(180)
        self.setProperty("class", "sidebar")
        self._buttons = []
        self._build()
        ThemeManager.add_listener(self.apply_theme)

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Logo/title area
        header = QFrame()
        header.setFixedHeight(56)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(12, 0, 12, 0)
        h_layout.setSpacing(8)

        logo_path = assets_path() / "logo.ico"
        self.logo_lbl = QLabel()
        if logo_path.exists():
            pix = QPixmap(str(logo_path)).scaled(
                24, 24,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.logo_lbl.setPixmap(pix)
        self.logo_lbl.setFixedSize(28, 28)

        self.app_name = QLabel("IPOGenie")
        self.app_name.setStyleSheet(
            "font-size: 15px; font-weight: 700;"
            "background: transparent; border: 0px;"
        )

        h_layout.addWidget(self.logo_lbl)
        h_layout.addWidget(self.app_name)
        h_layout.addStretch()
        layout.addWidget(header)

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(
            f"background: {ThemeManager.get('border')}; border: 0px;"
        )
        layout.addWidget(div)

        layout.addSpacing(8)
        for i, label in enumerate(self.NAV_ITEMS):
            btn = NavButton(label)
            btn.clicked.connect(
                lambda checked, idx=i: self._on_nav(idx)
            )
            layout.addWidget(btn)
            self._buttons.append(btn)

        layout.addStretch()

        div2 = QFrame()
        div2.setFixedHeight(1)
        div2.setStyleSheet(
            f"background: {ThemeManager.get('border')}; border: 0px;"
        )
        layout.addWidget(div2)

        self.theme_btn = QPushButton()
        self.theme_btn.setFixedHeight(28)
        self.theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_btn.clicked.connect(self._toggle_theme)
        self._update_theme_btn()
        layout.addWidget(self.theme_btn)

        ver_lbl = QLabel("v1.0.0")
        ver_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ver_lbl.setStyleSheet(
            "font-size: 10px; color: #888888;"
            "background: transparent; border: 0px; padding: 4px;"
        )
        layout.addWidget(ver_lbl)

        self._set_active(0)

    def _on_nav(self, index: int):
        self._set_active(index)
        self.nav_clicked.emit(index)

    def _set_active(self, index: int):
        for i, btn in enumerate(self._buttons):
            btn.set_active(i == index)

    def set_page(self, index: int):
        self._set_active(index)

    def _toggle_theme(self):
        ThemeManager.toggle()
        app = QApplication.instance()
        if app:
            refresh_theme(app)
        self.apply_theme()

    def _update_theme_btn(self):
        c = ThemeManager.colors()
        text = "Switch to Light" if ThemeManager.is_dark() else "Switch to Dark"
        self.theme_btn.setText(text)
        self.theme_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {c['sidebar_text']};
                border: 0px;
                text-align: center;
                padding: 4px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background: {c['bg_hover']};
                color: {c['accent']};
            }}
        """)

    def apply_theme(self):
        c = ThemeManager.colors()
        self.setStyleSheet(
            f"background-color: {c['sidebar_bg']};"
            f"border: 0px; border-right: 1px solid {c['border']};"
        )
        self.app_name.setStyleSheet(
            f"font-size: 15px; font-weight: 700; color: {c['text_primary']};"
            f"background: transparent; border: 0px;"
        )
        self._update_theme_btn()
        for btn in self._buttons:
            btn.apply_theme()


# ─────────────────────────────────────────────
#  TOP BAR
# ─────────────────────────────────────────────
class TopBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self._build()
        ThemeManager.add_listener(self.apply_theme)

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(8)

        self.title_lbl = QLabel("Dashboard")
        self.title_lbl.setStyleSheet(
            "font-size: 14px; font-weight: 600;"
            "background: transparent; border: 0px;"
        )
        self.sub_lbl = QLabel("")
        self.sub_lbl.setStyleSheet(
            "font-size: 11px; background: transparent; border: 0px;"
        )

        col = QVBoxLayout()
        col.setSpacing(0)
        col.addWidget(self.title_lbl)
        col.addWidget(self.sub_lbl)

        layout.addLayout(col)
        layout.addStretch()
        self.apply_theme()

    def set_title(self, title: str, subtitle: str = ""):
        self.title_lbl.setText(title)
        self.sub_lbl.setText(subtitle)
        self.sub_lbl.setVisible(bool(subtitle))

    def apply_theme(self):
        c = ThemeManager.colors()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {c['bg_primary']};
                border: 0px;
                border-bottom: 1px solid {c['border']};
            }}
        """)
        self.title_lbl.setStyleSheet(
            f"font-size: 14px; font-weight: 600; color: {c['text_primary']};"
            f"background: transparent; border: 0px;"
        )
        self.sub_lbl.setStyleSheet(
            f"font-size: 11px; color: {c['text_muted']};"
            f"background: transparent; border: 0px;"
        )


# ─────────────────────────────────────────────
#  STATUS BAR
# ─────────────────────────────────────────────
class StatusBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(22)
        self._build()
        ThemeManager.add_listener(self.apply_theme)

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(8)

        self.status_lbl = QLabel("Ready")
        self.status_lbl.setStyleSheet(
            "font-size: 11px; background: transparent; border: 0px;"
        )
        layout.addWidget(self.status_lbl)
        layout.addStretch()

        self.right_lbl = QLabel("IPOGenie v1.0.0")
        self.right_lbl.setStyleSheet(
            "font-size: 11px; background: transparent; border: 0px;"
        )
        layout.addWidget(self.right_lbl)
        self.apply_theme()

    def set_status(self, msg: str):
        self.status_lbl.setText(msg)

    def apply_theme(self):
        c = ThemeManager.colors()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {c['bg_primary']};
                border: 0px;
                border-top: 1px solid {c['border']};
            }}
        """)
        self.status_lbl.setStyleSheet(
            f"font-size: 11px; color: {c['text_muted']};"
            f"background: transparent; border: 0px;"
        )
        self.right_lbl.setStyleSheet(
            f"font-size: 11px; color: {c['text_muted']};"
            f"background: transparent; border: 0px;"
        )


# ─────────────────────────────────────────────
#  MAIN WINDOW
# ─────────────────────────────────────────────
class MainWindow(QMainWindow):
    # Order MUST match Sidebar.NAV_ITEMS
    PAGE_TITLES = [
    ("Dashboard", "IPO Genie overview"),
    ("Registry", "Trademark registry"),
    ("Search", "Trademark and logo search"),
    ("Settings", "Configure IPO Genie"),
]

    # Page indexes
    IDX_DASHBOARD = 0
    IDX_SEARCH    = 4
    IDX_REGISTRY  = 5
    IDX_SETTINGS  = 6

    def __init__(self):
        super().__init__()
        self._current_page = 0
        self._current_project = None
        self._setup_window()
        self._build_ui()
        self._connect_signals()
        self._go_to_page(0)

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.WindowMinMaxButtonsHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setWindowTitle("IPOGenie")
        self.setMinimumSize(900, 600)
        self.resize(1100, 700)

        icon_path = assets_path() / "logo.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = (geo.width() - 1100) // 2
            y = (geo.height() - 700) // 2
            self.move(x, y)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.sidebar = Sidebar()
        root.addWidget(self.sidebar)

        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)

        self.topbar = TopBar()
        right.addWidget(self.topbar)

        # ── Build all pages ──────────────────────────
        self.stack = QStackedWidget()
        self.page_dashboard = DashboardPage()
        self.page_search    = SearchPage(self)
        self.page_registry  = RegistryPage(self)
        self.page_settings  = SettingsPage()

        self.stack.addWidget(self.page_dashboard)   # 0
        self.stack.addWidget(self.page_search)      # 1
        self.stack.addWidget(self.page_registry)    # 2
        self.stack.addWidget(self.page_settings)    # 3

        right.addWidget(self.stack, 1)

        self.statusbar_custom = StatusBar()
        right.addWidget(self.statusbar_custom)

        root.addLayout(right, 1)

    def _connect_signals(self):
        self.sidebar.nav_clicked.connect(self._go_to_page)

        
        # Settings signals
        if hasattr(self.page_settings, "theme_changed"):
            self.page_settings.theme_changed.connect(self._on_theme_changed)

        ThemeManager.add_listener(self._apply_theme)

    def _go_to_page(self, index: int):
        if index < 0 or index >= self.stack.count():
            return
        self._current_page = index
        self.stack.setCurrentIndex(index)
        self.sidebar.set_page(index)
        if index < len(self.PAGE_TITLES):
            title, subtitle = self.PAGE_TITLES[index]
            self.topbar.set_title(title, subtitle)
        self._refresh_page(index)

    def _refresh_page(self, index: int):
        page = self.stack.widget(index)
        if page is None:
            return

        # Try calling refresh, on_show, or load_project depending on page
        if index == self.IDX_DASHBOARD:
            self._safe_call(page, "refresh")
     
        else:
           self._safe_call(page, "refresh")
                
        elif index == self.IDX_SEARCH:
            self._safe_call(page, "on_show")
            self._safe_call(page, "refresh")
        elif index == self.IDX_REGISTRY:
            self._safe_call(page, "refresh")
        elif index == self.IDX_SETTINGS:
            self._safe_call(page, "refresh")

    def _safe_call(self, obj, method_name: str, *args):
        """Call obj.method_name(*args) if it exists, ignore errors."""
        try:
            if hasattr(obj, method_name):
                getattr(obj, method_name)(*args)
        except Exception as e:
            print(f"_safe_call {method_name} error: {e}")

    


   
    def _on_theme_changed(self):
        app = QApplication.instance()
        if app:
            refresh_theme(app)
        self._apply_theme()

    def _apply_theme(self):
        c = ThemeManager.colors()
        self.centralWidget().setStyleSheet(
            f"background-color: {c['bg_primary']};"
        )

    def closeEvent(self, event):
        try:
            ThemeManager.remove_listener(self._apply_theme)
        except Exception:
            pass
        event.accept()




