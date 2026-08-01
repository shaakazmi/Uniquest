import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame,
    QScrollArea, QSplitter, QTabWidget,
    QTextEdit, QSizePolicy, QStackedWidget,
    QGridLayout, QSpacerItem, QAbstractItemView,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QSlider, QCheckBox, QMessageBox,
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QTimer, QSize,
)
from PyQt6.QtGui import (
    QPixmap, QColor, QFont, QImage,
)

from utils.theme import ThemeManager
from core.similarity import (
    build_text_clusters,
    build_image_clusters,
    mark_text_pair_reviewed,
    mark_image_pair_reviewed,
    get_similarity_stats,
)
from core.processor import get_project
from ui.dashboard import EmptyState, LoadingLabel


# ─────────────────────────────────────────────
#  SCORE BADGE
# ─────────────────────────────────────────────
class ScoreBadge(QLabel):
    def __init__(self, score: float, parent=None):
        super().__init__(parent)
        self.set_score(score)
        self.setFixedWidth(60)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def set_score(self, score: float):
        pct = score * 100
        if score >= 0.90:
            color, bg = "#FF4C4C", "#FF4C4C22"
        elif score >= 0.80:
            color, bg = "#FFA500", "#FFA50022"
        elif score >= 0.70:
            color, bg = "#FFD700", "#FFD70022"
        else:
            color, bg = "#4A9EFF", "#4A9EFF22"

        self.setText(f"{pct:.0f}%")
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                color: {color};
                border: 1px solid {color}55;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 700;
                padding: 2px 6px;
            }}
        """)


# ─────────────────────────────────────────────
#  TEXT COMPARE PANEL
# ─────────────────────────────────────────────
class TextComparePanel(QFrame):
    reviewed_changed = pyqtSignal(int, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "card")
        self._pair_id  = None
        self._reviewed = False
        self._build()
        ThemeManager.add_listener(self.apply_theme)

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        header = QHBoxLayout()
        self.title_lbl = QLabel("Text Similarity")
        self.title_lbl.setStyleSheet(
            "font-size: 14px; font-weight: 700;"
            "background: transparent; border: none;"
        )
        self.score_badge = ScoreBadge(0.0)
        self.reviewed_btn = QPushButton("Mark Reviewed ✓")
        self.reviewed_btn.setFixedHeight(28)
        self.reviewed_btn.setFixedWidth(150)
        self.reviewed_btn.clicked.connect(self._on_reviewed_toggle)
        header.addWidget(self.title_lbl)
        header.addWidget(self.score_badge)
        header.addStretch()
        header.addWidget(self.reviewed_btn)
        layout.addLayout(header)

        files_row = QHBoxLayout()
        self.file_a_lbl = QLabel("File A")
        self.file_a_lbl.setStyleSheet(
            "font-size: 12px; font-weight: 600;"
            "color: #4A9EFF; background: transparent; border: none;"
        )
        vs_lbl = QLabel("VS")
        vs_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vs_lbl.setFixedWidth(30)
        vs_lbl.setStyleSheet(
            "font-size: 11px; font-weight: 700;"
            "color: #7986cb; background: transparent; border: none;"
        )
        self.file_b_lbl = QLabel("File B")
        self.file_b_lbl.setStyleSheet(
            "font-size: 12px; font-weight: 600;"
            "color: #4caf50; background: transparent; border: none;"
        )
        files_row.addWidget(self.file_a_lbl, 1)
        files_row.addWidget(vs_lbl)
        files_row.addWidget(self.file_b_lbl, 1)
        layout.addLayout(files_row)

        text_row = QHBoxLayout()
        text_row.setSpacing(8)
        self.text_a = QTextEdit()
        self.text_a.setReadOnly(True)
        self.text_a.setMinimumHeight(180)
        self.text_b = QTextEdit()
        self.text_b.setReadOnly(True)
        self.text_b.setMinimumHeight(180)
        text_row.addWidget(self.text_a)
        text_row.addWidget(self.text_b)
        layout.addLayout(text_row)

        self.page_lbl = QLabel("")
        self.page_lbl.setStyleSheet(
            "font-size: 11px; background: transparent; border: none;"
        )
        layout.addWidget(self.page_lbl)
        self.apply_theme()

    def load_from_cluster_pair(self, item_a: dict, item_b: dict):
        self._pair_id  = item_a.get("pair_id")
        self._reviewed = bool(item_a.get("reviewed", 0))
        score = item_a.get("score", 0.0)
        self.score_badge.set_score(score)
        self.title_lbl.setText(f"Text Similarity — {score*100:.1f}%")
        self.file_a_lbl.setText(f"📄 {item_a.get('file_name','File A')}")
        self.file_b_lbl.setText(f"📄 {item_b.get('file_name','File B')}")
        self.text_a.setPlainText(item_a.get("content", "") or "")
        self.text_b.setPlainText(item_b.get("content", "") or "")

        page_a = item_a.get("page", 0)
        page_b = item_b.get("page", 0)
        type_a = item_a.get("type", "")
        type_b = item_b.get("type", "")
        info_parts = []
        if page_a or page_b:
            info_parts.append(f"Page {page_a} (A)  •  Page {page_b} (B)")
        if type_a or type_b:
            info_parts.append(f"Type: {type_a} / {type_b}")
        self.page_lbl.setText("  |  ".join(info_parts))
        self._update_reviewed_btn()

    def clear(self):
        self._pair_id = None
        self.title_lbl.setText("Select a match to compare")
        self.file_a_lbl.setText("File A")
        self.file_b_lbl.setText("File B")
        self.text_a.clear()
        self.text_b.clear()
        self.page_lbl.setText("")
        self.score_badge.set_score(0.0)

    def _on_reviewed_toggle(self):
        if self._pair_id is None:
            return
        self._reviewed = not self._reviewed
        mark_text_pair_reviewed(self._pair_id, self._reviewed)
        self._update_reviewed_btn()
        self.reviewed_changed.emit(self._pair_id, self._reviewed)

    def _update_reviewed_btn(self):
        if self._reviewed:
            self.reviewed_btn.setText("✓ Reviewed")
            self.reviewed_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4caf5022;
                    color: #4caf50;
                    border: 1px solid #4caf5055;
                    border-radius: 6px;
                    font-size: 12px;
                    font-weight: 600;
                    padding: 4px 10px;
                }
            """)
        else:
            self.reviewed_btn.setText("Mark Reviewed ✓")
            self.reviewed_btn.setStyleSheet("")

    def apply_theme(self):
        c = ThemeManager.colors()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {c['bg_card']};
                border: 1px solid {c['border']};
                border-radius: 10px;
            }}
        """)
        self.text_a.setStyleSheet(f"""
            QTextEdit {{
                background-color: {c['bg_input']};
                color: {c['text_primary']};
                border: 1px solid {c['border']};
                border-left: 3px solid #4A9EFF;
                border-radius: 6px;
                font-size: 12px;
                padding: 8px;
            }}
        """)
        self.text_b.setStyleSheet(f"""
            QTextEdit {{
                background-color: {c['bg_input']};
                color: {c['text_primary']};
                border: 1px solid {c['border']};
                border-left: 3px solid #4caf50;
                border-radius: 6px;
                font-size: 12px;
                padding: 8px;
            }}
        """)
        self.page_lbl.setStyleSheet(
            f"font-size: 11px; color: {c['text_muted']};"
            f"background: transparent; border: none;"
        )


# ─────────────────────────────────────────────
#  IMAGE COMPARE PANEL
# ─────────────────────────────────────────────
class ImageComparePanel(QFrame):
    reviewed_changed = pyqtSignal(int, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "card")
        self._pair_id  = None
        self._reviewed = False
        self._build()
        ThemeManager.add_listener(self.apply_theme)

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        header = QHBoxLayout()
        self.title_lbl = QLabel("Image Similarity")
        self.title_lbl.setStyleSheet(
            "font-size: 14px; font-weight: 700;"
            "background: transparent; border: none;"
        )
        self.score_badge = ScoreBadge(0.0)
        self.reviewed_btn = QPushButton("Mark Reviewed ✓")
        self.reviewed_btn.setFixedHeight(28)
        self.reviewed_btn.setFixedWidth(150)
        self.reviewed_btn.clicked.connect(self._on_reviewed_toggle)
        header.addWidget(self.title_lbl)
        header.addWidget(self.score_badge)
        header.addStretch()
        header.addWidget(self.reviewed_btn)
        layout.addLayout(header)

        files_row = QHBoxLayout()
        self.file_a_lbl = QLabel("File A")
        self.file_a_lbl.setStyleSheet(
            "font-size: 12px; font-weight: 600;"
            "color: #4A9EFF; background: transparent; border: none;"
        )
        vs_lbl = QLabel("VS")
        vs_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vs_lbl.setFixedWidth(30)
        vs_lbl.setStyleSheet(
            "font-size: 11px; font-weight: 700;"
            "color: #7986cb; background: transparent; border: none;"
        )
        self.file_b_lbl = QLabel("File B")
        self.file_b_lbl.setStyleSheet(
            "font-size: 12px; font-weight: 600;"
            "color: #4caf50; background: transparent; border: none;"
        )
        files_row.addWidget(self.file_a_lbl, 1)
        files_row.addWidget(vs_lbl)
        files_row.addWidget(self.file_b_lbl, 1)
        layout.addLayout(files_row)

        img_row = QHBoxLayout()
        img_row.setSpacing(8)
        self.img_a_lbl = QLabel()
        self.img_a_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_a_lbl.setMinimumHeight(200)
        self.img_a_lbl.setStyleSheet(
            "border: 2px solid #4A9EFF; border-radius: 6px; background: #0f1f35;"
        )
        self.img_b_lbl = QLabel()
        self.img_b_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_b_lbl.setMinimumHeight(200)
        self.img_b_lbl.setStyleSheet(
            "border: 2px solid #4caf50; border-radius: 6px; background: #0f1f35;"
        )
        img_row.addWidget(self.img_a_lbl, 1)
        img_row.addWidget(self.img_b_lbl, 1)
        layout.addLayout(img_row)

        self.meta_lbl = QLabel("")
        self.meta_lbl.setStyleSheet(
            "font-size: 11px; background: transparent; border: none;"
        )
        layout.addWidget(self.meta_lbl)
        self.apply_theme()

    def load_pair(self, item_a: dict, item_b: dict):
        self._pair_id  = item_a.get("pair_id")
        self._reviewed = bool(item_a.get("reviewed", 0))
        score = item_a.get("score", 0.0)
        self.score_badge.set_score(score)
        dist = item_a.get("distance", 0)
        self.title_lbl.setText(
            f"Image Similarity — {score*100:.1f}%  (hash distance: {dist})"
        )
        self.file_a_lbl.setText(f"🖼️ {item_a.get('file_name','File A')}")
        self.file_b_lbl.setText(f"🖼️ {item_b.get('file_name','File B')}")
        self._load_image(self.img_a_lbl, item_a.get("img_path", ""))
        self._load_image(self.img_b_lbl, item_b.get("img_path", ""))
        self.meta_lbl.setText(
            f"{item_a.get('width',0)}×{item_a.get('height',0)} px (A)    •    "
            f"{item_b.get('width',0)}×{item_b.get('height',0)} px (B)"
        )
        self._update_reviewed_btn()

    def _load_image(self, label: QLabel, path: str):
        if path and os.path.isfile(path):
            pix = QPixmap(path)
            if not pix.isNull():
                scaled = pix.scaled(
                    320, 240,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                label.setPixmap(scaled)
                return
        label.setText("⚠️ Image not available")

    def _on_reviewed_toggle(self):
        if self._pair_id is None:
            return
        self._reviewed = not self._reviewed
        mark_image_pair_reviewed(self._pair_id, self._reviewed)
        self._update_reviewed_btn()
        self.reviewed_changed.emit(self._pair_id, self._reviewed)

    def _update_reviewed_btn(self):
        if self._reviewed:
            self.reviewed_btn.setText("✓ Reviewed")
            self.reviewed_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4caf5022;
                    color: #4caf50;
                    border: 1px solid #4caf5055;
                    border-radius: 6px;
                    font-size: 12px;
                    font-weight: 600;
                    padding: 4px 10px;
                }
            """)
        else:
            self.reviewed_btn.setText("Mark Reviewed ✓")
            self.reviewed_btn.setStyleSheet("")

    def apply_theme(self):
        c = ThemeManager.colors()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {c['bg_card']};
                border: 1px solid {c['border']};
                border-radius: 10px;
            }}
        """)
        self.meta_lbl.setStyleSheet(
            f"font-size: 11px; color: {c['text_muted']};"
            f"background: transparent; border: none;"
        )


# ─────────────────────────────────────────────
#  CLUSTER LIST ITEM
# ─────────────────────────────────────────────
class ClusterItem(QFrame):
    selected = pyqtSignal(int)

    def __init__(self, index: int, cluster: list, kind: str = "text", parent=None):
        super().__init__(parent)
        self.index   = index
        self.cluster = cluster
        self.kind    = kind
        self._active = False
        self.setFixedHeight(72)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build()
        ThemeManager.add_listener(self.apply_theme)
        self.apply_theme()

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(10)

        icon = "📝" if self.kind == "text" else "🖼️"
        icon_lbl = QLabel(icon)
        icon_lbl.setFixedWidth(24)
        icon_lbl.setStyleSheet(
            "font-size: 16px; background: transparent; border: none;"
        )

        info = QVBoxLayout()
        info.setSpacing(3)

        count = len(self.cluster)
        files_set = set(item.get("file_name", "") for item in self.cluster)
        scores = [item.get("score", 0.0) for item in self.cluster]
        avg_score = sum(scores) / len(scores) if scores else 0.0

        # Show preview text if text cluster
        if self.kind == "text" and self.cluster:
            first_content = self.cluster[0].get("content", "")[:40]
            title_text = f"Cluster #{self.index + 1}  —  {count} matches"
        else:
            title_text = f"Cluster #{self.index + 1}  —  {count} images"

        self.title_lbl = QLabel(title_text)
        self.title_lbl.setStyleSheet(
            "font-size: 12px; font-weight: 600;"
            "background: transparent; border: none;"
        )

        # Sub label
        if self.kind == "text" and self.cluster:
            preview = self.cluster[0].get("content", "")[:50]
            self.sub_lbl = QLabel(f'"{preview}..."' if len(preview) >= 50 else f'"{preview}"')
        else:
            file_names = ", ".join(list(files_set)[:2])
            if len(files_set) > 2:
                file_names += f"  +{len(files_set)-2}"
            self.sub_lbl = QLabel(file_names or "—")

        self.sub_lbl.setStyleSheet(
            "font-size: 11px; background: transparent; border: none;"
        )

        info.addWidget(self.title_lbl)
        info.addWidget(self.sub_lbl)

        layout.addWidget(icon_lbl)
        layout.addLayout(info, 1)

        self.badge = ScoreBadge(avg_score)
        layout.addWidget(self.badge)

    def set_active(self, active: bool):
        self._active = active
        self.apply_theme()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self.index)
        super().mousePressEvent(event)

    def apply_theme(self):
        c = ThemeManager.colors()
        if self._active:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {c['bg_selected']};
                    border-left: 3px solid {c['accent']};
                    border-top: none;
                    border-right: none;
                    border-bottom: 1px solid {c['border_light']};
                    border-radius: 0px;
                }}
            """)
            self.title_lbl.setStyleSheet(
                f"font-size: 12px; font-weight: 600;"
                f"color: {c['accent']}; background: transparent; border: none;"
            )
        else:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: transparent;
                    border-left: 3px solid transparent;
                    border-top: none;
                    border-right: none;
                    border-bottom: 1px solid {c['border_light']};
                }}
                QFrame:hover {{
                    background-color: {c['bg_hover']};
                }}
            """)
            self.title_lbl.setStyleSheet(
                f"font-size: 12px; font-weight: 600;"
                f"color: {c['text_primary']}; background: transparent; border: none;"
            )
        self.sub_lbl.setStyleSheet(
            f"font-size: 11px; color: {c['text_muted']};"
            f"background: transparent; border: none;"
        )


# ─────────────────────────────────────────────
#  STATS BAR
# ─────────────────────────────────────────────
class StatsBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(56)
        self._build()
        ThemeManager.add_listener(self.apply_theme)

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(0)

        self.chips = []
        self._chip_data = [
            ("📝", "Text Matches",  "0", "#4A9EFF"),
            ("🖼️", "Image Matches", "0", "#ff9800"),
            ("✅", "Reviewed",      "0", "#4caf50"),
            ("📊", "Total Found",   "0", "#e91e63"),
        ]

        for icon, label, val, color in self._chip_data:
            chip = self._make_chip(icon, label, val, color)
            layout.addWidget(chip)
            layout.addStretch()

        self.apply_theme()

    def _make_chip(self, icon, label, val, color):
        frame = QFrame()
        frame.setStyleSheet("background: transparent; border: none;")
        fl = QHBoxLayout(frame)
        fl.setContentsMargins(12, 4, 12, 4)
        fl.setSpacing(8)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(
            "font-size: 18px; background: transparent; border: none;"
        )

        text_col = QVBoxLayout()
        text_col.setSpacing(0)

        val_lbl = QLabel(val)
        val_lbl.setStyleSheet(
            f"font-size: 17px; font-weight: 700;"
            f"color: {color}; background: transparent; border: none;"
        )

        lbl_lbl = QLabel(label)
        lbl_lbl.setStyleSheet(
            "font-size: 10px; background: transparent; border: none;"
        )

        text_col.addWidget(val_lbl)
        text_col.addWidget(lbl_lbl)

        fl.addWidget(icon_lbl)
        fl.addLayout(text_col)
        self.chips.append(val_lbl)
        return frame

    def update_stats(self, stats: dict):
        values = [
            str(stats.get("text_total", 0)),
            str(stats.get("img_total", 0)),
            str(stats.get("text_reviewed", 0) + stats.get("img_reviewed", 0)),
            str(stats.get("grand_total", 0)),
        ]
        for lbl, val in zip(self.chips, values):
            lbl.setText(val)

    def apply_theme(self):
        c = ThemeManager.colors()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {c['bg_secondary']};
                border: none;
                border-bottom: 1px solid {c['border']};
            }}
        """)


# ─────────────────────────────────────────────
#  FILTER BAR
# ─────────────────────────────────────────────
class FilterBar(QFrame):
    filter_changed = pyqtSignal(str, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(48)
        self._build()
        ThemeManager.add_listener(self.apply_theme)

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 6, 16, 6)
        layout.setSpacing(12)

        self.kind_combo = QComboBox()
        self.kind_combo.setFixedHeight(32)
        self.kind_combo.setFixedWidth(160)
        self.kind_combo.addItem("📝 Text Matches", "text")
        self.kind_combo.addItem("🖼️ Image Matches", "image")
        self.kind_combo.currentIndexChanged.connect(self._emit)

        score_lbl = QLabel("Min score:")
        score_lbl.setStyleSheet(
            "font-size: 12px; background: transparent; border: none;"
        )

        self.score_slider = QSlider(Qt.Orientation.Horizontal)
        self.score_slider.setRange(50, 100)
        self.score_slider.setValue(70)
        self.score_slider.setFixedWidth(140)
        self.score_slider.valueChanged.connect(self._on_slider)

        self.score_val_lbl = QLabel("70%")
        self.score_val_lbl.setFixedWidth(44)
        self.score_val_lbl.setStyleSheet(
            "font-size: 13px; font-weight: 700;"
            "color: #4A9EFF; background: transparent; border: none;"
        )

        self.unreviewed_only = QCheckBox("Unreviewed only")
        self.unreviewed_only.stateChanged.connect(self._emit)

        layout.addWidget(self.kind_combo)
        layout.addSpacing(8)
        layout.addWidget(score_lbl)
        layout.addWidget(self.score_slider)
        layout.addWidget(self.score_val_lbl)
        layout.addSpacing(8)
        layout.addWidget(self.unreviewed_only)
        layout.addStretch()

        self.apply_theme()

    def _on_slider(self, val: int):
        self.score_val_lbl.setText(f"{val}%")
        self._emit()

    def _emit(self):
        kind = self.kind_combo.currentData()
        score = self.score_slider.value() / 100.0
        self.filter_changed.emit(kind, score)

    def current_kind(self) -> str:
        return self.kind_combo.currentData()

    def current_score(self) -> float:
        return self.score_slider.value() / 100.0

    def is_unreviewed_only(self) -> bool:
        return self.unreviewed_only.isChecked()

    def apply_theme(self):
        c = ThemeManager.colors()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {c['bg_card']};
                border: none;
                border-bottom: 1px solid {c['border']};
            }}
        """)


# ─────────────────────────────────────────────
#  RESULTS PAGE
# ─────────────────────────────────────────────
class ResultsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._project_id    = None
        self._text_clusters = []
        self._img_clusters  = []
        self._active_index  = -1
        self._active_cluster = []
        self._active_kind   = "text"
        self._pair_index    = 0
        self._cluster_items = []
        self._build()
        ThemeManager.add_listener(self.apply_theme)

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.stats_bar = StatsBar()
        outer.addWidget(self.stats_bar)

        self.filter_bar = FilterBar()
        self.filter_bar.filter_changed.connect(self._on_filter_changed)
        outer.addWidget(self.filter_bar)

        # Empty state for no project
        self.no_project = EmptyState(
            icon="📋",
            title="No results to show",
            message="Run an analysis on a project to see similarity results here.",
        )
        outer.addWidget(self.no_project, 1)

        # Main splitter
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setVisible(False)
        outer.addWidget(self.splitter, 1)

        # Left: cluster list
        left_frame = QFrame()
        left_frame.setMinimumWidth(280)
        left_frame.setMaximumWidth(400)
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        list_hdr = QFrame()
        list_hdr.setFixedHeight(36)
        lh_layout = QHBoxLayout(list_hdr)
        lh_layout.setContentsMargins(16, 0, 16, 0)
        self.list_count_lbl = QLabel("0 clusters")
        self.list_count_lbl.setStyleSheet(
            "font-size: 12px; font-weight: 600;"
            "background: transparent; border: none;"
        )
        lh_layout.addWidget(self.list_count_lbl)
        lh_layout.addStretch()
        left_layout.addWidget(list_hdr)

        self.cluster_scroll = QScrollArea()
        self.cluster_scroll.setWidgetResizable(True)
        self.cluster_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.cluster_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        # Container holds cluster items + empty state
        self.cluster_container = QWidget()
        self.cluster_layout = QVBoxLayout(self.cluster_container)
        self.cluster_layout.setContentsMargins(0, 0, 0, 0)
        self.cluster_layout.setSpacing(0)
        self.cluster_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.cluster_scroll.setWidget(self.cluster_container)
        left_layout.addWidget(self.cluster_scroll, 1)
        self.splitter.addWidget(left_frame)

        # Right: compare panel
        right_frame = QFrame()
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(12)

        self.compare_stack = QStackedWidget()

        # Placeholder — permanent widget (never gets deleted)
        placeholder = QWidget()
        ph_layout = QVBoxLayout(placeholder)
        ph_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph_layout.setSpacing(12)
        ph_icon = QLabel("👈")
        ph_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph_icon.setStyleSheet(
            "font-size: 48px; background: transparent; border: none;"
        )
        ph_title = QLabel("Select a cluster")
        ph_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph_title.setStyleSheet(
            "font-size: 16px; font-weight: 700;"
            "background: transparent; border: none;"
        )
        ph_msg = QLabel("Click a cluster on the left to view the side-by-side comparison.")
        ph_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph_msg.setWordWrap(True)
        ph_msg.setStyleSheet(
            "font-size: 13px; color: #7986cb;"
            "background: transparent; border: none;"
        )
        ph_layout.addStretch()
        ph_layout.addWidget(ph_icon)
        ph_layout.addWidget(ph_title)
        ph_layout.addWidget(ph_msg)
        ph_layout.addStretch()

        self.text_compare = TextComparePanel()
        self.text_compare.reviewed_changed.connect(self._on_reviewed_changed)

        self.img_compare = ImageComparePanel()
        self.img_compare.reviewed_changed.connect(self._on_reviewed_changed)

        self.compare_stack.addWidget(placeholder)      # 0
        self.compare_stack.addWidget(self.text_compare) # 1
        self.compare_stack.addWidget(self.img_compare)  # 2

        right_layout.addWidget(self.compare_stack, 1)

        # Pair navigation
        nav_row = QHBoxLayout()
        self.prev_btn = QPushButton("◀ Prev Pair")
        self.prev_btn.setProperty("class", "ghost")
        self.prev_btn.setFixedHeight(30)
        self.prev_btn.setFixedWidth(110)
        self.prev_btn.setVisible(False)
        self.prev_btn.clicked.connect(self._on_prev_pair)

        self.pair_lbl = QLabel("")
        self.pair_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pair_lbl.setStyleSheet(
            "font-size: 12px; background: transparent; border: none;"
        )

        self.next_btn = QPushButton("Next Pair ▶")
        self.next_btn.setProperty("class", "ghost")
        self.next_btn.setFixedHeight(30)
        self.next_btn.setFixedWidth(110)
        self.next_btn.setVisible(False)
        self.next_btn.clicked.connect(self._on_next_pair)

        nav_row.addWidget(self.prev_btn)
        nav_row.addStretch()
        nav_row.addWidget(self.pair_lbl)
        nav_row.addStretch()
        nav_row.addWidget(self.next_btn)
        right_layout.addLayout(nav_row)

        self.splitter.addWidget(right_frame)
        self.splitter.setSizes([300, 800])
        self.apply_theme()

    def load_project(self, project_id: int):
        self._project_id = project_id
        self._active_index = -1
        self._pair_index = 0
        self._load_data()

    def _load_data(self):
        if not self._project_id:
            return
        try:
            self._text_clusters = build_text_clusters(self._project_id)
            self._img_clusters = build_image_clusters(self._project_id)
            stats = get_similarity_stats(self._project_id)
            self.stats_bar.update_stats(stats)

            total = len(self._text_clusters) + len(self._img_clusters)
            if total == 0:
                self.no_project.setVisible(True)
                self.splitter.setVisible(False)
            else:
                self.no_project.setVisible(False)
                self.splitter.setVisible(True)
                self._render_clusters()
        except Exception as e:
            print(f"Results load error: {e}")
            import traceback
            traceback.print_exc()

    def _clear_cluster_list(self):
        """Safely remove all cluster items from the layout"""
        while self.cluster_layout.count():
            item = self.cluster_layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self._cluster_items = []

    def _render_clusters(self):
        kind = self.filter_bar.current_kind()
        min_score = self.filter_bar.current_score()
        unrev = self.filter_bar.is_unreviewed_only()

        clusters = (
            self._text_clusters if kind == "text"
            else self._img_clusters
        )

        # Filter clusters
        filtered = []
        for cluster in clusters:
            scores = [i.get("score", 0.0) for i in cluster]
            avg = sum(scores) / len(scores) if scores else 0.0
            if avg < min_score:
                continue
            if unrev:
                has_unrev = any(
                    not i.get("reviewed", False) for i in cluster
                )
                if not has_unrev:
                    continue
            filtered.append(cluster)

        # Clear old items safely
        self._clear_cluster_list()

        self.list_count_lbl.setText(
            f"{len(filtered)} cluster{'s' if len(filtered) != 1 else ''}"
        )

        if not filtered:
            # Create a fresh empty message widget each time
            empty_msg = QLabel(
                "🔍  No matches found\n\n"
                "No similarity matches above the current threshold."
            )
            empty_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_msg.setWordWrap(True)
            c = ThemeManager.colors()
            empty_msg.setStyleSheet(
                f"font-size: 13px; color: {c['text_muted']};"
                f"background: transparent; border: none;"
                f"padding: 40px 20px;"
            )
            self.cluster_layout.addWidget(empty_msg)
            self.compare_stack.setCurrentIndex(0)
            return

        for i, cluster in enumerate(filtered):
            item = ClusterItem(i, cluster, kind)
            item.selected.connect(
                lambda idx, cl=cluster, k=kind:
                    self._on_cluster_selected(idx, cl, k)
            )
            self.cluster_layout.addWidget(item)
            self._cluster_items.append(item)

        # Add a stretch at bottom to keep items at top
        self.cluster_layout.addStretch()

        # Auto-select first
        if filtered:
            self._on_cluster_selected(0, filtered[0], kind)

    def _on_filter_changed(self, kind: str, score: float):
        self._render_clusters()

    def _on_cluster_selected(self, index: int, cluster: list, kind: str):
        self._active_index = index
        self._active_cluster = cluster
        self._active_kind = kind
        self._pair_index = 0

        for i, item in enumerate(self._cluster_items):
            if item and not item.parent() is None:
                try:
                    item.set_active(i == index)
                except Exception:
                    pass

        self._show_pair(cluster, kind, 0)

    def _show_pair(self, cluster: list, kind: str, pair_idx: int):
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

        total_pairs = max(len(cluster) - 1, 1)
        if total_pairs > 1:
            self.prev_btn.setVisible(True)
            self.next_btn.setVisible(True)
            self.pair_lbl.setText(f"Pair {pair_idx + 1} of {total_pairs}")
        else:
            self.prev_btn.setVisible(False)
            self.next_btn.setVisible(False)
            self.pair_lbl.setText("")

    def _on_prev_pair(self):
        if self._active_index < 0:
            return
        self._show_pair(self._active_cluster, self._active_kind, self._pair_index - 1)

    def _on_next_pair(self):
        if self._active_index < 0:
            return
        self._show_pair(self._active_cluster, self._active_kind, self._pair_index + 1)

    def _on_reviewed_changed(self, pair_id: int, reviewed: bool):
        if self._project_id:
            stats = get_similarity_stats(self._project_id)
            self.stats_bar.update_stats(stats)

    def apply_theme(self):
        c = ThemeManager.colors()
        self.setStyleSheet(
            f"background-color: {c['bg_primary']};"
        )
        self.list_count_lbl.setStyleSheet(
            f"font-size: 12px; font-weight: 600;"
            f"color: {c['text_secondary']};"
            f"background: transparent; border: none;"
        )
        self.pair_lbl.setStyleSheet(
            f"font-size: 12px; color: {c['text_muted']};"
            f"background: transparent; border: none;"
        )
        self.splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {c['border']};
                width: 2px;
            }}
        """)
    