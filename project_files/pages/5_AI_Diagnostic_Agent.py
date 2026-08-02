import streamlit as st
import pandas as pd
import json
import time
from datetime import datetime
from openai import OpenAI
from utils.themes import apply_theme
from utils.navigation import render_horizontal_navigation, should_auto_refresh

st.set_page_config(
    page_title="AI Diagnostic Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

apply_theme()
render_horizontal_navigation()

# Set current page
st.session_state["current_page"] = "AI Diagnostic"

# ========================================
# GENERATION STATE MANAGEMENT
# ========================================

# Initialize generation tracking
if "ai_generation_queue" not in st.session_state:
    st.session_state["ai_generation_queue"] = []

if "ai_generation_in_progress" not in st.session_state:
    st.session_state["ai_generation_in_progress"] = False

# ========================================
# PAGE CONTENT STARTS HERE
# ========================================

st.title("🤖 AI Diagnostic Agent")
st.markdown("*Powered by LM Studio - Intelligent Pump Health Analysis*")

# Check for interrupted generations on page load
if st.session_state["ai_generation_queue"] and not st.session_state["ai_generation_in_progress"]:
    pending = st.session_state["ai_generation_queue"]
    
    st.warning(f"⚠️ You have {len(pending)} interrupted AI generation(s). Resume them below.")
    
    col_resume, col_clear = st.columns([3, 1])
    with col_resume:
        if st.button("🔄 Resume All Pending Generations", use_container_width=True):
            st.session_state["ai_generation_in_progress"] = True
            st.rerun()
    with col_clear:
        if st.button("❌ Clear Queue", use_container_width=True):
            st.session_state["ai_generation_queue"] = []
            st.rerun()

# -----------------------------
# CHECK DATA EXISTS
# -----------------------------
if "raw_df" not in st.session_state or st.session_state["raw_df"] is None:
    st.info("No production data loaded. Please upload sensor data in **Production Simulator** first.")
    st.stop()

active_pumps = st.session_state.get("sim_pump_ids", [])
if not active_pumps:
    st.warning("⚠️ No pumps selected in Production Simulator. Please select pumps and start simulation first.")
    st.stop()

sim_log = st.session_state.get("sim_log_df")
if sim_log is None or sim_log.empty:
    st.info("Waiting for simulation data... Start the simulation in **Production Simulator** to begin AI analysis.")
    st.stop()

# Show live status indicator
if st.session_state.get("sim_autoplay", False):
    st.markdown(
        '<div style="text-align: center; padding: 10px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); '
        'border-radius: 10px; margin-bottom: 20px;">'
        '<span class="live-indicator"></span>'
        '<span style="color: white; font-weight: 600; font-size: 16px;">LIVE - Dashboard updating automatically</span>'
        '</div>',
        unsafe_allow_html=True
    )

# -----------------------------
# SIDEBAR - LM STUDIO CONFIG & SIMULATION CONTROL
# -----------------------------
st.sidebar.header("🔧 AI Configuration")

lm_studio_url = st.sidebar.text_input(
    "LM Studio API URL",
    value="http://localhost:1234/v1",
    help="Make sure LM Studio is running with a model loaded"
)

# Test connection and detect available models
lm_studio_available = False
models_loaded = False
available_models = []

try:
    import requests
    client = OpenAI(base_url=lm_studio_url, api_key="not-needed")
    
    base_url = lm_studio_url.replace('/v1', '')
    response = requests.get(f"{base_url}/v1/models", timeout=2)
    
    if response.status_code == 200:
        data = response.json()
        models = data.get('data', [])
        
        if models:
            lm_studio_available = True
            models_loaded = True
            available_models = [m.get('id', 'Unknown') for m in models]
            
            st.sidebar.success(f"✅ Connected ({len(models)} model(s) available)")
        else:
            st.sidebar.warning("⚠️ LM Studio running but NO MODELS loaded")
    else:
        st.sidebar.error("❌ LM Studio server not responding")
        
except ImportError:
    st.sidebar.error("❌ 'requests' library not installed")
    st.sidebar.info("Run: pip install requests")
except Exception as e:
    st.sidebar.error("❌ Cannot connect to LM Studio")

# Model selector (if multiple models available)
selected_model = None
if available_models:
    if len(available_models) == 1:
        selected_model = available_models[0]
        st.sidebar.info(f"Using model: **{selected_model}**")
    else:
        selected_model = st.sidebar.selectbox(
            "Select Model",
            options=available_models,
            help="Choose which model to use for AI diagnostics"
        )

# Show detailed error if LM Studio not available
if not lm_studio_available or not models_loaded:
    st.error("🚫 AI Diagnostic Agent Unavailable")
    
    st.markdown("""
    ### LM Studio is Required for AI Features
    
    **Current Status:**
    - ❌ LM Studio not detected or no models loaded
    - ✅ All other dashboard pages work normally
    
    ---
    """)
    
    with st.expander("📖 Complete Setup Guide", expanded=True):
        st.markdown("""
        ### Step 1: Install LM Studio
        
        1. Download from **[lmstudio.ai](https://lmstudio.ai)**
        2. Install the application (Windows/Mac/Linux)
        3. Launch LM Studio
        
        ---
        
        ### Step 2: Download a Model
        
        1. Click the **🔍 Search** icon in LM Studio sidebar
        2. Search for one of these models:
           - **Nemotron 30B** (Recommended - Best quality)
           - **Qwen 2.5 14B** (Faster, less RAM)
           - Any model with "Instruct" in the name
        3. Click **Download** and wait (can take 10-30 minutes)
        4. Model appears in **"My Models"** tab when done
        
        **RAM Requirements:**
        - Nemotron 30B: ~20-24 GB RAM
        - Qwen 14B: ~10-12 GB RAM
        
        ---
        
        ### Step 3: Load the Model
        
        1. Click the **💬 Chat** tab in LM Studio
        2. At the top, click **"Select a model"** dropdown
        3. Choose your downloaded model
        4. Wait 20-30 seconds for model to load into memory
        5. You should see the chat interface become active
        
        ---
        
        ### Step 4: Start the Local Server
        
        1. Click the **🔌 Local Server** (or "Developer") tab
        2. Make sure the same model is selected
        3. Click the **"Start Server"** button (usually green)
        4. You should see:
           - Status: **"Running"** or **"Online"** (green indicator)
           - Server URL: `http://localhost:1234/v1`
        
        **Keep LM Studio open!** Closing it will stop the server.
        
        ---
        
        ### Step 5: Refresh This Page
        
        Once the server is running with a model loaded:
        1. Come back to this dashboard tab
        2. Refresh the page (F5 or Ctrl+R)
        3. AI features will become available
        
        ---
        
        ### Troubleshooting
        
        **"Cannot connect to LM Studio"**
        - Make sure LM Studio is actually running
        - Check the "Local Server" tab shows "Running"
        - Try changing port to 1234 if it's different
        
        **"No models loaded"**
        - Load a model in the Chat tab first
        - Then start the Local Server
        - Model must be loaded before starting server
        
        **"Out of memory"**
        - Close other applications
        - Try a smaller model (Qwen 14B instead of Nemotron 30B)
        - Restart LM Studio and your computer
        
        ---
        
        ### All Other Features Work Without AI:
        
        ✅ **Production Simulator** - Upload and simulate pump data  
        ✅ **Fleet Overview** - Multi-pump status monitoring  
        ✅ **Detailed View** - Real-time sensor gauges  
        ✅ **Sensor Trend** - Historical time-series analysis  
        
        Only this AI Diagnostic Agent page requires LM Studio.
        """)
    
    st.info("💡 **You can use all other dashboard pages while setting up LM Studio**")
    
    if st.button("🔄 Check LM Studio Connection Again", use_container_width=True):
        st.rerun()
    
    st.stop()

st.sidebar.markdown("---")

# SIMULATION CONTROL BOX
st.sidebar.markdown("### 🎮 Simulation Control")

step_hours = st.session_state.get("sim_step_hours", 72)
current_idx = st.session_state.get("sim_current_idx", 0)

# Calculate total steps
total_steps = 0
if active_pumps:
    pump_id = active_pumps[0]
    pump_data_full = st.session_state["raw_df"][
        st.session_state["raw_df"]["machine_id"] == pump_id
    ]
    total_steps = len(pump_data_full) // step_hours if len(pump_data_full) > 0 else 1

auto_advance = st.sidebar.checkbox(
    "Auto-refresh display",
    value=True,
    help="Automatically refresh when simulation advances",
    key="ai_auto_refresh"
)

sim_status = "🟢 Running" if st.session_state.get("sim_autoplay", False) else "⏸️ Paused"
st.sidebar.info(f"""
**Simulation Status:** {sim_status}
**Current Step:** {current_idx}/{total_steps}
**Active Pumps:** {len(active_pumps)}
""")

st.sidebar.markdown("---")

# -----------------------------
# AUTO-ADVANCE SIMULATION LOGIC
# -----------------------------
should_advance_flag = False
if auto_advance and st.session_state.get("sim_autoplay", False) and current_idx < total_steps:
    should_advance_flag = True
    
    for pump_id in active_pumps:
        simulator = st.session_state["simulators"].get(pump_id)
        if simulator:
            pump_data = st.session_state["raw_df"][
                st.session_state["raw_df"]["machine_id"] == pump_id
            ].copy()
            
            row_idx = current_idx * step_hours
            
            if row_idx < len(pump_data):
                row_df = pump_data.iloc[[row_idx]]
                result = simulator.process_streaming_row(row_df)
                
                log_entry = {
                    "machine_id": pump_id,
                    "timestamp": result["timestamp"],
                    "health_label": result["health_label"],
                    "rul_days": result["rul_days"],
                    "risk_score": result["risk_score"],
                    "risk_band": result["risk_band"],
                    "dominant_sensors": result["dominant_sensors"],
                    "comment": result["comment"],
                }
                
                if st.session_state.get("sim_log_df") is None:
                    st.session_state["sim_log_df"] = pd.DataFrame([log_entry])
                else:
                    st.session_state["sim_log_df"] = pd.concat(
                        [st.session_state["sim_log_df"], pd.DataFrame([log_entry])],
                        ignore_index=True
                    )
    
    st.session_state["sim_current_idx"] = current_idx + 1

# -----------------------------
# CONTEXT BUILDER
# -----------------------------
def build_pump_context(pump_id):
    """Build comprehensive context for a single pump"""
    pump_logs = sim_log[sim_log["machine_id"] == pump_id]
    
    if pump_logs.empty:
        return None
    
    latest = pump_logs.iloc[-1]
    
    raw_df = st.session_state["raw_df"]
    current_row_idx = current_idx * step_hours
    pump_data = raw_df[raw_df["machine_id"] == pump_id]
    
    if current_row_idx < len(pump_data):
        sensor_data = pump_data.iloc[current_row_idx]
    else:
        sensor_data = pump_data.iloc[-1]
    
    context = {
        "pump_id": pump_id,
        "timestamp": latest.get("timestamp", ""),
        "health_label": latest.get("health_label", "Unknown"),
        "rul_days": latest.get("rul_days", 0),
        "risk_score": int(latest.get("risk_score", 0)),
        "risk_band": latest.get("risk_band", ""),
        "dominant_sensors": latest.get("dominant_sensors", "None"),
        "comment": latest.get("comment", ""),
        "sensors": {
            "radial_vibration": sensor_data.get("radial_vibration_rms", 0),
            "axial_vibration": sensor_data.get("axial_vibration_rms", 0),
            "high_freq_vibration": sensor_data.get("high_freq_vibration", 0),
            "bearing_temp": sensor_data.get("bearing_temperature", 0),
            "casing_temp": sensor_data.get("casing_temperature", 0),
            "discharge_pressure": sensor_data.get("discharge_pressure", 0),
            "power_consumption": sensor_data.get("power_consumption", 0),
            "acoustics": sensor_data.get("acoustic_emission", 0)
        },
        "history_length": len(pump_logs)
    }
    
    if len(pump_logs) > 1:
        health_changes = []
        prev_health = None
        for idx, row in pump_logs.iterrows():
            curr_health = row.get("health_label")
            if prev_health and curr_health != prev_health:
                health_changes.append({
                    "timestamp": row.get("timestamp"),
                    "from": prev_health,
                    "to": curr_health
                })
            prev_health = curr_health
        context["health_changes"] = health_changes
    else:
        context["health_changes"] = []
    
    return context

def build_fleet_context():
    """Build fleet-level summary"""
    fleet_summary = []
    
    for pump_id in active_pumps:
        ctx = build_pump_context(pump_id)
        if ctx:
            fleet_summary.append({
                "pump_id": ctx["pump_id"],
                "health": ctx["health_label"],
                "risk": ctx["risk_score"],
                "rul_days": ctx["rul_days"],
                "issues": ctx["dominant_sensors"]
            })
    
    return fleet_summary

# -----------------------------
# AI AGENT FUNCTIONS
# -----------------------------
def call_ai(system_prompt, user_prompt, temperature=0.3):
    """Call LM Studio API with the selected model"""
    try:
        if not selected_model:
            return "Error: No model selected"
        
        response = client.chat.completions.create(
            model=selected_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=1500
        )
        
        content = response.choices[0].message.content
        
        # Clean up thinking tags
        if "</think>" in content:
            content = content.split("</think>")[-1].strip()
        
        content = content.replace("<think>", "").replace("</think>", "")
        
        reasoning_phrases = [
            "We need to respond", "Let's craft:", "Paragraph1:", "Paragraph2:",
            "Paragraph3:", "Paragraph4:", "Check formatting:", "Make sure",
            "Let's output", "Provide content", "Ensure each", "Must be exactly",
            "So paragraph", "Provide root cause"
        ]
        
        lines = content.split('\n')
        cleaned_lines = [line for line in lines if not any(phrase in line for phrase in reasoning_phrases)]
        content = '\n'.join(cleaned_lines).strip()
        
        return content
        
    except Exception as e:
        return f"Error: {str(e)}"

def generate_fleet_insights():
    """Proactive fleet-level analysis"""
    fleet_data = build_fleet_context()
    
    system_prompt = """You are a senior industrial maintenance engineer with 20+ years experience in predictive maintenance and cost optimization.

DO NOT show your thinking process. Output ONLY the final answer.

MAINTENANCE PHILOSOPHY:
- Schedule maintenance at 70-80% of predicted RUL (safety margin)
- Preventive maintenance (before Critical) costs 1/10th of emergency repairs
- Plan maintenance when pump is Degrading, not when Critical
- Consider parts lead time (typically 5-15 days for pumps)
- Batch maintenance jobs to reduce downtime costs

SENSOR INTERPRETATION:
- Radial Vibration >2.5 mm/s = bearing wear starting
- Bearing Temp >70°C = lubrication issues, friction increasing
- Discharge Pressure >6 bar = cavitation or blockage risk
- Multiple sensors failing = cascading failure imminent
- Rapid degradation (Healthy→Critical in <48h) = inspect immediately

HEALTHY RANGES:
- Radial Vibration: 0.5-2.5 mm/s | Axial: 0.3-2.0 mm/s | High Freq: 0.05-0.30 g
- Bearing Temp: 40-70°C | Casing: 35-65°C
- Discharge Pressure: 3.0-6.0 bar | Power: 15-30 kW | Acoustics: 50-70 dB

Provide strategic, cost-aware recommendations."""
    
    user_prompt = f"""Analyze this pump fleet and provide strategic insights:

{json.dumps(fleet_data, indent=2, default=str)}

Provide:

**1. Critical Actions (Next 48 Hours)**
- Which pumps need IMMEDIATE attention?
- What will happen if ignored? (cost impact, safety risk)
- Specific actions with timelines

**2. Short-Term Maintenance Plan (Next 2 Weeks)**
- Which pumps to schedule for preventive maintenance?
- Optimal maintenance windows (use 70-80% of RUL)
- Estimated parts needed and lead times

**3. Fleet Risk Assessment**
- Overall fleet health score (0-100)
- Biggest vulnerability (what's most likely to fail next?)
- Cost exposure (high/medium/low risk of unplanned downtime)

**4. Recommendations**
- Any pumps to monitor closely?
- Suggest operational changes (reduce load, adjust speed)?

Be specific with numbers, timelines, and reasoning."""
    
    return call_ai(system_prompt, user_prompt, temperature=0.4)

def generate_pump_diagnosis(pump_id):
    """Deep-dive analysis for single pump"""
    ctx = build_pump_context(pump_id)
    
    if not ctx:
        return "No data available for this pump."
    
    system_prompt = """You are an expert pump maintenance engineer specializing in predictive diagnostics and failure analysis.

DO NOT show your thinking process. Output ONLY the final answer.

CRITICAL RULES:
1. **Safety Margin**: Schedule maintenance at 70-80% of RUL, NOT at 100%
2. **Cost Optimization**: Preventive maintenance before Critical status costs 10x less than emergency repairs
3. **Parts Lead Time**: Account for 5-15 day procurement delays
4. **Operational Windows**: Suggest maintenance timing that minimizes production impact

SENSOR DIAGNOSTICS:
- Radial Vibration: >2.5 = bearing wear | >4.0 = severe misalignment | >7.0 = imminent failure
- Axial Vibration: >2.0 = shaft misalignment | >3.5 = coupling issues
- Bearing Temp: >70°C = lubrication breakdown | >85°C = thermal damage starting | >95°C = emergency
- Discharge Pressure: >6 bar = cavitation | >8 bar = blockage | <3 bar = impeller damage
- Power Consumption: >30 kW = mechanical resistance | >40 kW = severe load increase

ROOT CAUSE PATTERNS:
- High vibration + high temp = bearing failure (most common)
- High vibration + normal temp = imbalance or misalignment
- High pressure + high power = blockage or cavitation
- Rising temp alone = lubrication failure
- Multiple sensors spiking = cascading failure

FAILURE MODES:
- Bearing failure: 40% of pump failures, 5-10 day lead time for parts
- Seal failure: 25% of failures, 3-5 day lead time
- Impeller damage: 15% of failures, 10-20 day lead time
- Shaft/coupling: 10% of failures, 7-15 day lead time"""
    
    rul_display = "N/A" if (ctx['rul_days'] is None or pd.isna(ctx['rul_days'])) else f"{ctx['rul_days']:.1f}"
    
    user_prompt = f"""Provide detailed technical diagnosis for this pump:

**PUMP DATA:**
ID: {ctx['pump_id']}
Status: {ctx['health_label']}
RUL: {rul_display} days
Risk Score: {ctx['risk_score']}/100
Problem Sensors: {ctx['dominant_sensors']}
Comment: {ctx['comment']}

**SENSOR READINGS:**
- Radial Vibration: {ctx['sensors']['radial_vibration']:.2f} mm/s (threshold: 2.5)
- Axial Vibration: {ctx['sensors']['axial_vibration']:.2f} mm/s (threshold: 2.0)
- High Freq Vibration: {ctx['sensors']['high_freq_vibration']:.3f} g (threshold: 0.30)
- Bearing Temperature: {ctx['sensors']['bearing_temp']:.1f}°C (threshold: 70)
- Casing Temperature: {ctx['sensors']['casing_temp']:.1f}°C (threshold: 65)
- Discharge Pressure: {ctx['sensors']['discharge_pressure']:.2f} bar (threshold: 6.0)
- Power Consumption: {ctx['sensors']['power_consumption']:.1f} kW (threshold: 30)
- Acoustics: {ctx['sensors']['acoustics']:.1f} dB (threshold: 70)

**DEGRADATION HISTORY:**
{json.dumps(ctx['health_changes'], default=str) if ctx['health_changes'] else "No health state changes yet"}

Provide detailed analysis in 4 sections:

**1. Root Cause Analysis**
- What component is failing? (bearing/seal/impeller/shaft)
- What caused it? (wear/lubrication/misalignment/load)
- How severe? (early/moderate/advanced failure)
- Supporting evidence from sensors (cite specific readings)

**2. Failure Timeline & Urgency**
- Current RUL: {rul_display} days
- Recommended maintenance window: [Calculate 70-80% of RUL, or immediate if Critical]
- What happens if ignored? (describe failure mode and consequences)
- Cost impact: Compare preventive vs emergency repair costs

**3. Maintenance Plan**
- Immediate actions (next 24-48 hours)
- Scheduled maintenance date (with reasoning)
- Inspection checklist (what to verify during maintenance)
- Operational adjustments until repair (reduce speed/load if applicable)

**4. Parts & Procurement**
- Primary parts needed (with quantity and specifications)
- Lead time for parts (days)
- Order deadline (when to order to meet maintenance window)
- Backup/secondary parts to inspect (preventive replacement)

Be specific with numbers, dates, and technical details. Reference sensor values to support conclusions."""
    
    return call_ai(system_prompt, user_prompt, temperature=0.3)

def answer_question(pump_id, question):
    """Answer user's custom question"""
    ctx = build_pump_context(pump_id)
    
    system_prompt = f"""You are a senior pump maintenance engineer answering questions about {pump_id}.

DO NOT show your thinking process. Output ONLY the final answer.

MAINTENANCE PRINCIPLES:
- Always account for 20-30% safety margin in RUL predictions
- Preventive maintenance before Critical status saves 90% of repair costs
- Parts lead time is typically 5-15 days
- Emergency repairs cost 10x more than planned maintenance
- Consider production impact when scheduling downtime

Answer questions with:
- Specific numbers and timelines
- Cost/risk trade-offs
- Technical reasoning with sensor evidence
- Actionable recommendations

Be concise but thorough. Cite sensor values and thresholds."""
    
    rul_display = "N/A" if (ctx['rul_days'] is None or pd.isna(ctx['rul_days'])) else f"{ctx['rul_days']:.1f}"
    
    user_prompt = f"""**PUMP DATA:**
{json.dumps(ctx, indent=2, default=str)}

**USER QUESTION:** {question}

Answer with technical depth, specific timelines, and cost considerations. Reference sensor data."""
    
    return call_ai(system_prompt, user_prompt, temperature=0.5)

# -----------------------------
# PROACTIVE FLEET INSIGHTS
# -----------------------------
st.markdown("## 🚨 Fleet-Level Insights")
st.markdown("*Auto-generated analysis of all active pumps*")

# Check for pending fleet analysis
fleet_pending = any(item["type"] == "fleet" for item in st.session_state.get("ai_generation_queue", []))

if fleet_pending and st.session_state.get("ai_generation_in_progress"):
    # Auto-resume fleet analysis
    with st.spinner(f"Resuming fleet analysis with {selected_model}..."):
        insights = generate_fleet_insights()
        st.session_state["fleet_insights"] = insights
        st.session_state["insights_timestamp"] = datetime.now()
        
        # Remove from queue
        st.session_state["ai_generation_queue"] = [
            item for item in st.session_state["ai_generation_queue"] 
            if item["type"] != "fleet"
        ]
        
        if not st.session_state["ai_generation_queue"]:
            st.session_state["ai_generation_in_progress"] = False
        
        st.success("✅ Fleet analysis completed!")
        st.rerun()

if st.button("🔄 Refresh Fleet Analysis", use_container_width=True):
    # Add to queue before generating
    st.session_state["ai_generation_queue"].append({
        "type": "fleet",
        "timestamp": datetime.now()
    })
    st.session_state["ai_generation_in_progress"] = True
    
    with st.spinner(f"Analyzing fleet with {selected_model}..."):
        insights = generate_fleet_insights()
        st.session_state["fleet_insights"] = insights
        st.session_state["insights_timestamp"] = datetime.now()
        
        # Remove from queue after completion
        st.session_state["ai_generation_queue"] = [
            item for item in st.session_state["ai_generation_queue"] 
            if item["type"] != "fleet"
        ]
        
        if not st.session_state["ai_generation_queue"]:
            st.session_state["ai_generation_in_progress"] = False
        
        st.rerun()

if "fleet_insights" in st.session_state:
    timestamp = st.session_state.get("insights_timestamp", datetime.now())
    st.markdown(f"*Last updated: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}*")
    st.markdown(st.session_state["fleet_insights"])
else:
    st.info("Click **Refresh Fleet Analysis** to generate AI insights")

st.markdown("---")

# -----------------------------
# PUMP-SPECIFIC DIAGNOSTICS
# -----------------------------
st.markdown("## 🔍 Pump Deep-Dive Diagnostics")
st.markdown("*Select one or multiple pumps for detailed analysis*")

col1, col2 = st.columns([1, 3])

with col1:
    selected_diagnostic_pumps = st.multiselect(
        "Select Pump(s)",
        options=active_pumps,
        default=[active_pumps[0]] if active_pumps else [],
        key="diagnostic_pumps_select",
        help="Select one or more pumps for diagnosis"
    )
    
    # Check for pending pump diagnostics
    pending_pumps = [
        item["pump_id"] for item in st.session_state.get("ai_generation_queue", [])
        if item["type"] == "diagnosis" and item["pump_id"] in selected_diagnostic_pumps
    ]
    
    if pending_pumps and st.session_state.get("ai_generation_in_progress"):
        # Auto-resume diagnostics
        with st.spinner(f"Resuming diagnosis for {len(pending_pumps)} pump(s)..."):
            if "pump_diagnoses" not in st.session_state:
                st.session_state["pump_diagnoses"] = {}
            
            for pump in pending_pumps:
                diagnosis = generate_pump_diagnosis(pump)
                st.session_state["pump_diagnoses"][pump] = {
                    "content": diagnosis,
                    "timestamp": datetime.now()
                }
                
                # Remove from queue
                st.session_state["ai_generation_queue"] = [
                    item for item in st.session_state["ai_generation_queue"]
                    if not (item["type"] == "diagnosis" and item["pump_id"] == pump)
                ]
            
            if not st.session_state["ai_generation_queue"]:
                st.session_state["ai_generation_in_progress"] = False
            
            st.success(f"✅ Diagnosis completed for {len(pending_pumps)} pump(s)!")
            st.rerun()
    
    if st.button("🩺 Generate Diagnosis", use_container_width=True, disabled=not selected_diagnostic_pumps):
        # Add to queue before generating
        for pump in selected_diagnostic_pumps:
            st.session_state["ai_generation_queue"].append({
                "type": "diagnosis",
                "pump_id": pump,
                "timestamp": datetime.now()
            })
        
        st.session_state["ai_generation_in_progress"] = True
        
        with st.spinner(f"Analyzing {len(selected_diagnostic_pumps)} pump(s)..."):
            if "pump_diagnoses" not in st.session_state:
                st.session_state["pump_diagnoses"] = {}
            
            for pump in selected_diagnostic_pumps:
                diagnosis = generate_pump_diagnosis(pump)
                st.session_state["pump_diagnoses"][pump] = {
                    "content": diagnosis,
                    "timestamp": datetime.now()
                }
                
                # Remove from queue after completion
                st.session_state["ai_generation_queue"] = [
                    item for item in st.session_state["ai_generation_queue"]
                    if not (item["type"] == "diagnosis" and item["pump_id"] == pump)
                ]
            
            if not st.session_state["ai_generation_queue"]:
                st.session_state["ai_generation_in_progress"] = False
            
            st.rerun()

with col2:
    if "pump_diagnoses" in st.session_state and selected_diagnostic_pumps:
        for pump in selected_diagnostic_pumps:
            if pump in st.session_state["pump_diagnoses"]:
                diag = st.session_state["pump_diagnoses"][pump]
                
                st.markdown(f"### {pump}")
                st.markdown(f"*Generated at: {diag['timestamp'].strftime('%H:%M:%S')}*")
                st.markdown(diag["content"])
                
                report_text = f"""PUMP DIAGNOSTIC REPORT
Generated: {diag['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}
Pump ID: {pump}

{diag['content']}
"""
                st.download_button(
                    label=f"📥 Download {pump} Report",
                    data=report_text,
                    file_name=f"{pump}_diagnosis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain",
                    key=f"download_{pump}"
                )
                
                st.markdown("---")
    else:
        st.info("Select pump(s) and click **Generate Diagnosis** to analyze")

st.markdown("---")

# -----------------------------
# CHAT INTERFACE
# -----------------------------
st.markdown("## 💬 Ask the AI Agent")
st.markdown("*Interactive Q&A for detailed questions about a specific pump*")

if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

chat_pump = st.selectbox(
    "Select pump for chat",
    options=active_pumps,
    key="chat_pump_select"
)

chat_container = st.container()
with chat_container:
    for msg in st.session_state["chat_history"]:
        if msg["pump"] == chat_pump:
            with st.chat_message("user"):
                st.write(msg["question"])
            with st.chat_message("assistant"):
                st.write(msg["answer"])

user_question = st.chat_input(f"Ask about {chat_pump}... (e.g., 'When did the problem start?', 'What part should I replace?')")

if user_question:
    with st.spinner("Thinking..."):
        answer = answer_question(chat_pump, user_question)
    
    st.session_state["chat_history"].append({
        "pump": chat_pump,
        "question": user_question,
        "answer": answer,
        "timestamp": datetime.now()
    })
    st.rerun()

if st.button("🗑️ Clear Chat History"):
    st.session_state["chat_history"] = []
    st.rerun()

st.markdown("---")
st.markdown("*💡 Tip: Ask specific questions like 'What caused the failure?' or 'How urgent is this repair?'*")

# -----------------------------
# AUTO-REFRESH LOGIC
# -----------------------------
if should_auto_refresh():
    if should_advance_flag or not auto_advance:
        time.sleep(2 if auto_advance else 3)
        st.rerun()
