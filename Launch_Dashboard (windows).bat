@echo off
SETLOCAL EnableDelayedExpansion

:: Set colors for better visibility
COLOR 0A

:: Navigate to the actual code folder
cd project_files
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Could not find project_files folder!
    pause
    exit /b 1
)
echo ================================================================
echo         PUMP HEALTH MONITORING DASHBOARD V6.1
echo              TWIN-PULSE DIGITAL TWIN
echo              (AI + Theme System + Navigation)
echo ================================================================
echo.

:: Check if Python is installed
python --version 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo.
    echo Please install Python 3.8 or higher from:
    echo https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo [OK] Python is installed
echo.

:: Run verification script
echo [STEP 1/4] Verifying setup...
echo.
python verify_setup.py
if %ERRORLEVEL% EQU 1 (
    echo.
    echo [ERROR] Setup verification failed!
    echo Please check the error messages above.
    pause
    exit /b 1
)

:: Check if dependencies need to be installed
echo.
echo [STEP 2/4] Checking dependencies...
echo.

:: Try importing required packages
python -c "import streamlit, pandas, numpy, plotly, sklearn, joblib, openai" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [INFO] Installing missing dependencies...
    echo.
    pip install -r requirements.txt --quiet --disable-pip-version-check
    if %ERRORLEVEL% NEQ 0 (
        echo [WARNING] Some packages failed to install.
        echo [INFO] Attempting to continue anyway...
    ) else (
        echo [OK] Dependencies installed successfully!
    )
) else (
    echo [OK] All Python dependencies are installed!
)

:: Install requests if not present (for LM Studio check)
python -c "import requests" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [INFO] Installing 'requests' for LM Studio detection...
    pip install requests --quiet --disable-pip-version-check 2>nul
)

echo.

:: Check LM Studio with model detection
echo [STEP 3/4] Checking AI capabilities...
echo.

:: Create temp Python script for detailed LM Studio check
echo import requests > check_lm.py
echo try: >> check_lm.py
echo     r = requests.get('http://localhost:1234/v1/models', timeout=2) >> check_lm.py
echo     data = r.json() >> check_lm.py
echo     models = data.get('data', []) >> check_lm.py
echo     if models: >> check_lm.py
echo         print(f"MODELS:{len(models)}") >> check_lm.py
echo         for m in models[:3]: >> check_lm.py
echo             print(f"MODEL_NAME:{m.get('id', 'Unknown')}") >> check_lm.py
echo         exit(0) >> check_lm.py
echo     else: >> check_lm.py
echo         exit(1) >> check_lm.py
echo except: >> check_lm.py
echo     exit(2) >> check_lm.py

:: Run the check
for /f "delims=" %%i in ('python check_lm.py 2^>nul') do set "LM_OUTPUT=%%i"
set LM_STUDIO_STATUS=%ERRORLEVEL%
del check_lm.py 2>nul

if %LM_STUDIO_STATUS% EQU 2 (
    echo ================================================================
    echo                    AI FEATURES: UNAVAILABLE
    echo ================================================================
    echo.
    echo  LM Studio is NOT RUNNING
    echo.
    echo  DASHBOARD WILL WORK - All pages except AI Diagnostics will function.
    echo.
    echo  To enable AI Diagnostic Agent:
    echo   1. Install LM Studio from https://lmstudio.ai
    echo   2. Download a model (Nemotron 30B, Qwen 14B, or similar)
    echo   3. Open LM Studio Chat tab and load the model
    echo   4. Go to Local Server tab and click "Start Server"
    echo   5. Refresh the AI Diagnostics page in dashboard
    echo.
    echo  You can start LM Studio anytime without restarting dashboard.
    echo ================================================================
    echo.
) else if %LM_STUDIO_STATUS% EQU 1 (
    echo ================================================================
    echo                    AI FEATURES: UNAVAILABLE
    echo ================================================================
    echo.
    echo  LM Studio is RUNNING but NO MODELS LOADED
    echo.
    echo  DASHBOARD WILL WORK - All pages except AI Diagnostics will function.
    echo.
    echo  To enable AI:
    echo   1. Open LM Studio Chat tab
    echo   2. Select a model from the dropdown
    echo   3. Wait for it to load (20-30 seconds)
    echo   4. Go to Local Server tab and click "Start Server"
    echo   5. Refresh the AI Diagnostics page in dashboard
    echo ================================================================
    echo.
) else (
    echo ================================================================
    echo                     AI FEATURES: ENABLED!
    echo ================================================================
    echo.
    echo  LM Studio Status: RUNNING
    echo  Models Available: Multiple models detected
    echo.
    echo  AI Diagnostic Agent will be fully functional!
    echo  - Fleet-level insights and recommendations
    echo  - Individual pump diagnostics with root cause analysis
    echo  - Interactive Q^&A chat for specific questions
    echo  - Generation queue (resume if you navigate away)
    echo ================================================================
    echo.
)

:: Launch Streamlit
echo [STEP 4/4] Launching Dashboard...
echo.
echo ================================================================
echo    Dashboard is starting...
echo    It will open in your default web browser shortly.
echo.
echo    Default URL: http://localhost:8501
echo.
echo    FEATURES AVAILABLE:
echo    ------------------
echo    ^> Production Simulator
echo      - Upload sensor data (CSV)
echo      - Multi-pump simulation
echo      - Auto-play and manual control
echo      - Real-time ML inference
echo.
echo    ^> Fleet Overview
echo      - Multi-pump status cards
echo      - Click to view pump details
echo      - Live updates during simulation
echo.
echo    ^> Detailed View
echo      - Real-time sensor gauges
echo      - Health status and RUL
echo      - Click sensors to view trends
echo.
echo    ^> Sensor Trend Analysis
echo      - Historical time-series charts
echo      - Rolling statistics
echo      - Threshold visualization
echo.
echo    ^> Digital Twin Sandbox
echo      - What-if scenario simulation
echo      - Maintenance intervention modelling
echo      - Baseline vs. scenario comparison
echo      - Risk and RUL trajectory analysis
echo.
if %LM_STUDIO_STATUS% NEQ 0 (
echo    ^> AI Diagnostic Agent (REQUIRES LM STUDIO)
echo      - See setup instructions above
) else (
echo    ^> AI Diagnostic Agent (ENABLED)
echo      - Fleet insights and maintenance planning
echo      - Root cause analysis for failures
echo      - Interactive diagnostic chat
)
echo.
echo    ^> Settings
echo      - 6 color themes (Orange/Blue/Purple/Green/Red/Teal)
echo      - Auto-refresh toggle
echo      - Dashboard preferences
echo.
echo    TIPS:
echo    - Use horizontal navigation bar to switch pages
echo    - Click pump cards/sensors to drill down
echo    - AI generations resume if you navigate away
echo    - Change themes in Settings page
echo.
echo    Press Ctrl+C in this window to stop the dashboard.
echo ================================================================
echo.

:: Open browser after a short delay
start "" cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:8501"

:: Run Streamlit with App.py
python -m streamlit run App.py --server.headless true --server.port 8501 --server.address localhost

:: If Streamlit exits
echo.
echo ================================================================
echo    Dashboard has been stopped.
echo.
echo    To restart, run launch_dashboard.bat again.
echo ================================================================
pause
