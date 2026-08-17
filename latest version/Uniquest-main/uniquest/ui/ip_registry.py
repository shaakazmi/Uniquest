"""
Trademark Registry Page for IPOGenie.
Manages the trademark database and imports data from CSV, Excel,
or Pakistan IPO Trade Marks Journal PDFs.
"""

import csv
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QFileDialog, QMessageBox, QComboBox, QLineEdit,
    QAbstractItemView, QProgressDialog,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap

import database.db as db


# ─────────────────────────────────────────────
# NICE CLASSES (hardcoded fallback)
# ─────────────────────────────────────────────

NICE_CLASSES = {
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


def nice_class_label(class_num: Optional[int]) -> str:
    if class_num is None:
        return "Unknown"
    desc = NICE_CLASSES.get(class_num, "Unknown")
    return f"Class {class_num} — {desc}"


# ═════════════════════════════════════════════
# CSV / EXCEL IMPORT WORKER
# ═════════════════════════════════════════════

class _CsvExcelWorker(QThread):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(int, list)
    error    = pyqtSignal(str)

    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self.file_path = file_path

    def run(self):
        path = Path(self.file_path)
        ext = path.suffix.lower()

        try:
            if ext == ".csv":
                rows = self._read_csv()
            elif ext in (".xlsx", ".xls"):
                rows = self._read_excel()
            else:
                self.error.emit(f"Unsupported file type: {ext}")
                return
        except Exception as e:
            self.error.emit(f"Could not read file: {e}")
            return

        total = len(rows)
        imported = 0
        errors = []

        for i, row in enumerate(rows):
            self.progress.emit(i + 1, total)
            try:
                name = str(row.get("trademark_name", row.get("name", ""))).strip()
                if not name:
                    errors.append(f"Row {i+2}: Missing trademark name")
                    continue

                reg_num = str(row.get("registration_number",
                                      row.get("reg_number", f"IMP-{i+1}"))).strip()

                nice_class = None
                nice_raw = row.get("nice_class", row.get("class", ""))
                if nice_raw:
                    try:
                        nice_class = int(str(nice_raw).strip())
                    except ValueError:
                        pass

                db.insert_trademark(
                    registration_number=reg_num,
                    trademark_name=name,
                    logo_path=str(row.get("logo_path", "")).strip() or None,
                    nice_class=nice_class,
                    owner_name=str(row.get("owner_name", row.get("owner", ""))).strip(),
                    registration_date=str(row.get("registration_date",
                                                  row.get("date", ""))).strip() or None,
                    status=str(row.get("status", "registered")).strip().lower(),
                    country=str(row.get("country", "")).strip(),
                )
                imported += 1
            except Exception as e:
                errors.append(f"Row {i+2}: {e}")

        self.finished.emit(imported, errors)

    def _read_csv(self) -> list:
        rows = []
        with open(self.file_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append({k.lower().strip(): v for k, v in row.items()})
        return rows

    def _read_excel(self) -> list:
        try:
            import openpyxl
        except ImportError:
            raise ImportError("openpyxl is required to read Excel files.")

        wb = openpyxl.load_workbook(self.file_path, read_only=True, data_only=True)
        ws = wb.active
        rows_iter = ws.iter_rows(values_only=True)

        headers = [str(h).lower().strip() if h else f"col_{i}"
                   for i, h in enumerate(next(rows_iter, []))]

        result = []
        for row in rows_iter:
            result.append({
                headers[i]: (row[i] if i < len(row) else "")
                for i in range(len(headers))
            })

        wb.close()
        return result


# ═════════════════════════════════════════════
# JOURNAL PDF IMPORT WORKER
# ═════════════════════════════════════════════

class _JournalWorker(QThread):
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(list, int, list)
    error    = pyqtSignal(str)

    def __init__(self, pdf_path: str, logo_dir: str, parent=None):
        super().__init__(parent)
        self.pdf_path = pdf_path
        self.logo_dir = logo_dir
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            from core.journal_parser import parse_journal_pdf

            trademarks = parse_journal_pdf(
                self.pdf_path,
                self.logo_dir,
                progress_cb=lambda c, t, m: self.progress.emit(c, t, m),
                cancel_check=lambda: self._cancelled,
            )

            imported = 0
            errors = []
            total = len(trademarks)

            for i, tm in enumerate(trademarks):
                if self._cancelled:
                    break
                try:
                    self.progress.emit(
                        i + 1, total,
                        f"Saving {i+1}/{total}: {tm.trademark_name[:40]}"
                    )
                    db.insert_trademark(
                        registration_number=tm.application_number or f"IMP-{i+1}",
                        trademark_name=tm.trademark_name,
                        logo_path=tm.logo_path,
                        nice_class=tm.nice_class,
                        owner_name=tm.applicant_name,
                        registration_date=tm.filing_date,
                        status="registered",
                        country=tm.country,
                    )
                    imported += 1
                except Exception as e:
                    errors.append(f"App# {tm.application_number}: {e}")

            self.finished.emit(trademarks, imported, errors)
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self.error.emit(f"{e}\n\n{tb}")


# ═════════════════════════════════════════════
# REGISTRY PAGE
# ═════════════════════════════════════════════

class RegistryPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_rows = []
        self._csv_worker = None
        self._journal_worker = None
        self._build_ui()
        self.refresh()

    def on_show(self):
        self.refresh()

    # ─────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("Trademark Registry")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        hdr.addWidget(title)
        hdr.addStretch()
        self._lbl_count = QLabel("0 trademarks")
        self._lbl_count.setFont(QFont("Segoe UI", 10))
        hdr.addWidget(self._lbl_count)
        root.addLayout(hdr)

        # ── Import section ──
        grp_import = QGroupBox("Import Trademarks")
        imp_layout = QVBoxLayout(grp_import)

        info = QLabel(
            "Import trademarks from CSV, Excel, or a Pakistan IPO Trade Marks Journal PDF.\n"
            "CSV/Excel required column: trademark_name\n"
            "Optional: registration_number, nice_class, owner_name, "
            "registration_date, status, country, logo_path"
        )
        info.setWordWrap(True)
        imp_layout.addWidget(info)

        btn_row = QHBoxLayout()

        self._btn_import_csv = QPushButton("Import CSV")
        self._btn_import_csv.setFixedHeight(32)
        self._btn_import_csv.setMinimumWidth(140)
        self._btn_import_csv.clicked.connect(self._on_import_csv)

        self._btn_import_excel = QPushButton("Import Excel")
        self._btn_import_excel.setFixedHeight(32)
        self._btn_import_excel.setMinimumWidth(140)
        self._btn_import_excel.clicked.connect(self._on_import_excel)

        self._btn_import_journal = QPushButton("Import Journal PDF")
        self._btn_import_journal.setFixedHeight(32)
        self._btn_import_journal.setMinimumWidth(180)
        self._btn_import_journal.clicked.connect(self._on_import_journal)

        self._btn_clear = QPushButton("Clear Registry")
        self._btn_clear.setFixedHeight(32)
        self._btn_clear.setMinimumWidth(140)
        self._btn_clear.clicked.connect(self._on_clear)

        btn_row.addWidget(self._btn_import_csv)
        btn_row.addWidget(self._btn_import_excel)
        btn_row.addWidget(self._btn_import_journal)
        btn_row.addStretch()
        btn_row.addWidget(self._btn_clear)
        imp_layout.addLayout(btn_row)

        root.addWidget(grp_import)

        # ── Filter section ──
        grp_filter = QGroupBox("Filter")
        f_layout = QHBoxLayout(grp_filter)

        f_layout.addWidget(QLabel("Search:"))
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("Search trademark, applicant, application number...")
        self._search_box.setFixedHeight(28)
        self._search_box.textChanged.connect(self._trademark_name)
        f_layout.addWidget(self._search_box)

        f_layout.addWidget(QLabel("Nice Class:"))
        self._class_combo = QComboBox()
        self._class_combo.setFixedHeight(28)
        self._class_combo.setMinimumWidth(220)
        self._class_combo.addItem("All Classes", None)
        for num in sorted(NICE_CLASSES.keys()):
            self._class_combo.addItem(nice_class_label(num), num)
        self._class_combo.currentIndexChanged.connect(self._apply_filter)
        f_layout.addWidget(self._class_combo)

        f_layout.addStretch()
        root.addWidget(grp_filter)

        # ── Table ──
        grp_table = QGroupBox("Registered Trademarks")
        t_layout = QVBoxLayout(grp_table)

        self._table = QTableWidget()
        self._table.setColumnCount(8)
        self._table.setHorizontalHeaderLabels([
            "Logo", "Reg. Number", "Trademark Name", "Nice Class",
            "Owner", "Status", "Country", "Reg. Date"
        ])
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(56)

        hdr_view = self._table.horizontalHeader()
        hdr_view.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hdr_view.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        for col in (0, 1, 3, 5, 6, 7):
            hdr_view.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)

        t_layout.addWidget(self._table)

        tbl_btns = QHBoxLayout()
        self._btn_del_sel = QPushButton("Delete Selected")
        self._btn_del_sel.setFixedHeight(28)
        self._btn_del_sel.clicked.connect(self._on_delete_selected)
        tbl_btns.addWidget(self._btn_del_sel)
        tbl_btns.addStretch()

        self._btn_refresh = QPushButton("Refresh")
        self._btn_refresh.setFixedHeight(28)
        self._btn_refresh.clicked.connect(self.refresh)
        tbl_btns.addWidget(self._btn_refresh)
        t_layout.addLayout(tbl_btns)

        root.addWidget(grp_table, 1)

    # ─────────────────────────────────────────
    def refresh(self):
        try:
            self._all_rows = db.get_all_trademarks()
        except Exception as e:
            print(f"Registry refresh error: {e}")
            self._all_rows = []
        self._lbl_count.setText(f"{len(self._all_rows):,} trademark(s)")
        self._apply_filter()

    def _apply_filter(self):
        search = self._search_box.text().lower().strip()
        cls = self._class_combo.currentData()

        filtered = []
        for row in self._all_rows:
            name = (row.get("trademark_name") or "").lower()
            nc = row.get("nice_class")
            if search and search not in name:
                continue
            if cls is not None and nc != cls:
                continue
            filtered.append(row)

        self._populate_table(filtered)

    def _populate_table(self, rows: list):
        self._table.setRowCount(0)
        for row in rows:
            r = self._table.rowCount()
            self._table.insertRow(r)

            # Logo thumbnail
            logo_cell = QTableWidgetItem("")
            logo_path = row.get("logo_path")
            if logo_path and Path(logo_path).exists():
                pix = QPixmap(logo_path)
                if not pix.isNull():
                    pix = pix.scaled(
                        48, 48,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    logo_cell.setData(Qt.ItemDataRole.DecorationRole, pix)
            logo_cell.setData(Qt.ItemDataRole.UserRole, row.get("id"))
            self._table.setItem(r, 0, logo_cell)

            values = [
                row.get("registration_number", ""),
                row.get("trademark_name", ""),
                nice_class_label(row.get("nice_class")),
                row.get("owner_name", ""),
                (row.get("status") or "").title(),
                row.get("country", ""),
                row.get("registration_date", ""),
            ]
            for col, val in enumerate(values, start=1):
                item = QTableWidgetItem(str(val) if val else "")
                item.setData(Qt.ItemDataRole.UserRole, row.get("id"))
                self._table.setItem(r, col, item)

    # ─────────────────────────────────────────
    # CSV / EXCEL IMPORT
    # ─────────────────────────────────────────
    def _on_import_csv(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import CSV Registry", "", "CSV Files (*.csv)"
        )
        if path:
            self._start_csv_excel_import(path)

    def _on_import_excel(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Excel Registry", "", "Excel Files (*.xlsx *.xls)"
        )
        if path:
            self._start_csv_excel_import(path)

    def _start_csv_excel_import(self, path: str):
        self._csv_progress = QProgressDialog(
            "Importing trademarks...", "Cancel", 0, 100, self
        )
        self._csv_progress.setWindowTitle("Importing")
        self._csv_progress.setWindowModality(Qt.WindowModality.WindowModal)
        self._csv_progress.show()

        self._csv_worker = _CsvExcelWorker(path, parent=self)
        self._csv_worker.progress.connect(self._on_csv_progress)
        self._csv_worker.finished.connect(self._on_csv_finished)
        self._csv_worker.error.connect(self._on_csv_error)
        self._csv_worker.start()

    def _on_csv_progress(self, current: int, total: int):
        if total > 0:
            pct = int(current / total * 100)
            self._csv_progress.setValue(pct)

    def _on_csv_finished(self, imported: int, errors: list):
        self._csv_progress.close()
        self.refresh()

        msg = f"Import complete.\n\n{imported} trademarks imported."
        if errors:
            msg += f"\n\n{len(errors)} errors:\n" + "\n".join(errors[:10])
            if len(errors) > 10:
                msg += f"\n... and {len(errors) - 10} more."
        QMessageBox.information(self, "Import Complete", msg)

    def _on_csv_error(self, message: str):
        self._csv_progress.close()
        QMessageBox.critical(self, "Import Error", message)

    # ─────────────────────────────────────────
    # JOURNAL PDF IMPORT
    # ─────────────────────────────────────────
    def _on_import_journal(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Trade Marks Journal PDF", "",
            "PDF Files (*.pdf)"
        )
        if not path:
            return

        reply = QMessageBox.question(
            self,
            "Import Journal",
            "This will parse every page of the journal to extract trademarks.\n\n"
            "Large journals may take several minutes.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        logo_dir = Path.home() / ".ipogenie" / "trademark_logos"
        logo_dir.mkdir(parents=True, exist_ok=True)

        self._journal_progress = QProgressDialog(
            "Parsing journal PDF...", "Cancel", 0, 100, self
        )
        self._journal_progress.setWindowTitle("Import Trademark Journal")
        self._journal_progress.setWindowModality(Qt.WindowModality.WindowModal)
        self._journal_progress.show()

        self._journal_worker = _JournalWorker(path, str(logo_dir), parent=self)
        self._journal_worker.progress.connect(self._on_journal_progress)
        self._journal_worker.finished.connect(self._on_journal_finished)
        self._journal_worker.error.connect(self._on_journal_error)
        self._journal_progress.canceled.connect(self._journal_worker.cancel)
        self._journal_worker.start()

    def _on_journal_progress(self, current: int, total: int, msg: str):
        if total > 0:
            pct = int(current / total * 100)
            self._journal_progress.setValue(pct)
        self._journal_progress.setLabelText(msg)

    def _on_journal_finished(self, trademarks: list, imported: int, errors: list):
        self._journal_progress.close()
        self.refresh()

        msg = (
            f"Journal import complete.\n\n"
            f"Trademarks extracted: {len(trademarks)}\n"
            f"Successfully imported: {imported}\n"
        )
        if errors:
            msg += f"\nErrors: {len(errors)}\n"
            msg += "\n".join(errors[:5])
            if len(errors) > 5:
                msg += f"\n... and {len(errors) - 5} more."
        QMessageBox.information(self, "Import Complete", msg)

    def _on_journal_error(self, error: str):
        self._journal_progress.close()
        QMessageBox.critical(self, "Journal Import Error", error)

    # ─────────────────────────────────────────
    # DELETE / CLEAR
    # ─────────────────────────────────────────
    def _on_clear(self):
        count = db.get_trademark_count()
        if count == 0:
            QMessageBox.information(self, "Registry Empty",
                                    "The registry is already empty.")
            return
        reply = QMessageBox.question(
            self, "Clear Registry",
            f"Delete all {count:,} trademark(s)?\n\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            db.clear_all_trademarks()
            self.refresh()

    def _on_delete_selected(self):
        selected = self._table.selectedItems()
        if not selected:
            return
        ids = set()
        for item in selected:
            tid = item.data(Qt.ItemDataRole.UserRole)
            if tid:
                ids.add(tid)
        if not ids:
            return
        reply = QMessageBox.question(
            self, "Delete Trademarks",
            f"Delete {len(ids)} trademark(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            for tid in ids:
                db.delete_trademark(tid)
            self.refresh()