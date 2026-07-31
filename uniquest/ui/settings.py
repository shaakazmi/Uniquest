from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame,
    QScrollArea, QSlider, QComboBox,
    QLineEdit, QFileDialog, QMessageBox,
    QSizePolicy, QSpacerItem, QCheckBox,
    QGroupBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPixmap

from utils.theme import ThemeManager, build_stylesheet
from database.db import get_setting, set_setting, get_db_path
from PyQt6.QtWidgets import QApplication


# ─────────────────────────────────────────────
#  SECTION CARD
# ─────────────────────────────────────────────
class SectionCard(QFrame):
    """Grouped settings section card"""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setProperty("class", "card")
        self._build(title)
        ThemeManager.add_listener(self.apply_theme)
        self.apply_theme()

    def _build(self, title: str):
        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(20, 16, 20, 20)
        self._outer.setSpacing(14)

        # Section title
        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet(
            "font-size: 13px; font-weight: 700;"
            "background: transparent;"
        )
        self._outer.addWidget(self.title_lbl)

        # Divider
        div = QFrame()
        div.setFixedHeight(1)
        div.setProperty("class", "divider")
        self._outer.addWidget(div)

        # Content area
        self.content = QVBoxLayout()
        self.content.setSpacing(14)
        self._outer.addLayout(self.content)

    def add_row(self, widget: QWidget):
        self.content.addWidget(widget)

    def add_layout(self, layout):
        self.content.addLayout(layout)

    def apply_theme(self):
        c = ThemeManager.colors()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {c['bg_card']};
                border: 1px solid {c['border']};
                border-radius: 10px;
            }}
        """)
        self.title_lbl.setStyleSheet(
            f"font-size: 13px; font-weight: 700;"
            f"color: {c['text_primary']}; background: transparent;"
        )


# ─────────────────────────────────────────────
#  SETTING ROW
# ─────────────────────────────────────────────
class SettingRow(QFrame):
    """Single setting row with label + control"""

    def __init__(
        self,
        label: str,
        description: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        self._build(label, description)
        ThemeManager.add_listener(self.apply_theme)

    def _build(self, label: str, description: str):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # Left: label + description
        left = QVBoxLayout()
        left.setSpacing(2)

        self.label_lbl = QLabel(label)
        self.label_lbl.setStyleSheet(
            "font-size: 13px; font-weight: 600;"
            "background: transparent;"
        )

        left.addWidget(self.label_lbl)

        if description:
            self.desc_lbl = QLabel(description)
            self.desc_lbl.setWordWrap(True)
            self.desc_lbl.setStyleSheet(
                "font-size: 11px; background: transparent;"
            )
            left.addWidget(self.desc_lbl)

        layout.addLayout(left, 1)

        # Right: control placeholder
        self.control_layout = QHBoxLayout()
        self.control_layout.setAlignment(
            Qt.AlignmentFlag.AlignRight |
            Qt.AlignmentFlag.AlignVCenter
        )
        layout.addLayout(self.control_layout)

    def set_control(self, widget: QWidget):
        self.control_layout.addWidget(widget)

    def apply_theme(self):
        c = ThemeManager.colors()
        self.label_lbl.setStyleSheet(
            f"font-size: 13px; font-weight: 600;"
            f"color: {c['text_primary']}; background: transparent;"
        )
        if hasattr(self, "desc_lbl"):
            self.desc_lbl.setStyleSheet(
                f"font-size: 11px; color: {c['text_muted']};"
                f"background: transparent;"
            )


# ─────────────────────────────────────────────
#  THEME TOGGLE CARD
# ─────────────────────────────────────────────
class ThemeToggleCard(QFrame):
    """Dark / Light mode toggle buttons"""

    theme_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        self._current = ThemeManager.current()
        self._build()
        ThemeManager.add_listener(self.apply_theme)

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.dark_btn  = self._make_btn(
            "🌙", "Dark", "dark"
        )
        self.light_btn = self._make_btn(
            "☀️", "Light", "light"
        )

        layout.addWidget(self.dark_btn)
        layout.addWidget(self.light_btn)
        layout.addStretch()

        self.apply_theme()

    def _make_btn(
        self, icon: str, label: str, theme: str
    ) -> QPushButton:
        btn = QPushButton(f"{icon}  {label}")
        btn.setFixedSize(110, 38)
        btn.setCheckable(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(
            lambda: self._on_select(theme)
        )
        return btn

    def _on_select(self, theme: str):
        self._current = theme
        self.theme_selected.emit(theme)
        self.apply_theme()

    def apply_theme(self):
        c       = ThemeManager.colors()
        current = self._current

        active_style = f"""
            QPushButton {{
                background-color: {c['accent']};
                color: #ffffff;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 600;
            }}
        """
        inactive_style = f"""
            QPushButton {{
                background-color: {c['bg_input']};
                color: {c['text_secondary']};
                border: 1px solid {c['border']};
                border-radius: 6px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {c['bg_hover']};
                color: {c['text_primary']};
            }}
        """
        self.dark_btn.setStyleSheet(
            active_style if current == "dark"
            else inactive_style
        )
        self.light_btn.setStyleSheet(
            active_style if current == "light"
            else inactive_style
        )


# ─────────────────────────────────────────────
#  SLIDER ROW
# ─────────────────────────────────────────────
class SliderRow(QFrame):
    """Reusable slider with label and value display"""

    value_changed = pyqtSignal(int)

    def __init__(
        self,
        min_val: int,
        max_val: int,
        current: int,
        suffix: str = "%",
        parent=None,
    ):
        super().__init__(parent)
        self.suffix  = suffix
        self.setStyleSheet("background: transparent;")
        self._build(min_val, max_val, current)
        ThemeManager.add_listener(self.apply_theme)

    def _build(self, min_val, max_val, current):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.min_lbl = QLabel(f"{min_val}{self.suffix}")
        self.min_lbl.setFixedWidth(36)
        self.min_lbl.setStyleSheet(
            "font-size: 11px; background: transparent;"
        )

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(min_val, max_val)
        self.slider.setValue(current)
        self.slider.setFixedWidth(200)
        self.slider.valueChanged.connect(self._on_change)

        self.max_lbl = QLabel(f"{max_val}{self.suffix}")
        self.max_lbl.setFixedWidth(40)
        self.max_lbl.setStyleSheet(
            "font-size: 11px; background: transparent;"
        )

        self.val_lbl = QLabel(f"{current}{self.suffix}")
        self.val_lbl.setFixedWidth(46)
        self.val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.val_lbl.setStyleSheet(
            "font-size: 13px; font-weight: 700;"
            "color: #4A9EFF; background: transparent;"
        )

        layout.addWidget(self.min_lbl)
        layout.addWidget(self.slider)
        layout.addWidget(self.max_lbl)
        layout.addWidget(self.val_lbl)

    def _on_change(self, val: int):
        self.val_lbl.setText(f"{val}{self.suffix}")
        self.value_changed.emit(val)

    def value(self) -> int:
        return self.slider.value()

    def set_value(self, val: int):
        self.slider.setValue(val)

    def apply_theme(self):
        c = ThemeManager.colors()
        self.min_lbl.setStyleSheet(
            f"font-size: 11px; color: {c['text_muted']};"
            f"background: transparent;"
        )
        self.max_lbl.setStyleSheet(
            f"font-size: 11px; color: {c['text_muted']};"
            f"background: transparent;"
        )
        self.val_lbl.setStyleSheet(
            f"font-size: 13px; font-weight: 700;"
            f"color: {c['accent']}; background: transparent;"
        )


# ─────────────────────────────────────────────
#  INFO ROW
# ─────────────────────────────────────────────
class InfoRow(QFrame):
    """Key → Value info display row"""

    def __init__(
        self,
        key: str,
        value: str,
        parent=None,
    ):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        self._build(key, value)
        ThemeManager.add_listener(self.apply_theme)

    def _build(self, key: str, value: str):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(12)

        self.key_lbl = QLabel(key)
        self.key_lbl.setFixedWidth(200)
        self.key_lbl.setStyleSheet(
            "font-size: 12px; background: transparent;"
        )

        self.val_lbl = QLabel(value)
        self.val_lbl.setStyleSheet(
            "font-size: 12px; font-weight: 600;"
            "background: transparent;"
        )
        self.val_lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        layout.addWidget(self.key_lbl)
        layout.addWidget(self.val_lbl, 1)

    def set_value(self, value: str):
        self.val_lbl.setText(value)

    def apply_theme(self):
        c = ThemeManager.colors()
        self.key_lbl.setStyleSheet(
            f"font-size: 12px; color: {c['text_muted']};"
            f"background: transparent;"
        )
        self.val_lbl.setStyleSheet(
            f"font-size: 12px; font-weight: 600;"
            f"color: {c['text_primary']}; background: transparent;"
        )


# ─────────────────────────────────────────────
#  SETTINGS PAGE
# ─────────────────────────────────────────────
class SettingsPage(QWidget):
    """
    Page 4 — Settings
    Theme, similarity thresholds, export path, about.
    """

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

        # ── Scroll area ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        content = QWidget()
        self.main_layout = QVBoxLayout(content)
        self.main_layout.setContentsMargins(28, 24, 28, 28)
        self.main_layout.setSpacing(20)

        # ── Appearance ──
        self._build_appearance()

        # ── Similarity thresholds ──
        self._build_thresholds()

        # ── Export ──
        self._build_export()

        # ── Data management ──
        self._build_data_management()

        # ── About ──
        self._build_about()

        # ── Save button ──
        save_row = QHBoxLayout()
        save_row.addStretch()

        self.save_btn = QPushButton("💾  Save Settings")
        self.save_btn.setFixedHeight(38)
        self.save_btn.setFixedWidth(160)
        self.save_btn.clicked.connect(self._on_save)
        save_row.addWidget(self.save_btn)
        self.main_layout.addLayout(save_row)
        self.main_layout.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)

        self.apply_theme()

    # ─────────────────────────────────────────
    #  SECTION BUILDERS
    # ─────────────────────────────────────────
    def _build_appearance(self):
        card = SectionCard("🎨  Appearance")

        # Theme toggle
        theme_row = SettingRow(
            "Theme",
            "Choose between dark and light mode.",
        )
        self.theme_toggle = ThemeToggleCard()
        self.theme_toggle.theme_selected.connect(
            self._on_theme_selected
        )
        theme_row.set_control(self.theme_toggle)
        card.add_row(theme_row)

        self.main_layout.addWidget(card)

    def _build_thresholds(self):
        card = SectionCard("🎯  Similarity Thresholds")

        # Text threshold
        text_row = SettingRow(
            "Text Similarity Threshold",
            "Minimum similarity score for text matches. "
            "Lower = more matches found.",
        )
        saved_text = int(
            float(
                get_setting("text_similarity_threshold", "0.70")
            ) * 100
        )
        self.text_slider = SliderRow(50, 100, saved_text)
        self.text_slider.value_changed.connect(
            lambda v: self._mark_unsaved()
        )
        text_row.set_control(self.text_slider)
        card.add_row(text_row)

        # Color legend
        legend = self._build_score_legend()
        card.add_row(legend)

        # Image threshold
        img_row = SettingRow(
            "Image Similarity Threshold",
            "Minimum similarity score for image matches. "
            "Higher = only near-identical images.",
        )
        saved_img = int(
            float(
                get_setting("image_similarity_threshold", "0.85")
            ) * 100
        )
        self.img_slider = SliderRow(50, 100, saved_img)
        self.img_slider.value_changed.connect(
            lambda v: self._mark_unsaved()
        )
        img_row.set_control(self.img_slider)
        card.add_row(img_row)

        self.main_layout.addWidget(card)

    def _build_score_legend(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        legend_lbl = QLabel("Score legend:")
        legend_lbl.setStyleSheet(
            "font-size: 11px; background: transparent;"
        )
        layout.addWidget(legend_lbl)

        for color, label in [
            ("#FF4C4C", "≥90% Very High"),
            ("#FFA500", "≥80% High"),
            ("#FFD700", "≥70% Medium"),
            ("#4A9EFF", "<70%  Low"),
        ]:
            dot = QLabel(f"●  {label}")
            dot.setStyleSheet(
                f"font-size: 11px; color: {color};"
                f"background: transparent;"
            )
            layout.addWidget(dot)

        layout.addStretch()
        return frame

    def _build_export(self):
        card = SectionCard("📤  Export")

        # Export path
        export_row = SettingRow(
            "Default Export Folder",
            "Where exported CSV and PDF reports will be saved.",
        )

        path_layout = QHBoxLayout()
        path_layout.setSpacing(8)

        saved_path = get_setting(
            "export_path",
            str(Path.home() / "Documents"),
        )
        self.export_path_input = QLineEdit(saved_path)
        self.export_path_input.setFixedHeight(34)
        self.export_path_input.setMinimumWidth(240)
        self.export_path_input.textChanged.connect(
            lambda: self._mark_unsaved()
        )

        browse_btn = QPushButton("📂 Browse")
        browse_btn.setProperty("class", "ghost")
        browse_btn.setFixedHeight(34)
        browse_btn.setFixedWidth(90)
        browse_btn.clicked.connect(self._on_browse_export)

        path_layout.addWidget(self.export_path_input)
        path_layout.addWidget(browse_btn)

        export_row.control_layout.addLayout(path_layout)
        card.add_row(export_row)

        # Export format note
        fmt_lbl = QLabel(
            "💡 Supported export formats: CSV, PDF Report"
        )
        fmt_lbl.setStyleSheet(
            "font-size: 11px; background: transparent;"
        )
        card.add_row(fmt_lbl)

        self.main_layout.addWidget(card)

    def _build_data_management(self):
        card = SectionCard("🗄️  Data Management")

        # DB path info
        db_row = InfoRow(
            "Database Location",
            get_db_path(),
        )
        card.add_row(db_row)

        images_dir = str(
            Path(get_db_path()).parent / "extracted_images"
        )
        img_dir_row = InfoRow(
            "Extracted Images Folder",
            images_dir,
        )
        card.add_row(img_dir_row)

        # Danger zone
        danger_lbl = QLabel("⚠️  Danger Zone")
        danger_lbl.setStyleSheet(
            "font-size: 12px; font-weight: 700;"
            "color: #f44336; background: transparent;"
        )
        card.add_row(danger_lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        open_db_btn = QPushButton("📂 Open Data Folder")
        open_db_btn.setProperty("class", "ghost")
        open_db_btn.setFixedHeight(34)
        open_db_btn.clicked.connect(self._on_open_data_folder)

        btn_row.addWidget(open_db_btn)
        btn_row.addStretch()
        card.add_layout(btn_row)

        self.main_layout.addWidget(card)

    def _build_about(self):
        card = SectionCard("ℹ️  About Uniquest")

        from assets_path import assets_path
        logo_path = assets_path() / "logo.ico"

        # Logo row
        logo_row = QHBoxLayout()
        logo_row.setSpacing(14)

        logo_lbl = QLabel()
        if logo_path.exists():
            pix = QPixmap(str(logo_path)).scaled(
                48, 48,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            logo_lbl.setPixmap(pix)
        else:
            logo_lbl.setText("🔎")
            logo_lbl.setStyleSheet("font-size: 36px;")
        logo_lbl.setFixedSize(52, 52)

        info_col = QVBoxLayout()
        info_col.setSpacing(3)

        name_lbl = QLabel("Uniquest")
        name_lbl.setStyleSheet(
            "font-size: 18px; font-weight: 700;"
            "color: #4A9EFF; background: transparent;"
        )
        ver_lbl = QLabel("Version 1.0.0")
        ver_lbl.setStyleSheet(
            "font-size: 12px; background: transparent;"
        )
        tag_lbl = QLabel(
            "Find similar text and images across hundreds of files"
        )
        tag_lbl.setStyleSheet(
            "font-size: 12px; background: transparent;"
        )

        info_col.addWidget(name_lbl)
        info_col.addWidget(ver_lbl)
        info_col.addWidget(tag_lbl)

        logo_row.addWidget(logo_lbl)
        logo_row.addLayout(info_col)
        logo_row.addStretch()
        card.add_layout(logo_row)

        # Tech stack info
        for key, val in [
            ("Built with",  "Python 3.11 + PyQt6"),
            ("Database",    "SQLite (local)"),
            ("Text Engine", "TF-IDF + Cosine Similarity"),
            ("Image Engine","Perceptual Hashing (pHash)"),
            ("Packaging",   "PyInstaller → .exe"),
        ]:
            card.add_row(InfoRow(key, val))

        self.main_layout.addWidget(card)

    # ─────────────────────────────────────────
    #  ACTIONS
    # ─────────────────────────────────────────
    def _on_theme_selected(self, theme: str):
        ThemeManager.set_theme(theme)
        app = QApplication.instance()
        if app:
            app.setStyleSheet(build_stylesheet())
        self.theme_changed.emit()
        self._mark_unsaved()

    def _on_browse_export(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Export Folder",
            self.export_path_input.text(),
        )
        if folder:
            self.export_path_input.setText(folder)
            self._mark_unsaved()

    def _on_open_data_folder(self):
        folder = str(Path(get_db_path()).parent)
        import subprocess, sys
        try:
            if sys.platform == "win32":
                subprocess.Popen(["explorer", folder])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception as e:
            QMessageBox.warning(
                self, "Error",
                f"Could not open folder:\n{e}"
            )

    def _mark_unsaved(self):
        self._unsaved = True
        self.save_btn.setText("💾  Save Settings *")

    def _on_save(self):
        # Save all settings to DB
        text_val = self.text_slider.value() / 100.0
        img_val  = self.img_slider.value()  / 100.0
        exp_path = self.export_path_input.text().strip()

        set_setting(
            "text_similarity_threshold",
            str(text_val),
        )
        set_setting(
            "image_similarity_threshold",
            str(img_val),
        )
        set_setting("export_path", exp_path)
        set_setting("theme", ThemeManager.current())

        self._unsaved = False
        self.save_btn.setText("💾  Save Settings")

        QMessageBox.information(
            self,
            "Settings Saved",
            "✅ Your settings have been saved successfully.",
        )

    def refresh(self):
        """Reload settings from DB"""
        # Text threshold
        saved_text = int(
            float(
                get_setting(
                    "text_similarity_threshold", "0.70"
                )
            ) * 100
        )
        self.text_slider.set_value(saved_text)

        # Image threshold
        saved_img = int(
            float(
                get_setting(
                    "image_similarity_threshold", "0.85"
                )
            ) * 100
        )
        self.img_slider.set_value(saved_img)

        # Export path
        saved_path = get_setting(
            "export_path",
            str(Path.home() / "Documents"),
        )
        self.export_path_input.setText(saved_path)

        # Theme toggle sync
        self.theme_toggle._current = ThemeManager.current()
        self.theme_toggle.apply_theme()

        self._unsaved = False
        self.save_btn.setText("💾  Save Settings")

    def apply_theme(self):
        c = ThemeManager.colors()
        self.setStyleSheet(
            f"background-color: {c['bg_primary']};"
        )