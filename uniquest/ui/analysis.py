import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame,
    QScrollArea, QProgressBar,
    QFileDialog, QMessageBox,
    QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView,
    QSizePolicy, QSplitter,
    QTextEdit, QComboBox,
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QTimer, QThread,
)
from PyQt6.QtGui import QColor, QFont, QIcon

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
#  FILE TYPE ICON MAP
# ─────────────────────────────────────────────
FILE_ICONS = {
    "pdf":  "📕",
    "docx": "📘", "doc": "📘",
    "txt":  "📄", "rtf": "📄",
    "xlsx": "📗", "xls": "📗", "csv": "📊",
    "pptx": "📙", "ppt": "📙",
    "jpg":  "🖼️", "jpeg": "🖼️",
    "png":  "🖼️", "bmp": "🖼️",
    "tiff": "🖼️", "tif": "🖼️",
    "webp": "🖼️", "gif": "🖼️",
    "svg":  "🖼️",
}

STATUS_ICONS = {
    "pending":    "⏳",
    "processing": "⚙️",
    "done":       "✅",
    "error":      "❌",
}


# ─────────────────────────────────────────────
#  DROP ZONE
# ─────────────────────────────────────────────
class DropZone(QFrame):
    """
    Drag-and-drop zone for importing files.
    Also has a browse button.
    """

    files_dropped = pyqtSignal(list)   # list of file paths

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFixedHeight(160)
        self._build()
        ThemeManager.add_listener(self.apply_theme)
        self.apply_theme()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)

        self.icon_lbl = QLabel("📂")
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_lbl.setStyleSheet(
            "font-size: 36px; background: transparent;"
        )

        self.main_lbl = QLabel(
            "Drag & Drop files here"
        )
        self.main_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_lbl.setStyleSheet(
            "font-size: 14px; font-weight: 600;"
            "background: transparent;"
        )

        self.sub_lbl = QLabel(
            "PDF, DOCX, XLSX, CSV, PPTX, JPG, PNG and more"
        )
        self.sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sub_lbl.setStyleSheet(
            "font-size: 12px; background: transparent;"
        )

        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_row.setSpacing(10)

        self.browse_btn = QPushButton("📁  Browse Files")
        self.browse_btn.setFixedHeight(34)
        self.browse_btn.setFixedWidth(150)
        self.browse_btn.clicked.connect(self._on_browse_files)

        self.browse_folder_btn = QPushButton("📂  Browse Folder")
        self.browse_folder_btn.setProperty("class", "ghost")
        self.browse_folder_btn.setFixedHeight(34)
        self.browse_folder_btn.setFixedWidth(160)
        self.browse_folder_btn.clicked.connect(
            self._on_browse_folder
        )

        btn_row.addWidget(self.browse_btn)
        btn_row.addWidget(self.browse_folder_btn)

        layout.addWidget(self.icon_lbl)
        layout.addWidget(self.main_lbl)
        layout.addWidget(self.sub_lbl)
        layout.addLayout(btn_row)

    def _on_browse_files(self):
        ext_list = " ".join(
            f"*.{e}" for e in SUPPORTED_EXTENSIONS
        )
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Files",
            str(Path.home()),
            f"Supported Files ({ext_list});;All Files (*)",
        )
        if paths:
            self.files_dropped.emit(paths)

    def _on_browse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Folder",
            str(Path.home()),
        )
        if folder:
            # Collect all supported files in folder
            found = []
            for root, dirs, files in os.walk(folder):
                for fname in files:
                    ext = fname.rsplit(".", 1)[-1].lower()
                    if ext in SUPPORTED_EXTENSIONS:
                        found.append(
                            os.path.join(root, fname)
                        )
            if found:
                self.files_dropped.emit(found)
            else:
                QMessageBox.information(
                    self,
                    "No Files Found",
                    "No supported files were found in "
                    "the selected folder.",
                )

    # ── Drag & Drop ──
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._set_drag_active(True)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self._set_drag_active(False)

    def dropEvent(self, event):
        self._set_drag_active(False)
        urls  = event.mimeData().urls()
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
                            paths.append(
                                os.path.join(root, fname)
                            )
        if paths:
            self.files_dropped.emit(paths)
        elif urls:
            QMessageBox.information(
                self,
                "Unsupported Files",
                "None of the dropped files are supported.\n\n"
                "Supported: PDF, DOCX, XLSX, CSV, "
                "PPTX, JPG, PNG, and more.",
            )

    def _set_drag_active(self, active: bool):
        c = ThemeManager.colors()
        if active:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {c['accent']}18;
                    border: 2px dashed {c['accent']};
                    border-radius: 10px;
                }}
            """)
        else:
            self.apply_theme()

    def apply_theme(self):
        c = ThemeManager.colors()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {c['bg_card']};
                border: 2px dashed {c['border']};
                border-radius: 10px;
            }}
            QFrame:hover {{
                border-color: {c['accent']};
                background-color: {c['bg_hover']};
            }}
        """)
        self.main_lbl.setStyleSheet(
            f"font-size: 14px; font-weight: 600;"
            f"color: {c['text_primary']}; background: transparent;"
        )
        self.sub_lbl.setStyleSheet(
            f"font-size: 12px; color: {c['text_muted']};"
            f"background: transparent;"
        )


# ─────────────────────────────────────────────
#  PROGRESS PANEL
# ─────────────────────────────────────────────
class ProgressPanel(QFrame):
    """Shows analysis progress"""

    cancel_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "card")
        self.setVisible(False)
        self._build()
        ThemeManager.add_listener(self.apply_theme)

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        # Header row
        header = QHBoxLayout()

        self.stage_lbl = QLabel("🔍 Analyzing...")
        self.stage_lbl.setStyleSheet(
            "font-size: 14px; font-weight: 700;"
            "background: transparent;"
        )

        self.cancel_btn = QPushButton("✕ Cancel")
        self.cancel_btn.setProperty("class", "danger")
        self.cancel_btn.setFixedHeight(28)
        self.cancel_btn.setFixedWidth(90)
        self.cancel_btn.clicked.connect(self.cancel_clicked)

        header.addWidget(self.stage_lbl)
        header.addStretch()
        header.addWidget(self.cancel_btn)
        layout.addLayout(header)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(8)
        layout.addWidget(self.progress_bar)

        # Message
        self.msg_lbl = QLabel("Starting...")
        self.msg_lbl.setStyleSheet(
            "font-size: 12px; background: transparent;"
        )
        layout.addWidget(self.msg_lbl)

        # Log box
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setFixedHeight(120)
        self.log_box.setStyleSheet(
            "font-family: 'Consolas', monospace; font-size: 11px;"
        )
        layout.addWidget(self.log_box)

        self.apply_theme()

    def start(self):
        self.setVisible(True)
        self.progress_bar.setValue(0)
        self.log_box.clear()
        self.msg_lbl.setText("Starting analysis...")
        self.stage_lbl.setText("🔍 Analyzing...")
        self.cancel_btn.setEnabled(True)

    def stop(self):
        self.cancel_btn.setEnabled(False)

    def update_progress(self, pct: int, msg: str):
        self.progress_bar.setValue(pct)
        self.msg_lbl.setText(msg)

    def update_stage(self, stage: str):
        self.stage_lbl.setText(f"🔍 {stage}")

    def append_log(self, msg: str):
        self.log_box.append(msg)
        # Auto scroll to bottom
        sb = self.log_box.verticalScrollBar()
        sb.setValue(sb.maximum())

    def apply_theme(self):
        c = ThemeManager.colors()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {c['bg_card']};
                border: 1px solid {c['border']};
                border-radius: 10px;
            }}
        """)
        self.stage_lbl.setStyleSheet(
            f"font-size: 14px; font-weight: 700;"
            f"color: {c['text_primary']}; background: transparent;"
        )
        self.msg_lbl.setStyleSheet(
            f"font-size: 12px; color: {c['text_muted']};"
            f"background: transparent;"
        )
        self.log_box.setStyleSheet(f"""
            QTextEdit {{
                background-color: {c['bg_input']};
                color: {c['text_secondary']};
                border: 1px solid {c['border']};
                border-radius: 6px;
                font-family: 'Consolas', monospace;
                font-size: 11px;
            }}
        """)


# ─────────────────────────────────────────────
#  FILE TABLE
# ─────────────────────────────────────────────
class FileTable(QTableWidget):
    """Table showing files in current project"""

    remove_file = pyqtSignal(int)   # file_id

    COLUMNS = ["", "File Name", "Type", "Size", "Status", "Chunks", "Images", ""]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._file_ids: list = []
        self._setup()
        ThemeManager.add_listener(self.apply_theme)

    def _setup(self):
        self.setColumnCount(len(self.COLUMNS))
        self.setHorizontalHeaderLabels(self.COLUMNS)
        self.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.setAlternatingRowColors(False)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(False)

        hdr = self.horizontalHeader()
        hdr.setSectionResizeMode(
            0, QHeaderView.ResizeMode.Fixed
        )          # icon
        hdr.setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )         # name
        hdr.setSectionResizeMode(
            2, QHeaderView.ResizeMode.Fixed
        )          # type
        hdr.setSectionResizeMode(
            3, QHeaderView.ResizeMode.Fixed
        )          # size
        hdr.setSectionResizeMode(
            4, QHeaderView.ResizeMode.Fixed
        )          # status
        hdr.setSectionResizeMode(
            5, QHeaderView.ResizeMode.Fixed
        )          # chunks
        hdr.setSectionResizeMode(
            6, QHeaderView.ResizeMode.Fixed
        )          # images
        hdr.setSectionResizeMode(
            7, QHeaderView.ResizeMode.Fixed
        )          # delete btn

        self.setColumnWidth(0, 34)
        self.setColumnWidth(2, 60)
        self.setColumnWidth(3, 80)
        self.setColumnWidth(4, 90)
        self.setColumnWidth(5, 70)
        self.setColumnWidth(6, 70)
        self.setColumnWidth(7, 36)
        self.setRowHeight(0, 40)

        self.apply_theme()

    def load_files(self, files: list):
        """Populate table with file data"""
        self._file_ids = []
        self.setRowCount(0)

        for f in files:
            row = self.rowCount()
            self.insertRow(row)
            self.setRowHeight(row, 40)

            fid  = f["id"]
            ext  = f.get("file_type", "").lower()
            icon = FILE_ICONS.get(ext, "📄")
            self._file_ids.append(fid)

            # Col 0: icon
            icon_item = QTableWidgetItem(icon)
            icon_item.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter
            )
            self.setItem(row, 0, icon_item)

            # Col 1: name
            name_item = QTableWidgetItem(
                f.get("file_name", "")
            )
            name_item.setToolTip(
                f.get("original_path", "")
            )
            self.setItem(row, 1, name_item)

            # Col 2: type
            type_item = QTableWidgetItem(
                ext.upper()
            )
            type_item.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter
            )
            self.setItem(row, 2, type_item)

            # Col 3: size
            size_bytes = f.get("file_size", 0)
            size_str   = self._fmt_size(size_bytes)
            size_item  = QTableWidgetItem(size_str)
            size_item.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter
            )
            self.setItem(row, 3, size_item)

            # Col 4: status
            status     = f.get("status", "pending")
            status_ico = STATUS_ICONS.get(status, "⏳")
            status_item = QTableWidgetItem(
                f"{status_ico} {status.capitalize()}"
            )
            status_item.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter
            )
            color = {
                "pending":    "#5c6bc0",
                "processing": "#ff9800",
                "done":       "#4caf50",
                "error":      "#f44336",
            }.get(status, "#5c6bc0")
            status_item.setForeground(QColor(color))
            self.setItem(row, 4, status_item)

            # Col 5: text chunks
            tc_item = QTableWidgetItem(
                str(f.get("text_extracted", 0))
            )
            tc_item.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter
            )
            self.setItem(row, 5, tc_item)

            # Col 6: images
            ic_item = QTableWidgetItem(
                str(f.get("images_extracted", 0))
            )
            ic_item.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter
            )
            self.setItem(row, 6, ic_item)

            # Col 7: remove button
            del_btn = QPushButton("✕")
            del_btn.setFixedSize(26, 26)
            del_btn.setProperty("class", "danger")
            del_btn.setToolTip("Remove file from project")
            del_btn.clicked.connect(
                lambda _, fid=fid: self.remove_file.emit(fid)
            )
            self.setCellWidget(row, 7, del_btn)

    def _fmt_size(self, size: int) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.0f} {unit}"
            size /= 1024
        return f"{size:.1f} GB"

    def apply_theme(self):
        c = ThemeManager.colors()
        self.setStyleSheet(f"""
            QTableWidget {{
                background-color: {c['bg_card']};
                color: {c['text_primary']};
                border: 1px solid {c['border']};
                border-radius: 8px;
                gridline-color: transparent;
                selection-background-color: {c['bg_selected']};
            }}
            QTableWidget::item {{
                padding: 6px;
                border-bottom: 1px solid {c['border_light']};
            }}
            QTableWidget::item:selected {{
                background-color: {c['bg_selected']};
            }}
            QHeaderView::section {{
                background-color: {c['bg_input']};
                color: {c['text_secondary']};
                font-weight: 600;
                font-size: 11px;
                padding: 6px;
                border: none;
                border-bottom: 1px solid {c['border']};
            }}
        """)


# ─────────────────────────────────────────────
#  PROJECT SELECTOR BAR
# ─────────────────────────────────────────────
class ProjectSelectorBar(QFrame):
    """Top bar showing selected project with switcher"""

    project_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(56)
        self._build()
        ThemeManager.add_listener(self.apply_theme)

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(28, 0, 28, 0)
        layout.setSpacing(14)

        lbl = QLabel("Active Project:")
        lbl.setStyleSheet(
            "font-size: 12px; font-weight: 600;"
            "background: transparent;"
        )

        self.project_combo = QComboBox()
        self.project_combo.setFixedHeight(34)
        self.project_combo.setMinimumWidth(280)
        self.project_combo.currentIndexChanged.connect(
            self._on_changed
        )

        layout.addWidget(lbl)
        layout.addWidget(self.project_combo)
        layout.addStretch()

        self.apply_theme()

    def load_projects(self, projects: list, selected_id: int = None):
        self.project_combo.blockSignals(True)
        self.project_combo.clear()

        if not projects:
            self.project_combo.addItem(
                "No projects — create one first", -1
            )
            self.project_combo.blockSignals(False)
            return

        for p in projects:
            self.project_combo.addItem(
                f"📁  {p['name']}  ({p['file_count']} files)",
                p["id"],
            )

        # Select the active project
        if selected_id:
            for i in range(self.project_combo.count()):
                if self.project_combo.itemData(i) == selected_id:
                    self.project_combo.setCurrentIndex(i)
                    break

        self.project_combo.blockSignals(False)

    def current_project_id(self) -> int:
        return self.project_combo.currentData() or -1

    def _on_changed(self, index: int):
        pid = self.project_combo.currentData()
        if pid and pid != -1:
            self.project_changed.emit(pid)

    def apply_theme(self):
        c = ThemeManager.colors()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {c['bg_secondary']};
                border-bottom: 1px solid {c['border']};
            }}
        """)


# ─────────────────────────────────────────────
#  ANALYSIS PAGE
# ─────────────────────────────────────────────
class AnalysisPage(QWidget):
    """
    Page 2 — Analysis
    Import files, manage project files, run analysis.
    """

    analysis_complete = pyqtSignal(int, int, int)  # pid, text, img
    status_message    = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._project_id: int      = None
        self._project_data: dict   = None
        self._worker: AnalysisWorker = None
        self._files: list          = []
        self._build()
        ThemeManager.add_listener(self.apply_theme)

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Project selector ──
        self.selector = ProjectSelectorBar()
        self.selector.project_changed.connect(
            self.set_project
        )
        outer.addWidget(self.selector)

        # ── Scroll content ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        content = QWidget()
        self.main_layout = QVBoxLayout(content)
        self.main_layout.setContentsMargins(28, 20, 28, 28)
        self.main_layout.setSpacing(18)

        # No project selected state
        self.no_project_state = EmptyState(
            icon    = "📁",
            title   = "No project selected",
            message = (
                "Select a project from the dropdown above, "
                "or go to Projects to create one."
            ),
        )
        self.no_project_state.setVisible(True)
        self.main_layout.addWidget(self.no_project_state)

        # ── Project info ──
        self.info_frame = QFrame()
        self.info_frame.setVisible(False)
        self._build_info_frame()
        self.main_layout.addWidget(self.info_frame)

        # ── Drop zone ──
        self.drop_zone = DropZone()
        self.drop_zone.files_dropped.connect(self._on_files_dropped)
        self.drop_zone.setVisible(False)
        self.main_layout.addWidget(self.drop_zone)

        # ── Action bar ──
        self.action_bar = QFrame()
        self.action_bar.setVisible(False)
        self._build_action_bar()
        self.main_layout.addWidget(self.action_bar)

        # ── Progress panel ──
        self.progress_panel = ProgressPanel()
        self.progress_panel.cancel_clicked.connect(
            self._on_cancel
        )
        self.main_layout.addWidget(self.progress_panel)

        # ── File table ──
        self.file_table_frame = QFrame()
        self.file_table_frame.setVisible(False)
        self._build_file_table()
        self.main_layout.addWidget(self.file_table_frame, 1)

        # Empty file state
        self.empty_files = EmptyState(
            icon    = "📂",
            title   = "No files imported yet",
            message = (
                "Drag and drop files above, or use "
                "Browse to add files to this project."
            ),
        )
        self.empty_files.setVisible(False)
        self.main_layout.addWidget(self.empty_files)

        self.main_layout.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

        self.apply_theme()

    def _build_info_frame(self):
        layout = QHBoxLayout(self.info_frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        # Project name
        name_col = QVBoxLayout()
        name_col.setSpacing(2)

        self.proj_name_lbl = QLabel("Project Name")
        self.proj_name_lbl.setStyleSheet(
            "font-size: 16px; font-weight: 700;"
            "background: transparent;"
        )

        self.proj_meta_lbl = QLabel("")
        self.proj_meta_lbl.setStyleSheet(
            "font-size: 12px; background: transparent;"
        )

        name_col.addWidget(self.proj_name_lbl)
        name_col.addWidget(self.proj_meta_lbl)
        layout.addLayout(name_col, 1)

        # Stats chips
        stats_row = QHBoxLayout()
        stats_row.setSpacing(10)

        self.chip_files = self._make_chip("📄", "0 files")
        self.chip_threshold = self._make_chip("🎯", "70% threshold")
        self.chip_status = self._make_chip("📊", "Idle")

        stats_row.addWidget(self.chip_files)
        stats_row.addWidget(self.chip_threshold)
        stats_row.addWidget(self.chip_status)
        layout.addLayout(stats_row)

    def _make_chip(self, icon: str, text: str) -> QLabel:
        lbl = QLabel(f"{icon}  {text}")
        lbl.setStyleSheet("""
            QLabel {
                background-color: #1e3a5f;
                color: #9aa5c4;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 12px;
            }
        """)
        return lbl

    def _build_action_bar(self):
        layout = QHBoxLayout(self.action_bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.file_count_lbl = QLabel("0 files")
        self.file_count_lbl.setStyleSheet(
            "font-size: 13px; background: transparent;"
        )

        layout.addWidget(self.file_count_lbl)
        layout.addStretch()

        self.clear_results_btn = QPushButton("🗑️ Clear Results")
        self.clear_results_btn.setProperty("class", "ghost")
        self.clear_results_btn.setFixedHeight(34)
        self.clear_results_btn.clicked.connect(
            self._on_clear_results
        )

        self.remove_all_btn = QPushButton("✕ Remove All Files")
        self.remove_all_btn.setProperty("class", "ghost")
        self.remove_all_btn.setFixedHeight(34)
        self.remove_all_btn.clicked.connect(
            self._on_remove_all
        )

        self.run_btn = QPushButton("▶  Run Analysis")
        self.run_btn.setFixedHeight(36)
        self.run_btn.setFixedWidth(160)
        self.run_btn.clicked.connect(self._on_run)

        layout.addWidget(self.clear_results_btn)
        layout.addWidget(self.remove_all_btn)
        layout.addWidget(self.run_btn)

    def _build_file_table(self):
        layout = QVBoxLayout(self.file_table_frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        hdr = QHBoxLayout()
        sec_lbl = QLabel("IMPORTED FILES")
        sec_lbl.setStyleSheet(
            "font-size: 10px; font-weight: 700;"
            "letter-spacing: 1.5px; background: transparent;"
        )
        hdr.addWidget(sec_lbl)
        hdr.addStretch()

        self.refresh_btn = QPushButton("↻ Refresh")
        self.refresh_btn.setProperty("class", "ghost")
        self.refresh_btn.setFixedHeight(28)
        self.refresh_btn.clicked.connect(self._load_files)
        hdr.addWidget(self.refresh_btn)
        layout.addLayout(hdr)

        self.file_table = FileTable()
        self.file_table.setMinimumHeight(200)
        self.file_table.remove_file.connect(
            self._on_remove_file
        )
        layout.addWidget(self.file_table)

    # ─────────────────────────────────────────
    #  PROJECT LOADING
    # ─────────────────────────────────────────
    def refresh(self):
        """Reload project list in selector"""
        from core.processor import get_all_projects
        projects = get_all_projects()
        self.selector.load_projects(
            projects, self._project_id
        )
        if self._project_id:
            self._load_files()

    def set_project(self, project_id: int):
        """Set active project"""
        if project_id == self._project_id:
            return

        self._project_id   = project_id
        self._project_data = get_project(project_id)

        if not self._project_data:
            return

        # Update UI
        self.no_project_state.setVisible(False)
        self.info_frame.setVisible(True)
        self.drop_zone.setVisible(True)
        self.action_bar.setVisible(True)

        self._update_info()
        self._load_files()

    def _update_info(self):
        if not self._project_data:
            return
        p = self._project_data

        self.proj_name_lbl.setText(p.get("name", ""))
        desc = p.get("description", "") or "No description"
        self.proj_meta_lbl.setText(desc)

        self.chip_files.setText(
            f"📄  {p.get('file_count', 0)} files"
        )
        pct = int(p.get("similarity_threshold", 0.70) * 100)
        self.chip_threshold.setText(
            f"🎯  {pct}% threshold"
        )
        status = p.get("status", "idle").capitalize()
        self.chip_status.setText(f"📊  {status}")

    def _load_files(self):
        if not self._project_id:
            return
        try:
            self._files = get_files_for_project(
                self._project_id
            )
            self._render_files()
        except Exception as e:
            print(f"Load files error: {e}")

    def _render_files(self):
        count = len(self._files)
        self.file_count_lbl.setText(
            f"{count} file{'s' if count != 1 else ''} imported"
        )

        if count == 0:
            self.file_table_frame.setVisible(False)
            self.empty_files.setVisible(True)
        else:
            self.empty_files.setVisible(False)
            self.file_table_frame.setVisible(True)
            self.file_table.load_files(self._files)

    # ─────────────────────────────────────────
    #  FILE ACTIONS
    # ─────────────────────────────────────────
    def _on_files_dropped(self, paths: list):
        if not self._project_id:
            QMessageBox.warning(
                self, "No Project",
                "Please select or create a project first."
            )
            return

        storage_mode = (
            self._project_data.get("storage_mode", "reference")
            if self._project_data else "reference"
        )

        self.status_message.emit(
            f"Adding {len(paths)} file(s)..."
        )

        try:
            added = add_files_to_project(
                self._project_id, paths, storage_mode
            )
            self._load_files()
            self._project_data = get_project(self._project_id)
            self._update_info()
            self.status_message.emit(
                f"✅ Added {len(added)} file(s) to project"
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Error",
                f"Failed to add files:\n{e}"
            )

    def _on_remove_file(self, file_id: int):
        reply = QMessageBox.question(
            self,
            "Remove File",
            "Remove this file from the project?\n\n"
            "Analysis results for this file will also be removed.",
            QMessageBox.StandardButton.Yes |
            QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            remove_file_from_project(file_id)
            self._load_files()
            self._project_data = get_project(self._project_id)
            self._update_info()

    def _on_remove_all(self):
        if not self._files:
            return
        reply = QMessageBox.question(
            self,
            "Remove All Files",
            f"Remove all {len(self._files)} files from project?\n\n"
            "This will also clear all analysis results.",
            QMessageBox.StandardButton.Yes |
            QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            for f in self._files:
                remove_file_from_project(f["id"])
            self._load_files()
            self._project_data = get_project(self._project_id)
            self._update_info()

    def _on_clear_results(self):
        if not self._project_id:
            return
        reply = QMessageBox.question(
            self,
            "Clear Results",
            "Clear all analysis results for this project?\n\n"
            "Files will remain but results will be deleted.\n"
            "You can re-run the analysis after clearing.",
            QMessageBox.StandardButton.Yes |
            QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            clear_project_results(self._project_id)
            self._load_files()
            self.status_message.emit(
                "🗑️ Results cleared — ready to re-run analysis"
            )

    # ─────────────────────────────────────────
    #  ANALYSIS RUNNER
    # ─────────────────────────────────────────
    def _on_run(self):
        if not self._project_id:
            QMessageBox.warning(
                self, "No Project",
                "Please select a project first."
            )
            return

        if not self._files:
            QMessageBox.warning(
                self, "No Files",
                "Please add files to the project before "
                "running analysis."
            )
            return

        # Confirm re-run if already done
        if self._project_data:
            status = self._project_data.get("status", "idle")
            if status == "done":
                reply = QMessageBox.question(
                    self,
                    "Re-run Analysis",
                    "This project has already been analyzed.\n\n"
                    "Re-running will replace the existing results.\n"
                    "Continue?",
                    QMessageBox.StandardButton.Yes |
                    QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return

        threshold = (
            self._project_data.get("similarity_threshold", 0.70)
            if self._project_data else 0.70
        )

        # Start worker
        self._worker = AnalysisWorker(
            project_id       = self._project_id,
            text_threshold   = threshold,
            image_threshold  = 0.85,
        )

        self._worker.progress_changed.connect(
            self.progress_panel.update_progress
        )
        self._worker.stage_changed.connect(
            self.progress_panel.update_stage
        )
        self._worker.log_message.connect(
            self.progress_panel.append_log
        )
        self._worker.file_processed.connect(
            self._on_file_processed
        )
        self._worker.finished_ok.connect(
            self._on_finished_ok
        )
        self._worker.finished_error.connect(
            self._on_finished_error
        )

        # Update UI state
        self.run_btn.setEnabled(False)
        self.run_btn.setText("⏳ Running...")
        self.progress_panel.start()
        self.status_message.emit("🔍 Analysis running...")

        self._worker.start()

    def _on_cancel(self):
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self.run_btn.setEnabled(True)
            self.run_btn.setText("▶  Run Analysis")
            self.progress_panel.stop()
            self.status_message.emit("⚠️ Analysis cancelled")

    def _on_file_processed(self, file_name: str, success: bool):
        """Update file status in table as files complete"""
        self._load_files()

    def _on_finished_ok(
        self,
        files_done: int,
        text_found: int,
        img_found: int,
    ):
        self.run_btn.setEnabled(True)
        self.run_btn.setText("▶  Run Analysis")
        self.progress_panel.stop()

        self._project_data = get_project(self._project_id)
        self._update_info()
        self._load_files()

        self.status_message.emit(
            f"✅ Done — {text_found} text, "
            f"{img_found} image matches"
        )
        self.analysis_complete.emit(
            self._project_id, text_found, img_found
        )

        QMessageBox.information(
            self,
            "✅ Analysis Complete",
            f"Analysis finished successfully!\n\n"
            f"📄 Files processed:   {files_done}\n"
            f"📝 Text matches:      {text_found}\n"
            f"🖼️ Image matches:     {img_found}\n\n"
            f"Switching to Results page...",
        )

    def _on_finished_error(self, error: str):
        self.run_btn.setEnabled(True)
        self.run_btn.setText("▶  Run Analysis")
        self.progress_panel.stop()
        self.status_message.emit(f"❌ Error: {error}")

        QMessageBox.critical(
            self, "Analysis Error",
            f"Analysis failed:\n\n{error}"
        )

    def apply_theme(self):
        c = ThemeManager.colors()
        self.setStyleSheet(
            f"background-color: {c['bg_primary']};"
        )
        self.file_count_lbl.setStyleSheet(
            f"font-size: 13px; color: {c['text_secondary']};"
            f"background: transparent;"
        )