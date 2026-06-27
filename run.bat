@echo off
chcp 65001 >nul
title Realtime Voice Changer
echo.
echo  Realtime Voice Changer (TD-PSOLA)
echo  --------------------------------
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [Error] Python not found. Install Python 3.8+ from
    echo https://www.python.org/downloads/  (tick "Add Python to PATH")
    pause & exit /b 1
)

echo [1/2] Installing dependencies (into the running Python)...
python -m pip install -r requirements.txt --quiet
echo       done
echo.
echo [2/2] Launching...
python -m voicechanger

if errorlevel 1 (
    echo.
    echo [Error] Run manually: python -m pip install -r requirements.txt
    pause
)
