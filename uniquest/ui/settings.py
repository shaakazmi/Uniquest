from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QGroupBox,
    QLabel, QPushButton, QComboBox, QDoubleSpinBox,
    QLineEdit, QHBoxLayout, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from database.db import get_setting, set_setting
from utils.theme import apply_theme


class SettingsPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self._build_ui()
        self._load_settings()

    def on_show(self):
        self._load_settings()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # appearance
        appear_group  = QGroupBox("Appearance")
        appear_layout = QFormLayout(appear_group)

        self._theme_combo = QComboBox()
        self._theme_combo.addItems(["Light", "Dark"])
        appear_layout.addRow("Theme:", self._theme_combo)
        layout.addWidget(appear_group)

        # similarity thresholds
        thresh_group  = QGroupBox("Similarity Thresholds")
        thresh_layout = QFormLayout(thresh_group)

        self._text_thresh = QDoubleSpinBox()
        self._text_thresh.setRange(0.50, 1.00)
        self._text_thresh.setSingleStep(0.05)
        self._text_thresh.setDecimals(2)

        self._image_thresh = QDoubleSpinBox()
        self._image_thresh.setRange(0.50, 1.00)
        self._image_thresh.setSingleStep(0.05)
        self._image_thresh.setDecimals(2)

        thresh_layout.addRow("Text Similarity Threshold:", self._text_thresh)
        thresh_layout.addRow("Image Similarity Threshold:", self._image_thresh)
        layout.addWidget(thresh_group)

        # storage
        storage_group  = QGroupBox("Storage")
        storage_layout = QFormLayout(storage_group)

        self._storage_combo = QComboBox()
        self._storage_combo.addItems(["Reference (keep files in place)", "Copy to app folder"])
        storage_layout.addRow("Default Storage Mode:", self._storage_combo)

        export_row   = QHBoxLayout()
        self._export_path = QLineEdit()
        self._export_path.setReadOnly(True)
        btn_browse = QPushButton("Browse...")
        btn_browse.setMinimumWidth(90)
        btn_browse.setFixedHeight(26)
        btn_browse.clicked.connect(self._pick_export_folder)
        export_row.addWidget(self._export_path, 1)
        export_row.addWidget(btn_browse)
        storage_layout.addRow("Export Folder:", export_row)

        layout.addWidget(storage_group)

        # save button
        btn_row  = QHBoxLayout()
        btn_save = QPushButton("Save Settings")
        btn_save.setObjectName("primary_btn")
        btn_save.setFixedHeight(32)
        btn_save.setMinimumWidth(140)
        btn_save.clicked.connect(self._save_settings)
        btn_row.addStretch()
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)

        layout.addStretch()

    def _load_settings(self):
        theme = get_setting("theme", "light")
        self._theme_combo.setCurrentIndex(0 if theme == "light" else 1)

        tt = float(get_setting("text_similarity_threshold",  "0.75"))
        it = float(get_setting("image_similarity_threshold", "0.85"))
        self._text_thresh.setValue(tt)
        self._image_thresh.setValue(it)

        sm = get_setting("default_storage_mode", "reference")
        self._storage_combo.setCurrentIndex(0 if sm == "reference" else 1)

        from pathlib import Path
        ep = get_setting("export_path", str(Path.home() / "Documents"))
        self._export_path.setText(ep)

    def _pick_export_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Select Export Folder",
                                              self._export_path.text())
        if d:
            self._export_path.setText(d)

    def _save_settings(self):
        theme = "light" if self._theme_combo.currentIndex() == 0 else "dark"
        set_setting("theme", theme)
        set_setting("text_similarity_threshold",  str(self._text_thresh.value()))
        set_setting("image_similarity_threshold",  str(self._image_thresh.value()))
        sm = "reference" if self._storage_combo.currentIndex() == 0 else "copy"
        set_setting("default_storage_mode", sm)
        set_setting("export_path", self._export_path.text())

        from PyQt6.QtWidgets import QApplication
        apply_theme(QApplication.instance(), theme)

        QMessageBox.information(self, "Settings", "Settings saved successfully.")