from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame,
    QScrollArea, QGridLayout, QGroupBox,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

from utils.theme import ThemeManager
from database.db import get_dashboard_stats      # ← CORRECT

# ─────────────────────────────────────────────
#  STAT ITEM (native-looking)
# ─────────────────────────────────────────────
class StatItem(QFrame):
    def __init__(self, label: str, value: str = "0", parent=None):
        super().__init__(parent)
        self.label_text = label
        self.value_text = value
        self.setFixedHeight(64)
        self._build()
        ThemeManager.add_listener(self.apply_theme)

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        self.value_lbl = QLabel(self.value_text)
        self.value_lbl.setStyleSheet(
            "font-size: 22px; font-weight: 700;"
            "background: transparent; border: 0px;"
        )
        self.value_lbl.setFixedWidth(60)
        self.value_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.label_lbl = QLabel(self.label_text)
        self.label_lbl.setStyleSheet(
            "font-size: 12px; background: transparent; border: 0px;"
        )
        self.label_lbl.setWordWrap(True)

        layout.addWidget(self.value_lbl)
        layout.addWidget(self.label_lbl, 1)
        self.apply_theme()

    def update_value(self, value: str):
        self.value_lbl.setText(value)

    def apply_theme(self):
        c = ThemeManager.colors()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {c['bg_input']};
                border: 1px solid {c['border']};
                border-radius: 0px;
            }}
        """)
        self.value_lbl.setStyleSheet(
            f"font-size: 22px; font-weight: 700; color: {c['accent']};"
            f"background: transparent; border: 0px;"
        )
        self.label_lbl.setStyleSheet(
            f"font-size: 12px; color: {c['text_secondary']};"
            f"background: transparent; border: 0px;"
        )


# ─────────────────────────────────────────────
#  RECENT PROJECT ROW
# ─────────────────────────────────────────────
class RecentProjectRow(QFrame):
    clicked = pyqtSignal(int)

    def __init__(self, project: dict, parent=None):
        super().__init__(parent)
        self.project = project
        self.setFixedHeight(36)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build()
        ThemeManager.add_listener(self.apply_theme)

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(10)

        self.name_lbl = QLabel(self.project.get("name", "Unnamed"))
        self.name_lbl.setStyleSheet(
            "font-size: 12px; background: transparent; border: 0px;"
        )

        file_count = self.project.get("file_count", 0)
        updated = self.project.get("updated_at", "")[:10]
        status = self.project.get("status", "idle").capitalize()

        meta = f"{file_count} files  |  {updated}  |  {status}"
        self.meta_lbl = QLabel(meta)
        self.meta_lbl.setStyleSheet(
            "font-size: 11px; background: transparent; border: 0px;"
        )

        layout.addWidget(self.name_lbl, 1)
        layout.addWidget(self.meta_lbl)
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
                background-color: {c['bg_input']};
                border: 1px solid {c['border']};
            }}
            QFrame:hover {{
                background-color: {c['bg_hover']};
                border: 1px solid {c['accent']};
            }}
        """)
        self.name_lbl.setStyleSheet(
            f"font-size: 12px; color: {c['text_primary']};"
            f"background: transparent; border: 0px;"
        )
        self.meta_lbl.setStyleSheet(
            f"font-size: 11px; color: {c['text_muted']};"
            f"background: transparent; border: 0px;"
        )


# ─────────────────────────────────────────────
#  EMPTY STATE (simple)
# ─────────────────────────────────────────────
class EmptyState(QFrame):
    action_clicked = pyqtSignal()

    def __init__(self, title="Nothing here yet", message="",
                 btn_text="", parent=None):
        super().__init__(parent)
        self._build(title, message, btn_text)
        ThemeManager.add_listener(self.apply_theme)

    def _build(self, title, message, btn_text):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(8)
        layout.setContentsMargins(30, 30, 30, 30)

        self.title_lbl = QLabel(title)
        self.title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_lbl.setStyleSheet(
            "font-size: 13px; font-weight: 600;"
            "background: transparent; border: 0px;"
        )
        layout.addWidget(self.title_lbl)

        if message:
            self.msg_lbl = QLabel(message)
            self.msg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.msg_lbl.setWordWrap(True)
            self.msg_lbl.setStyleSheet(
                "font-size: 12px; background: transparent; border: 0px;"
            )
            layout.addWidget(self.msg_lbl)

        if btn_text:
            btn = QPushButton(btn_text)
            btn.setFixedWidth(160)
            btn.setProperty("class", "accent")
            btn.clicked.connect(self.action_clicked)
            layout.addWidget(btn, 0, Qt.AlignmentFlag.AlignCenter)

        self.apply_theme()

    def apply_theme(self):
        c = ThemeManager.colors()
        self.setStyleSheet(
            f"background: transparent; color: {c['text_muted']}; border: 0px;"
        )
        self.title_lbl.setStyleSheet(
            f"font-size: 13px; font-weight: 600; color: {c['text_primary']};"
            f"background: transparent; border: 0px;"
        )
        if hasattr(self, "msg_lbl"):
            self.msg_lbl.setStyleSheet(
                f"font-size: 12px; color: {c['text_muted']};"
                f"background: transparent; border: 0px;"
            )


# ─────────────────────────────────────────────
#  LOADING LABEL
# ─────────────────────────────────────────────
class LoadingLabel(QLabel):
    FRAMES = ["|", "/", "-", "\\"]

    def __init__(self, text="Loading...", parent=None):
        super().__init__(parent)
        self._text = text
        self._frame = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            "font-size: 12px; background: transparent; border: 0px;"
        )

    def start(self):
        self._timer.start(150)
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
    open_project = pyqtSignal(int)
    go_to_projects = pyqtSignal()
    go_to_analysis = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()
        ThemeManager.add_listener(self.apply_theme)
        QTimer.singleShot(100, self.refresh)

    def _build(self):
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
        self.main_layout.setContentsMargins(16, 12, 16, 12)
        self.main_layout.setSpacing(12)

        scroll.setWidget(content)
        outer.addWidget(scroll)

        self.loading_lbl = LoadingLabel("Loading...")
        self.loading_lbl.setFixedHeight(30)
        self.loading_lbl.setVisible(False)
        self.main_layout.addWidget(self.loading_lbl)

        # Welcome message
        self.welcome_lbl = QLabel("Welcome to Uniquest")
        self.welcome_lbl.setStyleSheet(
            "font-size: 16px; font-weight: 700;"
            "background: transparent; border: 0px;"
        )
        self.main_layout.addWidget(self.welcome_lbl)

        self.sub_lbl = QLabel(
            "Find similar text and images across your files."
        )
        self.sub_lbl.setStyleSheet(
            "font-size: 12px; background: transparent; border: 0px;"
        )
        self.main_layout.addWidget(self.sub_lbl)

        # ── Statistics group ──
        stats_group = QGroupBox("Statistics")
        stats_layout = QGridLayout(stats_group)
        stats_layout.setSpacing(6)
        stats_layout.setContentsMargins(10, 14, 10, 10)

        self.card_projects = StatItem("Total projects")
        self.card_files    = StatItem("Total files")
        self.card_text     = StatItem("Text matches")
        self.card_images   = StatItem("Image matches")
        self.card_runs     = StatItem("Scans completed")
        self.card_total    = StatItem("Total matches")

        stats_layout.addWidget(self.card_projects, 0, 0)
        stats_layout.addWidget(self.card_files,    0, 1)
        stats_layout.addWidget(self.card_text,     0, 2)
        stats_layout.addWidget(self.card_images,   1, 0)
        stats_layout.addWidget(self.card_runs,     1, 1)
        stats_layout.addWidget(self.card_total,    1, 2)

        self.main_layout.addWidget(stats_group)

        # ── Quick actions group ──
        actions_group = QGroupBox("Quick Actions")
        actions_layout = QHBoxLayout(actions_group)
        actions_layout.setSpacing(8)
        actions_layout.setContentsMargins(10, 14, 10, 10)

        self.btn_new_project = QPushButton("New Project")
        self.btn_new_project.setProperty("class", "accent")
        self.btn_new_project.setMinimumHeight(32)
        self.btn_new_project.clicked.connect(self.go_to_projects)

        self.btn_run_analysis = QPushButton("Run Analysis")
        self.btn_run_analysis.setMinimumHeight(32)
        self.btn_run_analysis.clicked.connect(self.go_to_analysis)

        self.btn_view_results = QPushButton("View Results")
        self.btn_view_results.setMinimumHeight(32)
        self.btn_view_results.clicked.connect(self.go_to_analysis)

        actions_layout.addWidget(self.btn_new_project)
        actions_layout.addWidget(self.btn_run_analysis)
        actions_layout.addWidget(self.btn_view_results)
        actions_layout.addStretch()

        self.main_layout.addWidget(actions_group)

        # ── Recent projects group ──
        recent_group = QGroupBox("Recent Projects")
        recent_layout = QVBoxLayout(recent_group)
        recent_layout.setSpacing(4)
        recent_layout.setContentsMargins(10, 14, 10, 10)

        self.recent_container = QVBoxLayout()
        self.recent_container.setSpacing(4)
        recent_layout.addLayout(self.recent_container)

        # Buttons row
        rec_btn_row = QHBoxLayout()
        rec_btn_row.addStretch()
        see_all_btn = QPushButton("See All Projects")
        see_all_btn.setMinimumWidth(140)
        see_all_btn.clicked.connect(self.go_to_projects)
        rec_btn_row.addWidget(see_all_btn)
        recent_layout.addLayout(rec_btn_row)

        self.empty_state = EmptyState(
            title="No projects yet",
            message="Create your first project to get started.",
            btn_text="Create Project",
        )
        self.empty_state.action_clicked.connect(self.go_to_projects)
        self.empty_state.setVisible(False)
        recent_layout.addWidget(self.empty_state)

        self.main_layout.addWidget(recent_group)

        self.main_layout.addStretch()
        self.apply_theme()

    def refresh(self):
        self._show_loading(True)
        QTimer.singleShot(80, self._load_data)

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
        self.card_projects.update_value(str(stats.get("total_projects", 0)))
        self.card_files.update_value(str(stats.get("total_files", 0)))
        self.card_text.update_value(str(stats.get("total_text_sim", 0)))
        self.card_images.update_value(str(stats.get("total_img_sim", 0)))
        self.card_runs.update_value(str(stats.get("total_runs", 0)))
        self.card_total.update_value(str(stats.get("grand_total_sim", 0)))

    def _update_recent(self, projects: list):
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
        self.welcome_lbl.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {c['text_primary']};"
            f"background: transparent; border: 0px;"
        )
        self.sub_lbl.setStyleSheet(
            f"font-size: 12px; color: {c['text_muted']};"
            f"background: transparent; border: 0px;"
        )