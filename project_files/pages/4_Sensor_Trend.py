import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import time
from utils.themes import apply_theme
from utils.navigation import render_horizontal_navigation, should_auto_refresh
from utils.cache_helpers import run_auto_advance, get_total_steps

st.set_page_config(
    page_title="Sensor Trend", 
    page_icon="📈", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Apply centralized theme
apply_theme()
render_horizontal_navigation()

# Set current page
st.session_state["current_page"] = "Sensor Trend"

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
</style>
""", unsafe_allow_html=True)

# ========================================
# PAGE CONTENT STARTS HERE
# ========================================

st.title("📈 Sensor Trend Analysis")

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

# Get data safely
raw_df = st.session_state["raw_df"]

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

# Available sensor columns
sensor_columns = {
    "radial_vibration_rms": {"name": "Radial Vibration", "unit": "mm/s", "healthy": [0, 2.5], "degrading": [2.5, 4.5], "critical": [4.5, 7.0], "failed": [7.0, 10]},
    "axial_vibration_rms": {"name": "Axial Vibration", "unit": "mm/s", "healthy": [0.5, 2.5], "degrading": [2.5, 4.5], "critical": [4.5, 7.0], "failed": [7.0, 10]},
    "high_freq_vibration": {"name": "High Freq Vibration", "unit": "g", "healthy": [0, 4.5], "degrading": [4.5, 6.5], "critical": [6.5, 10], "failed": [10, 20]},
    "bearing_temperature": {"name": "Bearing Temperature", "unit": "°C", "healthy": [20, 40], "degrading": [40, 60], "critical": [60, 75], "failed": [75, 95]},
    "casing_temperature": {"name": "Casing Temperature", "unit": "°C", "healthy": [0, 50], "degrading": [50, 60], "critical": [60, 70], "failed": [70, 90]},
    "discharge_pressure": {"name": "Discharge Pressure", "unit": "bar", "healthy": [3.5, 5.0], "degrading": [5.0, 5.5], "critical": [5.5, 6.0], "failed": [6.0, 10]},
    "power_consumption": {"name": "Power Consumption", "unit": "kW", "healthy": [5, 18], "degrading": [18, 25], "critical": [25, 30], "failed": [30, 35]},
    "acoustic_emission": {"name": "Acoustics", "unit": "dB", "healthy": [58, 65], "degrading": [65, 75], "critical": [75, 85], "failed": [85, 95]}
}

# Filter available sensors
available_sensors = {col: info for col, info in sensor_columns.items() if col in raw_df.columns}

if not available_sensors:
    st.warning("No sensor columns found in data.")
    st.stop()

# -----------------------------
# AUTO-ADVANCE SIMULATION LOGIC
# -----------------------------
step_hours = st.session_state.get("sim_step_hours", 72)
current_idx = st.session_state.get("sim_current_idx", 0)
total_steps = get_total_steps(active_pumps, raw_df, step_hours)

# Auto-refresh toggle (moved to sidebar for status display)
auto_refresh = st.session_state.get("trend_auto_refresh", True)

# Auto-advance logic
should_advance_flag = False
if auto_refresh and st.session_state.get("sim_autoplay", False) and current_idx < total_steps:
    should_advance_flag = run_auto_advance(
        active_pumps, step_hours, current_idx, raw_df, total_steps
    )

# Get latest timestamp from simulation log
sim_log = st.session_state.get("sim_log_df")
latest_timestamp = None

if sim_log is not None and not sim_log.empty:
    latest_timestamp = sim_log["timestamp"].max()

# === PREPARE DEFAULTS FOR PUMP AND SENSOR SELECTION ===
pump_ids = sorted(active_pumps)
sensor_display_options = {col: f"{info['name']} ({info['unit']})" for col, info in available_sensors.items()}

# Check if navigated from Detailed View
if "sensor_trend_pump" in st.session_state and st.session_state["sensor_trend_pump"]:
    default_pump = st.session_state["sensor_trend_pump"]
    st.session_state["sensor_trend_pump"] = None  # Clear after using
else:
    if "trend_selected_pump" not in st.session_state:
        st.session_state["trend_selected_pump"] = pump_ids[0] if pump_ids else None
    default_pump = st.session_state["trend_selected_pump"]

# Ensure default pump is valid
if default_pump not in pump_ids and pump_ids:
    default_pump = pump_ids[0]

# Check if sensor was pre-selected from Detailed View
if "sensor_trend_selected" in st.session_state and st.session_state["sensor_trend_selected"]:
    preselected_sensor = st.session_state["sensor_trend_selected"]
    st.session_state["sensor_trend_selected"] = None  # Clear after using
    
    sensor_list = list(available_sensors.keys())
    try:
        default_sensor_index = sensor_list.index(preselected_sensor)
    except ValueError:
        default_sensor_index = 0
else:
    default_sensor_index = 0

# Get current simulation index
current_sim_idx = st.session_state.get("sim_current_idx", 0)

# === INITIAL DATA LOAD (for title display) ===
selected_pump = default_pump
selected_sensor_col = list(available_sensors.keys())[default_sensor_index]
sensor_info = available_sensors[selected_sensor_col]

# === TITLE WITH TIMESTAMP ===
if latest_timestamp:
    timestamp_str = latest_timestamp.strftime("%Y-%m-%d %H:%M:%S") if isinstance(latest_timestamp, pd.Timestamp) else str(latest_timestamp)
    st.markdown(f'### Monitoring: **{selected_pump}** - **{sensor_info["name"]}** <span class="timestamp-badge">🕒 {timestamp_str}</span>', unsafe_allow_html=True)
else:
    st.markdown(f"### Monitoring: **{selected_pump}** - **{sensor_info['name']}**")

# Filter initial data
pump_sensor_data = raw_df[raw_df["machine_id"] == selected_pump].copy()

# ONLY SHOW DATA UP TO CURRENT SIMULATION STEP
max_row_idx = current_sim_idx * step_hours
if max_row_idx > 0:
    pump_sensor_data = pump_sensor_data.iloc[:max_row_idx].copy()

if not pump_sensor_data.empty and selected_sensor_col in pump_sensor_data.columns:
    pump_sensor_data = pump_sensor_data[["timestamp", selected_sensor_col]].copy()
    pump_sensor_data["timestamp"] = pd.to_datetime(pump_sensor_data["timestamp"])
    pump_sensor_data = pump_sensor_data.sort_values("timestamp")

    st.markdown("---")

    # === STATS ===
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Data Points", f"{len(pump_sensor_data):,}")
    with col2:
        time_span = pump_sensor_data['timestamp'].max() - pump_sensor_data['timestamp'].min()
        st.metric("Time Span", f"{time_span.days} days")
    with col3:
        st.metric("Latest Value", f"{pump_sensor_data[selected_sensor_col].iloc[-1]:.2f} {sensor_info['unit']}")
    with col4:
        st.metric("Average", f"{pump_sensor_data[selected_sensor_col].mean():.2f} {sensor_info['unit']}")

st.markdown("---")

# === MAIN TIME SERIES CHART ===
st.markdown("### Historical Trend")

# === PUMP AND SENSOR SELECTION DROPDOWNS (IN MAIN CONTENT) ===
col_pump, col_sensor = st.columns(2)

with col_pump:
    selected_pump = st.selectbox(
        "Select Pump",
        options=pump_ids,
        index=pump_ids.index(default_pump) if default_pump in pump_ids else 0,
        key="trend_pump_select_main"
    )
    st.session_state["trend_selected_pump"] = selected_pump

with col_sensor:
    selected_sensor_col = st.selectbox(
        "Select Sensor",
        options=list(available_sensors.keys()),
        format_func=lambda col: sensor_display_options[col],
        index=default_sensor_index,
        key="trend_sensor_select_main"
    )

sensor_info = available_sensors[selected_sensor_col]
sensor_display_name = f"{sensor_info['name']} ({sensor_info['unit']})"

# Recalculate data for the selected pump/sensor
pump_sensor_data = raw_df[raw_df["machine_id"] == selected_pump].copy()

if selected_sensor_col not in pump_sensor_data.columns:
    st.error(f"No data found for {sensor_display_name} on pump {selected_pump}")
    st.stop()

# ONLY SHOW DATA UP TO CURRENT SIMULATION STEP
max_row_idx = current_sim_idx * step_hours
if max_row_idx > 0:
    pump_sensor_data = pump_sensor_data.iloc[:max_row_idx].copy()

if pump_sensor_data.empty:
    st.info("No data points processed yet. Waiting for simulation to advance...")
    st.stop()

pump_sensor_data = pump_sensor_data[["timestamp", selected_sensor_col]].copy()
pump_sensor_data["timestamp"] = pd.to_datetime(pump_sensor_data["timestamp"])
pump_sensor_data = pump_sensor_data.sort_values("timestamp")

st.markdown("---")

fig_trend = go.Figure()

# Add main line
fig_trend.add_trace(go.Scatter(
    x=pump_sensor_data["timestamp"],
    y=pump_sensor_data[selected_sensor_col],
    mode='lines+markers',
    name=sensor_display_name,
    line=dict(color='#1f77b4', width=2),
    marker=dict(size=4)
))

# Add threshold lines
fig_trend.add_hline(
    y=sensor_info["healthy"][1], 
    line_dash="dash", 
    line_color="green", 
    annotation_text="Healthy Limit", 
    annotation_position="right"
)
fig_trend.add_hline(
    y=sensor_info["degrading"][1], 
    line_dash="dash", 
    line_color="orange", 
    annotation_text="Degrading Limit", 
    annotation_position="right"
)
fig_trend.add_hline(
    y=sensor_info["critical"][1], 
    line_dash="dash", 
    line_color="red", 
    annotation_text="Critical Limit", 
    annotation_position="right"
)

# Add shaded regions
fig_trend.add_hrect(
    y0=sensor_info["healthy"][0], y1=sensor_info["healthy"][1],
    fillcolor="green", opacity=0.1, line_width=0
)
fig_trend.add_hrect(
    y0=sensor_info["degrading"][0], y1=sensor_info["degrading"][1],
    fillcolor="orange", opacity=0.1, line_width=0
)
fig_trend.add_hrect(
    y0=sensor_info["critical"][0], y1=sensor_info["critical"][1],
    fillcolor="red", opacity=0.1, line_width=0
)
fig_trend.add_hrect(
    y0=sensor_info["failed"][0], y1=sensor_info["failed"][1],
    fillcolor="darkred", opacity=0.1, line_width=0
)

fig_trend.update_layout(
    title=f"{sensor_display_name} - Historical Trend for {selected_pump}",
    xaxis_title="Timestamp",
    yaxis_title=sensor_display_name,
    height=500,
    hovermode='x unified',
    showlegend=True
)

st.plotly_chart(fig_trend, use_container_width=True)

# === ROLLING STATISTICS ===
st.markdown("### Rolling Statistics (7-point window)")

pump_sensor_data['rolling_mean'] = pump_sensor_data[selected_sensor_col].rolling(window=7, min_periods=1).mean()
pump_sensor_data['rolling_std'] = pump_sensor_data[selected_sensor_col].rolling(window=7, min_periods=1).std()

fig_stats = go.Figure()

fig_stats.add_trace(go.Scatter(
    x=pump_sensor_data['timestamp'],
    y=pump_sensor_data[selected_sensor_col],
    mode='lines',
    name='Raw Data',
    line=dict(color='lightblue', width=1),
    opacity=0.5
))

fig_stats.add_trace(go.Scatter(
    x=pump_sensor_data['timestamp'],
    y=pump_sensor_data['rolling_mean'],
    mode='lines',
    name='7-pt Rolling Mean',
    line=dict(color='orange', width=3)
))

fig_stats.add_trace(go.Scatter(
    x=pump_sensor_data['timestamp'],
    y=pump_sensor_data['rolling_mean'] + pump_sensor_data['rolling_std'],
    mode='lines',
    line=dict(color='rgba(255,0,0,0.2)', width=0),
    showlegend=False,
    name='Upper Bound'
))

fig_stats.add_trace(go.Scatter(
    x=pump_sensor_data['timestamp'],
    y=pump_sensor_data['rolling_mean'] - pump_sensor_data['rolling_std'],
    mode='lines',
    fill='tonexty',
    line=dict(color='rgba(255,0,0,0.2)', width=0),
    fillcolor='rgba(255,0,0,0.1)',
    name='±1 Std Dev'
))

fig_stats.update_layout(
    title=f"{sensor_display_name} - Rolling Statistics",
    xaxis_title="Timestamp",
    yaxis_title=sensor_display_name,
    height=400,
    hovermode='x unified'
)

st.plotly_chart(fig_stats, use_container_width=True)

# === DATA TABLE ===
st.markdown("### Recent Data (Last 50 readings)")
display_df = pump_sensor_data[["timestamp", selected_sensor_col]].tail(50).copy()
display_df.columns = ["Timestamp", sensor_display_name]
st.dataframe(display_df, use_container_width=True, hide_index=True)

# === DOWNLOAD BUTTON ===
csv = pump_sensor_data[["timestamp", selected_sensor_col]].to_csv(index=False)
st.download_button(
    label=f"📥 Download {sensor_info['name']} Data for {selected_pump}",
    data=csv,
    file_name=f"{selected_pump}_{selected_sensor_col}_trend.csv",
    mime="text/csv"
)

# -----------------------------
# AUTO-REFRESH LOGIC (AT THE END!)
# -----------------------------
if should_auto_refresh():
    if should_advance_flag or not auto_refresh:
        time.sleep(1.0 if auto_refresh else 1.5)
        st.rerun()
