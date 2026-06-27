@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  Realtime Voice Changer (TD-PSOLA)
echo  --------------------------------
echo.

where python >nul 2>nul
if %errorlevel% neq 0 goto NOPYTHON

echo [1/2] Installing dependencies...
python -m pip install -r requirements.txt
echo.
echo [2/2] Launching...
python -m voicechanger
if %errorlevel% neq 0 goto RUNERROR
goto END

:NOPYTHON
echo [Error] Python not found on PATH.
echo Install Python 3.8+ from https://www.python.org/downloads/
echo and tick "Add Python to PATH" during install.
echo.
pause
exit /b 1

:RUNERROR
echo.
echo [Error] The app exited with an error above.
echo If it says a module is missing, run:
echo     python -m pip install -r requirements.txt
echo.
pause
exit /b 1

:END
