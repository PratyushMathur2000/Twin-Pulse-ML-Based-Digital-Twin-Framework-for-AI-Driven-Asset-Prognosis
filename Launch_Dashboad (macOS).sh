#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Navigate to the actual code folder
cd project_files || {
    echo -e "${RED}[ERROR] Could not find project_files folder!${NC}"
    read -p "Press Enter to exit..."
    exit 1
}
echo "================================================================"
echo "        PUMP HEALTH MONITORING DASHBOARD V6.1"
echo "             TWIN-PULSE DIGITAL TWIN"
echo "        (AI + Theme System + Navigation)"
echo "================================================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null
then
    echo -e "${RED}[ERROR] Python 3 is not installed!${NC}"
    echo ""
    echo "Please install Python 3.8 or higher:"
    echo "  - Mac: brew install python3"
    echo "  - Linux: sudo apt-get install python3"
    echo ""
    read -p "Press Enter to exit..."
    exit 1
fi

echo -e "${GREEN}[OK] Python is installed${NC}"
python3 --version
echo ""

# Run verification script
echo -e "${BLUE}[STEP 1/4] Verifying setup...${NC}"
echo ""
python3 verify_setup.py
if [ $? -ne 0 ]; then
    echo ""
    echo -e "${RED}[ERROR] Setup verification failed!${NC}"
    echo "Please check the error messages above."
    read -p "Press Enter to exit..."
    exit 1
fi

echo ""
echo -e "${BLUE}[STEP 2/4] Checking dependencies...${NC}"
echo ""

# Check if requirements.txt exists
if [ ! -f requirements.txt ]; then
    echo -e "${RED}[ERROR] requirements.txt not found!${NC}"
    read -p "Press Enter to exit..."
    exit 1
fi

# Check if required packages are installed
python3 -c "import streamlit, pandas, numpy, plotly, sklearn, joblib, openai" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}[INFO] Installing missing dependencies...${NC}"
    echo ""
    python3 -m pip install --upgrade pip --quiet
    python3 -m pip install -r requirements.txt --quiet
    
    if [ $? -ne 0 ]; then
        echo ""
        echo -e "${YELLOW}[WARNING] Some packages may have failed to install.${NC}"
        echo "Attempting to continue..."
    else
        echo -e "${GREEN}[OK] Dependencies installed successfully!${NC}"
    fi
else
    echo -e "${GREEN}[OK] All Python dependencies are installed!${NC}"
fi

# Install requests if not present (for LM Studio check)
python3 -c "import requests" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}[INFO] Installing 'requests' for LM Studio detection...${NC}"
    python3 -m pip install requests --quiet 2>/dev/null
fi

echo ""

# Check LM Studio with model detection
echo -e "${BLUE}[STEP 3/4] Checking AI capabilities...${NC}"
echo ""

# Create temp Python script for detailed LM Studio check
cat > check_lm.py << 'EOF'
import requests
try:
    r = requests.get('http://localhost:1234/v1/models', timeout=2)
    data = r.json()
    models = data.get('data', [])
    if models:
        print(f"MODELS:{len(models)}")
        for m in models[:3]:
            print(f"MODEL_NAME:{m.get('id', 'Unknown')}")
        exit(0)
    else:
        exit(1)
except:
    exit(2)
EOF

# Run the check
LM_OUTPUT=$(python3 check_lm.py 2>/dev/null)
LM_STUDIO_STATUS=$?
rm -f check_lm.py 2>/dev/null

if [ $LM_STUDIO_STATUS -eq 2 ]; then
    echo "================================================================"
    echo "                   AI FEATURES: UNAVAILABLE"
    echo "================================================================"
    echo ""
    echo "  LM Studio is NOT RUNNING"
    echo ""
    echo "  DASHBOARD WILL WORK - All pages except AI Diagnostics will function."
    echo ""
    echo "  To enable AI Diagnostic Agent:"
    echo "   1. Install LM Studio from https://lmstudio.ai"
    echo "   2. Download a model (Nemotron 30B, Qwen 14B, or similar)"
    echo "   3. Open LM Studio Chat tab and load the model"
    echo "   4. Go to Local Server tab and click 'Start Server'"
    echo "   5. Refresh the AI Diagnostics page in dashboard"
    echo ""
    echo "  You can start LM Studio anytime without restarting dashboard."
    echo "================================================================"
    echo ""
elif [ $LM_STUDIO_STATUS -eq 1 ]; then
    echo "================================================================"
    echo "                   AI FEATURES: UNAVAILABLE"
    echo "================================================================"
    echo ""
    echo "  LM Studio is RUNNING but NO MODELS LOADED"
    echo ""
    echo "  DASHBOARD WILL WORK - All pages except AI Diagnostics will function."
    echo ""
    echo "  To enable AI:"
    echo "   1. Open LM Studio Chat tab"
    echo "   2. Select a model from the dropdown"
    echo "   3. Wait for it to load (20-30 seconds)"
    echo "   4. Go to Local Server tab and click 'Start Server'"
    echo "   5. Refresh the AI Diagnostics page in dashboard"
    echo "================================================================"
    echo ""
else
    echo "================================================================"
    echo "                    AI FEATURES: ENABLED!"
    echo "================================================================"
    echo ""
    echo "  LM Studio Status: RUNNING"
    echo "  Models Available: Multiple models detected"
    echo ""
    echo "  AI Diagnostic Agent will be fully functional!"
    echo "  - Fleet-level insights and recommendations"
    echo "  - Individual pump diagnostics with root cause analysis"
    echo "  - Interactive Q&A chat for specific questions"
    echo "  - Generation queue (resume if you navigate away)"
    echo "================================================================"
    echo ""
fi

# Launch Streamlit
echo -e "${BLUE}[STEP 4/4] Launching Dashboard...${NC}"
echo ""
echo "================================================================"
echo "   Dashboard is starting..."
echo "   It will open in your default web browser shortly."
echo ""
echo "   Default URL: http://localhost:8501"
echo ""
echo "   FEATURES AVAILABLE:"
echo "   ------------------"
echo "   > Production Simulator"
echo "     - Upload sensor data (CSV)"
echo "     - Multi-pump simulation"
echo "     - Auto-play and manual control"
echo "     - Real-time ML inference"
echo ""
echo "   > Fleet Overview"
echo "     - Multi-pump status cards"
echo "     - Click to view pump details"
echo "     - Live updates during simulation"
echo ""
echo "   > Detailed View"
echo "     - Real-time sensor gauges"
echo "     - Health status and RUL"
echo "     - Click sensors to view trends"
echo ""
echo "   > Sensor Trend Analysis"
echo "     - Historical time-series charts"
echo "     - Rolling statistics"
echo "     - Threshold visualization"
echo ""
echo "   > Digital Twin Sandbox"
echo "     - What-if scenario simulation"
echo "     - Maintenance intervention modelling"
echo "     - Baseline vs. scenario comparison"
echo "     - Risk and RUL trajectory analysis"
echo ""
if [ $LM_STUDIO_STATUS -ne 0 ]; then
    echo "   > AI Diagnostic Agent (REQUIRES LM STUDIO)"
    echo "     - See setup instructions above"
else
    echo "   > AI Diagnostic Agent (ENABLED)"
    echo "     - Fleet insights and maintenance planning"
    echo "     - Root cause analysis for failures"
    echo "     - Interactive diagnostic chat"
fi
echo ""
echo "   > Settings"
echo "     - 6 color themes (Orange/Blue/Purple/Green/Red/Teal)"
echo "     - Auto-refresh toggle"
echo "     - Dashboard preferences"
echo ""
echo "   TIPS:"
echo "   - Use horizontal navigation bar to switch pages"
echo "   - Click pump cards/sensors to drill down"
echo "   - AI generations resume if you navigate away"
echo "   - Change themes in Settings page"
echo ""
echo "   Press Ctrl+C in this window to stop the dashboard."
echo "================================================================"
echo ""

# Open browser after a short delay (Mac)
if [[ "$OSTYPE" == "darwin"* ]]; then
    (sleep 3 && open http://localhost:8501) &
# Open browser after a short delay (Linux)
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    (sleep 3 && xdg-open http://localhost:8501) &
fi

# Run Streamlit with App.py
python3 -m streamlit run App.py --server.headless true --server.port 8501 --server.address localhost

# If Streamlit exits
echo ""
echo "================================================================"
echo "   Dashboard has been stopped."
echo ""
echo "   To restart, run ./launch_dashboard.sh again."
echo "================================================================"
read -p "Press Enter to exit..."
