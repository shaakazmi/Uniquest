from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame,
    QScrollArea, QLineEdit, QTextEdit,
    QDialog, QComboBox, QMessageBox,
    QSlider, QGroupBox, QSizePolicy,
    QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor

from utils.theme import ThemeManager
from core.processor import (
    get_all_projects,
    create_project,
    update_project,
    delete_project,
)
from ui.dashboard import EmptyState, LoadingLabel


# ─────────────────────────────────────────────
#  PROJECT DIALOG
# ─────────────────────────────────────────────
class ProjectDialog(QDialog):
    def __init__(self, parent=None, project: dict = None):
        super().__init__(parent)
        self.project = project
        self.is_edit = project is not None
        self.setWindowTitle("Edit Project" if self.is_edit else "New Project")
        self.setFixedWidth(440)
        self.setModal(True)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # Project details
        details_group = QGroupBox("Project Details")
        d_layout = QVBoxLayout(details_group)
        d_layout.setSpacing(8)
        d_layout.setContentsMargins(10, 14, 10, 10)

        # Name
        d_layout.addWidget(self._label("Project name:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. Q1 Duplicate Report")
        if self.is_edit:
            self.name_input.setText(self.project.get("name", ""))
        d_layout.addWidget(self.name_input)

        # Description
        d_layout.addWidget(self._label("Description (optional):"))
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("Short description...")
        self.desc_input.setFixedHeight(60)
        if self.is_edit:
            self.desc_input.setPlainText(self.project.get("description", ""))
        d_layout.addWidget(self.desc_input)

        layout.addWidget(details_group)

        # Options
        options_group = QGroupBox("Options")
        o_layout = QVBoxLayout(options_group)
        o_layout.setSpacing(8)
        o_layout.setContentsMargins(10, 14, 10, 10)

        # Storage mode
        o_layout.addWidget(self._label("File storage mode:"))
        self.storage_combo = QComboBox()
        self.storage_combo.addItem(
            "Reference original files (saves disk space)", "reference"
        )
        self.storage_combo.addItem(
            "Copy files into app folder (portable)", "copy"
        )
        if self.is_edit:
            mode = self.project.get("storage_mode", "reference")
            idx = 0 if mode == "reference" else 1
            self.storage_combo.setCurrentIndex(idx)
        o_layout.addWidget(self.storage_combo)

        # Threshold slider
        o_layout.addWidget(self._label("Text similarity threshold:"))

        slider_row = QHBoxLayout()
        slider_row.setSpacing(6)

        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setRange(50, 100)

        default_val = int(
            self.project.get("similarity_threshold", 0.70) * 100
            if self.is_edit else 70
        )
        self.threshold_slider.setValue(default_val)

        self.threshold_lbl = QLabel(f"{default_val}%")
        self.threshold_lbl.setFixedWidth(36)
        self.threshold_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.threshold_lbl.setStyleSheet(
            "font-weight: 700; background: transparent; border: 0px;"
        )

        self.threshold_slider.valueChanged.connect(
            lambda v: self.threshold_lbl.setText(f"{v}%")
        )

        slider_row.addWidget(QLabel("50%"))
        slider_row.addWidget(self.threshold_slider, 1)
        slider_row.addWidget(QLabel("100%"))
        slider_row.addWidget(self.threshold_lbl)
        o_layout.addLayout(slider_row)

        hint = QLabel(
            "Lower = more matches found. Higher = only near-identical."
        )
        hint.setStyleSheet(
            "font-size: 11px; color: #767676;"
            "background: transparent; border: 0px;"
        )
        o_layout.addWidget(hint)

        layout.addWidget(options_group)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumWidth(80)
        cancel_btn.clicked.connect(self.reject)

        self.save_btn = QPushButton(
            "Save Changes" if self.is_edit else "Create Project"
        )
        self.save_btn.setProperty("class", "accent")
        self.save_btn.setMinimumWidth(120)
        self.save_btn.clicked.connect(self._on_save)

        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(self.save_btn)
        layout.addLayout(btn_row)

    def _label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            "font-size: 12px; background: transparent; border: 0px;"
        )
        return lbl

    def _on_save(self):
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Validation", "Project name is required.")
            self.name_input.setFocus()
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "name": self.name_input.text().strip(),
            "description": self.desc_input.toPlainText().strip(),
            "storage_mode": self.storage_combo.currentData(),
            "similarity_threshold": self.threshold_slider.value() / 100.0,
        }


# ─────────────────────────────────────────────
#  PROJECTS PAGE
# ─────────────────────────────────────────────
class ProjectsPage(QWidget):
    open_analysis = pyqtSignal(int)
    project_created = pyqtSignal(int)

    COLUMNS = ["Name", "Files", "Threshold", "Status", "Updated", "Actions"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._projects = []
        self._search_text = ""
        self._build()
        ThemeManager.add_listener(self.apply_theme)

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 12, 16, 12)
        outer.setSpacing(10)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search projects...")
        self.search_input.setMaximumWidth(240)
        self.search_input.textChanged.connect(self._on_search)

        toolbar.addWidget(self.search_input)
        toolbar.addStretch()

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setMinimumWidth(80)
        self.refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(self.refresh_btn)

        self.new_btn = QPushButton("New Project")
        self.new_btn.setProperty("class", "accent")
        self.new_btn.setMinimumWidth(120)
        self.new_btn.clicked.connect(self._on_create)
        toolbar.addWidget(self.new_btn)

        outer.addLayout(toolbar)

        # Loading
        self.loading_lbl = LoadingLabel("Loading projects...")
        self.loading_lbl.setFixedHeight(24)
        self.loading_lbl.setVisible(False)
        outer.addWidget(self.loading_lbl)

        # Stats label
        self.stats_lbl = QLabel("0 projects")
        self.stats_lbl.setStyleSheet(
            "font-size: 11px; background: transparent; border: 0px;"
        )
        outer.addWidget(self.stats_lbl)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)

        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)

        self.table.setColumnWidth(1, 60)
        self.table.setColumnWidth(2, 80)
        self.table.setColumnWidth(3, 80)
        self.table.setColumnWidth(4, 100)
        self.table.setColumnWidth(5, 200)

        outer.addWidget(self.table, 1)

        # Empty state
        self.empty_state = EmptyState(
            title="No projects yet",
            message="Create your first project to start finding similar content.",
            btn_text="Create Project",
        )
        self.empty_state.action_clicked.connect(self._on_create)
        self.empty_state.setVisible(False)
        outer.addWidget(self.empty_state)

        self.apply_theme()

    def refresh(self):
        self._show_loading(True)
        QTimer.singleShot(60, self._load_data)

    def _load_data(self):
        try:
            self._projects = get_all_projects()
            self._render_table()
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

    def _render_table(self):
        filtered = self._filtered_projects()

        total = len(self._projects)
        shown = len(filtered)
        if self._search_text:
            self.stats_lbl.setText(f"Showing {shown} of {total} projects")
        else:
            self.stats_lbl.setText(f"{total} project{'s' if total != 1 else ''}")

        if not filtered:
            self.table.setVisible(False)
            self.empty_state.setVisible(True)
            return

        self.table.setVisible(True)
        self.empty_state.setVisible(False)

        self.table.setRowCount(0)
        for proj in filtered:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setRowHeight(row, 32)

            pid = proj["id"]

            # Name
            name_item = QTableWidgetItem(proj.get("name", ""))
            self.table.setItem(row, 0, name_item)

            # Files
            fc = QTableWidgetItem(str(proj.get("file_count", 0)))
            fc.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 1, fc)

            # Threshold
            pct = int(proj.get("similarity_threshold", 0.70) * 100)
            th = QTableWidgetItem(f"{pct}%")
            th.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 2, th)

            # Status
            status = proj.get("status", "idle").capitalize()
            st = QTableWidgetItem(status)
            st.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            color = {
                "Idle":     "#767676",
                "Scanning": "#ca5010",
                "Done":     "#107c10",
                "Error":    "#a80000",
            }.get(status, "#767676")
            st.setForeground(QColor(color))
            self.table.setItem(row, 3, st)

            # Updated
            up = QTableWidgetItem(proj.get("updated_at", "")[:10])
            up.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 4, up)

            # Actions
            actions_w = QWidget()
            act_layout = QHBoxLayout(actions_w)
            act_layout.setContentsMargins(4, 2, 4, 2)
            act_layout.setSpacing(4)

            open_btn = QPushButton("Open")
            open_btn.setFixedHeight(24)
            open_btn.setFixedWidth(50)
            open_btn.clicked.connect(lambda _, p=pid: self._on_open(p))

            edit_btn = QPushButton("Edit")
            edit_btn.setFixedHeight(24)
            edit_btn.setFixedWidth(50)
            edit_btn.clicked.connect(lambda _, p=pid: self._on_edit(p))

            del_btn = QPushButton("Delete")
            del_btn.setProperty("class", "danger")
            del_btn.setFixedHeight(24)
            del_btn.setFixedWidth(60)
            del_btn.clicked.connect(lambda _, p=pid: self._on_delete(p))

            act_layout.addWidget(open_btn)
            act_layout.addWidget(edit_btn)
            act_layout.addWidget(del_btn)
            act_layout.addStretch()

            self.table.setCellWidget(row, 5, actions_w)

    def _show_loading(self, show: bool):
        self.loading_lbl.setVisible(show)
        if show:
            self.loading_lbl.start()
        else:
            self.loading_lbl.stop()

    def _on_search(self, text: str):
        self._search_text = text
        self._render_table()

    def _on_create(self):
        dlg = ProjectDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            try:
                pid = create_project(
                    name=data["name"],
                    description=data["description"],
                    similarity_threshold=data["similarity_threshold"],
                    storage_mode=data["storage_mode"],
                )
                self.project_created.emit(pid)
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create project:\n{e}")

    def _on_open(self, project_id: int):
        self.open_analysis.emit(project_id)

    def _on_edit(self, project_id: int):
        proj = next((p for p in self._projects if p["id"] == project_id), None)
        if not proj:
            return
        dlg = ProjectDialog(self, project=proj)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            try:
                update_project(
                    project_id=project_id,
                    name=data["name"],
                    description=data["description"],
                    similarity_threshold=data["similarity_threshold"],
                    storage_mode=data["storage_mode"],
                )
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to update:\n{e}")

    def _on_delete(self, project_id: int):
        proj = next((p for p in self._projects if p["id"] == project_id), None)
        name = proj.get("name", "this project") if proj else "this project"

        reply = QMessageBox.question(
            self, "Delete Project",
            f"Delete \"{name}\"?\n\nAll files, results, and data will be removed.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                delete_project(project_id)
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete:\n{e}")

    def apply_theme(self):
        c = ThemeManager.colors()
        self.setStyleSheet(
            f"background-color: {c['bg_primary']};"
        )
        self.stats_lbl.setStyleSheet(
            f"font-size: 11px; color: {c['text_muted']};"
            f"background: transparent; border: 0px;"
        )