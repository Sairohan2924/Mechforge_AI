@echo off
cd /d "%~dp0"
echo ==============================================
echo       MechForge AI - Full Build v2.0
echo ==============================================
echo.
py -3.14 -m pip install -r requirements.txt
if errorlevel 1 (
  echo Dependency installation failed.
  pause
  exit /b 1
)
echo.
echo Starting MechForge AI...
py -3.14 -m streamlit run app.py
pause
