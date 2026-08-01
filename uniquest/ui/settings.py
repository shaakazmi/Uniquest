from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QGroupBox,
    QScrollArea, QSlider, QComboBox,
    QLineEdit, QFileDialog, QMessageBox,
    QRadioButton, QButtonGroup, QApplication,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap

from utils.theme import ThemeManager, build_stylesheet, refresh_theme
from database.db import get_setting, set_setting, get_db_path


class SettingsPage(QWidget):
    theme_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._unsaved = False
        self._build()
        ThemeManager.add_listener(self.apply_theme)

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        self.main_layout = QVBoxLayout(content)
        self.main_layout.setContentsMargins(16, 12, 16, 12)
        self.main_layout.setSpacing(12)

        # Appearance
        appearance = QGroupBox("Appearance")
        a_layout = QVBoxLayout(appearance)
        a_layout.setContentsMargins(10, 14, 10, 10)
        a_layout.setSpacing(6)

        a_layout.addWidget(QLabel("Theme:"))
        theme_row = QHBoxLayout()
        theme_row.setSpacing(10)

        self.theme_group = QButtonGroup(self)
        self.radio_light = QRadioButton("Light")
        self.radio_dark = QRadioButton("Dark")
        if ThemeManager.is_dark():
            self.radio_dark.setChecked(True)
        else:
            self.radio_light.setChecked(True)
        self.radio_light.toggled.connect(
            lambda c: self._on_theme_selected("light") if c else None
        )
        self.radio_dark.toggled.connect(
            lambda c: self._on_theme_selected("dark") if c else None
        )
        self.theme_group.addButton(self.radio_light)
        self.theme_group.addButton(self.radio_dark)
        theme_row.addWidget(self.radio_light)
        theme_row.addWidget(self.radio_dark)
        theme_row.addStretch()
        a_layout.addLayout(theme_row)

        self.main_layout.addWidget(appearance)

        # Thresholds
        thresh = QGroupBox("Similarity Thresholds")
        t_layout = QVBoxLayout(thresh)
        t_layout.setContentsMargins(10, 14, 10, 10)
        t_layout.setSpacing(6)

        t_layout.addWidget(QLabel("Text similarity threshold:"))
        text_row = QHBoxLayout()
        saved_text = int(float(get_setting("text_similarity_threshold", "0.70")) * 100)
        self.text_slider = QSlider(Qt.Orientation.Horizontal)
        self.text_slider.setRange(50, 100)
        self.text_slider.setValue(saved_text)
        self.text_slider.setFixedWidth(200)
        self.text_slider.valueChanged.connect(lambda v: self._on_text_slider(v))
        self.text_val_lbl = QLabel(f"{saved_text}%")
        self.text_val_lbl.setFixedWidth(40)
        self.text_val_lbl.setStyleSheet(
            "font-weight: 700; background: transparent; border: 0px;"
        )
        text_row.addWidget(QLabel("50%"))
        text_row.addWidget(self.text_slider)
        text_row.addWidget(QLabel("100%"))
        text_row.addWidget(self.text_val_lbl)
        text_row.addStretch()
        t_layout.addLayout(text_row)

        t_layout.addSpacing(6)
        t_layout.addWidget(QLabel("Image similarity threshold:"))
        img_row = QHBoxLayout()
        saved_img = int(float(get_setting("image_similarity_threshold", "0.85")) * 100)
        self.img_slider = QSlider(Qt.Orientation.Horizontal)
        self.img_slider.setRange(50, 100)
        self.img_slider.setValue(saved_img)
        self.img_slider.setFixedWidth(200)
        self.img_slider.valueChanged.connect(lambda v: self._on_img_slider(v))
        self.img_val_lbl = QLabel(f"{saved_img}%")
        self.img_val_lbl.setFixedWidth(40)
        self.img_val_lbl.setStyleSheet(
            "font-weight: 700; background: transparent; border: 0px;"
        )
        img_row.addWidget(QLabel("50%"))
        img_row.addWidget(self.img_slider)
        img_row.addWidget(QLabel("100%"))
        img_row.addWidget(self.img_val_lbl)
        img_row.addStretch()
        t_layout.addLayout(img_row)

        hint = QLabel("Lower = more matches found. Higher = only near-identical.")
        hint.setStyleSheet(
            "font-size: 11px; color: #767676;"
            "background: transparent; border: 0px;"
        )
        t_layout.addWidget(hint)

        self.main_layout.addWidget(thresh)

        # Export
        exp = QGroupBox("Export")
        e_layout = QVBoxLayout(exp)
        e_layout.setContentsMargins(10, 14, 10, 10)
        e_layout.setSpacing(6)
        e_layout.addWidget(QLabel("Default export folder:"))
        exp_row = QHBoxLayout()
        saved_path = get_setting("export_path", str(Path.home() / "Documents"))
        self.export_path_input = QLineEdit(saved_path)
        self.export_path_input.textChanged.connect(lambda: self._mark_unsaved())
        browse = QPushButton("Browse...")
        browse.setMinimumWidth(90)
        browse.clicked.connect(self._on_browse_export)
        exp_row.addWidget(self.export_path_input)
        exp_row.addWidget(browse)
        e_layout.addLayout(exp_row)
        self.main_layout.addWidget(exp)

        # Data
        data = QGroupBox("Data Location")
        d_layout = QVBoxLayout(data)
        d_layout.setContentsMargins(10, 14, 10, 10)
        d_layout.setSpacing(6)

        db_lbl = QLabel(f"Database:  {get_db_path()}")
        db_lbl.setWordWrap(True)
        db_lbl.setStyleSheet(
            "font-size: 11px; background: transparent; border: 0px;"
        )
        d_layout.addWidget(db_lbl)

        img_dir = str(Path(get_db_path()).parent / "extracted_images")
        img_lbl = QLabel(f"Extracted images:  {img_dir}")
        img_lbl.setWordWrap(True)
        img_lbl.setStyleSheet(
            "font-size: 11px; background: transparent; border: 0px;"
        )
        d_layout.addWidget(img_lbl)

        open_btn = QPushButton("Open Data Folder")
        open_btn.setMinimumWidth(140)
        open_btn.clicked.connect(self._on_open_data_folder)
        d_layout.addWidget(open_btn)

        self.main_layout.addWidget(data)

        # About
        about = QGroupBox("About")
        ab_layout = QVBoxLayout(about)
        ab_layout.setContentsMargins(10, 14, 10, 10)
        ab_layout.setSpacing(4)
        for line in [
            "Uniquest v1.0.0",
            "Find similar text and images across files",
            "Built with Python 3 + PyQt6",
            "Local SQLite database",
        ]:
            l = QLabel(line)
            l.setStyleSheet(
                "font-size: 11px; background: transparent; border: 0px;"
            )
            ab_layout.addWidget(l)

        self.main_layout.addWidget(about)

        # Save button
        save_row = QHBoxLayout()
        save_row.addStretch()
        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setProperty("class", "accent")
        self.save_btn.setMinimumWidth(140)
        self.save_btn.clicked.connect(self._on_save)
        save_row.addWidget(self.save_btn)
        self.main_layout.addLayout(save_row)

        self.main_layout.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)

        self.apply_theme()

    def _on_text_slider(self, val):
        self.text_val_lbl.setText(f"{val}%")
        self._mark_unsaved()

    def _on_img_slider(self, val):
        self.img_val_lbl.setText(f"{val}%")
        self._mark_unsaved()

    def _on_theme_selected(self, theme):
        ThemeManager.set_theme(theme)
        app = QApplication.instance()
        if app:
            refresh_theme(app)
        self.theme_changed.emit()
        self._mark_unsaved()

    def _on_browse_export(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Folder", self.export_path_input.text()
        )
        if folder:
            self.export_path_input.setText(folder)
            self._mark_unsaved()

    def _on_open_data_folder(self):
        import subprocess, sys
        folder = str(Path(get_db_path()).parent)
        try:
            if sys.platform == "win32":
                subprocess.Popen(["explorer", folder])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open:\n{e}")

    def _mark_unsaved(self):
        self._unsaved = True
        self.save_btn.setText("Save Settings *")

    def _on_save(self):
        set_setting("text_similarity_threshold", str(self.text_slider.value() / 100.0))
        set_setting("image_similarity_threshold", str(self.img_slider.value() / 100.0))
        set_setting("export_path", self.export_path_input.text().strip())
        set_setting("theme", ThemeManager.current())
        self._unsaved = False
        self.save_btn.setText("Save Settings")
        QMessageBox.information(self, "Saved", "Settings saved successfully.")

    def refresh(self):
        self.text_slider.setValue(int(float(get_setting("text_similarity_threshold", "0.70")) * 100))
        self.img_slider.setValue(int(float(get_setting("image_similarity_threshold", "0.85")) * 100))
        self.export_path_input.setText(get_setting("export_path", str(Path.home() / "Documents")))
        if ThemeManager.is_dark():
            self.radio_dark.setChecked(True)
        else:
            self.radio_light.setChecked(True)
        self._unsaved = False
        self.save_btn.setText("Save Settings")

    def apply_theme(self):
        c = ThemeManager.colors()
        self.setStyleSheet(f"background-color: {c['bg_primary']};")