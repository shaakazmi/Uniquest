@echo off
echo ========================================
echo  Uniquest — Building .exe
echo ========================================

pip install pyinstaller

pyinstaller ^
  --onefile ^
  --windowed ^
  --name "Uniquest" ^
  --icon "assets/logo.ico" ^
  --add-data "assets;assets" ^
  main.py

echo.
echo ========================================
echo  Done — check dist\Uniquest.exe
echo ========================================
pause