import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame,
    QScrollArea, QProgressBar, QGroupBox,
    QFileDialog, QMessageBox,
    QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView,
    QRadioButton, QButtonGroup,
    QTextEdit, QComboBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor

from utils.theme import ThemeManager
from core.processor import (
    get_project,
    get_all_projects,
    get_files_for_project,
    add_files_to_project,
    remove_file_from_project,
    clear_project_results,
    AnalysisWorker,
)
from database.models import SUPPORTED_EXTENSIONS
from ui.dashboard import EmptyState, LoadingLabel


# ─────────────────────────────────────────────
#  SCAN MODE SELECTOR (single vs multiple)
# ─────────────────────────────────────────────
class ScanModeSelector(QGroupBox):
    """Rufus-style scan mode selector"""

    mode_changed = pyqtSignal(str)  # "single" or "multiple"

    def __init__(self, parent=None):
        super().__init__("Scan Mode", parent)
        self._mode = "single"
        self._build()

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 14, 10, 10)
        layout.setSpacing(20)

        self.btn_group = QButtonGroup(self)

        self.radio_single = QRadioButton("Single file (find duplicates within one file)")
        self.radio_single.setChecked(True)
        self.radio_single.toggled.connect(
            lambda checked: self._on_toggle("single") if checked else None
        )

        self.radio_multi = QRadioButton("Multiple files (compare across files)")
        self.radio_multi.toggled.connect(
            lambda checked: self._on_toggle("multiple") if checked else None
        )

        self.btn_group.addButton(self.radio_single, 0)
        self.btn_group.addButton(self.radio_multi, 1)

        layout.addWidget(self.radio_single)
        layout.addWidget(self.radio_multi)
        layout.addStretch()

    def _on_toggle(self, mode: str):
        self._mode = mode
        self.mode_changed.emit(mode)

    def get_mode(self) -> str:
        return self._mode

    def set_mode(self, mode: str):
        if mode == "single":
            self.radio_single.setChecked(True)
        else:
            self.radio_multi.setChecked(True)


# ─────────────────────────────────────────────
#  FILE IMPORT PANEL
# ─────────────────────────────────────────────
class FileImportPanel(QGroupBox):
    files_dropped = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__("Import Files", parent)
        self.setAcceptDrops(True)
        self._mode = "single"
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 14, 10, 10)
        layout.setSpacing(8)

        # Info label
        self.info_lbl = QLabel(
            "Select ONE file to find duplicate content within it."
        )
        self.info_lbl.setStyleSheet(
            "font-size: 11px; background: transparent; border: 0px;"
        )
        layout.addWidget(self.info_lbl)

        # Button row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self.browse_file_btn = QPushButton("Browse File...")
        self.browse_file_btn.setMinimumWidth(120)
        self.browse_file_btn.clicked.connect(self._on_browse_file)

        self.browse_folder_btn = QPushButton("Browse Folder...")
        self.browse_folder_btn.setMinimumWidth(120)
        self.browse_folder_btn.clicked.connect(self._on_browse_folder)
        self.browse_folder_btn.setVisible(False)

        self.drop_hint = QLabel("or drag files here")
        self.drop_hint.setStyleSheet(
            "font-size: 11px; color: #767676;"
            "background: transparent; border: 0px;"
        )

        btn_row.addWidget(self.browse_file_btn)
        btn_row.addWidget(self.browse_folder_btn)
        btn_row.addWidget(self.drop_hint)
        btn_row.addStretch()

        layout.addLayout(btn_row)

    def set_mode(self, mode: str):
        self._mode = mode
        if mode == "single":
            self.info_lbl.setText(
                "Select ONE file to find duplicate content within it."
            )
            self.browse_file_btn.setText("Browse File...")
            self.browse_folder_btn.setVisible(False)
        else:
            self.info_lbl.setText(
                "Select MULTIPLE files or a folder to compare content across files."
            )
            self.browse_file_btn.setText("Browse Files...")
            self.browse_folder_btn.setVisible(True)

    def _on_browse_file(self):
        ext_list = " ".join(f"*.{e}" for e in SUPPORTED_EXTENSIONS)
        if self._mode == "single":
            path, _ = QFileDialog.getOpenFileName(
                self, "Select File", str(Path.home()),
                f"Supported Files ({ext_list});;All Files (*)",
            )
            if path:
                self.files_dropped.emit([path])
        else:
            paths, _ = QFileDialog.getOpenFileNames(
                self, "Select Files", str(Path.home()),
                f"Supported Files ({ext_list});;All Files (*)",
            )
            if paths:
                self.files_dropped.emit(paths)

    def _on_browse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Folder", str(Path.home()),
        )
        if folder:
            found = []
            for root, dirs, files in os.walk(folder):
                for fname in files:
                    ext = fname.rsplit(".", 1)[-1].lower()
                    if ext in SUPPORTED_EXTENSIONS:
                        found.append(os.path.join(root, fname))
            if found:
                self.files_dropped.emit(found)
            else:
                QMessageBox.information(
                    self, "No Files Found",
                    "No supported files found in that folder."
                )

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        paths = []
        for url in urls:
            path = url.toLocalFile()
            if os.path.isfile(path):
                ext = path.rsplit(".", 1)[-1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    paths.append(path)
            elif os.path.isdir(path):
                for root, dirs, files in os.walk(path):
                    for fname in files:
                        ext = fname.rsplit(".", 1)[-1].lower()
                        if ext in SUPPORTED_EXTENSIONS:
                            paths.append(os.path.join(root, fname))

        # Enforce single-file mode
        if self._mode == "single" and len(paths) > 1:
            paths = [paths[0]]
            QMessageBox.information(
                self, "Single File Mode",
                "In Single File mode, only the first file was added.\n"
                "Switch to Multiple Files mode to add more."
            )

        if paths:
            self.files_dropped.emit(paths)


# ─────────────────────────────────────────────
#  PROGRESS PANEL
# ─────────────────────────────────────────────
class ProgressPanel(QGroupBox):
    cancel_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("Progress", parent)
        self.setVisible(False)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 14, 10, 10)
        layout.setSpacing(6)

        header = QHBoxLayout()
        self.stage_lbl = QLabel("Analyzing...")
        self.stage_lbl.setStyleSheet(
            "font-size: 12px; font-weight: 600;"
            "background: transparent; border: 0px;"
        )
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setFixedWidth(80)
        self.cancel_btn.setFixedHeight(24)
        self.cancel_btn.clicked.connect(self.cancel_clicked)
        header.addWidget(self.stage_lbl)
        header.addStretch()
        header.addWidget(self.cancel_btn)
        layout.addLayout(header)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.msg_lbl = QLabel("Starting...")
        self.msg_lbl.setStyleSheet(
            "font-size: 11px; background: transparent; border: 0px;"
        )
        layout.addWidget(self.msg_lbl)

        self.log_box = QTextEdit()
        self.log_box.document().setMaximumBlockCount(300)
        self.log_box.setReadOnly(True)
        self.log_box.setFixedHeight(80)
        self.log_box.setStyleSheet(
            "font-family: 'Consolas', monospace; font-size: 10px;"
        )
        layout.addWidget(self.log_box)

    def start(self):
        self.setVisible(True)
        self.progress_bar.setValue(0)
        self.log_box.clear()
        self.msg_lbl.setText("Starting...")
        self.stage_lbl.setText("Analyzing...")
        self.cancel_btn.setEnabled(True)

    def stop(self):
        self.cancel_btn.setEnabled(False)

    def update_progress(self, pct: int, msg: str):
        self.progress_bar.setValue(pct)
        self.msg_lbl.setText(msg)

    def update_stage(self, stage: str):
        self.stage_lbl.setText(stage)

    def append_log(self, msg: str):
        self.log_box.append(msg)
        sb = self.log_box.verticalScrollBar()
        sb.setValue(sb.maximum())


# ─────────────────────────────────────────────
#  FILE TABLE
# ─────────────────────────────────────────────
class FileTable(QTableWidget):
    remove_file = pyqtSignal(int)

    COLUMNS = ["File Name", "Type", "Size", "Status", "Chunks", "Images", ""]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._file_ids = []
        self._setup()

    def _setup(self):
        self.setColumnCount(len(self.COLUMNS))
        self.setHorizontalHeaderLabels(self.COLUMNS)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(False)

        hdr = self.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)

        self.setColumnWidth(1, 60)
        self.setColumnWidth(2, 70)
        self.setColumnWidth(3, 80)
        self.setColumnWidth(4, 60)
        self.setColumnWidth(5, 60)
        self.setColumnWidth(6, 60)

    def load_files(self, files: list):
        self._file_ids = []
        self.setRowCount(0)

        for f in files:
            row = self.rowCount()
            self.insertRow(row)
            self.setRowHeight(row, 26)

            fid = f["id"]
            self._file_ids.append(fid)

            self.setItem(row, 0, QTableWidgetItem(f.get("file_name", "")))

            type_item = QTableWidgetItem(f.get("file_type", "").upper())
            type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(row, 1, type_item)

            size = f.get("file_size", 0)
            size_str = self._fmt_size(size)
            size_item = QTableWidgetItem(size_str)
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(row, 2, size_item)

            status = f.get("status", "pending").capitalize()
            st_item = QTableWidgetItem(status)
            st_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            color = {
                "Pending":    "#767676",
                "Processing": "#ca5010",
                "Done":       "#107c10",
                "Error":      "#a80000",
            }.get(status, "#767676")
            st_item.setForeground(QColor(color))
            self.setItem(row, 3, st_item)

            tc = QTableWidgetItem(str(f.get("text_extracted", 0)))
            tc.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(row, 4, tc)

            ic = QTableWidgetItem(str(f.get("images_extracted", 0)))
            ic.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(row, 5, ic)

            del_btn = QPushButton("Remove")
            del_btn.setFixedHeight(22)
            del_btn.setFixedWidth(56)
            del_btn.setProperty("class", "danger")
            del_btn.clicked.connect(lambda _, fid=fid: self.remove_file.emit(fid))
            self.setCellWidget(row, 6, del_btn)

    def _fmt_size(self, size: int) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.0f} {unit}"
            size /= 1024
        return f"{size:.1f} GB"


# ─────────────────────────────────────────────
#  ANALYSIS PAGE
# ─────────────────────────────────────────────
class AnalysisPage(QWidget):
    analysis_complete = pyqtSignal(int, int, int)
    status_message = pyqtSignal(str)
    log_message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._project_id = None
        self._project_data = None
        self._pending_logs = []
        self._worker = None
        self._files = []
        self._scan_mode = "single"
        self._build()
        ThemeManager.add_listener(self.apply_theme)
        self._pending_progress = None
        self._log_timer = QTimer(self)
        self._log_timer.setInterval(100)
        self._log_timer.timeout.connect(self._flush_logs)
        self._log_timer.start()

    def _queue_progress(self, pct: int, msg: str):
     self._pending_progress = (pct, msg)


    def _flush_logs(self):
    if self._pending_progress is not None:
        pct, msg = self._pending_progress
        self.progress_panel.update_progress(pct, msg)
        self._pending_progress = None

    if not self._pending_logs:
        return

    messages = self._pending_logs
    self._pending_logs.clear()

    for msg in messages:
        self.progress_panel.append_log(msg)

        
    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 12, 16, 12)
        outer.setSpacing(10)

        # Project selector
        proj_row = QHBoxLayout()
        proj_row.setSpacing(8)

        proj_lbl = QLabel("Active Project:")
        proj_lbl.setStyleSheet(
            "font-size: 12px; font-weight: 600;"
            "background: transparent; border: 0px;"
        )

        self.project_combo = QComboBox()
        self.project_combo.setMinimumWidth(240)
        self.project_combo.currentIndexChanged.connect(self._on_project_changed)

        proj_row.addWidget(proj_lbl)
        proj_row.addWidget(self.project_combo)
        proj_row.addStretch()
        outer.addLayout(proj_row)

        # No project state
        self.no_project_state = EmptyState(
            title="No project selected",
            message="Select a project or go to Projects page to create one.",
        )
        outer.addWidget(self.no_project_state)

        # ── Scan mode ──
        self.mode_selector = ScanModeSelector()
        self.mode_selector.mode_changed.connect(self._on_mode_changed)
        self.mode_selector.setVisible(False)
        outer.addWidget(self.mode_selector)

        # ── File import ──
        self.import_panel = FileImportPanel()
        self.import_panel.files_dropped.connect(self._on_files_dropped)
        self.import_panel.setVisible(False)
        outer.addWidget(self.import_panel)

        # ── File list ──
        self.files_group = QGroupBox("Imported Files")
        fg_layout = QVBoxLayout(self.files_group)
        fg_layout.setContentsMargins(10, 14, 10, 10)
        fg_layout.setSpacing(6)

        # File list toolbar
        fl_toolbar = QHBoxLayout()
        self.file_count_lbl = QLabel("0 files")
        self.file_count_lbl.setStyleSheet(
            "font-size: 11px; background: transparent; border: 0px;"
        )

        self.clear_results_btn = QPushButton("Clear Results")
        self.clear_results_btn.setFixedHeight(24)
        self.clear_results_btn.setMinimumWidth(100)
        self.clear_results_btn.clicked.connect(self._on_clear_results)

        self.remove_all_btn = QPushButton("Remove All")
        self.remove_all_btn.setFixedHeight(24)
        self.remove_all_btn.setMinimumWidth(90)
        self.remove_all_btn.clicked.connect(self._on_remove_all)

        fl_toolbar.addWidget(self.file_count_lbl)
        fl_toolbar.addStretch()
        fl_toolbar.addWidget(self.clear_results_btn)
        fl_toolbar.addWidget(self.remove_all_btn)
        fg_layout.addLayout(fl_toolbar)

        self.file_table = FileTable()
        self.file_table.setMinimumHeight(140)
        self.file_table.remove_file.connect(self._on_remove_file)
        fg_layout.addWidget(self.file_table)

        self.files_group.setVisible(False)
        outer.addWidget(self.files_group, 1)

        # ── Progress ──
        self.progress_panel = ProgressPanel()
        self.progress_panel.cancel_clicked.connect(self._on_cancel)
        outer.addWidget(self.progress_panel)

        # ── Action bar ──
        self.action_bar = QFrame()
        act_layout = QHBoxLayout(self.action_bar)
        act_layout.setContentsMargins(0, 0, 0, 0)
        act_layout.setSpacing(8)

        self.status_hint_lbl = QLabel("")
        self.status_hint_lbl.setStyleSheet(
            "font-size: 11px; background: transparent; border: 0px;"
        )

        self.run_btn = QPushButton("Find Duplicates")
        self.run_btn.setProperty("class", "accent")
        self.run_btn.setMinimumWidth(140)
        self.run_btn.setMinimumHeight(30)
        self.run_btn.clicked.connect(self._on_run)

        act_layout.addWidget(self.status_hint_lbl, 1)
        act_layout.addWidget(self.run_btn)

        self.action_bar.setVisible(False)
        outer.addWidget(self.action_bar)

        self.apply_theme()

    def refresh(self):
        try:
            projects = get_all_projects()
            self._load_project_list(projects)
            if self._project_id:
                self._load_files()
        except Exception as e:
            print(f"Analysis refresh error: {e}")

    def _load_project_list(self, projects):
        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        if not projects:
            self.project_combo.addItem("No projects — create one first", -1)
        else:
            for p in projects:
                label = f"{p['name']}  ({p['file_count']} files)"
                self.project_combo.addItem(label, p["id"])
            if self._project_id:
                for i in range(self.project_combo.count()):
                    if self.project_combo.itemData(i) == self._project_id:
                        self.project_combo.setCurrentIndex(i)
                        break
        self.project_combo.blockSignals(False)

    def _on_project_changed(self, index):
        pid = self.project_combo.currentData()
        if pid and pid != -1:
            self.set_project(pid)

    def set_project(self, project_id: int):
        if project_id == self._project_id:
            return
        self._project_id = project_id
        self._project_data = get_project(project_id)
        if not self._project_data:
            return

        self.no_project_state.setVisible(False)
        self.mode_selector.setVisible(True)
        self.import_panel.setVisible(True)
        self.files_group.setVisible(True)
        self.action_bar.setVisible(True)
        self._load_files()
        self._update_run_hint()

    def _load_files(self):
        if not self._project_id:
            return
        try:
            self._files = get_files_for_project(self._project_id)
            self._render_files()
        except Exception as e:
            print(f"Load files error: {e}")

    def _render_files(self):
        count = len(self._files)
        self.file_count_lbl.setText(
            f"{count} file{'s' if count != 1 else ''} imported"
        )
        self.file_table.load_files(self._files)
        self._update_run_hint()

    def _update_run_hint(self):
        count = len(self._files)
        if count == 0:
            self.status_hint_lbl.setText("Import files to begin analysis.")
            self.run_btn.setEnabled(False)
        elif self._scan_mode == "single" and count == 1:
            self.status_hint_lbl.setText("Ready to find duplicates within this file.")
            self.run_btn.setEnabled(True)
        elif self._scan_mode == "single" and count > 1:
            self.status_hint_lbl.setText(
                f"Single mode: only first file will be scanned. "
                f"Switch to Multiple mode to compare all {count} files."
            )
            self.run_btn.setEnabled(True)
        elif self._scan_mode == "multiple" and count < 2:
            self.status_hint_lbl.setText(
                "Multiple mode needs at least 2 files. Import more or switch to Single mode."
            )
            self.run_btn.setEnabled(False)
        else:
            self.status_hint_lbl.setText(
                f"Ready to compare {count} files."
            )
            self.run_btn.setEnabled(True)

    def _on_mode_changed(self, mode: str):
        self._scan_mode = mode
        self.import_panel.set_mode(mode)
        self._update_run_hint()

    def _on_files_dropped(self, paths: list):
        if not self._project_id:
            QMessageBox.warning(self, "No Project", "Select a project first.")
            return

        # Single mode: replace all files with the new one
        if self._scan_mode == "single":
            if len(paths) > 1:
                paths = [paths[0]]
            # Clear existing files first
            for f in self._files:
                remove_file_from_project(f["id"])

        storage_mode = (
            self._project_data.get("storage_mode", "reference")
            if self._project_data else "reference"
        )

        try:
            added = add_files_to_project(
                self._project_id, paths, storage_mode
            )
            self._load_files()
            self._project_data = get_project(self._project_id)
            self.status_message.emit(f"Added {len(added)} file(s)")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add files:\n{e}")

    def _on_remove_file(self, file_id: int):
        reply = QMessageBox.question(
            self, "Remove File", "Remove this file from the project?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            remove_file_from_project(file_id)
            self._load_files()
            self._project_data = get_project(self._project_id)

    def _on_remove_all(self):
        if not self._files:
            return
        reply = QMessageBox.question(
            self, "Remove All",
            f"Remove all {len(self._files)} files?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            for f in self._files:
                remove_file_from_project(f["id"])
            self._load_files()
            self._project_data = get_project(self._project_id)

    def _on_clear_results(self):
        if not self._project_id:
            return
        reply = QMessageBox.question(
            self, "Clear Results",
            "Clear all analysis results?\n\nFiles will remain but results deleted.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            clear_project_results(self._project_id)
            self._load_files()
            self.status_message.emit("Results cleared")

    def _on_run(self):
        if not self._project_id or not self._files:
            return

        threshold = (
            self._project_data.get("similarity_threshold", 0.70)
            if self._project_data else 0.70
        )

        self._worker = AnalysisWorker(
            project_id=self._project_id,
            text_threshold=threshold,
            image_threshold=0.85,
        )
        self._worker.progress_changed.connect(self._queue_progress)
        self._worker.stage_changed.connect(self.progress_panel.update_stage)
        self._worker.log_message.connect(self._queue_log_message)
        # self._worker
        self._worker.finished_ok.connect(self._on_finished_ok)
        self._worker.finished_error.connect(self._on_finished_error)

        self.run_btn.setEnabled(False)
        self.run_btn.setText("Running...")
        self.progress_panel.start()
        self.status_message.emit("Analysis running...")
        self._worker.start()
        self._load_files()

    def _on_cancel(self):
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self.run_btn.setEnabled(True)
            self.run_btn.setText("Find Duplicates")
            self.progress_panel.stop()

    def _on_finished_ok(self, files_done, text_found, img_found):
        self.run_btn.setEnabled(True)
        self.run_btn.setText("Find Duplicates")
        self.progress_panel.stop()
        self._project_data = get_project(self._project_id)
        self._load_files()

        self.status_message.emit(
            f"Done - {text_found} text, {img_found} image matches"
        )
        self.analysis_complete.emit(self._project_id, text_found, img_found)

        QMessageBox.information(
            self, "Analysis Complete",
            f"Analysis finished!\n\n"
            f"Files processed: {files_done}\n"
            f"Text matches:    {text_found}\n"
            f"Image matches:   {img_found}\n\n"
            f"Opening Results...",
        )

    def _on_finished_error(self, error: str):
        self.run_btn.setEnabled(True)
        self.run_btn.setText("Find Duplicates")
        self.progress_panel.stop()
        QMessageBox.critical(self, "Error", f"Analysis failed:\n{error}")

    def apply_theme(self):
        c = ThemeManager.colors()
        self.setStyleSheet(f"background-color: {c['bg_primary']};")
       
    def _queue_log_message(self, msg: str):
    
       self._pending_logs.append(msg)