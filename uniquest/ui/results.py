import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QGroupBox,
    QScrollArea, QSplitter, QTextEdit,
    QStackedWidget, QAbstractItemView,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QSlider, QCheckBox, QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QColor

from utils.theme import ThemeManager
from core.similarity import (
    build_text_clusters,
    build_image_clusters,
    mark_text_pair_reviewed,
    mark_image_pair_reviewed,
    get_similarity_stats,
)
from core.processor import get_project


# ─────────────────────────────────────────────
#  TEXT COMPARE PANEL
# ─────────────────────────────────────────────
class TextComparePanel(QGroupBox):
    reviewed_changed = pyqtSignal(int, bool)

    def __init__(self, parent=None):
        super().__init__("Text Comparison", parent)
        self._pair_id = None
        self._reviewed = False
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 14, 10, 10)
        layout.setSpacing(8)

        header = QHBoxLayout()
        self.score_lbl = QLabel("Score: —")
        self.score_lbl.setStyleSheet(
            "font-size: 12px; font-weight: 700;"
            "background: transparent; border: 0px;"
        )
        self.reviewed_btn = QPushButton("Mark Reviewed")
        self.reviewed_btn.setFixedHeight(24)
        self.reviewed_btn.setFixedWidth(120)
        self.reviewed_btn.clicked.connect(self._on_reviewed_toggle)
        header.addWidget(self.score_lbl)
        header.addStretch()
        header.addWidget(self.reviewed_btn)
        layout.addLayout(header)

        files_row = QHBoxLayout()
        self.file_a_lbl = QLabel("File A")
        self.file_a_lbl.setStyleSheet(
            "font-size: 11px; font-weight: 600;"
            "background: transparent; border: 0px;"
        )
        self.file_b_lbl = QLabel("File B")
        self.file_b_lbl.setStyleSheet(
            "font-size: 11px; font-weight: 600;"
            "background: transparent; border: 0px;"
        )
        files_row.addWidget(self.file_a_lbl, 1)
        files_row.addWidget(self.file_b_lbl, 1)
        layout.addLayout(files_row)

        text_row = QHBoxLayout()
        text_row.setSpacing(6)
        self.text_a = QTextEdit()
        self.text_a.setReadOnly(True)
        self.text_a.setMinimumHeight(160)
        self.text_b = QTextEdit()
        self.text_b.setReadOnly(True)
        self.text_b.setMinimumHeight(160)
        text_row.addWidget(self.text_a)
        text_row.addWidget(self.text_b)
        layout.addLayout(text_row)

        self.page_lbl = QLabel("")
        self.page_lbl.setStyleSheet(
            "font-size: 11px; background: transparent; border: 0px;"
        )
        layout.addWidget(self.page_lbl)

    def load_from_cluster_pair(self, item_a, item_b):
        self._pair_id = item_a.get("pair_id")
        self._reviewed = bool(item_a.get("reviewed", 0))
        score = item_a.get("score", 0.0)
        self.score_lbl.setText(f"Score: {score*100:.1f}%")
        self.file_a_lbl.setText(f"File: {item_a.get('file_name', 'A')}")
        self.file_b_lbl.setText(f"File: {item_b.get('file_name', 'B')}")
        self.text_a.setPlainText(item_a.get("content", "") or "")
        self.text_b.setPlainText(item_b.get("content", "") or "")

        parts = []
        if item_a.get("page") or item_b.get("page"):
            parts.append(f"Page {item_a.get('page',0)} vs Page {item_b.get('page',0)}")
        if item_a.get("type") or item_b.get("type"):
            parts.append(f"Type: {item_a.get('type','')} / {item_b.get('type','')}")
        self.page_lbl.setText("  |  ".join(parts))
        self._update_reviewed_btn()

    def _on_reviewed_toggle(self):
        if self._pair_id is None:
            return
        self._reviewed = not self._reviewed
        mark_text_pair_reviewed(self._pair_id, self._reviewed)
        self._update_reviewed_btn()
        self.reviewed_changed.emit(self._pair_id, self._reviewed)

    def _update_reviewed_btn(self):
        if self._reviewed:
            self.reviewed_btn.setText("Reviewed")
        else:
            self.reviewed_btn.setText("Mark Reviewed")


# ─────────────────────────────────────────────
#  IMAGE COMPARE PANEL
# ─────────────────────────────────────────────
class ImageComparePanel(QGroupBox):
    reviewed_changed = pyqtSignal(int, bool)

    def __init__(self, parent=None):
        super().__init__("Image Comparison", parent)
        self._pair_id = None
        self._reviewed = False
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 14, 10, 10)
        layout.setSpacing(8)

        header = QHBoxLayout()
        self.score_lbl = QLabel("Score: —")
        self.score_lbl.setStyleSheet(
            "font-size: 12px; font-weight: 700;"
            "background: transparent; border: 0px;"
        )
        self.reviewed_btn = QPushButton("Mark Reviewed")
        self.reviewed_btn.setFixedHeight(24)
        self.reviewed_btn.setFixedWidth(120)
        self.reviewed_btn.clicked.connect(self._on_reviewed_toggle)
        header.addWidget(self.score_lbl)
        header.addStretch()
        header.addWidget(self.reviewed_btn)
        layout.addLayout(header)

        files_row = QHBoxLayout()
        self.file_a_lbl = QLabel("File A")
        self.file_a_lbl.setStyleSheet(
            "font-size: 11px; font-weight: 600;"
            "background: transparent; border: 0px;"
        )
        self.file_b_lbl = QLabel("File B")
        self.file_b_lbl.setStyleSheet(
            "font-size: 11px; font-weight: 600;"
            "background: transparent; border: 0px;"
        )
        files_row.addWidget(self.file_a_lbl, 1)
        files_row.addWidget(self.file_b_lbl, 1)
        layout.addLayout(files_row)

        img_row = QHBoxLayout()
        img_row.setSpacing(6)
        self.img_a_lbl = QLabel()
        self.img_a_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_a_lbl.setMinimumHeight(180)
        self.img_a_lbl.setStyleSheet(
            "border: 1px solid #adadad; background: #fafafa;"
        )
        self.img_b_lbl = QLabel()
        self.img_b_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_b_lbl.setMinimumHeight(180)
        self.img_b_lbl.setStyleSheet(
            "border: 1px solid #adadad; background: #fafafa;"
        )
        img_row.addWidget(self.img_a_lbl, 1)
        img_row.addWidget(self.img_b_lbl, 1)
        layout.addLayout(img_row)

        self.meta_lbl = QLabel("")
        self.meta_lbl.setStyleSheet(
            "font-size: 11px; background: transparent; border: 0px;"
        )
        layout.addWidget(self.meta_lbl)

    def load_pair(self, item_a, item_b):
        self._pair_id = item_a.get("pair_id")
        self._reviewed = bool(item_a.get("reviewed", 0))
        score = item_a.get("score", 0.0)
        self.score_lbl.setText(f"Score: {score*100:.1f}%  (distance: {item_a.get('distance',0)})")
        self.file_a_lbl.setText(f"File: {item_a.get('file_name','A')}")
        self.file_b_lbl.setText(f"File: {item_b.get('file_name','B')}")
        self._load_image(self.img_a_lbl, item_a.get("img_path", ""))
        self._load_image(self.img_b_lbl, item_b.get("img_path", ""))
        self.meta_lbl.setText(
            f"{item_a.get('width',0)}x{item_a.get('height',0)} px  |  "
            f"{item_b.get('width',0)}x{item_b.get('height',0)} px"
        )
        self._update_reviewed_btn()

    def _load_image(self, label, path):
        if path and os.path.isfile(path):
            pix = QPixmap(path)
            if not pix.isNull():
                scaled = pix.scaled(
                    280, 200,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                label.setPixmap(scaled)
                return
        label.setText("Image not available")

    def _on_reviewed_toggle(self):
        if self._pair_id is None:
            return
        self._reviewed = not self._reviewed
        mark_image_pair_reviewed(self._pair_id, self._reviewed)
        self._update_reviewed_btn()
        self.reviewed_changed.emit(self._pair_id, self._reviewed)

    def _update_reviewed_btn(self):
        if self._reviewed:
            self.reviewed_btn.setText("Reviewed")
        else:
            self.reviewed_btn.setText("Mark Reviewed")


# ─────────────────────────────────────────────
#  RESULTS PAGE
# ─────────────────────────────────────────────
class ResultsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._project_id = None
        self._text_clusters = []
        self._img_clusters = []
        self._active_cluster = []
        self._active_kind = "text"
        self._pair_index = 0
        self._build()
        ThemeManager.add_listener(self.apply_theme)

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 12, 16, 12)
        outer.setSpacing(10)

        # Stats
        stats_row = QHBoxLayout()
        stats_row.setSpacing(20)

        self.stat_text = QLabel("Text matches: 0")
        self.stat_img = QLabel("Image matches: 0")
        self.stat_reviewed = QLabel("Reviewed: 0")
        self.stat_total = QLabel("Total: 0")

        for lbl in [self.stat_text, self.stat_img, self.stat_reviewed, self.stat_total]:
            lbl.setStyleSheet(
                "font-size: 12px; font-weight: 600;"
                "background: transparent; border: 0px;"
            )
            stats_row.addWidget(lbl)
        stats_row.addStretch()
        outer.addLayout(stats_row)

        # Filter bar
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)

        self.kind_combo = QComboBox()
        self.kind_combo.setMinimumWidth(140)
        self.kind_combo.addItem("Text Matches", "text")
        self.kind_combo.addItem("Image Matches", "image")
        self.kind_combo.currentIndexChanged.connect(lambda: self._render_clusters())

        score_lbl = QLabel("Min score:")
        score_lbl.setStyleSheet(
            "font-size: 12px; background: transparent; border: 0px;"
        )

        self.score_slider = QSlider(Qt.Orientation.Horizontal)
        self.score_slider.setRange(50, 100)
        self.score_slider.setValue(70)
        self.score_slider.setFixedWidth(140)
        self.score_slider.valueChanged.connect(self._on_slider)

        self.score_val_lbl = QLabel("70%")
        self.score_val_lbl.setFixedWidth(40)
        self.score_val_lbl.setStyleSheet(
            "font-size: 12px; font-weight: 700;"
            "background: transparent; border: 0px;"
        )

        self.unreviewed_only = QCheckBox("Unreviewed only")
        self.unreviewed_only.stateChanged.connect(lambda: self._render_clusters())

        filter_row.addWidget(self.kind_combo)
        filter_row.addWidget(score_lbl)
        filter_row.addWidget(self.score_slider)
        filter_row.addWidget(self.score_val_lbl)
        filter_row.addWidget(self.unreviewed_only)
        filter_row.addStretch()
        outer.addLayout(filter_row)

        # Empty state
        self.empty_lbl = QLabel(
            "No results to show. Run an analysis on a project."
        )
        self.empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_lbl.setStyleSheet(
            "font-size: 13px; background: transparent; border: 0px; padding: 30px;"
        )
        outer.addWidget(self.empty_lbl, 1)

        # Splitter
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setVisible(False)
        outer.addWidget(self.splitter, 1)

        # Left: cluster table
        left_group = QGroupBox("Clusters")
        left_layout = QVBoxLayout(left_group)
        left_layout.setContentsMargins(10, 14, 10, 10)
        left_layout.setSpacing(6)

        self.count_lbl = QLabel("0 clusters")
        self.count_lbl.setStyleSheet(
            "font-size: 11px; background: transparent; border: 0px;"
        )
        left_layout.addWidget(self.count_lbl)

        self.cluster_table = QTableWidget()
        self.cluster_table.setColumnCount(3)
        self.cluster_table.setHorizontalHeaderLabels(["#", "Score", "Preview"])
        self.cluster_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.cluster_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.cluster_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.cluster_table.verticalHeader().setVisible(False)
        self.cluster_table.setShowGrid(False)
        hdr = self.cluster_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.cluster_table.setColumnWidth(0, 40)
        self.cluster_table.setColumnWidth(1, 60)
        self.cluster_table.itemSelectionChanged.connect(self._on_cluster_selected)
        left_layout.addWidget(self.cluster_table)

        self.splitter.addWidget(left_group)

        # Right: compare
        right_frame = QFrame()
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        self.compare_stack = QStackedWidget()

        # Placeholder
        placeholder = QLabel("Select a cluster to view comparison.")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet(
            "font-size: 13px; color: #767676;"
            "background: transparent; border: 0px;"
        )

        self.text_compare = TextComparePanel()
        self.text_compare.reviewed_changed.connect(self._on_reviewed_changed)

        self.img_compare = ImageComparePanel()
        self.img_compare.reviewed_changed.connect(self._on_reviewed_changed)

        self.compare_stack.addWidget(placeholder)
        self.compare_stack.addWidget(self.text_compare)
        self.compare_stack.addWidget(self.img_compare)

        right_layout.addWidget(self.compare_stack, 1)

        # Pair navigation
        nav = QHBoxLayout()
        self.prev_btn = QPushButton("< Prev Pair")
        self.prev_btn.setFixedWidth(100)
        self.prev_btn.setVisible(False)
        self.prev_btn.clicked.connect(self._on_prev_pair)
        self.pair_lbl = QLabel("")
        self.pair_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pair_lbl.setStyleSheet(
            "font-size: 11px; background: transparent; border: 0px;"
        )
        self.next_btn = QPushButton("Next Pair >")
        self.next_btn.setFixedWidth(100)
        self.next_btn.setVisible(False)
        self.next_btn.clicked.connect(self._on_next_pair)
        nav.addWidget(self.prev_btn)
        nav.addStretch()
        nav.addWidget(self.pair_lbl)
        nav.addStretch()
        nav.addWidget(self.next_btn)
        right_layout.addLayout(nav)

        self.splitter.addWidget(right_frame)
        self.splitter.setSizes([280, 700])

        self.apply_theme()

    def _on_slider(self, val):
        self.score_val_lbl.setText(f"{val}%")
        self._render_clusters()

    def load_project(self, project_id):
        self._project_id = project_id
        self._load_data()

    def _load_data(self):
        if not self._project_id:
            return
        try:
            self._text_clusters = build_text_clusters(self._project_id)
            self._img_clusters = build_image_clusters(self._project_id)
            stats = get_similarity_stats(self._project_id)
            self._update_stats(stats)

            total = len(self._text_clusters) + len(self._img_clusters)
            if total == 0:
                self.empty_lbl.setVisible(True)
                self.splitter.setVisible(False)
            else:
                self.empty_lbl.setVisible(False)
                self.splitter.setVisible(True)
                self._render_clusters()
        except Exception as e:
            print(f"Results load error: {e}")

    def _update_stats(self, stats):
        self.stat_text.setText(f"Text matches: {stats.get('text_total', 0)}")
        self.stat_img.setText(f"Image matches: {stats.get('img_total', 0)}")
        rev = stats.get("text_reviewed", 0) + stats.get("img_reviewed", 0)
        self.stat_reviewed.setText(f"Reviewed: {rev}")
        self.stat_total.setText(f"Total: {stats.get('grand_total', 0)}")

    def _render_clusters(self):
        kind = self.kind_combo.currentData()
        min_score = self.score_slider.value() / 100.0
        unrev = self.unreviewed_only.isChecked()

        clusters = self._text_clusters if kind == "text" else self._img_clusters

        filtered = []
        for cluster in clusters:
            scores = [i.get("score", 0.0) for i in cluster]
            avg = sum(scores) / len(scores) if scores else 0.0
            if avg < min_score:
                continue
            if unrev:
                has_unrev = any(not i.get("reviewed", False) for i in cluster)
                if not has_unrev:
                    continue
            filtered.append(cluster)

        self.count_lbl.setText(
            f"{len(filtered)} cluster{'s' if len(filtered) != 1 else ''}"
        )
        self._filtered_clusters = filtered

        self.cluster_table.setRowCount(0)
        for i, cluster in enumerate(filtered):
            row = self.cluster_table.rowCount()
            self.cluster_table.insertRow(row)
            self.cluster_table.setRowHeight(row, 32)

            num_item = QTableWidgetItem(str(i + 1))
            num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.cluster_table.setItem(row, 0, num_item)

            scores = [c.get("score", 0.0) for c in cluster]
            avg = sum(scores) / len(scores) if scores else 0
            sc_item = QTableWidgetItem(f"{avg*100:.0f}%")
            sc_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            color = "#a80000" if avg >= 0.9 else ("#ca5010" if avg >= 0.8 else "#107c10")
            sc_item.setForeground(QColor(color))
            self.cluster_table.setItem(row, 1, sc_item)

            if kind == "text" and cluster:
                preview = cluster[0].get("content", "")[:50]
            else:
                preview = f"{len(cluster)} images"
            self.cluster_table.setItem(row, 2, QTableWidgetItem(preview))

        if filtered:
            self.cluster_table.selectRow(0)
        else:
            self.compare_stack.setCurrentIndex(0)

    def _on_cluster_selected(self):
        row = self.cluster_table.currentRow()
        if row < 0 or row >= len(self._filtered_clusters):
            return
        cluster = self._filtered_clusters[row]
        kind = self.kind_combo.currentData()
        self._active_cluster = cluster
        self._active_kind = kind
        self._pair_index = 0
        self._show_pair(cluster, kind, 0)

    def _show_pair(self, cluster, kind, pair_idx):
        if len(cluster) < 2:
            return
        max_pairs = len(cluster) - 1
        pair_idx = max(0, min(pair_idx, max_pairs - 1))
        self._pair_index = pair_idx
        item_a = cluster[pair_idx]
        item_b = cluster[pair_idx + 1] if pair_idx + 1 < len(cluster) else cluster[0]

        if kind == "text":
            self.compare_stack.setCurrentIndex(1)
            self.text_compare.load_from_cluster_pair(item_a, item_b)
        else:
            self.compare_stack.setCurrentIndex(2)
            self.img_compare.load_pair(item_a, item_b)

        total = max(len(cluster) - 1, 1)
        if total > 1:
            self.prev_btn.setVisible(True)
            self.next_btn.setVisible(True)
            self.pair_lbl.setText(f"Pair {pair_idx + 1} of {total}")
        else:
            self.prev_btn.setVisible(False)
            self.next_btn.setVisible(False)
            self.pair_lbl.setText("")

    def _on_prev_pair(self):
        self._show_pair(self._active_cluster, self._active_kind, self._pair_index - 1)

    def _on_next_pair(self):
        self._show_pair(self._active_cluster, self._active_kind, self._pair_index + 1)

    def _on_reviewed_changed(self, pair_id, reviewed):
        if self._project_id:
            stats = get_similarity_stats(self._project_id)
            self._update_stats(stats)

    def apply_theme(self):
        c = ThemeManager.colors()
        self.setStyleSheet(f"background-color: {c['bg_primary']};")
        for lbl in [self.stat_text, self.stat_img, self.stat_reviewed, self.stat_total]:
            lbl.setStyleSheet(
                f"font-size: 12px; font-weight: 600; color: {c['text_primary']};"
                f"background: transparent; border: 0px;"
            )