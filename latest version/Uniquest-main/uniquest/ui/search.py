"""
Search page for Uniquest.
Provides live search across all indexed content:
- Text search (TF-IDF)
- Image search (upload + hash)
- Trademark search (phonetic + fuzzy)
"""

import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QComboBox, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QMessageBox, QFileDialog,
    QTabWidget, QCheckBox, QSizePolicy, QFrame,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap, QColor

from core.search import search_text, search_image, search_trademark
from core.processor import get_all_projects


VERDICT_COLORS = {
    "IDENTICAL":           "#c0392b",
    "CONFUSINGLY SIMILAR": "#e67e22",
    "SIMILAR":             "#f1c40f",
    "DISTINCT":            "#27ae60",
}


class SearchWorker(QThread):
    """Runs search in the background so UI stays responsive."""

    finished_ok = pyqtSignal(list)
    error       = pyqtSignal(str)

    def __init__(self, kind: str, **kwargs):
        super().__init__()
        self.kind = kind
        self.kwargs = kwargs

    def run(self):
        try:
            if self.kind == "text":
                res = search_text(**self.kwargs)
            elif self.kind == "image":
                res = search_image(**self.kwargs)
            elif self.kind == "trademark":
                res = search_trademark(**self.kwargs)
            else:
                res = []
            self.finished_ok.emit(res)
        except Exception as e:
            import traceback
            self.error.emit(f"{e}\n\n{traceback.format_exc()}")


class SearchPage(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: SearchWorker | None = None
        self._image_query_path: str | None = None
        self._build_ui()

    def on_show(self):
        self._refresh_project_lists()

    def refresh(self):
        self._refresh_project_lists()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(10)

        title = QLabel("Live Search")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        root.addWidget(title)

        subtitle = QLabel(
            "Search across all indexed content. No re-scan needed."
        )
        subtitle.setFont(QFont("Segoe UI", 9))
        root.addWidget(subtitle)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_text_tab(),     "Text Search")
        self._tabs.addTab(self._build_image_tab(),    "Image Search")
        self._tabs.addTab(self._build_trademark_tab(), "Trademark Search")
        root.addWidget(self._tabs, 1)

    # ─────────────────────────────────────────
    # TEXT SEARCH TAB
    # ─────────────────────────────────────────
    def _build_text_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 0)

        grp = QGroupBox("Text Query")
        gl  = QVBoxLayout(grp)

        row_input = QHBoxLayout()
        row_input.addWidget(QLabel("Search:"))
        self._text_input = QLineEdit()
        self._text_input.setPlaceholderText(
            "Type a word, phrase, or sentence to find similar content..."
        )
        self._text_input.setFixedHeight(28)
        self._text_input.returnPressed.connect(self._run_text_search)
        row_input.addWidget(self._text_input, 1)

        self._text_btn = QPushButton("Search")
        self._text_btn.setFixedHeight(28)
        self._text_btn.setMinimumWidth(100)
        self._text_btn.clicked.connect(self._run_text_search)
        row_input.addWidget(self._text_btn)
        gl.addLayout(row_input)

        row_scope = QHBoxLayout()
        row_scope.addWidget(QLabel("Scope:"))
        self._text_scope = QComboBox()
        self._text_scope.setFixedHeight(26)
        self._text_scope.setMinimumWidth(220)
        self._text_scope.addItem("All Projects", None)
        row_scope.addWidget(self._text_scope)
        row_scope.addStretch()
        gl.addLayout(row_scope)

        layout.addWidget(grp)

        self._text_status = QLabel("")
        self._text_status.setFont(QFont("Segoe UI", 9))
        layout.addWidget(self._text_status)

        self._text_table = QTableWidget()
        self._text_table.setColumnCount(6)
        self._text_table.setHorizontalHeaderLabels([
            "Score", "Project", "File", "Page", "Type", "Preview"
        ])
        self._text_table.verticalHeader().setVisible(False)
        self._text_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._text_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._text_table.setAlternatingRowColors(True)
        hdr = self._text_table.horizontalHeader()
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        for col in (0, 1, 2, 3, 4):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self._text_table, 1)

        return page

    def _run_text_search(self):
        query = self._text_input.text().strip()
        if not query:
            return
        pid = self._text_scope.currentData()

        self._text_btn.setEnabled(False)
        self._text_status.setText("Searching...")

        self._worker = SearchWorker("text", query=query, project_id=pid)
        self._worker.finished_ok.connect(self._on_text_results)
        self._worker.error.connect(self._on_search_error)
        self._worker.start()

    def _on_text_results(self, results: list):
        self._text_btn.setEnabled(True)
        self._text_status.setText(f"{len(results)} result(s) found.")
        self._text_table.setRowCount(0)

        for r in results:
            row = self._text_table.rowCount()
            self._text_table.insertRow(row)
            self._text_table.setItem(row, 0, QTableWidgetItem(f"{r['score']*100:.1f}%"))
            self._text_table.setItem(row, 1, QTableWidgetItem(r["project_name"] or ""))
            self._text_table.setItem(row, 2, QTableWidgetItem(r["file_name"] or ""))
            self._text_table.setItem(row, 3, QTableWidgetItem(str(r["page_number"] or 0)))
            self._text_table.setItem(row, 4, QTableWidgetItem(r["chunk_type"] or ""))
            self._text_table.setItem(row, 5, QTableWidgetItem(r["snippet"] or ""))

    # ─────────────────────────────────────────
    # IMAGE SEARCH TAB
    # ─────────────────────────────────────────
    def _build_image_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 0)

        grp = QGroupBox("Image Query")
        gl  = QVBoxLayout(grp)

        row_pick = QHBoxLayout()
        self._img_btn_browse = QPushButton("Browse Image...")
        self._img_btn_browse.setFixedHeight(30)
        self._img_btn_browse.setMinimumWidth(150)
        self._img_btn_browse.clicked.connect(self._on_pick_image)

        self._img_path_lbl = QLabel("No image selected")
        self._img_path_lbl.setFont(QFont("Segoe UI", 9))

        row_pick.addWidget(self._img_btn_browse)
        row_pick.addWidget(self._img_path_lbl, 1)
        gl.addLayout(row_pick)

        self._img_preview = QLabel()
        self._img_preview.setFixedSize(150, 150)
        self._img_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._img_preview.setText("Preview")
        self._img_preview.setStyleSheet("border: 1px solid #ccc;")
        gl.addWidget(self._img_preview)

        row_scope = QHBoxLayout()
        row_scope.addWidget(QLabel("Scope:"))
        self._img_scope = QComboBox()
        self._img_scope.setFixedHeight(26)
        self._img_scope.setMinimumWidth(220)
        self._img_scope.addItem("All Projects", None)
        row_scope.addWidget(self._img_scope)

        self._img_btn = QPushButton("Search")
        self._img_btn.setFixedHeight(28)
        self._img_btn.setMinimumWidth(100)
        self._img_btn.clicked.connect(self._run_image_search)
        row_scope.addWidget(self._img_btn)
        row_scope.addStretch()
        gl.addLayout(row_scope)

        layout.addWidget(grp)

        self._img_status = QLabel("")
        self._img_status.setFont(QFont("Segoe UI", 9))
        layout.addWidget(self._img_status)

        self._img_table = QTableWidget()
        self._img_table.setColumnCount(6)
        self._img_table.setHorizontalHeaderLabels([
            "Score", "Project", "File", "Page", "Dimensions", "Path"
        ])
        self._img_table.verticalHeader().setVisible(False)
        self._img_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._img_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._img_table.setAlternatingRowColors(True)
        hdr = self._img_table.horizontalHeader()
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        for col in (0, 1, 2, 3, 4):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self._img_table, 1)

        return page

    def _on_pick_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Query Image", "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp)"
        )
        if path:
            self._image_query_path = path
            self._img_path_lbl.setText(Path(path).name)
            pix = QPixmap(path)
            if not pix.isNull():
                pix = pix.scaled(
                    150, 150,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self._img_preview.setPixmap(pix)

    def _run_image_search(self):
        if not self._image_query_path:
            QMessageBox.warning(self, "No Image", "Please select an image first.")
            return
        pid = self._img_scope.currentData()

        self._img_btn.setEnabled(False)
        self._img_status.setText("Searching...")

        self._worker = SearchWorker(
            "image",
            image_path=self._image_query_path,
            project_id=pid,
        )
        self._worker.finished_ok.connect(self._on_image_results)
        self._worker.error.connect(self._on_search_error)
        self._worker.start()

    def _on_image_results(self, results: list):
        self._img_btn.setEnabled(True)
        self._img_status.setText(f"{len(results)} similar image(s) found.")
        self._img_table.setRowCount(0)

        for r in results:
            row = self._img_table.rowCount()
            self._img_table.insertRow(row)
            self._img_table.setItem(row, 0, QTableWidgetItem(f"{r['score']*100:.1f}%"))
            self._img_table.setItem(row, 1, QTableWidgetItem(r["project_name"] or ""))
            self._img_table.setItem(row, 2, QTableWidgetItem(r["file_name"] or ""))
            self._img_table.setItem(row, 3, QTableWidgetItem(str(r["page_number"] or 0)))
            self._img_table.setItem(row, 4, QTableWidgetItem(f"{r['width']}x{r['height']}"))
            self._img_table.setItem(row, 5, QTableWidgetItem(r["stored_path"] or ""))

    # ─────────────────────────────────────────
    # TRADEMARK SEARCH TAB
    # ─────────────────────────────────────────
    def _build_trademark_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 0)

        grp = QGroupBox("Trademark Query")
        gl  = QVBoxLayout(grp)

        info = QLabel(
            "Search the trademark registry (IP / WIPO mode) for similar brand names."
        )
        info.setWordWrap(True)
        gl.addWidget(info)

        row = QHBoxLayout()
        row.addWidget(QLabel("Brand Name:"))
        self._tm_input = QLineEdit()
        self._tm_input.setPlaceholderText("e.g. Coca-Cola")
        self._tm_input.setFixedHeight(28)
        self._tm_input.returnPressed.connect(self._run_trademark_search)
        row.addWidget(self._tm_input, 1)

        self._tm_btn = QPushButton("Search")
        self._tm_btn.setFixedHeight(28)
        self._tm_btn.setMinimumWidth(100)
        self._tm_btn.clicked.connect(self._run_trademark_search)
        row.addWidget(self._tm_btn)
        gl.addLayout(row)

        row_class = QHBoxLayout()
        row_class.addWidget(QLabel("Nice Class:"))
        self._tm_class = QComboBox()
        self._tm_class.setFixedHeight(26)
        self._tm_class.setMinimumWidth(260)
        self._tm_class.addItem("All Classes", None)
                # Load Nice Classes — with hardcoded fallback so it always works
        nice_classes_loaded = False
        try:
            from database.ip_models import nice_class_choices
            for num, label in nice_class_choices():
                self._tm_class.addItem(label, num)
            nice_classes_loaded = True
        except Exception as e:
            print(f"nice_class_choices import failed: {e}")

        if not nice_classes_loaded:
            # Hardcoded fallback
            _CLASSES = {
                1: "Chemicals", 2: "Paints", 3: "Cosmetics", 4: "Oils and fuels",
                5: "Pharmaceuticals", 6: "Metal goods", 7: "Machinery",
                8: "Hand tools", 9: "Electronics", 10: "Medical apparatus",
                11: "Environmental apparatus", 12: "Vehicles", 13: "Firearms",
                14: "Jewellery", 15: "Musical instruments", 16: "Paper goods",
                17: "Rubber goods", 18: "Leather goods", 19: "Building materials",
                20: "Furniture", 21: "Housewares", 22: "Cordage",
                23: "Yarns", 24: "Fabrics", 25: "Clothing",
                26: "Fancy goods", 27: "Floor coverings", 28: "Toys and sports",
                29: "Meats and processed foods", 30: "Staple foods",
                31: "Agricultural products", 32: "Beverages", 33: "Wines and spirits",
                34: "Smokers' articles", 35: "Advertising", 36: "Financial services",
                37: "Construction", 38: "Telecommunications", 39: "Transportation",
                40: "Material treatment", 41: "Education and entertainment",
                42: "Scientific services", 43: "Food services",
                44: "Medical services", 45: "Legal services",
            }
            for num in sorted(_CLASSES.keys()):
                label = f"Class {num} — {_CLASSES[num]}"
                self._tm_class.addItem(label, num)
        row_class.addWidget(self._tm_class)
        row_class.addStretch()
        gl.addLayout(row_class)

        layout.addWidget(grp)

        self._tm_status = QLabel("")
        self._tm_status.setFont(QFont("Segoe UI", 9))
        layout.addWidget(self._tm_status)

        self._tm_table = QTableWidget()
        self._tm_table.setColumnCount(6)
        self._tm_table.setHorizontalHeaderLabels([
            "Score", "Verdict", "Trademark Name", "Reg. No.", "Class", "Owner"
        ])
        self._tm_table.verticalHeader().setVisible(False)
        self._tm_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tm_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._tm_table.setAlternatingRowColors(True)
        hdr = self._tm_table.horizontalHeader()
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        for col in (0, 1, 3, 4, 5):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self._tm_table, 1)

        return page

    def _run_trademark_search(self):
        query = self._tm_input.text().strip()
        if not query:
            return

        # Check if registry has any trademarks
        try:
            from database.db import get_trademark_count
            count = get_trademark_count()
        except Exception:
            count = 0

        if count == 0:
            QMessageBox.information(
                self, "Registry Empty",
                "The trademark registry is empty.\n\n"
                "You need to import trademarks first:\n"
                "1. Switch to IP / WIPO mode (if available)\n"
                "2. Go to Registry page\n"
                "3. Import a CSV or Excel file of trademarks\n\n"
                "Or add trademarks manually via the database."
            )
            return

        nc = self._tm_class.currentData()

        self._tm_btn.setEnabled(False)
        self._tm_status.setText(f"Searching {count} trademark(s)...")

        self._worker = SearchWorker("trademark", query=query, nice_class=nc)
        self._worker.finished_ok.connect(self._on_tm_results)
        self._worker.error.connect(self._on_search_error)
        self._worker.start()

    def _on_tm_results(self, results: list):
        self._tm_btn.setEnabled(True)
        self._tm_status.setText(f"{len(results)} match(es) in registry.")
        self._tm_table.setRowCount(0)

        for r in results:
            row = self._tm_table.rowCount()
            self._tm_table.insertRow(row)
            self._tm_table.setItem(row, 0, QTableWidgetItem(f"{r['overall_score']*100:.1f}%"))

            verdict_item = QTableWidgetItem(r["verdict"])
            color = VERDICT_COLORS.get(r["verdict"], "#555")
            verdict_item.setForeground(QColor(color))
            self._tm_table.setItem(row, 1, verdict_item)

            self._tm_table.setItem(row, 2, QTableWidgetItem(r["trademark_name"] or ""))
            self._tm_table.setItem(row, 3, QTableWidgetItem(r["registration_number"] or ""))

            nc = r["nice_class"]
            nc_str = f"Class {nc}" if nc else "—"
            self._tm_table.setItem(row, 4, QTableWidgetItem(nc_str))
            self._tm_table.setItem(row, 5, QTableWidgetItem(r["owner_name"] or ""))

    # ─────────────────────────────────────────
    # SHARED
    # ─────────────────────────────────────────
    def _on_search_error(self, msg: str):
        self._text_btn.setEnabled(True)
        self._img_btn.setEnabled(True)
        self._tm_btn.setEnabled(True)
        QMessageBox.critical(self, "Search Error", msg)

    def _refresh_project_lists(self):
        try:
            projects = get_all_projects()
        except Exception:
            projects = []

        for combo in (self._text_scope, self._img_scope):
            current = combo.currentData()
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("All Projects", None)
            for p in projects:
                combo.addItem(p["name"], p["id"])
            # Restore selection if possible
            for i in range(combo.count()):
                if combo.itemData(i) == current:
                    combo.setCurrentIndex(i)
                    break
            combo.blockSignals(False)