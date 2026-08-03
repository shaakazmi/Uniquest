from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QGroupBox, QLineEdit, QComboBox, QDoubleSpinBox,
    QDialog, QFormLayout, QMessageBox, QHeaderView,
    QTextEdit, QAbstractItemView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from database.db import (
    get_all_projects, create_project, update_project,
    delete_project, get_setting
)


class ProjectsPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self._build_ui()

    def on_show(self):
        self._refresh_table()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # toolbar
        toolbar = QHBoxLayout()
        btn_new = QPushButton("New Project")
        btn_new.setObjectName("primary_btn")
        btn_new.setFixedHeight(30)
        btn_new.clicked.connect(self._new_project)
        toolbar.addWidget(btn_new)
        toolbar.addStretch()

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search projects...")
        self._search.setFixedWidth(220)
        self._search.textChanged.connect(self._filter_table)
        toolbar.addWidget(self._search)
        layout.addLayout(toolbar)

        # table
        tbl_group = QGroupBox("Projects")
        tbl_layout = QVBoxLayout(tbl_group)

        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels([
            "Name", "Description", "Threshold",
            "Storage", "Created", "Status"
        ])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)

        tbl_layout.addWidget(self._table)
        layout.addWidget(tbl_group, 1)

        # action buttons
        btn_row = QHBoxLayout()
        btn_edit   = QPushButton("Edit Selected")
        btn_delete = QPushButton("Delete Selected")
        btn_delete.setObjectName("danger_btn")
        btn_edit.clicked.connect(self._edit_selected)
        btn_delete.clicked.connect(self._delete_selected)
        btn_row.addWidget(btn_edit)
        btn_row.addWidget(btn_delete)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._all_projects = []

    def _refresh_table(self):
        self._all_projects = get_all_projects()
        self._populate_table(self._all_projects)

    def _populate_table(self, projects: list):
        self._table.setRowCount(0)
        for proj in projects:
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._table.setItem(row, 0, QTableWidgetItem(proj["name"]))
            self._table.setItem(row, 1, QTableWidgetItem(proj["description"] or ""))
            self._table.setItem(row, 2, QTableWidgetItem(f"{proj['similarity_threshold']:.0%}"))
            self._table.setItem(row, 3, QTableWidgetItem(proj["storage_mode"].capitalize()))
            self._table.setItem(row, 4, QTableWidgetItem((proj["created_at"] or "")[:10]))
            self._table.setItem(row, 5, QTableWidgetItem(proj["status"].capitalize()))

            # store id in first item
            self._table.item(row, 0).setData(Qt.ItemDataRole.UserRole, proj["id"])

    def _filter_table(self, text: str):
        filtered = [
            p for p in self._all_projects
            if text.lower() in p["name"].lower() or
               text.lower() in (p["description"] or "").lower()
        ]
        self._populate_table(filtered)

    def _get_selected_id(self) -> int:
        row = self._table.currentRow()
        if row < 0:
            return -1
        item = self._table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else -1

    def _new_project(self):
        dialog = _ProjectDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            create_project(
                data["name"], data["description"],
                data["threshold"], data["storage_mode"]
            )
            self._refresh_table()

    def _edit_selected(self):
        pid = self._get_selected_id()
        if pid < 0:
            QMessageBox.information(self, "Edit", "Select a project first.")
            return

        proj = next((p for p in self._all_projects if p["id"] == pid), None)
        if not proj:
            return

        dialog = _ProjectDialog(self, proj)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            update_project(
                pid, data["name"], data["description"],
                data["threshold"], data["storage_mode"]
            )
            self._refresh_table()

    def _delete_selected(self):
        pid = self._get_selected_id()
        if pid < 0:
            QMessageBox.information(self, "Delete", "Select a project first.")
            return

        reply = QMessageBox.question(
            self, "Delete Project",
            "Delete this project and all its data?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            delete_project(pid)
            self._refresh_table()


class _ProjectDialog(QDialog):
    def __init__(self, parent, project: dict = None):
        super().__init__(parent)
        self.setWindowTitle("Edit Project" if project else "New Project")
        self.setFixedWidth(400)
        self._project = project
        self._build_ui()
        if project:
            self._populate(project)

    def _build_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(10)

        self._name = QLineEdit()
        self._desc = QTextEdit()
        self._desc.setMaximumHeight(80)

        self._threshold = QDoubleSpinBox()
        self._threshold.setRange(0.50, 1.00)
        self._threshold.setSingleStep(0.05)
        self._threshold.setValue(0.75)
        self._threshold.setDecimals(2)

        self._storage = QComboBox()
        self._storage.addItems(["Reference (keep in place)", "Copy to app folder"])

        layout.addRow("Name *", self._name)
        layout.addRow("Description", self._desc)
        layout.addRow("Similarity Threshold", self._threshold)
        layout.addRow("Storage Mode", self._storage)

        btn_row = QHBoxLayout()
        btn_ok     = QPushButton("Save")
        btn_cancel = QPushButton("Cancel")
        btn_ok.setObjectName("primary_btn")
        btn_ok.clicked.connect(self._validate)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        layout.addRow(btn_row)

    def _populate(self, proj: dict):
        self._name.setText(proj["name"])
        self._desc.setPlainText(proj["description"] or "")
        self._threshold.setValue(proj["similarity_threshold"])
        self._storage.setCurrentIndex(
            0 if proj["storage_mode"] == "reference" else 1
        )

    def _validate(self):
        if not self._name.text().strip():
            QMessageBox.warning(self, "Validation", "Project name is required.")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "name":         self._name.text().strip(),
            "description":  self._desc.toPlainText().strip(),
            "threshold":    self._threshold.value(),
            "storage_mode": "reference" if self._storage.currentIndex() == 0 else "copy",
        }