from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem,
    QGroupBox, QComboBox, QTextEdit, QSplitter,
    QScrollArea, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QPixmap

from database.db import (
    get_text_similarities, get_image_similarities,
    get_all_projects, mark_similarity_reviewed, get_setting
)
from utils.exporter import show_export_dialog


class ResultsPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window    = main_window
        self._text_pairs    = []
        self._image_pairs   = []
        self._current_pairs = []
        self._current_idx   = 0
        self._build_ui()

    def on_show(self):
        self._refresh_projects()

    # ─────────────────────────────────────────────────────────
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # top controls
        ctrl_group  = QGroupBox("Filter & Navigation")
        ctrl_layout = QHBoxLayout(ctrl_group)

        self._proj_combo = QComboBox()
        self._proj_combo.setMinimumWidth(200)
        self._proj_combo.currentIndexChanged.connect(self._load_results)

        self._type_combo = QComboBox()
        self._type_combo.addItems(["All", "Text Only", "Images Only"])
        self._type_combo.currentIndexChanged.connect(self._apply_filter)

        self._filter_combo = QComboBox()
        self._filter_combo.addItems(["All", "Unreviewed Only", "Reviewed Only"])
        self._filter_combo.currentIndexChanged.connect(self._apply_filter)

        btn_export = QPushButton("Export Results")
        btn_export.setFixedHeight(28)
        btn_export.clicked.connect(self._export)

        ctrl_layout.addWidget(QLabel("Project:"))
        ctrl_layout.addWidget(self._proj_combo)
        ctrl_layout.addWidget(QLabel("Type:"))
        ctrl_layout.addWidget(self._type_combo)
        ctrl_layout.addWidget(QLabel("Filter:"))
        ctrl_layout.addWidget(self._filter_combo)
        ctrl_layout.addStretch()
        ctrl_layout.addWidget(btn_export)
        layout.addWidget(ctrl_group)

        # main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # left: cluster list
        left = QGroupBox("Matches")
        left_layout = QVBoxLayout(left)

        self._count_label = QLabel("0 matches found")
        left_layout.addWidget(self._count_label)

        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._show_pair)
        left_layout.addWidget(self._list)

        splitter.addWidget(left)

        # right: comparison
        right = QGroupBox("Comparison")
        right_layout = QVBoxLayout(right)

        # score label
        self._score_label = QLabel("Select a match to compare")
        self._score_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self._score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self._score_label)

        # pair navigation
        nav_row = QHBoxLayout()
        self._prev_btn = QPushButton("Previous")
        self._next_btn = QPushButton("Next")
        self._pair_label = QLabel("")
        self._pair_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._prev_btn.clicked.connect(self._prev_pair)
        self._next_btn.clicked.connect(self._next_pair)
        nav_row.addWidget(self._prev_btn)
        nav_row.addWidget(self._pair_label, 1)
        nav_row.addWidget(self._next_btn)
        right_layout.addLayout(nav_row)

        # side by side
        compare_row = QHBoxLayout()

        # left panel
        left_panel = QVBoxLayout()
        self._label_a = QLabel("File A")
        self._label_a.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self._text_a  = QTextEdit()
        self._text_a.setReadOnly(True)
        self._img_a   = QLabel()
        self._img_a.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._img_a.setMinimumHeight(200)
        left_panel.addWidget(self._label_a)
        left_panel.addWidget(self._text_a)
        left_panel.addWidget(self._img_a)
        compare_row.addLayout(left_panel)

        # separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        compare_row.addWidget(sep)

        # right panel
        right_panel = QVBoxLayout()
        self._label_b = QLabel("File B")
        self._label_b.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self._text_b  = QTextEdit()
        self._text_b.setReadOnly(True)
        self._img_b   = QLabel()
        self._img_b.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._img_b.setMinimumHeight(200)
        right_panel.addWidget(self._label_b)
        right_panel.addWidget(self._text_b)
        right_panel.addWidget(self._img_b)
        compare_row.addLayout(right_panel)

        right_layout.addLayout(compare_row, 1)

        # mark reviewed
        mark_row = QHBoxLayout()
        self._mark_btn = QPushButton("Mark as Reviewed")
        self._mark_btn.setFixedHeight(28)
        self._mark_btn.clicked.connect(self._mark_reviewed)
        mark_row.addStretch()
        mark_row.addWidget(self._mark_btn)
        right_layout.addLayout(mark_row)

        splitter.addWidget(right)
        splitter.setSizes([350, 700])

        layout.addWidget(splitter, 1)

    # ─────────────────────────────────────────────────────────
    def _refresh_projects(self):
        self._proj_combo.blockSignals(True)
        self._proj_combo.clear()
        projects = get_all_projects()
        if not projects:
            self._proj_combo.addItem("No projects", -1)
        else:
            for p in projects:
                self._proj_combo.addItem(p["name"], p["id"])
        self._proj_combo.blockSignals(False)
        self._load_results()

    def _load_results(self):
        pid = self._proj_combo.currentData()
        if not pid or pid == -1:
            self._text_pairs  = []
            self._image_pairs = []
        else:
            self._text_pairs  = get_text_similarities(pid)
            self._image_pairs = get_image_similarities(pid)
        self._apply_filter()

    def _apply_filter(self):
        type_idx   = self._type_combo.currentIndex()
        filter_idx = self._filter_combo.currentIndex()

        if type_idx == 0:
            pairs = [("text",  r) for r in self._text_pairs] + \
                    [("image", r) for r in self._image_pairs]
        elif type_idx == 1:
            pairs = [("text",  r) for r in self._text_pairs]
        else:
            pairs = [("image", r) for r in self._image_pairs]

        if filter_idx == 1:
            pairs = [(t, r) for t, r in pairs if not r["reviewed"]]
        elif filter_idx == 2:
            pairs = [(t, r) for t, r in pairs if r["reviewed"]]

        # sort by score
        pairs.sort(key=lambda x: x[1]["similarity_score"], reverse=True)

        self._current_pairs = pairs
        self._current_idx   = 0
        self._populate_list()

    def _populate_list(self):
        self._list.clear()
        self._count_label.setText(f"{len(self._current_pairs)} matches found")

        for kind, pair in self._current_pairs:
            score = pair["similarity_score"]
            fa    = pair["file_name_a"]
            fb    = pair["file_name_b"]
            rev   = " [Reviewed]" if pair["reviewed"] else ""

            if kind == "text":
                label = f"[TEXT] {score:.0%} | {fa} vs {fb}{rev}"
            else:
                label = f"[IMG]  {score:.0%} | {fa} vs {fb}{rev}"

            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, (kind, pair["id"]))
            self._list.addItem(item)

        if self._current_pairs:
            self._list.setCurrentRow(0)

    def _show_pair(self, row: int):
        if row < 0 or row >= len(self._current_pairs):
            return

        self._current_idx = row
        self._pair_label.setText(f"{row + 1} / {len(self._current_pairs)}")

        kind, pair = self._current_pairs[row]
        score = pair["similarity_score"]
        self._score_label.setText(f"Similarity Score: {score:.2%}")

        if kind == "text":
            self._show_text_pair(pair)
        else:
            self._show_image_pair(pair)

    def _show_text_pair(self, pair: dict):
        self._text_a.show()
        self._text_b.show()
        self._img_a.hide()
        self._img_b.hide()

        self._label_a.setText(f"{pair['file_name_a']} — Page {pair['page_a']}")
        self._label_b.setText(f"{pair['file_name_b']} — Page {pair['page_b']}")
        self._text_a.setPlainText(pair["content_a"])
        self._text_b.setPlainText(pair["content_b"])

    def _show_image_pair(self, pair: dict):
        self._text_a.hide()
        self._text_b.hide()
        self._img_a.show()
        self._img_b.show()

        self._label_a.setText(f"{pair['file_name_a']}")
        self._label_b.setText(f"{pair['file_name_b']}")

        def load_img(label: QLabel, path: str):
            if path and os.path.exists(path):
                pix = QPixmap(path).scaled(
                    300, 300,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                label.setPixmap(pix)
            else:
                label.setText("Image not found")

        import os
        load_img(self._img_a, pair["path_a"])
        load_img(self._img_b, pair["path_b"])

    def _prev_pair(self):
        if self._current_idx > 0:
            self._list.setCurrentRow(self._current_idx - 1)

    def _next_pair(self):
        if self._current_idx < len(self._current_pairs) - 1:
            self._list.setCurrentRow(self._current_idx + 1)

    def _mark_reviewed(self):
        if not self._current_pairs:
            return
        row = self._current_idx
        if row < 0 or row >= len(self._current_pairs):
            return

        kind, pair = self._current_pairs[row]
        mark_similarity_reviewed(pair["id"], kind)
        self._load_results()

    def _export(self):
        pid = self._proj_combo.currentData()
        if not pid or pid == -1:
            QMessageBox.warning(self, "Export", "Select a project first.")
            return
        project_name = self._proj_combo.currentText()
        default_dir  = get_setting("export_path", str(Path.home() / "Documents"))
        show_export_dialog(self, pid, project_name, default_dir)

from pathlib import Path