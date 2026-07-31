import sys
import os
import traceback
from pathlib import Path

# ─────────────────────────────────────────────
#  PATH SETUP  (must be before any local imports)
# ─────────────────────────────────────────────
def setup_paths():
    """
    Add the project root to sys.path so all
    imports work both in dev and in .exe mode.
    """
    if getattr(sys, "frozen", False):
        # Running as PyInstaller .exe
        root = Path(sys.executable).parent
    else:
        # Running as normal Python script
        root = Path(__file__).parent

    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)

    return root


ROOT = setup_paths()


# ─────────────────────────────────────────────
#  ASSETS PATH HELPER  (used by ui modules)
# ─────────────────────────────────────────────
def assets_path() -> Path:
    """Return path to the assets folder"""
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
    else:
        base = Path(__file__).parent
    return base / "assets"


# Make assets_path importable as a module
# (settings.py imports it as: from assets_path import assets_path)
import types
_mod = types.ModuleType("assets_path")
_mod.assets_path = assets_path
sys.modules["assets_path"] = _mod


# ─────────────────────────────────────────────
#  ENVIRONMENT CHECKS
# ─────────────────────────────────────────────
def check_dependencies() -> list:
    """
    Check all required packages are installed.
    Returns list of missing package names.
    """
    required = {
        "PyQt6":        "PyQt6",
        "fitz":         "PyMuPDF",
        "docx":         "python-docx",
        "openpyxl":     "openpyxl",
        "pptx":         "python-pptx",
        "PIL":          "Pillow",
        "imagehash":    "imagehash",
        "sklearn":      "scikit-learn",
        "numpy":        "numpy",
        "pandas":       "pandas",
        "reportlab":    "reportlab",
    }
    missing = []
    for module, package in required.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(package)
    return missing


# ─────────────────────────────────────────────
#  CRASH HANDLER
# ─────────────────────────────────────────────
def setup_crash_handler():
    """
    Write unhandled exceptions to a crash log
    next to the .exe / script.
    """
    log_path = ROOT / "uniquest_crash.log"

    def handle_exception(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return

        error_msg = "".join(
            traceback.format_exception(
                exc_type, exc_value, exc_tb
            )
        )
        print(f"CRASH:\n{error_msg}")

        try:
            with open(log_path, "a", encoding="utf-8") as f:
                from datetime import datetime
                f.write(
                    f"\n{'='*60}\n"
                    f"{datetime.now()}\n"
                    f"{error_msg}\n"
                )
        except Exception:
            pass

        # Show error dialog if PyQt6 is available
        try:
            from PyQt6.QtWidgets import QApplication, QMessageBox
            app = QApplication.instance()
            if app:
                QMessageBox.critical(
                    None,
                    "Uniquest — Unexpected Error",
                    f"An unexpected error occurred:\n\n"
                    f"{exc_type.__name__}: {exc_value}\n\n"
                    f"Details saved to:\n{log_path}",
                )
        except Exception:
            pass

    sys.excepthook = handle_exception


# ─────────────────────────────────────────────
#  HIGH DPI  (Windows scaling support)
# ─────────────────────────────────────────────
def setup_hidpi():
    """Enable high-DPI scaling for Windows"""
    os.environ.setdefault(
        "QT_AUTO_SCREEN_SCALE_FACTOR", "1"
    )
    os.environ.setdefault(
        "QT_ENABLE_HIGHDPI_SCALING", "1"
    )


# ─────────────────────────────────────────────
#  SPLASH SCREEN
# ─────────────────────────────────────────────
def show_splash(app):
    """
    Show a simple splash screen while
    the database and UI are initializing.
    """
    from PyQt6.QtWidgets import QSplashScreen, QLabel
    from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont
    from PyQt6.QtCore import Qt

    # Create splash pixmap
    pix = QPixmap(480, 280)
    pix.fill(QColor("#1a1a2e"))

    painter = QPainter(pix)
    painter.setRenderHint(
        QPainter.RenderHint.Antialiasing
    )

    # Try to draw logo
    logo_path = assets_path() / "logo.ico"
    if logo_path.exists():
        logo_pix = QPixmap(str(logo_path)).scaled(
            64, 64,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        painter.drawPixmap(
            (480 - 64) // 2, 60,
            logo_pix,
        )

    # App name
    painter.setPen(QColor("#4A9EFF"))
    font = QFont("Segoe UI", 26, QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(
        0, 150, 480, 40,
        Qt.AlignmentFlag.AlignHCenter |
        Qt.AlignmentFlag.AlignVCenter,
        "Uniquest",
    )

    # Tagline
    painter.setPen(QColor("#8892b0"))
    font2 = QFont("Segoe UI", 11)
    painter.setFont(font2)
    painter.drawText(
        0, 195, 480, 30,
        Qt.AlignmentFlag.AlignHCenter |
        Qt.AlignmentFlag.AlignVCenter,
        "Find similar content across hundreds of files",
    )

    # Version
    painter.setPen(QColor("#3d4f7c"))
    font3 = QFont("Segoe UI", 9)
    painter.setFont(font3)
    painter.drawText(
        0, 248, 480, 20,
        Qt.AlignmentFlag.AlignHCenter |
        Qt.AlignmentFlag.AlignVCenter,
        "v1.0.0  •  Initializing...",
    )

    painter.end()

    splash = QSplashScreen(pix)
    splash.setWindowFlag(
        Qt.WindowType.WindowStaysOnTopHint
    )
    splash.show()
    app.processEvents()
    return splash


# ─────────────────────────────────────────────
#  DEPENDENCY ERROR SCREEN
# ─────────────────────────────────────────────
def show_dependency_error(missing: list):
    """Show error if packages are missing"""
    from PyQt6.QtWidgets import (
        QApplication, QMessageBox
    )
    app = QApplication(sys.argv)
    pkg_list = "\n".join(f"  • {p}" for p in missing)
    QMessageBox.critical(
        None,
        "Uniquest — Missing Dependencies",
        f"The following packages are required but not installed:\n\n"
        f"{pkg_list}\n\n"
        f"Please run:\n"
        f"  pip install -r requirements.txt\n\n"
        f"Then restart the application.",
    )
    sys.exit(1)


# ─────────────────────────────────────────────
#  MAIN APPLICATION
# ─────────────────────────────────────────────
def main():
    # ── 1. Crash handler ──
    setup_crash_handler()

    # ── 2. HiDPI ──
    setup_hidpi()

    # ── 3. Check deps (skip in frozen .exe) ──
    if not getattr(sys, "frozen", False):
        missing = check_dependencies()
        if missing:
            try:
                show_dependency_error(missing)
            except Exception:
                print(
                    f"Missing packages: {missing}\n"
                    f"Run: pip install -r requirements.txt"
                )
                sys.exit(1)

    # ── 4. Create Qt application ──
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt

    app = QApplication(sys.argv)
    app.setApplicationName("Uniquest")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Uniquest")

    # ── 5. Show splash ──
    splash = None
    try:
        splash = show_splash(app)
    except Exception as e:
        print(f"Splash error (non-fatal): {e}")

    # ── 6. Apply theme ──
    try:
        from utils.theme import apply_theme, ThemeManager
        apply_theme(app)
    except Exception as e:
        print(f"Theme error: {e}")

    # ── 7. Initialize database ──
    try:
        from database.db import initialize_database
        initialize_database()
    except Exception as e:
        print(f"Database init error: {e}")
        if splash:
            splash.close()
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(
            None,
            "Database Error",
            f"Failed to initialize database:\n\n{e}\n\n"
            f"Please check write permissions for:\n"
            f"{Path.home() / '.uniquest'}",
        )
        sys.exit(1)

    # ── 8. Build main window ──
    try:
        from ui.main_window import MainWindow
        window = MainWindow()
    except Exception as e:
        print(f"Window build error: {e}")
        traceback.print_exc()
        if splash:
            splash.close()
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(
            None,
            "Startup Error",
            f"Failed to build main window:\n\n{e}",
        )
        sys.exit(1)

    # ── 9. Close splash and show window ──
    import time
    time.sleep(0.8)   # Let splash be visible briefly

    if splash:
        splash.finish(window)

    window.show()
    window.raise_()
    window.activateWindow()

    print("✅ Uniquest started successfully")

    # ── 10. Run event loop ──
    sys.exit(app.exec())


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    main()