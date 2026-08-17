import sys
import os
import traceback
from pathlib import Path


def setup_paths():
    if getattr(sys, "frozen", False):
        root = Path(sys.executable).parent
    else:
        root = Path(__file__).parent
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    return root


ROOT = setup_paths()


def assets_path() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS) if hasattr(sys, "_MEIPASS") else Path(sys.executable).parent
    else:
        base = Path(__file__).parent
    return base / "assets"


import types
_mod = types.ModuleType("assets_path")
_mod.assets_path = assets_path
sys.modules["assets_path"] = _mod


def check_dependencies() -> list:
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


def setup_crash_handler():
    log_path = ROOT / "IPOGenie_crash.log"

    def handle_exception(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return

        error_msg = "".join(
            traceback.format_exception(exc_type, exc_value, exc_tb)
        )
        print(f"CRASH:\n{error_msg}")

        try:
            with open(log_path, "a", encoding="utf-8") as f:
                from datetime import datetime
                f.write(f"\n{'='*60}\n{datetime.now()}\n{error_msg}\n")
        except Exception:
            pass

        try:
            from PyQt6.QtWidgets import QApplication, QMessageBox
            app = QApplication.instance()
            if app:
                QMessageBox.critical(
                    None,
                    "IPOGenie — Unexpected Error",
                    f"An unexpected error occurred:\n\n"
                    f"{exc_type.__name__}: {exc_value}\n\n"
                    f"Details saved to:\n{log_path}",
                )
        except Exception:
            pass

    sys.excepthook = handle_exception


def setup_hidpi():
    os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")


def show_splash(app):
    from PyQt6.QtWidgets import QSplashScreen
    from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont
    from PyQt6.QtCore import Qt

    pix = QPixmap(480, 280)
    pix.fill(QColor("#1a1a2e"))
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    logo_path = assets_path() / "logo.ico"
    if logo_path.exists():
        logo_pix = QPixmap(str(logo_path)).scaled(
            64, 64,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        painter.drawPixmap((480 - 64) // 2, 60, logo_pix)

    painter.setPen(QColor("#4A9EFF"))
    painter.setFont(QFont("Segoe UI", 26, QFont.Weight.Bold))
    painter.drawText(
        0, 150, 480, 40,
        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
        "IPOGenie",
    )

    painter.setPen(QColor("#8892b0"))
    painter.setFont(QFont("Segoe UI", 11))
    painter.drawText(
        0, 195, 480, 30,
        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
        "Find similar content across hundreds of files",
    )

    painter.setPen(QColor("#3d4f7c"))
    painter.setFont(QFont("Segoe UI", 9))
    painter.drawText(
        0, 248, 480, 20,
        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
        "v1.0.0  •  Loading...",
    )
    painter.end()

    splash = QSplashScreen(pix)
    # ⚠️ Do NOT use WindowStaysOnTopHint — it breaks the main window titlebar
    splash.show()
    app.processEvents()
    return splash


def show_dependency_error(missing: list):
    from PyQt6.QtWidgets import QApplication, QMessageBox
    app = QApplication(sys.argv)
    pkg_list = "\n".join(f"  • {p}" for p in missing)
    QMessageBox.critical(
        None,
        "IPOGenie — Missing Dependencies",
        f"Missing packages:\n\n{pkg_list}\n\n"
        f"Run:\n  pip install -r requirements.txt",
    )
    sys.exit(1)


def main():
    setup_crash_handler()
    setup_hidpi()

    if not getattr(sys, "frozen", False):
        missing = check_dependencies()
        if missing:
            try:
                show_dependency_error(missing)
            except Exception:
                print(f"Missing: {missing}")
                sys.exit(1)

    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt

    app = QApplication(sys.argv)
    app.setApplicationName("IPOGenie")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("IPOGenie")

    # Set app-wide icon
    from PyQt6.QtGui import QIcon
    icon_path = assets_path() / "logo.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    splash = None
    try:
        splash = show_splash(app)
    except Exception as e:
        print(f"Splash error: {e}")

    try:
        from utils.theme import apply_theme
        apply_theme(app)
    except Exception as e:
        print(f"Theme error: {e}")

    try:
        from database.db import initialize_database
        initialize_database()
    except Exception as e:
        print(f"DB error: {e}")
        if splash:
            splash.close()
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(
            None, "Database Error",
            f"Failed to initialize database:\n\n{e}",
        )
        sys.exit(1)

    try:
        from ui.main_window import MainWindow
        window = MainWindow()
    except Exception as e:
        print(f"Window error: {e}")
        traceback.print_exc()
        if splash:
            splash.close()
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(
            None, "Startup Error",
            f"Failed to build main window:\n\n{e}",
        )
        sys.exit(1)

    import time
    time.sleep(0.6)

    if splash:
        splash.finish(window)

    window.show()
    window.raise_()
    window.activateWindow()

    print("✅ IPOGenie started successfully")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()