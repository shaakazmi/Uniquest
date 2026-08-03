import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QGroupBox, QProgressBar,
    QTableWidget, QTableWidgetItem, QFileDialog,
    QMessageBox, QRadioButton, QButtonGroup,
    QHeaderView, QAbstractItemView, QFrame
)
from PyQt6.QtCore import Qt, QMimeData
from PyQt6.QtGui import QDragEnterEvent, QDropEvent

from database.db import (
    get_all_projects, add_file_record,
    get_project_files, get_project, get_setting
)
from database.models import format_file_size, SUPPORTED_TYPES
from core.processor import AnalysisWorker


class AnalysisPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window  = main_window
        self._worker      = None
        self._file_list   = []   # list of dicts: {id, path, name, type, size}
        self._build_ui()
        self.setAcceptDrops(True)

    def on_show(self):
        self._refresh_projects()

    # ─────────────────────────────────────────────────────────
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # project selector
        proj_group  = QGroupBox("Active Project")
        proj_layout = QHBoxLayout(proj_group)
        self._proj_combo = QComboBox()
        self._proj_combo.setMinimumWidth(300)
        proj_layout.addWidget(self._proj_combo)
        proj_layout.addStretch()
        layout.addWidget(proj_group)

        # scan mode
        mode_group  = QGroupBox("Scan Mode")
        mode_layout = QVBoxLayout(mode_group)

        self._rb_single   = QRadioButton("Single file — find duplicates within one file")
        self._rb_multiple = QRadioButton("Multiple files — compare content across files")
        self._rb_single.setChecked(True)

        self._mode_group = QButtonGroup()
        self._mode_group.addButton(self._rb_single,   1)
        self._mode_group.addButton(self._rb_multiple, 2)

        self._rb_single.toggled.connect(self._on_mode_changed)

        mode_layout.addWidget(self._rb_single)
        mode_layout.addWidget(self._rb_multiple)
        layout.addWidget(mode_group)

        # import area
        import_group  = QGroupBox("Import Files")
        import_layout = QHBoxLayout(import_group)

        self._browse_btn = QPushButton("Browse File...")
        self._browse_btn.setFixedHeight(30)
        self._browse_btn.clicked.connect(self._browse_files)

        drop_label = QLabel("or drag and drop files here")
        drop_label.setStyleSheet("color: #888888;")

        import_layout.addWidget(self._browse_btn)
        import_layout.addWidget(drop_label)
        import_layout.addStretch()
        layout.addWidget(import_group)

        # file table
        files_group  = QGroupBox("Imported Files")
        files_layout = QVBoxLayout(files_group)

        # table toolbar
        tbl_toolbar = QHBoxLayout()
        self._file_count_label = QLabel("0 files")
        btn_clear  = QPushButton("Clear Results")
        btn_remove = QPushButton("Remove All")
        btn_clear.setFixedHeight(26)
        btn_remove.setFixedHeight(26)
        btn_remove.setObjectName("danger_btn")
        btn_clear.clicked.connect(self._clear_results)
        btn_remove.clicked.connect(self._remove_all_files)
        tbl_toolbar.addWidget(self._file_count_label)
        tbl_toolbar.addStretch()
        tbl_toolbar.addWidget(btn_clear)
        tbl_toolbar.addWidget(btn_remove)
        files_layout.addLayout(tbl_toolbar)

        self._file_table = QTableWidget()
        self._file_table.setColumnCount(4)
        self._file_table.setHorizontalHeaderLabels(["File Name", "Type", "Size", "Status"])
        self._file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._file_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._file_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._file_table.setAlternatingRowColors(True)
        self._file_table.verticalHeader().setVisible(False)
        self._file_table.setMaximumHeight(200)
        files_layout.addWidget(self._file_table)
        layout.addWidget(files_group)

        # progress
        progress_group  = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        self._progress_bar = QProgressBar()
        self._progress_bar.setFixedHeight(22)
        self._status_label = QLabel("Ready to find duplicates.")
        progress_layout.addWidget(self._progress_bar)
        progress_layout.addWidget(self._status_label)
        layout.addWidget(progress_group)

        # run button
        run_row = QHBoxLayout()
        self._run_btn = QPushButton("Find Duplicates")
        self._run_btn.setObjectName("primary_btn")
        self._run_btn.setFixedHeight(34)
        self._run_btn.setMinimumWidth(180)
        self._run_btn.clicked.connect(self._run_analysis)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setFixedHeight(34)
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.clicked.connect(self._cancel_analysis)

        run_row.addStretch()
        run_row.addWidget(self._cancel_btn)
        run_row.addWidget(self._run_btn)
        layout.addLayout(run_row)

        layout.addStretch()

    # ─────────────────────────────────────────────────────────
    def _refresh_projects(self):
        self._proj_combo.clear()
        projects = get_all_projects()
        if not projects:
            self._proj_combo.addItem("No projects — create one first", -1)
        else:
            for p in projects:
                self._proj_combo.addItem(p["name"], p["id"])

    def _on_mode_changed(self):
        """If single file mode, enforce max 1 file."""
        if self._rb_single.isChecked() and len(self._file_list) > 1:
            self._file_list = self._file_list[:1]
            self._update_file_table()

    # ─────────────────────────────────────────────────────────
    def _browse_files(self):
        ext_filter = "Supported Files (*.pdf *.docx *.xlsx *.csv *.pptx *.txt *.rtf *.png *.jpg *.jpeg *.bmp *.tiff)"
        if self._rb_single.isChecked():
            path, _ = QFileDialog.getOpenFileName(self, "Select File", "", ext_filter)
            if path:
                self._add_file(path)
        else:
            paths, _ = QFileDialog.getOpenFileNames(self, "Select Files", "", ext_filter)
            for path in paths:
                self._add_file(path)

    def _add_file(self, path: str):
        # single mode: only 1 file allowed
        if self._rb_single.isChecked():
            self._file_list = []

        # check duplicate path
        if any(f["path"] == path for f in self._file_list):
            return

        ext  = Path(path).suffix.lower().lstrip(".")
        size = os.path.getsize(path)

        self._file_list.append({
            "path":   path,
            "name":   Path(path).name,
            "type":   ext.upper(),
            "size":   size,
            "status": "Pending",
            "db_id":  None,
        })
        self._update_file_table()

    def _update_file_table(self):
        self._file_table.setRowCount(0)
        for f in self._file_list:
            row = self._file_table.rowCount()
            self._file_table.insertRow(row)
            self._file_table.setItem(row, 0, QTableWidgetItem(f["name"]))
            self._file_table.setItem(row, 1, QTableWidgetItem(f["type"]))
            self._file_table.setItem(row, 2, QTableWidgetItem(format_file_size(f["size"])))
            self._file_table.setItem(row, 3, QTableWidgetItem(f["status"]))
        self._file_count_label.setText(f"{len(self._file_list)} file(s)")

    def _clear_results(self):
        for f in self._file_list:
            f["status"] = "Pending"
        self._update_file_table()
        self._progress_bar.setValue(0)
        self._status_label.setText("Ready to find duplicates.")

    def _remove_all_files(self):
        self._file_list = []
        self._update_file_table()

    # ─────────────────────────────────────────────────────────
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isfile(path):
                self._add_file(path)

    # ─────────────────────────────────────────────────────────
    def _run_analysis(self):
        pid = self._proj_combo.currentData()
        if not pid or pid == -1:
            QMessageBox.warning(self, "No Project", "Create and select a project first.")
            return

        if not self._file_list:
            QMessageBox.warning(self, "No Files", "Add at least one file.")
            return

        if self._rb_single.isChecked() and len(self._file_list) > 1:
            QMessageBox.warning(self, "Single File Mode", "Only one file allowed in single file mode.")
            return

        proj = get_project(pid)
        threshold = proj.get("similarity_threshold", 0.75)
        storage   = proj.get("storage_mode", "reference")

        # register files in DB
        file_records = []
        for f in self._file_list:
            db_id = add_file_record(
                pid, f["path"], f["name"], f["type"].lower(),
                f["size"], storage
            )
            f["db_id"] = db_id
            file_records.append({"id": db_id, "path": f["path"]})
            f["status"] = "Queued"

        self._update_file_table()

        # disable UI
        self._run_btn.setEnabled(False)
        self._cancel_btn.setEnabled(True)
        self._browse_btn.setEnabled(False)
        self._progress_bar.setValue(0)
        self._status_label.setText("Starting analysis...")

        # start worker
        self._worker = AnalysisWorker(pid, file_records, threshold)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _cancel_analysis(self):
        if self._worker:
            self._worker.cancel()
        self._run_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)
        self._browse_btn.setEnabled(True)
        self._status_label.setText("Cancelled.")

    # ─────────────────────────────────────────────────────────
    def _on_progress(self, pct: int, msg: str):
        self._progress_bar.setValue(pct)
        self._status_label.setText(msg)
        self.main_window.set_status(msg)

    def _on_finished(self, summary: dict):
        self._run_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)
        self._browse_btn.setEnabled(True)
        self._progress_bar.setValue(100)

        for f in self._file_list:
            f["status"] = "Done"
        self._update_file_table()

        msg = (
            f"Analysis complete.\n\n"
            f"Text matches found: {summary['text_similarities']}\n"
            f"Image matches found: {summary['image_similarities']}\n"
            f"Chunks processed: {summary['chunks_processed']}"
        )
        self._status_label.setText(
            f"Done — {summary['text_similarities']} text matches, "
            f"{summary['image_similarities']} image matches"
        )
        self.main_window.set_status("Analysis complete")

        box = QMessageBox(self)
        box.setWindowTitle("Analysis Complete")
        box.setText(msg)
        box.setWindowFlags(box.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        box.addButton("View Results", QMessageBox.ButtonRole.AcceptRole)
        box.addButton("Close", QMessageBox.ButtonRole.RejectRole)
        result = box.exec()
        if result == 0:
            self.main_window.navigate_to("results")

    def _on_error(self, error_msg: str):
        self._run_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)
        self._browse_btn.setEnabled(True)
        self._status_label.setText("Error during analysis.")
        QMessageBox.critical(self, "Analysis Error", error_msg)