import sys
import os
import traceback
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QSplashScreen, QLabel, QMessageBox
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QColor, QFont

from utils.theme import apply_theme
from database.db import initialize_database


# ─────────────────────────────────────────────────────────────
def handle_exception(exc_type, exc_value, exc_tb):
    log_path = Path("uniquest_crash.log")
    with open(log_path, "w") as f:
        traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
    QMessageBox.critical(
        None,
        "Uniquest — Unexpected Error",
        f"A critical error occurred:\n\n{exc_value}\n\nSee uniquest_crash.log for details."
    )
    sys.__excepthook__(exc_type, exc_value, exc_tb)


sys.excepthook = handle_exception


# ─────────────────────────────────────────────────────────────
def create_splash(app: QApplication) -> QSplashScreen:
    pixmap = QPixmap(480, 280)
    pixmap.fill(QColor("#1a73e8"))

    splash = QSplashScreen(pixmap, Qt.WindowType.WindowStaysOnTopHint)

    title = QLabel("Uniquest", splash)
    title.setFont(QFont("Segoe UI", 32, QFont.Weight.Bold))
    title.setStyleSheet("color: white; background: transparent;")
    title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    title.setGeometry(0, 80, 480, 60)

    sub = QLabel("Intelligent Duplicate Finder", splash)
    sub.setFont(QFont("Segoe UI", 12))
    sub.setStyleSheet("color: rgba(255,255,255,180); background: transparent;")
    sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
    sub.setGeometry(0, 150, 480, 30)

    version = QLabel("v1.0.0", splash)
    version.setFont(QFont("Segoe UI", 9))
    version.setStyleSheet("color: rgba(255,255,255,150); background: transparent;")
    version.setAlignment(Qt.AlignmentFlag.AlignCenter)
    version.setGeometry(0, 240, 480, 20)

    splash.show()
    app.processEvents()
    return splash


# ─────────────────────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Uniquest")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Uniquest")

    # apply default light theme
    apply_theme(app, "light")

    # splash screen
    splash = create_splash(app)

    # initialize database
    try:
        initialize_database()
    except Exception as e:
        QMessageBox.critical(None, "Database Error", f"Failed to initialize database:\n{e}")
        sys.exit(1)

    # import main window after DB ready
    from ui.main_window import MainWindow
    window = MainWindow()

    def show_main():
        splash.finish(window)
        window.showNormal()
        window.raise_()
        window.activateWindow()

    QTimer.singleShot(2000, show_main)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()