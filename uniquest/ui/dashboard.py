from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame,
    QScrollArea, QGridLayout, QSizePolicy,
    QSpacerItem,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor

from utils.theme import ThemeManager
from core.processor import get_dashboard_stats


# ─────────────────────────────────────────────
#  STAT CARD
# ─────────────────────────────────────────────
class StatCard(QFrame):
    """Single stat card widget"""

    def __init__(
        self,
        icon: str,
        title: str,
        value: str,
        subtitle: str = "",
        accent: str = "#4A9EFF",
        parent=None,
    ):
        super().__init__(parent)
        self.icon_txt  = icon
        self.title_txt = title
        self.value_txt = value
        self.sub_txt   = subtitle
        self.accent    = accent
        self.setProperty("class", "card")
        self.setMinimumWidth(180)
        self.setFixedHeight(120)
        self._build()
        ThemeManager.add_listener(self.apply_theme)

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(6)

        # Top row: icon + title
        top = QHBoxLayout()
        top.setSpacing(8)

        self.icon_lbl = QLabel(self.icon_txt)
        self.icon_lbl.setStyleSheet(
            f"font-size: 20px; background: transparent;"
        )

        self.title_lbl = QLabel(self.title_txt)
        self.title_lbl.setStyleSheet(
            "font-size: 12px; font-weight: 600;"
            "background: transparent;"
        )
        top.addWidget(self.icon_lbl)
        top.addWidget(self.title_lbl)
        top.addStretch()
        layout.addLayout(top)

        # Value
        self.value_lbl = QLabel(self.value_txt)
        self.value_lbl.setStyleSheet(
            f"font-size: 28px; font-weight: 700;"
            f"color: {self.accent}; background: transparent;"
        )
        layout.addWidget(self.value_lbl)

        # Subtitle
        self.sub_lbl = QLabel(self.sub_txt)
        self.sub_lbl.setStyleSheet(
            "font-size: 11px; background: transparent;"
        )
        self.sub_lbl.setVisible(bool(self.sub_txt))
        layout.addWidget(self.sub_lbl)

        self.apply_theme()

    def update_value(self, value: str, subtitle: str = ""):
        self.value_lbl.setText(value)
        if subtitle:
            self.sub_lbl.setText(subtitle)
            self.sub_lbl.setVisible(True)

    def apply_theme(self):
        c = ThemeManager.colors()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {c['bg_card']};
                border: 1px solid {c['border']};
                border-radius: 10px;
            }}
        """)
        self.title_lbl.setStyleSheet(
            f"font-size: 12px; font-weight: 600;"
            f"color: {c['text_secondary']}; background: transparent;"
        )
        self.sub_lbl.setStyleSheet(
            f"font-size: 11px; color: {c['text_muted']};"
            f"background: transparent;"
        )


# ─────────────────────────────────────────────
#  RECENT PROJECT ROW
# ─────────────────────────────────────────────
class RecentProjectRow(QFrame):
    """Single row in recent projects list"""

    clicked = pyqtSignal(int)

    def __init__(self, project: dict, parent=None):
        super().__init__(parent)
        self.project = project
        self.setProperty("class", "card")
        self.setFixedHeight(64)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build()
        ThemeManager.add_listener(self.apply_theme)

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(14)

        # Status dot
        status = self.project.get("status", "idle")
        dot_color = {
            "idle":     "#5c6bc0",
            "scanning": "#ff9800",
            "done":     "#4caf50",
            "error":    "#f44336",
        }.get(status, "#5c6bc0")

        dot = QLabel("●")
        dot.setStyleSheet(
            f"font-size: 10px; color: {dot_color};"
            f"background: transparent;"
        )
        dot.setFixedWidth(16)
        layout.addWidget(dot)

        # Name + meta
        info = QVBoxLayout()
        info.setSpacing(2)

        name = self.project.get("name", "Unnamed")
        self.name_lbl = QLabel(name)
        self.name_lbl.setStyleSheet(
            "font-size: 13px; font-weight: 600;"
            "background: transparent;"
        )

        file_count = self.project.get("file_count", 0)
        updated    = self.project.get("updated_at", "")[:10]
        meta_text  = f"{file_count} files  •  {updated}"
        self.meta_lbl = QLabel(meta_text)
        self.meta_lbl.setStyleSheet(
            "font-size: 11px; background: transparent;"
        )

        info.addWidget(self.name_lbl)
        info.addWidget(self.meta_lbl)
        layout.addLayout(info, 1)

        # Status badge
        status_text = {
            "idle":     "Idle",
            "scanning": "Scanning",
            "done":     "Done",
            "error":    "Error",
        }.get(status, status.capitalize())

        badge = QLabel(status_text)
        badge.setFixedWidth(70)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(f"""
            QLabel {{
                background-color: {dot_color}22;
                color: {dot_color};
                border: 1px solid {dot_color}44;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 600;
                padding: 2px 8px;
            }}
        """)
        layout.addWidget(badge)

        # Open arrow
        arrow = QLabel("›")
        arrow.setStyleSheet(
            "font-size: 18px; color: #5c6bc0; background: transparent;"
        )
        layout.addWidget(arrow)

        self.apply_theme()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pid = self.project.get("id")
            if pid:
                self.clicked.emit(pid)
        super().mousePressEvent(event)

    def apply_theme(self):
        c = ThemeManager.colors()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {c['bg_card']};
                border: 1px solid {c['border']};
                border-radius: 8px;
            }}
            QFrame:hover {{
                background-color: {c['bg_hover']};
                border-color: {c['accent']};
            }}
        """)
        self.name_lbl.setStyleSheet(
            f"font-size: 13px; font-weight: 600;"
            f"color: {c['text_primary']}; background: transparent;"
        )
        self.meta_lbl.setStyleSheet(
            f"font-size: 11px; color: {c['text_muted']};"
            f"background: transparent;"
        )


# ─────────────────────────────────────────────
#  EMPTY STATE
# ─────────────────────────────────────────────
class EmptyState(QFrame):
    """Empty state widget shown when no data exists"""

    action_clicked = pyqtSignal()

    def __init__(
        self,
        icon: str = "📭",
        title: str = "Nothing here yet",
        message: str = "",
        btn_text: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self._build(icon, title, message, btn_text)
        ThemeManager.add_listener(self.apply_theme)

    def _build(self, icon, title, message, btn_text):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)
        layout.setContentsMargins(40, 40, 40, 40)

        icon_lbl = QLabel(icon)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(
            "font-size: 48px; background: transparent;"
        )

        title_lbl = QLabel(title)
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_lbl.setStyleSheet(
            "font-size: 16px; font-weight: 700;"
            "background: transparent;"
        )

        layout.addWidget(icon_lbl)
        layout.addWidget(title_lbl)

        if message:
            msg_lbl = QLabel(message)
            msg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            msg_lbl.setWordWrap(True)
            msg_lbl.setStyleSheet(
                "font-size: 13px; background: transparent;"
            )
            layout.addWidget(msg_lbl)
            self.msg_lbl = msg_lbl

        if btn_text:
            btn = QPushButton(btn_text)
            btn.setFixedWidth(180)
            btn.clicked.connect(self.action_clicked)
            layout.addWidget(
                btn, 0, Qt.AlignmentFlag.AlignCenter
            )

        self.apply_theme()

    def apply_theme(self):
        c = ThemeManager.colors()
        self.setStyleSheet(
            f"background: transparent; color: {c['text_muted']};"
        )


# ─────────────────────────────────────────────
#  QUICK ACTION BUTTON
# ─────────────────────────────────────────────
class QuickActionBtn(QFrame):
    """Large quick action card button"""

    clicked = pyqtSignal()

    def __init__(
        self,
        icon: str,
        title: str,
        desc: str,
        parent=None,
    ):
        super().__init__(parent)
        self.setProperty("class", "card")
        self.setFixedHeight(90)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build(icon, title, desc)
        ThemeManager.add_listener(self.apply_theme)

    def _build(self, icon, title, desc):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 0, 18, 0)
        layout.setSpacing(14)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(
            "font-size: 28px; background: transparent;"
        )
        icon_lbl.setFixedWidth(40)

        text_col = QVBoxLayout()
        text_col.setSpacing(3)

        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet(
            "font-size: 14px; font-weight: 700;"
            "background: transparent;"
        )

        self.desc_lbl = QLabel(desc)
        self.desc_lbl.setStyleSheet(
            "font-size: 12px; background: transparent;"
        )
        self.desc_lbl.setWordWrap(True)

        text_col.addWidget(self.title_lbl)
        text_col.addWidget(self.desc_lbl)

        layout.addWidget(icon_lbl)
        layout.addLayout(text_col, 1)

        arrow = QLabel("›")
        arrow.setStyleSheet(
            "font-size: 22px; background: transparent;"
        )
        layout.addWidget(arrow)

        self.apply_theme()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def apply_theme(self):
        c = ThemeManager.colors()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {c['bg_card']};
                border: 1px solid {c['border']};
                border-radius: 10px;
            }}
            QFrame:hover {{
                background-color: {c['bg_hover']};
                border-color: {c['accent']};
            }}
        """)
        self.title_lbl.setStyleSheet(
            f"font-size: 14px; font-weight: 700;"
            f"color: {c['text_primary']}; background: transparent;"
        )
        self.desc_lbl.setStyleSheet(
            f"font-size: 12px; color: {c['text_muted']};"
            f"background: transparent;"
        )


# ─────────────────────────────────────────────
#  LOADING SPINNER LABEL
# ─────────────────────────────────────────────
class LoadingLabel(QLabel):
    """Animated loading indicator"""

    FRAMES = ["⠋", "⠙", "⠸", "⠴", "⠦", "⠇"]

    def __init__(self, text: str = "Loading...", parent=None):
        super().__init__(parent)
        self._text    = text
        self._frame   = 0
        self._timer   = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            "font-size: 14px; color: #4A9EFF;"
            "background: transparent;"
        )

    def start(self):
        self._timer.start(120)
        self._tick()

    def stop(self):
        self._timer.stop()
        self.setText("")

    def _tick(self):
        frame = self.FRAMES[self._frame % len(self.FRAMES)]
        self.setText(f"{frame}  {self._text}")
        self._frame += 1


# ─────────────────────────────────────────────
#  DASHBOARD PAGE
# ─────────────────────────────────────────────
class DashboardPage(QWidget):
    """
    Page 0 — Dashboard
    Shows: stat cards, quick actions, recent projects
    """

    # Signals to main window
    open_project  = pyqtSignal(int)
    go_to_projects = pyqtSignal()
    go_to_analysis = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._loading = False
        self._build()
        ThemeManager.add_listener(self.apply_theme)
        # Load data after UI is ready
        QTimer.singleShot(100, self.refresh)

    def _build(self):
        # ── Outer scroll area ──
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        content = QWidget()
        self.main_layout = QVBoxLayout(content)
        self.main_layout.setContentsMargins(28, 24, 28, 28)
        self.main_layout.setSpacing(24)

        scroll.setWidget(content)
        outer.addWidget(scroll)

        # ── Loading indicator ──
        self.loading_lbl = LoadingLabel("Loading dashboard...")
        self.loading_lbl.setFixedHeight(60)
        self.loading_lbl.setVisible(False)
        self.main_layout.addWidget(self.loading_lbl)

        # ── Welcome banner ──
        self._build_welcome()

        # ── Stat cards ──
        self._build_stat_cards()

        # ── Quick actions ──
        self._build_quick_actions()

        # ── Recent projects ──
        self._build_recent_projects()

        self.main_layout.addStretch()

    def _build_welcome(self):
        frame = QFrame()
        frame.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)

        col = QVBoxLayout()
        col.setSpacing(4)

        self.welcome_lbl = QLabel("Welcome to Uniquest 👋")
        self.welcome_lbl.setStyleSheet(
            "font-size: 22px; font-weight: 700;"
            "background: transparent;"
        )

        self.sub_lbl = QLabel(
            "Find similar text and images across hundreds of files."
        )
        self.sub_lbl.setStyleSheet(
            "font-size: 13px; background: transparent;"
        )

        col.addWidget(self.welcome_lbl)
        col.addWidget(self.sub_lbl)
        layout.addLayout(col)
        layout.addStretch()

        self.main_layout.addWidget(frame)

    def _build_stat_cards(self):
        # Section label
        sec = QLabel("OVERVIEW")
        sec.setStyleSheet(
            "font-size: 10px; font-weight: 700;"
            "letter-spacing: 1.5px; background: transparent;"
        )
        self.main_layout.addWidget(sec)

        grid = QGridLayout()
        grid.setSpacing(14)

        self.card_projects = StatCard(
            "📁", "Total Projects", "0",
            "Projects created",
            accent="#4A9EFF",
        )
        self.card_files = StatCard(
            "📄", "Total Files", "0",
            "Files imported",
            accent="#9c27b0",
        )
        self.card_text = StatCard(
            "📝", "Text Matches", "0",
            "Similar text found",
            accent="#ff9800",
        )
        self.card_images = StatCard(
            "🖼️", "Image Matches", "0",
            "Similar images found",
            accent="#f44336",
        )
        self.card_runs = StatCard(
            "🔍", "Scans Run", "0",
            "Analysis runs done",
            accent="#4caf50",
        )
        self.card_total = StatCard(
            "⚡", "Total Matches", "0",
            "Text + Image combined",
            accent="#e91e63",
        )

        grid.addWidget(self.card_projects, 0, 0)
        grid.addWidget(self.card_files,    0, 1)
        grid.addWidget(self.card_text,     0, 2)
        grid.addWidget(self.card_images,   1, 0)
        grid.addWidget(self.card_runs,     1, 1)
        grid.addWidget(self.card_total,    1, 2)

        self.main_layout.addLayout(grid)

    def _build_quick_actions(self):
        sec = QLabel("QUICK ACTIONS")
        sec.setStyleSheet(
            "font-size: 10px; font-weight: 700;"
            "letter-spacing: 1.5px; background: transparent;"
        )
        self.main_layout.addWidget(sec)

        row = QHBoxLayout()
        row.setSpacing(14)

        self.btn_new_project = QuickActionBtn(
            "➕",
            "New Project",
            "Create a new analysis project and import files",
        )
        self.btn_run_analysis = QuickActionBtn(
            "🔍",
            "Run Analysis",
            "Scan imported files for similar text and images",
        )
        self.btn_view_results = QuickActionBtn(
            "📋",
            "View Results",
            "Browse similarity matches found in your projects",
        )

        self.btn_new_project.clicked.connect(
            self.go_to_projects
        )
        self.btn_run_analysis.clicked.connect(
            self.go_to_analysis
        )
        self.btn_view_results.clicked.connect(
            self.go_to_analysis
        )

        row.addWidget(self.btn_new_project)
        row.addWidget(self.btn_run_analysis)
        row.addWidget(self.btn_view_results)
        self.main_layout.addLayout(row)

    def _build_recent_projects(self):
        # Header row
        header = QHBoxLayout()

        sec = QLabel("RECENT PROJECTS")
        sec.setStyleSheet(
            "font-size: 10px; font-weight: 700;"
            "letter-spacing: 1.5px; background: transparent;"
        )

        see_all = QPushButton("See All →")
        see_all.setProperty("class", "ghost")
        see_all.setFixedHeight(28)
        see_all.clicked.connect(self.go_to_projects)

        header.addWidget(sec)
        header.addStretch()
        header.addWidget(see_all)
        self.main_layout.addLayout(header)

        # Container for project rows
        self.recent_container = QVBoxLayout()
        self.recent_container.setSpacing(8)
        self.main_layout.addLayout(self.recent_container)

        # Empty state (shown when no projects)
        self.empty_state = EmptyState(
            icon    = "📭",
            title   = "No projects yet",
            message = "Create your first project to get started.",
            btn_text = "➕ Create Project",
        )
        self.empty_state.action_clicked.connect(
            self.go_to_projects
        )
        self.empty_state.setVisible(False)
        self.main_layout.addWidget(self.empty_state)

    # ─────────────────────────────────────────
    #  DATA LOADING
    # ─────────────────────────────────────────
    def refresh(self):
        """Reload dashboard data"""
        self._show_loading(True)
        QTimer.singleShot(100, self._load_data)

    def _load_data(self):
        try:
            stats = get_dashboard_stats()
            self._update_stats(stats)
            self._update_recent(stats.get("recent_projects", []))
        except Exception as e:
            print(f"Dashboard load error: {e}")
        finally:
            self._show_loading(False)

    def _update_stats(self, stats: dict):
        self.card_projects.update_value(
            str(stats.get("total_projects", 0))
        )
        self.card_files.update_value(
            str(stats.get("total_files", 0))
        )
        self.card_text.update_value(
            str(stats.get("total_text_sim", 0))
        )
        self.card_images.update_value(
            str(stats.get("total_img_sim", 0))
        )
        self.card_runs.update_value(
            str(stats.get("total_runs", 0))
        )
        self.card_total.update_value(
            str(stats.get("grand_total_sim", 0))
        )

    def _update_recent(self, projects: list):
        # Clear old rows
        while self.recent_container.count():
            item = self.recent_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not projects:
            self.empty_state.setVisible(True)
            return

        self.empty_state.setVisible(False)
        for proj in projects:
            row = RecentProjectRow(proj)
            row.clicked.connect(self.open_project)
            self.recent_container.addWidget(row)

    def _show_loading(self, show: bool):
        self._loading = show
        self.loading_lbl.setVisible(show)
        if show:
            self.loading_lbl.start()
        else:
            self.loading_lbl.stop()

    def apply_theme(self):
        c = ThemeManager.colors()
        self.setStyleSheet(
            f"background-color: {c['bg_primary']};"
        )
        # Update section labels color
        for lbl in self.findChildren(QLabel):
            txt = lbl.text()
            if txt in (
                "OVERVIEW", "QUICK ACTIONS", "RECENT PROJECTS"
            ):
                lbl.setStyleSheet(
                    f"font-size: 10px; font-weight: 700;"
                    f"letter-spacing: 1.5px;"
                    f"color: {c['text_muted']};"
                    f"background: transparent;"
                )
        self.welcome_lbl.setStyleSheet(
            f"font-size: 22px; font-weight: 700;"
            f"color: {c['text_primary']}; background: transparent;"
        )
        self.sub_lbl.setStyleSheet(
            f"font-size: 13px; color: {c['text_secondary']};"
            f"background: transparent;"
        )