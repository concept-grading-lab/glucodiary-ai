@echo off
cd /d "%~dp0"
echo Starting GlucoDiary AI on http://127.0.0.1:8000/
echo Keep this window open while using the local app. Press Ctrl+C to stop it.
py -m uvicorn app.main:app --host 127.0.0.1 --port 8000
if errorlevel 1 (
    echo Could not launch. Run INSTALL_WINDOWS.bat first, or check Python and firewall settings.
    pause
)
