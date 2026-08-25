@echo off
title Velodictum - Build Engine
cd /d "%~dp0"

echo ============================================================
echo   VELODICTUM - WINDOWS BUILD ENGINE
echo ============================================================
echo.
echo   Dieses Skript erstellt eine portable Velodictum.exe,
echo   die ohne Python-Installation auf jedem Windows-PC laeuft.
echo.
echo ============================================================

:: ---------------------------------------------------------------
:: 1. Pruefe virtuelle Umgebung
:: ---------------------------------------------------------------
if not exist ".venv\Scripts\python.exe" (
    echo.
    echo   [FEHLER] Virtuelle Python-Umgebung nicht gefunden.
    echo   Bitte zuerst einrichten:
    echo.
    echo     python -m venv .venv
    echo     .venv\Scripts\pip install -r requirements.txt
    echo     .venv\Scripts\pip install pyinstaller
    echo.
    pause
    exit /b 1
)

:: ---------------------------------------------------------------
:: 2. Pruefe ob PyInstaller installiert ist
:: ---------------------------------------------------------------
.venv\Scripts\python.exe -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo.
    echo   [INFO] PyInstaller nicht gefunden. Wird jetzt installiert...
    .venv\Scripts\pip install pyinstaller pyinstaller-hooks-contrib
    echo.
)

:: ---------------------------------------------------------------
:: 3. Build starten
:: ---------------------------------------------------------------
echo.
echo   Build wird gestartet...
echo.

.venv\Scripts\python.exe build_executable.py

if errorlevel 1 (
    echo.
    echo   [FEHLER] Build fehlgeschlagen. Siehe Ausgabe oben.
    echo.
    pause
    exit /b 1
)

:: ---------------------------------------------------------------
:: 4. Optional: ZIP erstellen
:: ---------------------------------------------------------------
echo.
set /p zipChoice="  ZIP-Archiv zum Weitergeben erstellen? (j/n): "
if /i "%zipChoice%"=="j" (
    echo.
    echo   Erstelle ZIP-Archiv...

    if exist "dist\Velodictum.zip" del "dist\Velodictum.zip"

    :: Versuche PowerShell Compress-Archive (Windows 10+)
    powershell -NoProfile -Command "Compress-Archive -Path 'dist\Velodictum\*' -DestinationPath 'dist\Velodictum.zip' -Force" 2>nul

    if exist "dist\Velodictum.zip" (
        echo.
        echo   ============================================================
        echo   [FERTIG] ZIP erstellt: dist\Velodictum.zip
        echo.
        echo   Sende diese ZIP an deinen Freund.
        echo   Er entpackt sie und startet Velodictum.exe - fertig!
        echo   ============================================================
    ) else (
        echo.
        echo   [HINWEIS] ZIP konnte nicht automatisch erstellt werden.
        echo   Bitte den Ordner dist\Velodictum\ manuell als ZIP verpacken.
    )
)

echo.
echo   ============================================================
echo   Build abgeschlossen. Druecke eine beliebige Taste zum Beenden.
echo   ============================================================
pause >nul
