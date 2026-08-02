import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import time
from utils.themes import apply_theme, get_current_theme, THEMES
from utils.navigation import render_horizontal_navigation, should_auto_refresh
from utils.cache_helpers import run_auto_advance, get_total_steps

st.set_page_config(
    page_title="Detailed Sensor View", 
    page_icon="🔍", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Apply centralized theme
apply_theme()
render_horizontal_navigation()  # ← Keep only ONE
st.session_state["current_page"] = "Detailed View"

# ========================================
# PAGE-SPECIFIC STYLING
# ========================================
st.markdown("""
<style>
    /* ===== PAGE-SPECIFIC STYLING ===== */
    .timestamp-badge {
        display: inline-block;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 8px 16px;
        border-radius: 20px;
        font-size: 14px;
        font-weight: 500;
        margin-left: 15px;
        box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
    }
    
    [data-testid="column"] {
        padding: 0.5rem;
    }
    
    div.row-widget.stHorizontalBlock {
        gap: 0.5rem !important;
        margin-bottom: 0.5rem !important;
    }
    
    /* Beautified gauge container */
    .gauge-container {
        background: white;
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
    }
    
    .gauge-container:hover {
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
        transform: translateY(-2px);
    }
</style>
""", unsafe_allow_html=True)

# ========================================
# PAGE CONTENT STARTS HERE
# ========================================

st.title("🔍 Detailed Sensor Monitoring")


# Check if production data exists
if "raw_df" not in st.session_state or st.session_state["raw_df"] is None:
    st.info(
        "No production data loaded yet. "
        "Please upload sensor data in the **Production Simulator** page first."
    )
    st.stop()

# Get pumps that are ACTIVELY SIMULATING
active_pumps = st.session_state.get("sim_pump_ids", [])

if not active_pumps:
    st.warning("⚠️ No pumps selected in Production Simulator. Please select pumps and start simulation first.")
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

# Get data safely
raw_df = st.session_state["raw_df"]

# -----------------------------
# SIDEBAR - SIMULATION CONTROL BOX
# -----------------------------
st.sidebar.markdown("### 🎮 Simulation Control")

# Get simulation parameters
step_hours = st.session_state.get("sim_step_hours", 72)
current_idx = st.session_state.get("sim_current_idx", 0)
total_steps = get_total_steps(active_pumps, st.session_state["raw_df"], step_hours)

# Add auto-refresh toggle
auto_refresh = st.sidebar.checkbox(
    "Auto-refresh display", 
    value=True,
    help="Automatically refresh sensor readings while simulation is running",
    key="detailed_auto_refresh"
)

# Display simulation status in info box
sim_status = "🟢 Running" if st.session_state.get("sim_autoplay", False) else "⏸️ Paused"
st.sidebar.info(f"""
**Simulation Status:** {sim_status}

**Current Step:** {current_idx}/{total_steps}
""")

st.sidebar.markdown("---")

# Pump selection
st.sidebar.header("Select Pump")

# Check if navigated from Fleet Overview
if "detailed_selected_pump" in st.session_state and st.session_state["detailed_selected_pump"] in active_pumps:
    default_pump = st.session_state["detailed_selected_pump"]
else:
    default_pump = active_pumps[0] if active_pumps else "PUMP_001"
    st.session_state["detailed_selected_pump"] = default_pump

pump_ids = active_pumps
selected_pump = st.sidebar.selectbox(
    "Choose Pump",
    options=pump_ids,
    index=pump_ids.index(default_pump) if default_pump in pump_ids else 0,
    key="detailed_pump_select",
)
st.session_state["detailed_selected_pump"] = selected_pump

# -----------------------------
# AUTO-ADVANCE SIMULATION LOGIC
# -----------------------------
should_advance_flag = False
if auto_refresh and st.session_state.get("sim_autoplay", False) and current_idx < total_steps:
    should_advance_flag = run_auto_advance(
        active_pumps, step_hours, current_idx,
        st.session_state["raw_df"], total_steps
    )

# Get latest timestamp and data from simulation log
sim_log = st.session_state.get("sim_log_df")
latest_timestamp = None
pump_status = "Healthy"
pump_rul = 0
pump_risk = 0

if sim_log is not None and not sim_log.empty:
    pump_logs = sim_log[sim_log["machine_id"] == selected_pump]
    if not pump_logs.empty:
        latest = pump_logs.iloc[-1]
        latest_timestamp = latest.get("timestamp")
        pump_status = latest.get("health_label", "Healthy")
        pump_rul = latest.get("rul_days", 0)
        pump_risk = int(latest.get("risk_score", 0))

# Display selected pump info with timestamp
if latest_timestamp:
    timestamp_str = latest_timestamp.strftime("%Y-%m-%d %H:%M:%S") if isinstance(latest_timestamp, pd.Timestamp) else str(latest_timestamp)
    st.markdown(f'### Monitoring: **{selected_pump}** <span class="timestamp-badge">🕒 {timestamp_str}</span>', unsafe_allow_html=True)
else:
    st.markdown(f"### Monitoring: **{selected_pump}**")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Status", pump_status)
with col2:
    rul_display = "N/A" if (pump_rul == 0 or pump_rul is None or pd.isna(pump_rul)) else f"{pump_rul:.1f} days"
    st.metric("RUL", rul_display)
with col3:
    risk_display = "N/A" if pump_risk == 0 else str(pump_risk)
    st.metric("Risk Score", risk_display)

st.markdown("---")

# === STATUS LEGEND ===
st.markdown("### Status Legend")
legend_cols = st.columns(5)
with legend_cols[0]:
    st.markdown("🔵 **Too Low** - Sensor reading error")
with legend_cols[1]:
    st.markdown("🟢 **Healthy** - Normal operation")
with legend_cols[2]:
    st.markdown("🟡 **Degrading** - Requires monitoring")
with legend_cols[3]:
    st.markdown("🟠 **Critical** - Maintenance needed")
with legend_cols[4]:
    st.markdown("🔴 **Failed** - Immediate action required")

st.markdown("---")

# === Get latest sensor data for selected pump at CURRENT SIMULATION STEP ===
current_sim_idx = st.session_state.get("sim_current_idx", 0)
step_hours = st.session_state.get("sim_step_hours", 72)

current_row_idx = current_sim_idx * step_hours

pump_data = raw_df[raw_df["machine_id"] == selected_pump]

if current_row_idx < len(pump_data):
    pump_sensor_data = pump_data.iloc[[current_row_idx]]
else:
    pump_sensor_data = pump_data.tail(1)

if pump_sensor_data.empty:
    st.warning(f"No sensor data found for pump {selected_pump}. Using sample values.")
    sensor_values = [1.5, 1.2, 0.2, 55, 50, 4.5, 22, 62]
else:
    sensor_values = [
        pump_sensor_data["radial_vibration_rms"].iloc[0] if "radial_vibration_rms" in pump_sensor_data.columns else 1.5,
        pump_sensor_data["axial_vibration_rms"].iloc[0] if "axial_vibration_rms" in pump_sensor_data.columns else 1.2,
        pump_sensor_data["high_freq_vibration"].iloc[0] if "high_freq_vibration" in pump_sensor_data.columns else 0.2,
        pump_sensor_data["bearing_temperature"].iloc[0] if "bearing_temperature" in pump_sensor_data.columns else 55,
        pump_sensor_data["casing_temperature"].iloc[0] if "casing_temperature" in pump_sensor_data.columns else 50,
        pump_sensor_data["discharge_pressure"].iloc[0] if "discharge_pressure" in pump_sensor_data.columns else 4.5,
        pump_sensor_data["power_consumption"].iloc[0] if "power_consumption" in pump_sensor_data.columns else 22,
        pump_sensor_data["acoustic_emission"].iloc[0] if "acoustic_emission" in pump_sensor_data.columns else 62
    ]

# Sensor definitions with ranges AND column names for navigation
sensor_definitions = [
    {
        "name": "Radial Vibration", 
        "column_name": "radial_vibration_rms",
        "unit": "mm/s", 
        "value": sensor_values[0], 
        "healthy_start": 0.3,
        "max": 11.0,
        "too_low": [0.3, 0.5],
        "healthy": [0.5, 2.5], 
        "degrading": [2.2, 4.0], 
        "critical": [2.8, 10.0], 
        "failed": [4.0, 11.0]
    },
    {
        "name": "Axial Vibration", 
        "column_name": "axial_vibration_rms",
        "unit": "mm/s", 
        "value": sensor_values[1], 
        "healthy_start": 0.2,
        "max": 11.0,
        "too_low": [0.2, 0.3],
        "healthy": [0.3, 2.0], 
        "degrading": [1.8, 3.5], 
        "critical": [2.4, 10.0], 
        "failed": [3.5, 11.0]
    },
    {
        "name": "High Freq Vibration", 
        "column_name": "high_freq_vibration",
        "unit": "g", 
        "value": sensor_values[2], 
        "healthy_start": 0.0,
        "max": 2.2,
        "too_low": [0.0, 0.05],
        "healthy": [0.05, 0.30], 
        "degrading": [0.27, 0.60], 
        "critical": [0.40, 2.0], 
        "failed": [0.60, 2.2]
    },
    {
        "name": "Bearing Temp", 
        "column_name": "bearing_temperature",
        "unit": "°C", 
        "value": sensor_values[3], 
        "healthy_start": 35,
        "max": 115,
        "too_low": [35, 40],
        "healthy": [40, 70], 
        "degrading": [65, 95], 
        "critical": [80, 110], 
        "failed": [95, 115]
    },
    {
        "name": "Casing Temp", 
        "column_name": "casing_temperature",
        "unit": "°C", 
        "value": sensor_values[4], 
        "healthy_start": 30,
        "max": 115,
        "too_low": [30, 35],
        "healthy": [35, 65], 
        "degrading": [60, 90], 
        "critical": [75, 110], 
        "failed": [90, 115]
    },
    {
        "name": "Discharge Pressure", 
        "column_name": "discharge_pressure",
        "unit": "bar", 
        "value": sensor_values[5], 
        "healthy_start": 2.5,
        "max": 12.5,
        "too_low": [2.5, 3.0],
        "healthy": [3.0, 6.0], 
        "degrading": [5.5, 8.0], 
        "critical": [6.8, 12.0], 
        "failed": [8.0, 12.5]
    },
    {
        "name": "Power Consumption", 
        "column_name": "power_consumption",
        "unit": "kW", 
        "value": sensor_values[6], 
        "healthy_start": 14,
        "max": 65,
        "too_low": [14, 15],
        "healthy": [15, 30], 
        "degrading": [28, 45], 
        "critical": [35, 60], 
        "failed": [45, 65]
    },
    {
        "name": "Acoustics", 
        "column_name": "acoustic_emission",
        "unit": "dB", 
        "value": sensor_values[7], 
        "healthy_start": 45,
        "max": 105,
        "too_low": [45, 50],
        "healthy": [50, 70], 
        "degrading": [68, 90], 
        "critical": [78, 100], 
        "failed": [90, 105]
    }
]

# Professional gauge creation function — NOT cached so it updates with live simulation data
def create_gauge(name, unit, value, healthy_start, max_val, too_low, healthy, degrading, critical, failed):
    """Create a gauge figure with live sensor values (no caching)."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        domain={'x': [0, 1], 'y': [0, 1]},
        number={
            'font': {'size': 28, 'color': 'white', 'family': 'Inter, sans-serif', 'weight': 700},
            'suffix': f" {unit}",
            'valueformat': '.2f'
        },
        gauge={
            'axis': {
                'range': [healthy_start, max_val],
                'tickwidth': 1,
                'tickcolor': "#94a3b8",
                'tickfont': {'size': 10, 'color': '#e2e8f0', 'family': 'Inter'},
                'tickmode': 'auto',
                'nticks': 5,
                'showticklabels': True
            },
            'bar': {
                'color': "#3b82f6",
                'thickness': 0.22,
                'line': {'width': 0}
            },
            'bgcolor': "#334155",
            'borderwidth': 2,
            'bordercolor': "#475569",
            'steps': [
                {'range': too_low, 'color': '#dbeafe', 'line': {'width': 0}},
                {'range': healthy, 'color': '#d1fae5', 'line': {'width': 0}},
                {'range': degrading, 'color': '#fef3c7', 'line': {'width': 0}},
                {'range': critical, 'color': '#fed7aa', 'line': {'width': 0}},
                {'range': failed, 'color': '#fecaca', 'line': {'width': 0}}
            ]
        }
    ))

    fig.add_annotation(
        text=f"<b>{name}</b>",
        xref="paper", yref="paper",
        x=0.5, y=1.15,
        showarrow=False,
        font=dict(size=15, color='#e2e8f0', family='Inter, sans-serif', weight=600),
        xanchor='center'
    )

    fig.update_layout(
        height=280,
        margin=dict(l=20, r=20, t=60, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        font={'family': 'Inter, Arial, sans-serif'}
    )
    return fig

# Display 8 gauges in 2 rows of 4 WITH NAVIGATION BUTTONS
st.markdown("### Real-time Sensor Gauges")
st.markdown("*Click 'View Trend' to analyze historical data for each sensor*")

gauge_figs = [
    create_gauge(
        sensor["name"], sensor["unit"], sensor["value"],
        sensor["healthy_start"], sensor["max"],
        tuple(sensor["too_low"]), tuple(sensor["healthy"]),
        tuple(sensor["degrading"]), tuple(sensor["critical"]),
        tuple(sensor["failed"])
    )
    for sensor in sensor_definitions
]

# Row 1
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.plotly_chart(gauge_figs[0], use_container_width=True, key="gauge_0")
    if st.button("📈 View Trend", key="btn_radial", use_container_width=True):
        st.session_state["sensor_trend_selected"] = sensor_definitions[0]["column_name"]
        st.session_state["sensor_trend_pump"] = selected_pump
        st.switch_page("pages/4_Sensor_Trend.py")

with col2:
    st.plotly_chart(gauge_figs[1], use_container_width=True, key="gauge_1")
    if st.button("📈 View Trend", key="btn_axial", use_container_width=True):
        st.session_state["sensor_trend_selected"] = sensor_definitions[1]["column_name"]
        st.session_state["sensor_trend_pump"] = selected_pump
        st.switch_page("pages/4_Sensor_Trend.py")

with col3:
    st.plotly_chart(gauge_figs[2], use_container_width=True, key="gauge_2")
    if st.button("📈 View Trend", key="btn_highfreq", use_container_width=True):
        st.session_state["sensor_trend_selected"] = sensor_definitions[2]["column_name"]
        st.session_state["sensor_trend_pump"] = selected_pump
        st.switch_page("pages/4_Sensor_Trend.py")

with col4:
    st.plotly_chart(gauge_figs[3], use_container_width=True, key="gauge_3")
    if st.button("📈 View Trend", key="btn_bearing", use_container_width=True):
        st.session_state["sensor_trend_selected"] = sensor_definitions[3]["column_name"]
        st.session_state["sensor_trend_pump"] = selected_pump
        st.switch_page("pages/4_Sensor_Trend.py")

# Row 2
col5, col6, col7, col8 = st.columns(4)

with col5:
    st.plotly_chart(gauge_figs[4], use_container_width=True, key="gauge_4")
    if st.button("📈 View Trend", key="btn_casing", use_container_width=True):
        st.session_state["sensor_trend_selected"] = sensor_definitions[4]["column_name"]
        st.session_state["sensor_trend_pump"] = selected_pump
        st.switch_page("pages/4_Sensor_Trend.py")

with col6:
    st.plotly_chart(gauge_figs[5], use_container_width=True, key="gauge_5")
    if st.button("📈 View Trend", key="btn_pressure", use_container_width=True):
        st.session_state["sensor_trend_selected"] = sensor_definitions[5]["column_name"]
        st.session_state["sensor_trend_pump"] = selected_pump
        st.switch_page("pages/4_Sensor_Trend.py")

with col7:
    st.plotly_chart(gauge_figs[6], use_container_width=True, key="gauge_6")
    if st.button("📈 View Trend", key="btn_power", use_container_width=True):
        st.session_state["sensor_trend_selected"] = sensor_definitions[6]["column_name"]
        st.session_state["sensor_trend_pump"] = selected_pump
        st.switch_page("pages/4_Sensor_Trend.py")

with col8:
    st.plotly_chart(gauge_figs[7], use_container_width=True, key="gauge_7")
    if st.button("📈 View Trend", key="btn_acoustics", use_container_width=True):
        st.session_state["sensor_trend_selected"] = sensor_definitions[7]["column_name"]
        st.session_state["sensor_trend_pump"] = selected_pump
        st.switch_page("pages/4_Sensor_Trend.py")

# Current Sensor Readings
st.markdown("---")
st.markdown("### Current Sensor Readings")

sensor_df = pd.DataFrame({
    'Sensor': [s['name'] for s in sensor_definitions],
    'Value': [f"{s['value']:.2f} {s['unit']}" for s in sensor_definitions],
    'Status': [
        "Too Low" if s["value"] < s["too_low"][1]
        else "Healthy" if s["value"] <= s["healthy"][1] 
        else "Degrading" if s["value"] <= s["degrading"][1]
        else "Critical" if s["value"] <= s["critical"][1]
        else "Failed" 
        for s in sensor_definitions
    ]
})

st.dataframe(sensor_df, use_container_width=True)

# Download button
csv = sensor_df.to_csv(index=False)
st.download_button(
    label="📥 Download Current Readings",
    data=csv,
    file_name=f"{selected_pump}_readings.csv",
    mime="text/csv"
)

# === TABLES AT BOTTOM ===
st.markdown("---")
st.markdown("### Sensor Operating Ranges by Health State")
ranges_df = pd.DataFrame({
    "Sensor": [
        "Radial Vibration RMS", "Axial Vibration RMS", "High Frequency Vibration",
        "Bearing Temperature", "Casing Temperature", "Discharge Pressure",
        "Power Consumption", "Acoustic Emission"
    ],
    "Unit": ["mm/s", "mm/s", "g", "°C", "°C", "bar", "kW", "dB"],
    "Too Low": ["<0.5", "<0.3", "<0.05", "<40", "<35", "<3.0", "<15", "<50"],
    "Healthy": ["0.5-2.5", "0.3-2.0", "0.05-0.30", "40-70", "35-65", "3.0-6.0", "15-30", "50-70"],
    "Degrading": ["2.2-4.0", "1.8-3.5", "0.27-0.60", "65-95", "60-90", "5.5-8.0", "28-45", "68-90"],
    "Critical": ["2.8-10", "2.4-10", "0.40-2.0", "80-110", "75-110", "6.8-12", "35-60", "78-100"],
    "Failed": ["4.0+", "3.5+", "0.60+", "95+", "90+", "8.0+", "45+", "90+"]
})
st.dataframe(ranges_df, use_container_width=True)

st.markdown("### Multi-sensor Configuration for Pump Health Monitoring")
config_df = pd.DataFrame({
    "Sensor Category": ["Vibration", "Vibration", "Vibration", "Temperature", 
                       "Temperature", "Pressure", "Power", "Acoustic"],
    "Sensor Name": ["Radial Vibration RMS", "Axial Vibration RMS", "High Frequency Vibration",
                   "Bearing Temperature", "Casing Temperature", "Discharge Pressure",
                   "Power Consumption", "Acoustic Emission"],
    "Unit": ["mm/s", "mm/s", "g", "°C", "°C", "bar", "kW", "dB"],
    "Description": [
        "Captures bearing wear and imbalance",
        "Indicates shaft misalignment",
        "Early indicator of bearing faults",
        "Reflects friction and thermal stress",
        "Represents heat dissipation behavior",
        "Captures hydraulic instability and cavitation",
        "Indicates mechanical resistance and inefficiency",
        "Captures high-frequency fault-related noise"
    ]
})
st.dataframe(config_df, use_container_width=True)

# -----------------------------
# AUTO-REFRESH LOGIC (AT THE END!) - Using navigation helper
# -----------------------------
if should_auto_refresh():
    # Always rerun while simulation is playing (gauges must reflect latest step)
    time.sleep(1.0)
    st.rerun()

