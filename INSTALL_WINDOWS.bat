@echo off
cd /d "%~dp0"
echo Installing GlucoDiary AI dependencies for the current Python installation...
py -m pip install -r requirements.txt
if errorlevel 1 (
    echo Installation failed. Check Python 3.11+ and internet access.
    pause
    exit /b 1
)
echo Installation complete. Run START_WINDOWS.bat next.
pause
