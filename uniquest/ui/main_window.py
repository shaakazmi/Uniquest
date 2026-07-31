import sys
from pathlib import Path
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
    QIcon, QPixmap, QFont, QColor,
    QPainter, QBrush,
)

from utils.theme import ThemeManager, build_stylesheet
from ui.dashboard import DashboardPage
from ui.projects import ProjectsPage
from ui.analysis import AnalysisPage
from ui.results import ResultsPage
from ui.settings import SettingsPage


# ─────────────────────────────────────────────
#  ASSETS PATH
# ─────────────────────────────────────────────
def assets_path() -> Path:
    base = Path(__file__).parent.parent / "assets"
    return base


# ─────────────────────────────────────────────
#  SIDEBAR NAV BUTTON
# ─────────────────────────────────────────────
class NavButton(QPushButton):
    """Single sidebar navigation button"""

    def __init__(
        self,
        icon_text: str,
        label: str,
        parent=None
    ):
        super().__init__(parent)
        self.icon_text  = icon_text
        self.label_text = label
        self._active    = False

        self.setFixedHeight(48)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build()

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)

        # Icon label
        self.icon_lbl = QLabel(self.icon_text)
        self.icon_lbl.setFixedWidth(22)
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_lbl.setStyleSheet("font-size: 16px; background: transparent;")

        # Text label
        self.text_lbl = QLabel(self.label_text)
        self.text_lbl.setStyleSheet(
            "font-size: 13px; font-weight: 500; background: transparent;"
        )

        layout.addWidget(self.icon_lbl)
        layout.addWidget(self.text_lbl)
        layout.addStretch()

        self.setLayout(layout)
        self._refresh_style()

    def set_active(self, active: bool):
        self._active = active
        self.setChecked(active)
        self._refresh_style()

    def _refresh_style(self):
        c = ThemeManager.colors()
        if self._active:
            style = f"""
                QPushButton {{
                    background-color: {c['sidebar_active_bg']};
                    border-left: 3px solid {c['sidebar_active']};
                    border-radius: 0px;
                    text-align: left;
                    padding: 0px;
                }}
            """
            self.icon_lbl.setStyleSheet(
                f"font-size: 16px; background: transparent;"
                f"color: {c['sidebar_active']};"
            )
            self.text_lbl.setStyleSheet(
                f"font-size: 13px; font-weight: 600;"
                f"background: transparent;"
                f"color: {c['sidebar_active']};"
            )
        else:
            style = f"""
                QPushButton {{
                    background-color: transparent;
                    border-left: 3px solid transparent;
                    border-radius: 0px;
                    text-align: left;
                    padding: 0px;
                }}
                QPushButton:hover {{
                    background-color: {c['bg_hover']};
                }}
            """
            self.icon_lbl.setStyleSheet(
                f"font-size: 16px; background: transparent;"
                f"color: {c['sidebar_text']};"
            )
            self.text_lbl.setStyleSheet(
                f"font-size: 13px; font-weight: 500;"
                f"background: transparent;"
                f"color: {c['sidebar_text']};"
            )
        self.setStyleSheet(style)

    def apply_theme(self):
        self._refresh_style()


# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────
class Sidebar(QFrame):
    """Left navigation sidebar"""

    nav_clicked = pyqtSignal(int)   # emits page index

    NAV_ITEMS = [
        ("📊", "Dashboard"),
        ("📁", "Projects"),
        ("🔍", "Analysis"),
        ("📋", "Results"),
        ("⚙️", "Settings"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(220)
        self.setProperty("class", "sidebar")
        self._buttons: list[NavButton] = []
        self._build()
        ThemeManager.add_listener(self.apply_theme)

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Logo area ──
        logo_frame = QFrame()
        logo_frame.setFixedHeight(72)
        logo_frame.setStyleSheet("background: transparent;")
        logo_layout = QHBoxLayout(logo_frame)
        logo_layout.setContentsMargins(16, 0, 16, 0)
        logo_layout.setSpacing(10)

        # Logo image
        logo_path = assets_path() / "logo.ico"
        self.logo_lbl = QLabel()
        if logo_path.exists():
            pix = QPixmap(str(logo_path)).scaled(
                32, 32,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.logo_lbl.setPixmap(pix)
        else:
            self.logo_lbl.setText("🔎")
            self.logo_lbl.setStyleSheet("font-size: 24px;")
        self.logo_lbl.setFixedSize(36, 36)

        # App name
        self.app_name = QLabel("Uniquest")
        self.app_name.setStyleSheet(
            "font-size: 18px; font-weight: 700;"
            "color: #4A9EFF; background: transparent;"
        )

        logo_layout.addWidget(self.logo_lbl)
        logo_layout.addWidget(self.app_name)
        logo_layout.addStretch()
        layout.addWidget(logo_frame)

        # ── Divider ──
        layout.addWidget(self._divider())

        # ── Nav buttons ──
        nav_label = QLabel("MENU")
        nav_label.setStyleSheet(
            "font-size: 10px; font-weight: 700;"
            "color: #5c6bc0; letter-spacing: 1.5px;"
            "background: transparent;"
            "padding: 12px 16px 4px 16px;"
        )
        layout.addWidget(nav_label)

        for i, (icon, label) in enumerate(self.NAV_ITEMS):
            btn = NavButton(icon, label)
            btn.clicked.connect(
                lambda checked, idx=i: self._on_nav(idx)
            )
            layout.addWidget(btn)
            self._buttons.append(btn)

        # ── Spacer ──
        layout.addSpacerItem(
            QSpacerItem(
                0, 0,
                QSizePolicy.Policy.Minimum,
                QSizePolicy.Policy.Expanding,
            )
        )

        # ── Divider ──
        layout.addWidget(self._divider())

        # ── Theme toggle ──
        self.theme_btn = QPushButton()
        self.theme_btn.setFixedHeight(44)
        self.theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_btn.clicked.connect(self._toggle_theme)
        self._update_theme_btn()
        layout.addWidget(self.theme_btn)

        # ── Version ──
        ver_lbl = QLabel("v1.0.0")
        ver_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ver_lbl.setStyleSheet(
            "font-size: 11px; color: #3d4f7c;"
            "background: transparent; padding: 6px;"
        )
        layout.addWidget(ver_lbl)

        # Activate first button
        self._set_active(0)

    def _divider(self) -> QFrame:
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(
            f"background: {ThemeManager.get('border')};"
        )
        return line

    def _on_nav(self, index: int):
        self._set_active(index)
        self.nav_clicked.emit(index)

    def _set_active(self, index: int):
        for i, btn in enumerate(self._buttons):
            btn.set_active(i == index)

    def set_page(self, index: int):
        """Programmatically set active nav item"""
        self._set_active(index)

    def _toggle_theme(self):
        ThemeManager.toggle()
        app = QApplication.instance()
        if app:
            app.setStyleSheet(build_stylesheet())
        self.apply_theme()

    def _update_theme_btn(self):
        c    = ThemeManager.colors()
        icon = "☀️ Light Mode" if ThemeManager.is_dark() \
               else "🌙 Dark Mode"
        self.theme_btn.setText(icon)
        self.theme_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {c['sidebar_text']};
                border: none;
                font-size: 12px;
                text-align: left;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                color: {c['text_primary']};
                background: {c['bg_hover']};
            }}
        """)

    def apply_theme(self):
        c = ThemeManager.colors()
        self.setStyleSheet(
            f"background-color: {c['sidebar_bg']};"
        )
        self._update_theme_btn()
        for btn in self._buttons:
            btn.apply_theme()


# ─────────────────────────────────────────────
#  TOP BAR
# ─────────────────────────────────────────────
class TopBar(QFrame):
    """Top header bar with page title and actions"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(56)
        self._build()
        ThemeManager.add_listener(self.apply_theme)

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(12)

        # Page title
        self.title_lbl = QLabel("Dashboard")
        self.title_lbl.setStyleSheet(
            "font-size: 17px; font-weight: 700;"
            "background: transparent;"
        )

        # Subtitle / breadcrumb
        self.sub_lbl = QLabel("")
        self.sub_lbl.setStyleSheet(
            "font-size: 12px; background: transparent;"
        )

        title_col = QVBoxLayout()
        title_col.setSpacing(1)
        title_col.addWidget(self.title_lbl)
        title_col.addWidget(self.sub_lbl)

        layout.addLayout(title_col)
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
                background-color: {c['bg_secondary']};
                border-bottom: 1px solid {c['border']};
            }}
        """)
        self.title_lbl.setStyleSheet(
            f"font-size: 17px; font-weight: 700;"
            f"color: {c['text_primary']}; background: transparent;"
        )
        self.sub_lbl.setStyleSheet(
            f"font-size: 12px; color: {c['text_muted']};"
            f"background: transparent;"
        )


# ─────────────────────────────────────────────
#  STATUS BAR
# ─────────────────────────────────────────────
class StatusBar(QFrame):
    """Bottom status bar"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(28)
        self._build()
        ThemeManager.add_listener(self.apply_theme)

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(16)

        self.status_lbl = QLabel("Ready")
        self.status_lbl.setStyleSheet(
            "font-size: 11px; background: transparent;"
        )

        layout.addWidget(self.status_lbl)
        layout.addStretch()

        self.right_lbl = QLabel("Uniquest v1.0.0")
        self.right_lbl.setStyleSheet(
            "font-size: 11px; background: transparent;"
        )
        layout.addWidget(self.right_lbl)
        self.apply_theme()

    def set_status(self, msg: str):
        self.status_lbl.setText(msg)

    def apply_theme(self):
        c = ThemeManager.colors()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {c['bg_secondary']};
                border-top: 1px solid {c['border']};
            }}
        """)
        self.status_lbl.setStyleSheet(
            f"font-size: 11px; color: {c['text_muted']};"
            f"background: transparent;"
        )
        self.right_lbl.setStyleSheet(
            f"font-size: 11px; color: {c['text_muted']};"
            f"background: transparent;"
        )


# ─────────────────────────────────────────────
#  MAIN WINDOW
# ─────────────────────────────────────────────
class MainWindow(QMainWindow):
    """
    Main application window.
    Layout:
        [Sidebar] | [TopBar     ]
                  | [Page Stack ]
                  | [Status Bar ]
    """

    PAGE_TITLES = [
        ("Dashboard",  "Overview of your projects and activity"),
        ("Projects",   "Manage your analysis projects"),
        ("Analysis",   "Import files and run similarity scan"),
        ("Results",    "View similar text and images found"),
        ("Settings",   "Configure app preferences"),
    ]

    def __init__(self):
        super().__init__()
        self._current_page    = 0
        self._current_project = None   # active project id
        self._setup_window()
        self._build_ui()
        self._connect_signals()
        self._go_to_page(0)

    def _setup_window(self):
        self.setWindowTitle("Uniquest")
        self.setMinimumSize(1100, 680)
        self.resize(1280, 780)

        # Window icon
        icon_path = assets_path() / "logo.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        # Center on screen
        screen = QApplication.primaryScreen()
        if screen:
            geo    = screen.availableGeometry()
            x      = (geo.width()  - 1280) // 2
            y      = (geo.height() - 780)  // 2
            self.move(x, y)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Sidebar ──
        self.sidebar = Sidebar()
        root.addWidget(self.sidebar)

        # ── Right side ──
        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)

        # Top bar
        self.topbar = TopBar()
        right.addWidget(self.topbar)

        # Page stack
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background: transparent;")

        # Instantiate pages
        self.page_dashboard = DashboardPage()
        self.page_projects  = ProjectsPage()
        self.page_analysis  = AnalysisPage()
        self.page_results   = ResultsPage()
        self.page_settings  = SettingsPage()

        self.stack.addWidget(self.page_dashboard)   # 0
        self.stack.addWidget(self.page_projects)    # 1
        self.stack.addWidget(self.page_analysis)    # 2
        self.stack.addWidget(self.page_results)     # 3
        self.stack.addWidget(self.page_settings)    # 4

        right.addWidget(self.stack, 1)

        # Status bar
        self.statusbar_custom = StatusBar()
        right.addWidget(self.statusbar_custom)

        root.addLayout(right, 1)

    def _connect_signals(self):
        # Sidebar nav
        self.sidebar.nav_clicked.connect(self._go_to_page)

        # Dashboard → open project
        self.page_dashboard.open_project.connect(
            self._open_project_from_dashboard
        )
        self.page_dashboard.go_to_projects.connect(
            lambda: self._go_to_page(1)
        )
        self.page_dashboard.go_to_analysis.connect(
            lambda: self._go_to_page(2)
        )

        # Projects → open analysis
        self.page_projects.open_analysis.connect(
            self._open_project_analysis
        )
        self.page_projects.project_created.connect(
            self._on_project_created
        )

        # Analysis → results
        self.page_analysis.analysis_complete.connect(
            self._on_analysis_complete
        )
        self.page_analysis.status_message.connect(
            self.statusbar_custom.set_status
        )

        # Settings → theme changed
        self.page_settings.theme_changed.connect(
            self._on_theme_changed
        )

        # Theme listener
        ThemeManager.add_listener(self._apply_theme)

    # ── Navigation ──
    def _go_to_page(self, index: int):
        self._current_page = index
        self.stack.setCurrentIndex(index)
        self.sidebar.set_page(index)

        title, subtitle = self.PAGE_TITLES[index]
        self.topbar.set_title(title, subtitle)

        # Refresh page data when switching
        self._refresh_page(index)

    def _refresh_page(self, index: int):
        """Refresh page data on navigation"""
        if index == 0:
            self.page_dashboard.refresh()
        elif index == 1:
            self.page_projects.refresh()
        elif index == 2:
            self.page_analysis.refresh()
        elif index == 3:
            if self._current_project:
                self.page_results.load_project(
                    self._current_project
                )
        elif index == 4:
            self.page_settings.refresh()

    # ── Project flow ──
    def _open_project_from_dashboard(self, project_id: int):
        self._current_project = project_id
        self.page_analysis.set_project(project_id)
        self._go_to_page(2)

    def _open_project_analysis(self, project_id: int):
        self._current_project = project_id
        self.page_analysis.set_project(project_id)
        self._go_to_page(2)

    def _on_project_created(self, project_id: int):
        self._current_project = project_id
        self.page_analysis.set_project(project_id)
        self._go_to_page(2)

    def _on_analysis_complete(
        self,
        project_id: int,
        text_found: int,
        img_found: int,
    ):
        self._current_project = project_id
        self.page_results.load_project(project_id)
        self.statusbar_custom.set_status(
            f"✅ Analysis complete — "
            f"{text_found} text matches, "
            f"{img_found} image matches found"
        )

        # ── Pop to front after scan ──
        self.setWindowState(
            self.windowState() & ~Qt.WindowState.WindowMinimized
        )
        self.raise_()
        self.activateWindow()
        self.showNormal()

        # Auto navigate to results
        QTimer.singleShot(
            800,
            lambda: self._go_to_page(3)
        )

    # ── Theme ──
    def _on_theme_changed(self):
        app = QApplication.instance()
        if app:
            app.setStyleSheet(build_stylesheet())
        self._apply_theme()

    def _apply_theme(self):
        c = ThemeManager.colors()
        self.centralWidget().setStyleSheet(
            f"background-color: {c['bg_primary']};"
        )

    def closeEvent(self, event):
        """Clean up on close"""
        ThemeManager.remove_listener(self._apply_theme)
        event.accept()