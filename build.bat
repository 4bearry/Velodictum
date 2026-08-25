@echo off
title Velodictum - Build Engine
cd /d "%~dp0"

echo ============================================================
echo   VELODICTUM - WINDOWS BUILD ENGINE
echo ============================================================
echo.
echo   This script creates a portable Velodictum.exe that runs
echo   on any Windows PC without requiring a Python installation.
echo.
echo ============================================================

:: ---------------------------------------------------------------
:: 1. Check virtual environment
:: ---------------------------------------------------------------
if not exist ".venv\Scripts\python.exe" (
    echo.
    echo   [ERROR] Virtual Python environment not found.
    echo   Please set it up first:
    echo.
    echo     python -m venv .venv
    echo     .venv\Scripts\pip install -r requirements.txt
    echo     .venv\Scripts\pip install -r requirements-dev.txt
    echo.
    pause
    exit /b 1
)

:: ---------------------------------------------------------------
:: 2. Check if PyInstaller is installed, install from requirements-dev.txt if not
:: ---------------------------------------------------------------
.venv\Scripts\python.exe -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo.
    echo   [INFO] PyInstaller not found. Installing from requirements-dev.txt...
    .venv\Scripts\pip install -r requirements-dev.txt
    echo.
)

:: ---------------------------------------------------------------
:: 3. Start build
:: ---------------------------------------------------------------
echo.
echo   Starting build...
echo.

.venv\Scripts\python.exe build_executable.py

if errorlevel 1 (
    echo.
    echo   [ERROR] Build failed. See output above for details.
    echo.
    pause
    exit /b 1
)

:: ---------------------------------------------------------------
:: 4. Optional: Create ZIP archive
:: ---------------------------------------------------------------
echo.
set /p zipChoice="  Create a ZIP archive for distribution? (y/n): "
if /i "%zipChoice%"=="y" (
    echo.
    echo   Creating ZIP archive...

    if exist "dist\Velodictum.zip" del "dist\Velodictum.zip"

    powershell -NoProfile -Command "Compress-Archive -Path 'dist\Velodictum\*' -DestinationPath 'dist\Velodictum.zip' -Force" 2>nul

    if exist "dist\Velodictum.zip" (
        echo.
        echo   ============================================================
        echo   [DONE] ZIP created: dist\Velodictum.zip
        echo.
        echo   Share this ZIP file. The recipient extracts it and
        echo   runs Velodictum.exe directly - no Python required!
        echo   ============================================================
    ) else (
        echo.
        echo   [NOTE] ZIP could not be created automatically.
        echo   Please manually zip the dist\Velodictum\ folder.
    )
)

echo.
echo   ============================================================
echo   Build complete. Press any key to exit.
echo   ============================================================
pause >nul
