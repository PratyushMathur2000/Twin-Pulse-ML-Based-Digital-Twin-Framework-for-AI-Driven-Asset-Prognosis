import streamlit as st
import pandas as pd
import time
import sys
from pathlib import Path
from datetime import datetime

# ===== IMPORTS FOR NAVIGATION =====
from utils.themes import apply_theme
from utils.navigation import render_horizontal_navigation, should_auto_refresh
from utils.cache_helpers import run_auto_advance, get_total_steps

# ===== PAGE CONFIG (MUST BE FIRST!) =====
st.set_page_config(
    page_title="Fleet Overview",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ===== APPLY THEME & NAVIGATION =====
apply_theme()
render_horizontal_navigation()

# Set current page
st.session_state["current_page"] = "Fleet Overview"


# ========================================
# FLEET-SPECIFIC CARD STYLING
# ========================================
st.markdown("""
<style>
    /* ===== FLEET-SPECIFIC CARD STYLING ===== */
    .pump-card {
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        text-align: center;
        height: 240px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    
    /* HOVER EFFECT - Float with enhanced shadow */
    .pump-card:hover {
        transform: translateY(-8px);
        box-shadow: 0 12px 24px rgba(0, 0, 0, 0.2);
    }
    
    .pump-card.healthy {
        background-color: #28a745;
        border: 3px solid #1e7e34;
    }
    .pump-card.degrading {
        background-color: #ffc107;
        border: 3px solid #d39e00;
    }
    .pump-card.critical {
        background-color: #fd7e14;
        border: 3px solid #dc6502;
    }
    .pump-card.failed {
        background-color: #dc3545;
        border: 3px solid #bd2130;
    }
    .pump-title {
        font-size: 24px;
        font-weight: bold;
        color: white;
        margin-bottom: 10px;
    }
    .pump-status {
        font-size: 18px;
        font-weight: 600;
        color: white;
        text-transform: uppercase;
        margin-bottom: 15px;
    }
    .pump-metric {
        font-size: 13px;
        color: white;
        margin: 5px 0;
    }
    .metric-label {
        font-weight: bold;
        font-size: 12px;
    }
    .metric-value {
        font-size: 18px;
        font-weight: 600;
    }
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
    .live-indicator {
        display: inline-block;
        width: 10px;
        height: 10px;
        background-color: #4ade80;
        border-radius: 50%;
        margin-right: 8px;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
</style>
""", unsafe_allow_html=True)

# ========================================
# PAGE CONTENT STARTS HERE
# ========================================

st.title("🚀 Fleet Overview Dashboard")  # ← Only ONE title

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

# -----------------------------
# SIDEBAR - SIMULATION CONTROL BOX
# -----------------------------
st.sidebar.markdown("### 🎮 Simulation Control")

# Get simulation parameters
step_hours = st.session_state.get("sim_step_hours", 72)
current_idx = st.session_state.get("sim_current_idx", 0)
total_steps = get_total_steps(active_pumps, st.session_state["raw_df"], step_hours)

# Add auto-refresh toggle
auto_advance = st.sidebar.checkbox(
    "Auto-refresh display", 
    value=True,
    help="Automatically refresh when simulation advances",
    key="fleet_auto_refresh"
)

# Display simulation status in info box
sim_status = "🟢 Running" if st.session_state.get("sim_autoplay", False) else "⏸️ Paused"
st.sidebar.info(f"""
**Simulation Status:** {sim_status}

**Current Step:** {current_idx}/{total_steps}
""")

st.sidebar.markdown("---")

# -----------------------------
# AUTO-ADVANCE SIMULATION LOGIC
# -----------------------------
should_advance_flag = False
if auto_advance and st.session_state.get("sim_autoplay", False) and current_idx < total_steps:
    should_advance_flag = run_auto_advance(
        active_pumps, step_hours, current_idx,
        st.session_state["raw_df"], total_steps
    )

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
# UPDATE FLEET DATA FROM SIMULATION
# -----------------------------
def update_fleet_from_simulation():
    """Extract latest status from simulation log."""
    sim_log = st.session_state.get("sim_log_df")
    
    fleet_rows = []
    
    for pump_id in active_pumps:
        if sim_log is not None and not sim_log.empty:
            pump_logs = sim_log[sim_log["machine_id"] == pump_id]
            
            if not pump_logs.empty:
                latest = pump_logs.iloc[-1]
                
                health_map = {
                    "Healthy": "Healthy",
                    "Degrading": "Degrading",
                    "Critical": "Critical",
                    "Failure": "Failed"
                }
                
                status = health_map.get(latest.get("health_label", "Healthy"), "Healthy")
                
                rul_days = latest.get("rul_days", None)
                if pd.isna(rul_days) or rul_days is None:
                    rul_display = 0
                else:
                    rul_display = round(rul_days, 1)
                
                risk_score = int(latest.get("risk_score", 0))
                
                fleet_rows.append({
                    "machine_id": pump_id,
                    "Status": status,
                    "RUL_days": rul_display,
                    "Risk_Score": risk_score,
                })
            else:
                fleet_rows.append({
                    "machine_id": pump_id,
                    "Status": "Healthy",
                    "RUL_days": 0,
                    "Risk_Score": 0,
                })
        else:
            fleet_rows.append({
                "machine_id": pump_id,
                "Status": "Healthy",
                "RUL_days": 0,
                "Risk_Score": 0,
            })
    
    return pd.DataFrame(fleet_rows)

# Update fleet data
fleet_df_raw = update_fleet_from_simulation()
fleet_df_raw.rename(columns={"machine_id": "Pump_ID"}, inplace=True)

# Sidebar controls
st.sidebar.header("Fleet Configuration")

if "fleet_selected_pumps" not in st.session_state:
    st.session_state["fleet_selected_pumps"] = active_pumps

valid_selected = [p for p in st.session_state["fleet_selected_pumps"] if p in active_pumps]
if not valid_selected:
    valid_selected = active_pumps

selected_pumps = st.sidebar.multiselect(
    "Select pumps to display",
    options=active_pumps,
    default=valid_selected,
    key="fleet_pump_multiselect",
)

st.session_state["fleet_selected_pumps"] = selected_pumps

if not selected_pumps:
    st.sidebar.warning("Select at least one pump.")
    st.stop()

fleet_df = fleet_df_raw[fleet_df_raw["Pump_ID"].isin(selected_pumps)].reset_index(drop=True)

cols_per_row = st.sidebar.selectbox("Cards per row", [3, 4, 5], index=0, key="fleet_cards_per_row")

# Summary metrics
st.markdown("### Fleet Summary")
col_sum1, col_sum2, col_sum3, col_sum4 = st.columns(4)

with col_sum1:
    healthy_count = len(fleet_df[fleet_df['Status'] == 'Healthy'])
    st.metric("🟢 Healthy", healthy_count)

with col_sum2:
    degrading_count = len(fleet_df[fleet_df['Status'] == 'Degrading'])
    st.metric("🟡 Degrading", degrading_count)

with col_sum3:
    critical_count = len(fleet_df[fleet_df['Status'] == 'Critical'])
    st.metric("🟠 Critical", critical_count)

with col_sum4:
    failed_count = len(fleet_df[fleet_df['Status'] == 'Failed'])
    st.metric("🔴 Failed", failed_count)

st.markdown("---")

# Get latest timestamp from simulation
latest_timestamp = None
sim_log = st.session_state.get("sim_log_df")
if sim_log is not None and not sim_log.empty:
    latest_timestamp = sim_log["timestamp"].max()

# Create pump card HTML
def create_pump_card(pump_id, status, rul, risk_score):
    status_lower = status.lower()
    
    # Fix RUL display based on status
    if status == "Failed":
        rul_display = "N/A"
    elif rul == 0:
        rul_display = "Long term"
    else:
        rul_display = f"{rul} days"
    
    card_html = f"""
    <div class="pump-card {status_lower}">
        <div class="pump-title">{pump_id}</div>
        <div class="pump-status">{status}</div>
        <div>
            <div class="pump-metric">
                <span class="metric-label">Remaining Useful Life:</span><br>
                <span class="metric-value">{rul_display}</span>
            </div>
            <div class="pump-metric" style="margin-top: 10px;">
                <span class="metric-label">Risk Score:</span><br>
                <span class="metric-value">{risk_score}</span>
            </div>
        </div>
    </div>
    """
    return card_html


# Display pump cards in grid with timestamp and NAVIGATION
if latest_timestamp:
    timestamp_str = latest_timestamp.strftime("%Y-%m-%d %H:%M:%S") if isinstance(latest_timestamp, pd.Timestamp) else str(latest_timestamp)
    st.markdown(f'### Individual Pump Status <span class="timestamp-badge">🕒 {timestamp_str}</span>', unsafe_allow_html=True)
else:
    st.markdown("### Individual Pump Status")

num_pumps = len(fleet_df)

for row_start in range(0, num_pumps, cols_per_row):
    cols = st.columns(cols_per_row)
    
    for idx, col in enumerate(cols):
        pump_idx = row_start + idx
        
        if pump_idx < num_pumps:
            pump = fleet_df.iloc[pump_idx]
            pump_id = pump['Pump_ID']
            
            with col:
                # Display the card with hover effect
                st.markdown(
                    create_pump_card(
                        pump_id,
                        pump['Status'],
                        pump['RUL_days'],
                        pump['Risk_Score']
                    ),
                    unsafe_allow_html=True
                )
                
                # Add "View Details" button below each card
                if st.button(f"🔍 View Details", key=f"view_{pump_id}", use_container_width=True):
                    # Store selected pump in session state
                    st.session_state["detailed_selected_pump"] = pump_id
                    # Navigate to Detailed View
                    st.switch_page("pages/2_Detailed_View.py")

# Fleet data table
st.markdown("---")
st.markdown("### Detailed Fleet Data")

def color_status(val):
    color_map = {
        'Healthy': 'background-color: #28a745; color: white',
        'Degrading': 'background-color: #ffc107; color: black',
        'Critical': 'background-color: #fd7e14; color: white',
        'Failed': 'background-color: #dc3545; color: white'
    }
    return color_map.get(val, '')

styled_df = fleet_df.style.map(color_status, subset=['Status'])
st.dataframe(styled_df, use_container_width=True)

# Download button
csv = fleet_df.to_csv(index=False)
st.download_button(
    label="📥 Download Fleet Data as CSV",
    data=csv,
    file_name="fleet_overview.csv",
    mime="text/csv"
)

# -----------------------------
# AUTO-REFRESH LOGIC (AT THE END!) - Using navigation helper
# -----------------------------
if should_auto_refresh():
    if should_advance_flag or not auto_advance:
        time.sleep(0.8 if auto_advance else 1.0)
        st.rerun()
