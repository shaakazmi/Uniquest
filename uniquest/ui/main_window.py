from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QStatusBar, QStackedWidget,
    QSizePolicy, QFrame
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont

from utils.theme import apply_theme, get_colors
from database.db import get_setting, set_setting


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Uniquest")
        self.setMinimumSize(1024, 680)
        self.resize(1280, 780)
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint |
            Qt.WindowType.WindowCloseButtonHint
        )

        self._theme    = get_setting("theme", "light")
        self._pages    = {}
        self._nav_btns = {}

        self._build_ui()
        self._navigate("dashboard")

    # ─────────────────────────────────────────────────────────
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # sidebar
        self._sidebar = self._make_sidebar()
        root.addWidget(self._sidebar)

        # right side
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self._topbar = self._make_topbar()
        right_layout.addWidget(self._topbar)

        self._stack = QStackedWidget()
        right_layout.addWidget(self._stack, 1)

        root.addWidget(right, 1)

        # status bar
        self._status = QStatusBar()
        self._status.showMessage("Ready")
        right_status = QLabel("Uniquest v1.0.0")
        self._status.addPermanentWidget(right_status)
        self.setStatusBar(self._status)

        # pages
        self._load_pages()

    # ─────────────────────────────────────────────────────────
    def _make_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(180)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # app title
        title = QLabel("Uniquest")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setContentsMargins(0, 16, 0, 16)
        layout.addWidget(title)

        # separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        # nav buttons
        nav_items = [
            ("dashboard", "Dashboard"),
            ("projects",  "Projects"),
            ("analysis",  "Analysis"),
            ("results",   "Results"),
            ("settings",  "Settings"),
        ]
        for key, label in nav_items:
            btn = QPushButton(label)
            btn.setObjectName("nav_btn")
            btn.setFixedHeight(40)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, k=key: self._navigate(k))
            self._nav_btns[key] = btn
            layout.addWidget(btn)

        layout.addStretch()

        # theme toggle
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep2)

        self._theme_btn = QPushButton(
            "Dark Mode" if self._theme == "light" else "Light Mode"
        )
        self._theme_btn.setObjectName("nav_btn")
        self._theme_btn.setFixedHeight(36)
        self._theme_btn.clicked.connect(self._toggle_theme)
        layout.addWidget(self._theme_btn)

        ver = QLabel("v1.0.0")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ver.setContentsMargins(0, 4, 0, 8)
        layout.addWidget(ver)

        return sidebar

    # ─────────────────────────────────────────────────────────
    def _make_topbar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(52)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 16, 0)

        self._page_title    = QLabel("Dashboard")
        self._page_subtitle = QLabel("Overview of your projects and recent activity")

        self._page_title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self._page_subtitle.setStyleSheet("color: #666666; font-size: 9pt;")

        title_col = QVBoxLayout()
        title_col.setSpacing(0)
        title_col.addWidget(self._page_title)
        title_col.addWidget(self._page_subtitle)

        layout.addLayout(title_col)
        layout.addStretch()

        return bar

    # ─────────────────────────────────────────────────────────
    def _load_pages(self):
        from ui.dashboard import DashboardPage
        from ui.projects  import ProjectsPage
        from ui.analysis  import AnalysisPage
        from ui.results   import ResultsPage
        from ui.settings  import SettingsPage

        pages = [
            ("dashboard", DashboardPage(self)),
            ("projects",  ProjectsPage(self)),
            ("analysis",  AnalysisPage(self)),
            ("results",   ResultsPage(self)),
            ("settings",  SettingsPage(self)),
        ]
        for key, page in pages:
            self._pages[key] = page
            self._stack.addWidget(page)

    # ─────────────────────────────────────────────────────────
    def _navigate(self, key: str):
        titles = {
            "dashboard": ("Dashboard",  "Overview of your projects and recent activity"),
            "projects":  ("Projects",   "Create and manage your projects"),
            "analysis":  ("Analysis",   "Import files and find duplicates"),
            "results":   ("Results",    "Review similarity matches"),
            "settings":  ("Settings",   "Configure application preferences"),
        }

        # update active button style
        for k, btn in self._nav_btns.items():
            btn.setProperty("active", k == key)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        # switch page
        if key in self._pages:
            self._stack.setCurrentWidget(self._pages[key])
            if hasattr(self._pages[key], "on_show"):
                self._pages[key].on_show()

        # update topbar
        if key in titles:
            t, s = titles[key]
            self._page_title.setText(t)
            self._page_subtitle.setText(s)

    # ─────────────────────────────────────────────────────────
    def _toggle_theme(self):
        self._theme = "dark" if self._theme == "light" else "light"
        set_setting("theme", self._theme)
        apply_theme(self._app_ref(), self._theme)
        self._theme_btn.setText(
            "Dark Mode" if self._theme == "light" else "Light Mode"
        )

    def _app_ref(self):
        from PyQt6.QtWidgets import QApplication
        return QApplication.instance()

    # ─────────────────────────────────────────────────────────
    def navigate_to(self, key: str):
        """Public method called from other pages."""
        self._navigate(key)

    def set_status(self, msg: str):
        self._status.showMessage(msg)