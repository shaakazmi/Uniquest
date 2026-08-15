@echo off
title Uniquest Builder
color 0B
cls

echo.
echo  ██╗   ██╗███╗   ██╗██╗ ██████╗ ██╗   ██╗███████╗███████╗████████╗
echo  ██║   ██║████╗  ██║██║██╔═══██╗██║   ██║██╔════╝██╔════╝╚══██╔══╝
echo  ██║   ██║██╔██╗ ██║██║██║   ██║██║   ██║█████╗  ███████╗   ██║
echo  ██║   ██║██║╚██╗██║██║██║▄▄ ██║██║   ██║██╔══╝  ╚════██║   ██║
echo  ╚██████╔╝██║ ╚████║██║╚██████╔╝╚██████╔╝███████╗███████║   ██║
echo   ╚═════╝ ╚═╝  ╚═══╝╚═╝ ╚══▀▀═╝  ╚═════╝ ╚══════╝╚══════╝   ╚═╝
echo.
echo  ============================================================
echo   Uniquest Builder  ^|  Packaging to Windows .exe
echo  ============================================================
echo.

REM ── Check Python ──
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found in PATH.
    echo          Please install Python 3.10+ and try again.
    echo          https://www.python.org/downloads/
    pause
    exit /b 1
)

echo  [1/7] Python found:
python --version
echo.

REM ── Check pip ──
pip --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] pip not found. Please reinstall Python with pip.
    pause
    exit /b 1
)

REM ── Check we are in the right folder ──
if not exist "main.py" (
    echo  [ERROR] main.py not found.
    echo          Please run this script from the uniquest/ folder.
    echo          cd uniquest
    echo          build.bat
    pause
    exit /b 1
)

echo  [2/7] Installing / upgrading dependencies...
echo.
pip install -r requirements.txt --quiet --upgrade
if errorlevel 1 (
    echo  [ERROR] Failed to install requirements.
    echo          Try running: pip install -r requirements.txt
    pause
    exit /b 1
)
echo  [OK] Dependencies installed.
echo.

REM ── Install PyInstaller ──
echo  [3/7] Installing PyInstaller...
pip install pyinstaller --quiet --upgrade
if errorlevel 1 (
    echo  [ERROR] Failed to install PyInstaller.
    pause
    exit /b 1
)
echo  [OK] PyInstaller ready.
echo.

REM ── Clean old build ──
echo  [4/7] Cleaning previous build...
if exist "dist"       rmdir /s /q "dist"
if exist "build"      rmdir /s /q "build"
if exist "Uniquest.spec" del /q "Uniquest.spec"
echo  [OK] Clean done.
echo.

REM ── Check for logo ──
echo  [5/7] Checking assets...
if not exist "assets\logo.ico" (
    echo  [WARN] assets\logo.ico not found.
    echo         The .exe will be built without a custom icon.
    echo         Add your logo.ico to assets\ and rebuild.
    echo.
    set ICON_ARG=
) else (
    echo  [OK] Found assets\logo.ico
    set ICON_ARG=--icon=assets\logo.ico
)
echo.

REM ── Run PyInstaller ──
echo  [6/7] Building Uniquest.exe ...
echo        This may take 2-5 minutes. Please wait...
echo.

pyinstaller ^
    --onefile ^
    --windowed ^
    --name "Uniquest" ^
    %ICON_ARG% ^
    --add-data "assets;assets" ^
    --add-data "database;database" ^
    --add-data "core;core" ^
    --add-data "ui;ui" ^
    --add-data "utils;utils" ^
    --hidden-import "PyQt6" ^
    --hidden-import "PyQt6.QtWidgets" ^
    --hidden-import "PyQt6.QtCore" ^
    --hidden-import "PyQt6.QtGui" ^
    --hidden-import "fitz" ^
    --hidden-import "docx" ^
    --hidden-import "openpyxl" ^
    --hidden-import "pptx" ^
    --hidden-import "PIL" ^
    --hidden-import "PIL.Image" ^
    --hidden-import "imagehash" ^
    --hidden-import "sklearn" ^
    --hidden-import "sklearn.feature_extraction.text" ^
    --hidden-import "sklearn.metrics.pairwise" ^
    --hidden-import "numpy" ^
    --hidden-import "pandas" ^
    --hidden-import "reportlab" ^
    --hidden-import "reportlab.platypus" ^
    --hidden-import "reportlab.lib.styles" ^
    --hidden-import "reportlab.lib.pagesizes" ^
    --hidden-import "striprtf" ^
    --hidden-import "striprtf.striprtf" ^
    --hidden-import "sqlite3" ^
    --hidden-import "csv" ^
    --hidden-import "zipfile" ^
    --hidden-import "pathlib" ^
    --hidden-import "dataclasses" ^
    --collect-all "fitz" ^
    --collect-all "sklearn" ^
    --collect-all "PIL" ^
    --collect-all "imagehash" ^
    --collect-all "reportlab" ^
    --noconfirm ^
    --clean ^
    main.py

if errorlevel 1 (
    echo.
    echo  [ERROR] Build failed. Check errors above.
    echo.
    echo  Common fixes:
    echo    - Run: pip install -r requirements.txt
    echo    - Make sure you are in the uniquest/ folder
    echo    - Check uniquest_crash.log for details
    echo.
    pause
    exit /b 1
)

echo.
echo  [7/7] Verifying output...
if not exist "dist\Uniquest.exe" (
    echo  [ERROR] Uniquest.exe not found in dist\
    echo          Build may have failed silently.
    pause
    exit /b 1
)

REM ── Get file size ──
for %%A in ("dist\Uniquest.exe") do set EXE_SIZE=%%~zA
set /a EXE_MB=%EXE_SIZE% / 1048576

echo.
echo  ============================================================
echo   BUILD SUCCESSFUL
echo  ============================================================
echo.
echo   Output:   dist\Uniquest.exe
echo   Size:     ~%EXE_MB% MB
echo.
echo   To run:
echo     dist\Uniquest.exe
echo.
echo   To distribute:
echo     Copy dist\Uniquest.exe to any Windows machine.
echo     No Python installation required.
echo.
echo  ============================================================
echo.

REM ── Ask to run now ──
set /p RUN_NOW= Run Uniquest.exe now? (Y/N):
if /i "%RUN_NOW%"=="Y" (
    echo.
    echo  Starting Uniquest...
    start "" "dist\Uniquest.exe"
)

echo.
echo  Done. Press any key to exit.
pause >nul
exit /b 0