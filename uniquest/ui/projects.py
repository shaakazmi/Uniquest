from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame,
    QScrollArea, QLineEdit, QTextEdit,
    QDialog, QDialogButtonBox, QComboBox,
    QMessageBox, QSizePolicy, QSpacerItem,
    QSlider, QGridLayout,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from utils.theme import ThemeManager
from core.processor import (
    get_all_projects,
    create_project,
    update_project,
    delete_project,
)
from ui.dashboard import EmptyState, LoadingLabel


# ─────────────────────────────────────────────
#  PROJECT DIALOG  (Create / Edit)
# ─────────────────────────────────────────────
class ProjectDialog(QDialog):
    """
    Modal dialog for creating or editing a project.
    """

    def __init__(self, parent=None, project: dict = None):
        super().__init__(parent)
        self.project    = project          # None = create mode
        self.is_edit    = project is not None
        self.setWindowTitle(
            "Edit Project" if self.is_edit else "New Project"
        )
        self.setFixedWidth(480)
        self.setModal(True)
        self._build()
        self._apply_theme()
        ThemeManager.add_listener(self._apply_theme)

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        # ── Title ──
        title = QLabel(
            "✏️ Edit Project" if self.is_edit
            else "➕ Create New Project"
        )
        title.setStyleSheet(
            "font-size: 16px; font-weight: 700;"
            "background: transparent;"
        )
        layout.addWidget(title)

        # ── Name ──
        layout.addWidget(self._field_label("Project Name *"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(
            "e.g. Q1 Report Duplicates"
        )
        self.name_input.setFixedHeight(38)
        if self.is_edit:
            self.name_input.setText(
                self.project.get("name", "")
            )
        layout.addWidget(self.name_input)

        # ── Description ──
        layout.addWidget(self._field_label("Description"))
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText(
            "Optional description of this project..."
        )
        self.desc_input.setFixedHeight(80)
        if self.is_edit:
            self.desc_input.setPlainText(
                self.project.get("description", "")
            )
        layout.addWidget(self.desc_input)

        # ── Storage mode ──
        layout.addWidget(self._field_label("File Storage Mode"))
        self.storage_combo = QComboBox()
        self.storage_combo.setFixedHeight(38)
        self.storage_combo.addItem(
            "📌  Reference original files (saves disk space)",
            "reference",
        )
        self.storage_combo.addItem(
            "📋  Copy files into app folder (portable)",
            "copy",
        )
        if self.is_edit:
            mode = self.project.get("storage_mode", "reference")
            idx  = 0 if mode == "reference" else 1
            self.storage_combo.setCurrentIndex(idx)
        layout.addWidget(self.storage_combo)

        # Storage hint
        self.storage_hint = QLabel(
            "💡 Reference: files stay in place. "
            "Copy: app keeps its own copy."
        )
        self.storage_hint.setWordWrap(True)
        self.storage_hint.setStyleSheet(
            "font-size: 11px; background: transparent;"
        )
        layout.addWidget(self.storage_hint)

        # ── Similarity threshold ──
        layout.addWidget(
            self._field_label("Text Similarity Threshold")
        )

        slider_row = QHBoxLayout()
        slider_row.setSpacing(12)

        self.threshold_slider = QSlider(
            Qt.Orientation.Horizontal
        )
        self.threshold_slider.setRange(50, 100)
        self.threshold_slider.setTickInterval(5)
        self.threshold_slider.setPageStep(5)

        default_val = int(
            self.project.get("similarity_threshold", 0.70) * 100
            if self.is_edit else 70
        )
        self.threshold_slider.setValue(default_val)

        self.threshold_lbl = QLabel(f"{default_val}%")
        self.threshold_lbl.setFixedWidth(40)
        self.threshold_lbl.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.threshold_lbl.setStyleSheet(
            "font-size: 13px; font-weight: 700;"
            "color: #4A9EFF; background: transparent;"
        )

        self.threshold_slider.valueChanged.connect(
            lambda v: self.threshold_lbl.setText(f"{v}%")
        )

        slider_row.addWidget(QLabel("50%"))
        slider_row.addWidget(self.threshold_slider, 1)
        slider_row.addWidget(QLabel("100%"))
        slider_row.addWidget(self.threshold_lbl)
        layout.addLayout(slider_row)

        hint = QLabel(
            "💡 Lower = catch more similarities. "
            "Higher = only near-identical matches."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(
            "font-size: 11px; background: transparent;"
        )
        layout.addWidget(hint)

        # ── Buttons ──
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setProperty("class", "ghost")
        cancel_btn.setFixedHeight(38)
        cancel_btn.clicked.connect(self.reject)

        self.save_btn = QPushButton(
            "💾 Save Changes" if self.is_edit
            else "➕ Create Project"
        )
        self.save_btn.setFixedHeight(38)
        self.save_btn.clicked.connect(self._on_save)

        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(self.save_btn)
        layout.addLayout(btn_row)

    def _field_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            "font-size: 12px; font-weight: 600;"
            "background: transparent;"
        )
        return lbl

    def _on_save(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(
                self, "Validation",
                "Project name is required."
            )
            self.name_input.setFocus()
            return

        self.accept()

    def get_data(self) -> dict:
        """Return form values as dict"""
        return {
            "name": self.name_input.text().strip(),
            "description": self.desc_input.toPlainText().strip(),
            "storage_mode": self.storage_combo.currentData(),
            "similarity_threshold": (
                self.threshold_slider.value() / 100.0
            ),
        }

    def _apply_theme(self):
        c = ThemeManager.colors()
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {c['bg_primary']};
                color: {c['text_primary']};
            }}
            QLabel {{
                color: {c['text_primary']};
                background: transparent;
            }}
        """)
        self.storage_hint.setStyleSheet(
            f"font-size: 11px; color: {c['text_muted']};"
            f"background: transparent;"
        )


# ─────────────────────────────────────────────
#  PROJECT CARD
# ─────────────────────────────────────────────
class ProjectCard(QFrame):
    """Card widget representing one project"""

    open_clicked   = pyqtSignal(int)
    edit_clicked   = pyqtSignal(int)
    delete_clicked = pyqtSignal(int)

    def __init__(self, project: dict, parent=None):
        super().__init__(parent)
        self.project    = project
        self.project_id = project["id"]
        self.setProperty("class", "card")
        self.setFixedHeight(148)
        self._build()
        ThemeManager.add_listener(self.apply_theme)

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(8)

        # ── Top row: name + status ──
        top = QHBoxLayout()
        top.setSpacing(10)

        status = self.project.get("status", "idle")
        dot_color = {
            "idle":     "#5c6bc0",
            "scanning": "#ff9800",
            "done":     "#4caf50",
            "error":    "#f44336",
        }.get(status, "#5c6bc0")

        dot = QLabel("●")
        dot.setFixedWidth(14)
        dot.setStyleSheet(
            f"font-size: 10px; color: {dot_color};"
            f"background: transparent;"
        )

        self.name_lbl = QLabel(
            self.project.get("name", "Unnamed")
        )
        self.name_lbl.setStyleSheet(
            "font-size: 14px; font-weight: 700;"
            "background: transparent;"
        )

        badge_text = {
            "idle":     "Idle",
            "scanning": "Scanning",
            "done":     "Done",
            "error":    "Error",
        }.get(status, status.capitalize())

        badge = QLabel(badge_text)
        badge.setStyleSheet(f"""
            QLabel {{
                background-color: {dot_color}22;
                color: {dot_color};
                border: 1px solid {dot_color}55;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 600;
                padding: 2px 8px;
            }}
        """)

        top.addWidget(dot)
        top.addWidget(self.name_lbl, 1)
        top.addWidget(badge)
        layout.addLayout(top)

        # ── Description ──
        desc = self.project.get("description", "") or ""
        self.desc_lbl = QLabel(
            desc if desc else "No description"
        )
        self.desc_lbl.setWordWrap(True)
        self.desc_lbl.setMaximumHeight(36)
        self.desc_lbl.setStyleSheet(
            "font-size: 12px; background: transparent;"
        )
        layout.addWidget(self.desc_lbl)

        # ── Meta row ──
        meta = QHBoxLayout()
        meta.setSpacing(16)

        file_count = self.project.get("file_count", 0)
        threshold  = int(
            self.project.get("similarity_threshold", 0.70) * 100
        )
        updated    = self.project.get("updated_at", "")[:10]
        mode       = self.project.get("storage_mode", "reference")
        mode_icon  = "📌" if mode == "reference" else "📋"

        for icon, text in [
            ("📄", f"{file_count} files"),
            ("🎯", f"{threshold}% threshold"),
            (mode_icon, mode.capitalize()),
            ("🕒", updated),
        ]:
            chip = QLabel(f"{icon} {text}")
            chip.setStyleSheet(
                "font-size: 11px; background: transparent;"
            )
            meta.addWidget(chip)

        meta.addStretch()
        layout.addLayout(meta)

        # ── Action buttons ──
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()

        open_btn = QPushButton("🔍 Open")
        open_btn.setFixedHeight(30)
        open_btn.setFixedWidth(90)
        open_btn.clicked.connect(
            lambda: self.open_clicked.emit(self.project_id)
        )

        edit_btn = QPushButton("✏️ Edit")
        edit_btn.setProperty("class", "ghost")
        edit_btn.setFixedHeight(30)
        edit_btn.setFixedWidth(80)
        edit_btn.clicked.connect(
            lambda: self.edit_clicked.emit(self.project_id)
        )

        del_btn = QPushButton("🗑️")
        del_btn.setProperty("class", "danger")
        del_btn.setFixedHeight(30)
        del_btn.setFixedWidth(40)
        del_btn.setToolTip("Delete project")
        del_btn.clicked.connect(
            lambda: self.delete_clicked.emit(self.project_id)
        )

        btn_row.addWidget(open_btn)
        btn_row.addWidget(edit_btn)
        btn_row.addWidget(del_btn)
        layout.addLayout(btn_row)

        self.apply_theme()

    def apply_theme(self):
        c = ThemeManager.colors()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {c['bg_card']};
                border: 1px solid {c['border']};
                border-radius: 10px;
            }}
            QFrame:hover {{
                border-color: {c['accent']};
            }}
        """)
        self.name_lbl.setStyleSheet(
            f"font-size: 14px; font-weight: 700;"
            f"color: {c['text_primary']}; background: transparent;"
        )
        self.desc_lbl.setStyleSheet(
            f"font-size: 12px; color: {c['text_muted']};"
            f"background: transparent;"
        )


# ─────────────────────────────────────────────
#  PROJECTS PAGE
# ─────────────────────────────────────────────
class ProjectsPage(QWidget):
    """
    Page 1 — Projects
    Full CRUD: create, read, update, delete projects
    """

    open_analysis   = pyqtSignal(int)
    project_created = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._projects: list = []
        self._search_text    = ""
        self._build()
        ThemeManager.add_listener(self.apply_theme)

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Toolbar ──
        toolbar = QFrame()
        toolbar.setFixedHeight(64)
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(28, 0, 28, 0)
        tb_layout.setSpacing(12)

        # Search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔎  Search projects...")
        self.search_input.setFixedHeight(36)
        self.search_input.setMaximumWidth(300)
        self.search_input.textChanged.connect(self._on_search)

        tb_layout.addWidget(self.search_input)
        tb_layout.addStretch()

        # New project button
        self.new_btn = QPushButton("➕  New Project")
        self.new_btn.setFixedHeight(36)
        self.new_btn.clicked.connect(self._on_create)
        tb_layout.addWidget(self.new_btn)

        outer.addWidget(toolbar)

        # Divider
        div = QFrame()
        div.setFixedHeight(1)
        div.setProperty("class", "divider")
        outer.addWidget(div)

        # ── Scroll area for cards ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(28, 20, 28, 28)
        self.content_layout.setSpacing(0)

        # Loading label
        self.loading_lbl = LoadingLabel("Loading projects...")
        self.loading_lbl.setFixedHeight(60)
        self.loading_lbl.setVisible(False)
        self.content_layout.addWidget(self.loading_lbl)

        # Stats row
        self.stats_lbl = QLabel("")
        self.stats_lbl.setStyleSheet(
            "font-size: 12px; background: transparent;"
            "padding-bottom: 12px;"
        )
        self.content_layout.addWidget(self.stats_lbl)

        # Grid for cards
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(14)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.content_layout.addLayout(self.grid_layout)

        # Empty state
        self.empty_state = EmptyState(
            icon     = "📁",
            title    = "No projects yet",
            message  = (
                "Create your first project to start finding "
                "similar content across your files."
            ),
            btn_text = "➕ Create First Project",
        )
        self.empty_state.action_clicked.connect(self._on_create)
        self.empty_state.setVisible(False)
        self.content_layout.addWidget(self.empty_state)

        self.content_layout.addStretch()
        scroll.setWidget(self.content_widget)
        outer.addWidget(scroll, 1)

        self.apply_theme()

    # ─────────────────────────────────────────
    #  DATA
    # ─────────────────────────────────────────
    def refresh(self):
        """Reload projects from DB"""
        self._show_loading(True)
        QTimer.singleShot(80, self._load_data)

    def _load_data(self):
        try:
            self._projects = get_all_projects()
            self._render_projects()
        except Exception as e:
            print(f"Projects load error: {e}")
        finally:
            self._show_loading(False)

    def _filtered_projects(self) -> list:
        if not self._search_text:
            return self._projects
        q = self._search_text.lower()
        return [
            p for p in self._projects
            if q in p.get("name", "").lower()
            or q in p.get("description", "").lower()
        ]

    def _render_projects(self):
        # Clear grid
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        filtered = self._filtered_projects()

        # Stats label
        total = len(self._projects)
        shown = len(filtered)
        if self._search_text:
            self.stats_lbl.setText(
                f"Showing {shown} of {total} projects"
            )
        else:
            self.stats_lbl.setText(
                f"{total} project{'s' if total != 1 else ''}"
            )

        if not filtered:
            self.empty_state.setVisible(True)
            return

        self.empty_state.setVisible(False)

        # 2-column grid
        cols = 2
        for i, proj in enumerate(filtered):
            card = ProjectCard(proj)
            card.open_clicked.connect(self._on_open)
            card.edit_clicked.connect(self._on_edit)
            card.delete_clicked.connect(self._on_delete)
            self.grid_layout.addWidget(
                card, i // cols, i % cols
            )

    def _show_loading(self, show: bool):
        self.loading_lbl.setVisible(show)
        if show:
            self.loading_lbl.start()
        else:
            self.loading_lbl.stop()

    # ─────────────────────────────────────────
    #  CRUD ACTIONS
    # ─────────────────────────────────────────
    def _on_search(self, text: str):
        self._search_text = text
        self._render_projects()

    def _on_create(self):
        dlg = ProjectDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            # Optimistic UI: show loading
            self._show_loading(True)

            try:
                pid = create_project(
                    name                 = data["name"],
                    description          = data["description"],
                    similarity_threshold = data["similarity_threshold"],
                    storage_mode         = data["storage_mode"],
                )
                self.project_created.emit(pid)
                self.refresh()
            except Exception as e:
                self._show_loading(False)
                QMessageBox.critical(
                    self, "Error",
                    f"Failed to create project:\n{e}"
                )

    def _on_open(self, project_id: int):
        self.open_analysis.emit(project_id)

    def _on_edit(self, project_id: int):
        # Find project data
        proj = next(
            (p for p in self._projects if p["id"] == project_id),
            None,
        )
        if not proj:
            return

        dlg = ProjectDialog(self, project=proj)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            try:
                ok = update_project(
                    project_id           = project_id,
                    name                 = data["name"],
                    description          = data["description"],
                    similarity_threshold = data["similarity_threshold"],
                    storage_mode         = data["storage_mode"],
                )
                if ok:
                    self.refresh()
                else:
                    QMessageBox.warning(
                        self, "Warning",
                        "Project not found or not updated."
                    )
            except Exception as e:
                QMessageBox.critical(
                    self, "Error",
                    f"Failed to update project:\n{e}"
                )

    def _on_delete(self, project_id: int):
        proj = next(
            (p for p in self._projects if p["id"] == project_id),
            None,
        )
        name = proj.get("name", "this project") if proj else "this project"

        reply = QMessageBox.question(
            self,
            "Delete Project",
            f"Are you sure you want to delete\n\"{name}\"?\n\n"
            "This will remove all files, results, and analysis "
            "data. This cannot be undone.",
            QMessageBox.StandardButton.Yes |
            QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._show_loading(True)
            try:
                ok = delete_project(project_id)
                if ok:
                    self.refresh()
                else:
                    self._show_loading(False)
                    QMessageBox.warning(
                        self, "Warning",
                        "Project could not be deleted."
                    )
            except Exception as e:
                self._show_loading(False)
                QMessageBox.critical(
                    self, "Error",
                    f"Failed to delete project:\n{e}"
                )

    def apply_theme(self):
        c = ThemeManager.colors()
        self.setStyleSheet(
            f"background-color: {c['bg_primary']};"
        )
        self.stats_lbl.setStyleSheet(
            f"font-size: 12px; color: {c['text_muted']};"
            f"background: transparent; padding-bottom: 12px;"
        )