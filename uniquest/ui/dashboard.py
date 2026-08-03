from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGridLayout, QGroupBox, QFrame,
    QScrollArea
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from database.db import get_dashboard_stats


class DashboardPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self._build_ui()

    def on_show(self):
        self._refresh()

    def _build_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        self._layout = QVBoxLayout(content)
        self._layout.setContentsMargins(20, 20, 20, 20)
        self._layout.setSpacing(16)

        # stats row
        self._stats_group = QGroupBox("Overview")
        self._stats_layout = QGridLayout(self._stats_group)
        self._layout.addWidget(self._stats_group)

        # quick actions
        qa_group  = QGroupBox("Quick Actions")
        qa_layout = QHBoxLayout(qa_group)

        btn_new    = QPushButton("New Project")
        btn_analyze = QPushButton("Start Analysis")
        btn_results = QPushButton("View Results")

        btn_new.setObjectName("primary_btn")
        btn_new.setFixedHeight(32)
        btn_analyze.setFixedHeight(32)
        btn_results.setFixedHeight(32)

        btn_new.clicked.connect(lambda: self.main_window.navigate_to("projects"))
        btn_analyze.clicked.connect(lambda: self.main_window.navigate_to("analysis"))
        btn_results.clicked.connect(lambda: self.main_window.navigate_to("results"))

        qa_layout.addWidget(btn_new)
        qa_layout.addWidget(btn_analyze)
        qa_layout.addWidget(btn_results)
        qa_layout.addStretch()
        self._layout.addWidget(qa_group)

        # recent projects
        self._recent_group = QGroupBox("Recent Projects")
        self._recent_layout = QVBoxLayout(self._recent_group)
        self._layout.addWidget(self._recent_group)

        self._layout.addStretch()

        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _refresh(self):
        stats = get_dashboard_stats()

        # clear stats grid
        while self._stats_layout.count():
            item = self._stats_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        stat_items = [
            ("Projects",      stats["total_projects"]),
            ("Files",         stats["total_files"]),
            ("Text Matches",  stats["total_text_matches"]),
            ("Image Matches", stats["total_image_matches"]),
        ]
        for col, (label, value) in enumerate(stat_items):
            card = self._make_stat_card(label, str(value))
            self._stats_layout.addWidget(card, 0, col)

        # recent projects
        while self._recent_layout.count():
            item = self._recent_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        recent = stats.get("recent_projects", [])
        if not recent:
            self._recent_layout.addWidget(QLabel("No projects yet."))
        else:
            for proj in recent:
                row = self._make_project_row(proj)
                self._recent_layout.addWidget(row)

    def _make_stat_card(self, label: str, value: str) -> QWidget:
        card = QGroupBox()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 8)

        val_lbl = QLabel(value)
        val_lbl.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl = QLabel(label)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(val_lbl)
        layout.addWidget(lbl)
        return card

    def _make_project_row(self, proj: dict) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(4, 4, 4, 4)

        name = QLabel(proj["name"])
        name.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))

        date = QLabel(proj["updated_at"][:10] if proj["updated_at"] else "")
        date.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        status = QLabel(proj["status"].capitalize())
        status.setFixedWidth(80)
        status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(name, 1)
        layout.addWidget(date)
        layout.addWidget(status)

        return row