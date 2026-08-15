"""
Results page for Uniquest.
Displays text and image similarity matches with side-by-side comparison,
pagination, filtering, and export.
"""

import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem,
    QGroupBox, QComboBox, QTextEdit, QSplitter,
    QFrame, QMessageBox, QSpinBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap

from database.db import get_setting, get_connection
from core.processor import get_all_projects, mark_similarity_reviewed
from utils.exporter import show_export_dialog


PAGE_SIZE = 200   # results per page


class ResultsPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window    = main_window
        self._current_pairs = []
        self._current_idx   = 0
        self._page          = 0
        self._total_pairs   = 0
        self._build_ui()

    def on_show(self):
        self._refresh_projects()

    def load_project(self, project_id: int):
        """Called by MainWindow when navigating to results page."""
        self._refresh_projects()
        for i in range(self._proj_combo.count()):
            if self._proj_combo.itemData(i) == project_id:
                self._proj_combo.setCurrentIndex(i)
                break

    def refresh(self):
        """Public refresh method."""
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
        self._proj_combo.currentIndexChanged.connect(self._reload)

        self._type_combo = QComboBox()
        self._type_combo.addItems(["All", "Text Only", "Images Only"])
        self._type_combo.currentIndexChanged.connect(self._reload)

        self._filter_combo = QComboBox()
        self._filter_combo.addItems(["All", "Unreviewed Only", "Reviewed Only"])
        self._filter_combo.currentIndexChanged.connect(self._reload)

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

        # pagination bar
        page_bar    = QHBoxLayout()
        self._count_label = QLabel("0 matches")
        self._page_label  = QLabel("Page 1")

        btn_first = QPushButton("<<")
        btn_prev  = QPushButton("<")
        btn_next  = QPushButton(">")
        btn_last  = QPushButton(">>")
        for b in (btn_first, btn_prev, btn_next, btn_last):
            b.setFixedWidth(40)

        btn_first.clicked.connect(lambda: self._go_page(0))
        btn_prev.clicked.connect(lambda: self._go_page(self._page - 1))
        btn_next.clicked.connect(lambda: self._go_page(self._page + 1))
        btn_last.clicked.connect(lambda: self._go_page(self._max_page()))

        page_bar.addWidget(self._count_label)
        page_bar.addStretch()
        page_bar.addWidget(btn_first)
        page_bar.addWidget(btn_prev)
        page_bar.addWidget(self._page_label)
        page_bar.addWidget(btn_next)
        page_bar.addWidget(btn_last)
        layout.addLayout(page_bar)

        # main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # left: list
        left = QGroupBox("Matches")
        left_layout = QVBoxLayout(left)
        self._list = QListWidget()
        self._list.setUniformItemSizes(True)
        self._list.currentRowChanged.connect(self._show_pair)
        left_layout.addWidget(self._list)
        splitter.addWidget(left)

        # right: comparison
        right = QGroupBox("Comparison")
        right_layout = QVBoxLayout(right)

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

        # side-by-side
        compare_row = QHBoxLayout()

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

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        compare_row.addWidget(sep)

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
        self._reload()

    # ─────────────────────────────────────────────────────────
    def _reload(self):
        self._page = 0
        self._count_total()
        self._load_page()

    def _get_where_and_params(self, kind: str) -> tuple:
        pid = self._proj_combo.currentData()
        params = [pid]
        where  = "project_id = ?"

        filter_idx = self._filter_combo.currentIndex()
        if filter_idx == 1:
            where += " AND reviewed = 0"
        elif filter_idx == 2:
            where += " AND reviewed = 1"

        return where, params

    def _count_total(self):
        pid = self._proj_combo.currentData()
        if not pid or pid == -1:
            self._total_pairs = 0
            self._count_label.setText("0 matches")
            return

        type_idx = self._type_combo.currentIndex()
        conn = get_connection()
        total = 0
        try:
            where, params = self._get_where_and_params("text")
            if type_idx in (0, 1):
                total += conn.execute(
                    f"SELECT COUNT(*) FROM text_similarities WHERE {where}",
                    params
                ).fetchone()[0]
            if type_idx in (0, 2):
                total += conn.execute(
                    f"SELECT COUNT(*) FROM image_similarities WHERE {where}",
                    params
                ).fetchone()[0]
        finally:
            conn.close()

        self._total_pairs = total
        self._count_label.setText(f"{total} matches")

    def _max_page(self) -> int:
        if self._total_pairs == 0:
            return 0
        return max(0, (self._total_pairs - 1) // PAGE_SIZE)

    def _go_page(self, page: int):
        page = max(0, min(page, self._max_page()))
        if page == self._page:
            return
        self._page = page
        self._load_page()

    def _load_page(self):
        """Load only current page from DB — NEVER load everything."""
        pid = self._proj_combo.currentData()
        if not pid or pid == -1:
            self._current_pairs = []
            self._list.clear()
            self._page_label.setText("Page 1 / 1")
            return

        offset   = self._page * PAGE_SIZE
        limit    = PAGE_SIZE
        type_idx = self._type_combo.currentIndex()

        conn = get_connection()
        pairs = []
        try:
            where, params = self._get_where_and_params("text")

            if type_idx in (0, 1):
                rows = conn.execute(
                    f"""SELECT id, similarity_score, reviewed,
                               chunk_id_a, chunk_id_b,
                               file_id_a, file_id_b
                        FROM text_similarities
                        WHERE {where}
                        ORDER BY similarity_score DESC
                        LIMIT ? OFFSET ?""",
                    params + [limit, offset]
                ).fetchall()
                for r in rows:
                    pairs.append(("text", dict(r)))

            if type_idx in (0, 2):
                remaining = limit - len(pairs)
                if remaining > 0:
                    text_count = conn.execute(
                        f"SELECT COUNT(*) FROM text_similarities WHERE {where}",
                        params
                    ).fetchone()[0]
                    img_offset = max(0, offset - text_count)

                    rows = conn.execute(
                        f"""SELECT id, similarity_score, reviewed, hash_distance,
                                   image_id_a, image_id_b,
                                   file_id_a, file_id_b
                            FROM image_similarities
                            WHERE {where}
                            ORDER BY similarity_score DESC
                            LIMIT ? OFFSET ?""",
                        params + [remaining, img_offset]
                    ).fetchall()
                    for r in rows:
                        pairs.append(("image", dict(r)))
        finally:
            conn.close()

        self._current_pairs = pairs
        self._current_idx   = 0
        self._populate_list()
        max_p = self._max_page()
        self._page_label.setText(f"Page {self._page + 1} / {max_p + 1}")

    def _populate_list(self):
        self._list.blockSignals(True)
        self._list.clear()

        for kind, pair in self._current_pairs:
            score = pair["similarity_score"]
            rev   = " [R]" if pair["reviewed"] else ""
            tag   = "TXT" if kind == "text" else "IMG"
            label = f"[{tag}] {score:.0%}{rev}"

            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, (kind, pair["id"]))
            self._list.addItem(item)

        self._list.blockSignals(False)

        if self._current_pairs:
            self._list.setCurrentRow(0)
        else:
            self._score_label.setText("No matches on this page")
            self._text_a.clear()
            self._text_b.clear()
            self._img_a.clear()
            self._img_b.clear()
            self._label_a.setText("File A")
            self._label_b.setText("File B")

    # ─────────────────────────────────────────────────────────
    def _show_pair(self, row: int):
        """Lazy-load full details only when a pair is selected."""
        if row < 0 or row >= len(self._current_pairs):
            return

        self._current_idx = row
        self._pair_label.setText(f"{row + 1} / {len(self._current_pairs)}")

        kind, pair = self._current_pairs[row]
        score = pair["similarity_score"]
        self._score_label.setText(f"Similarity Score: {score:.2%}")

        conn = get_connection()
        try:
            if kind == "text":
                row_a = conn.execute(
                    """SELECT tc.content, tc.page_number, tc.chunk_type,
                              f.file_name
                       FROM text_chunks tc
                       JOIN files f ON tc.file_id = f.id
                       WHERE tc.id = ?""",
                    (pair["chunk_id_a"],)
                ).fetchone()
                row_b = conn.execute(
                    """SELECT tc.content, tc.page_number, tc.chunk_type,
                              f.file_name
                       FROM text_chunks tc
                       JOIN files f ON tc.file_id = f.id
                       WHERE tc.id = ?""",
                    (pair["chunk_id_b"],)
                ).fetchone()

                if row_a and row_b:
                    self._show_text(row_a, row_b)

            else:
                row_a = conn.execute(
                    """SELECT ei.stored_path, f.file_name
                       FROM extracted_images ei
                       JOIN files f ON ei.file_id = f.id
                       WHERE ei.id = ?""",
                    (pair["image_id_a"],)
                ).fetchone()
                row_b = conn.execute(
                    """SELECT ei.stored_path, f.file_name
                       FROM extracted_images ei
                       JOIN files f ON ei.file_id = f.id
                       WHERE ei.id = ?""",
                    (pair["image_id_b"],)
                ).fetchone()

                if row_a and row_b:
                    self._show_image(row_a, row_b)

        finally:
            conn.close()

    def _show_text(self, row_a, row_b):
        self._text_a.show()
        self._text_b.show()
        self._img_a.hide()
        self._img_b.hide()

        self._label_a.setText(f"{row_a['file_name']} — Page {row_a['page_number']}")
        self._label_b.setText(f"{row_b['file_name']} — Page {row_b['page_number']}")

        text_a = str(row_a["content"])[:5000]
        text_b = str(row_b["content"])[:5000]
        self._text_a.setPlainText(text_a)
        self._text_b.setPlainText(text_b)

    def _show_image(self, row_a, row_b):
        self._text_a.hide()
        self._text_b.hide()
        self._img_a.show()
        self._img_b.show()

        self._label_a.setText(row_a["file_name"])
        self._label_b.setText(row_b["file_name"])

        def load(label, path):
            if path and os.path.exists(path):
                pix = QPixmap(path).scaled(
                    300, 300,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                label.setPixmap(pix)
            else:
                label.setText("Image not found")
                label.setPixmap(QPixmap())

        load(self._img_a, row_a["stored_path"])
        load(self._img_b, row_b["stored_path"])

    # ─────────────────────────────────────────────────────────
    def _prev_pair(self):
        if self._current_idx > 0:
            self._list.setCurrentRow(self._current_idx - 1)
        elif self._page > 0:
            self._go_page(self._page - 1)

    def _next_pair(self):
        if self._current_idx < len(self._current_pairs) - 1:
            self._list.setCurrentRow(self._current_idx + 1)
        elif self._page < self._max_page():
            self._go_page(self._page + 1)

    def _mark_reviewed(self):
        if not self._current_pairs:
            return
        row = self._current_idx
        if row < 0 or row >= len(self._current_pairs):
            return

        kind, pair = self._current_pairs[row]
        mark_similarity_reviewed(pair["id"], kind)
        self._load_page()

    def _export(self):
        pid = self._proj_combo.currentData()
        if not pid or pid == -1:
            QMessageBox.warning(self, "Export", "Select a project first.")
            return
        show_export_dialog(pid, self)