@echo off
title Velodictum Studio
cd /d "%~dp0"

:loop
cls
echo ============================================================
echo   VELODICTUM STUDIO - Starting Local AI Dictation Engine
echo   (Tastenkombination fuer Sofort-Abbruch: STRG + C)
echo ============================================================

if not exist .venv\Scripts\python.exe goto :no_venv

.venv\Scripts\python.exe main.py
goto :finished

:no_venv
echo [FEHLER] Virtuelle Python-Umgebung nicht gefunden (.venv)
pause
exit /b 1

:finished
echo.
echo ============================================================
echo   Velodictum wurde beendet.
echo ============================================================
echo   [R] Druecke R zum sofortigen NEUSTART
echo   [Beliebige Taste] BEENDEN
echo ============================================================
set choice=
set /p choice=Eingabe: 
if /i "%choice%"=="r" goto :loop
