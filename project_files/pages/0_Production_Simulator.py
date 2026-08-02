import streamlit as st
import pandas as pd
import os
import time
from utils.production_simulator import get_simulator
from utils.themes import apply_theme
from utils.navigation import render_horizontal_navigation

# ===== PAGE CONFIG (MUST BE FIRST!) =====
st.set_page_config(
    page_title="Production Simulator",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ===== APPLY THEME & NAVIGATION =====
apply_theme()
render_horizontal_navigation()

# Set current page
st.session_state["current_page"] = "Production Simulator"

# ===== CUSTOM PAGE STYLING =====
st.markdown("""
<style>
    /* Multiselect tags - match theme color */
    span[data-baseweb="tag"] {
        background-color: var(--primary-color, #f97316) !important;
        border: none !important;
    }

    /* FIX 1: Target the inner text span to force it White */
    span[data-baseweb="tag"] span {
        color: white !important;
    }
    
    span[data-baseweb="tag"] svg {
        fill: white !important;
    }
    
   
    /* Filled bar (The theme color part) */
    .stProgress > div > div {
        background-color: var(--primary-color, #e5e7eb) !important;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Session state initialization
# -----------------------------
st.session_state.setdefault("raw_df", None)
st.session_state.setdefault("fleet_data", None)
st.session_state.setdefault("sim_pump_ids", [])
st.session_state.setdefault("simulators", {})
st.session_state.setdefault("sim_step_hours", 72)
st.session_state.setdefault("sim_steps_per_click", 1)
st.session_state.setdefault("sim_log_df", None)
st.session_state.setdefault("sim_current_idx", 0)
st.session_state.setdefault("sim_autoplay", False)

# -----------------------------
# Constants
# -----------------------------
REQUIRED_COLUMNS = [
    "machine_id",
    "timestamp",
    "radial_vibration_rms",
    "axial_vibration_rms",
    "high_freq_vibration",
    "bearing_temperature",
    "casing_temperature",
    "discharge_pressure",
    "power_consumption",
    "acoustic_emission",
]

# ========================================
# PAGE CONTENT STARTS HERE
# ========================================

st.title("⚙️ Production Simulator – Digital Twin Inference")
st.markdown("*Multi-pump ML pipeline: Health state, Risk score, and RUL*")

# -----------------------------
# Data upload
# -----------------------------
uploaded_file = st.file_uploader(
    "Upload sensor data CSV (Optional)",
    type=["csv"],
    key="sensor_csv_upload",
    help="Must contain: machine_id, timestamp, and the 8 sensor columns. If left empty, default sample data is loaded.",
)

if st.session_state["raw_df"] is None:
    if uploaded_file is not None:
        df_raw = pd.read_csv(uploaded_file)
    else:
        default_file = "test_pump_digital_twin_synthetic_data.csv"
        if os.path.exists(default_file):
            df_raw = pd.read_csv(default_file)
            st.success(f"✅ Loaded sample dataset automatically ({default_file})")
        else:
            st.info("Upload your CSV file to start the simulation.")
            st.stop()
    missing = [c for c in REQUIRED_COLUMNS if c not in df_raw.columns]
    if missing:
        st.error("Missing required columns: " + ", ".join(missing))
        st.stop()

    df = df_raw[REQUIRED_COLUMNS].copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values(["machine_id", "timestamp"]).reset_index(drop=True)
    st.session_state["raw_df"] = df

    fleet = (
        df.groupby("machine_id")
        .agg(last_timestamp=("timestamp", "max"), rows=("timestamp", "size"))
        .reset_index()
    )
    fleet["Status"] = "Healthy"
    fleet["RUL_hours"] = fleet["rows"]
    fleet["Risk_Score"] = 10.0
    st.session_state["fleet_data"] = fleet
else:
    df = st.session_state["raw_df"]

# -----------------------------
# Pump selection (MULTIPLE pumps)
# -----------------------------
st.markdown("### 1. Select pumps and configuration")

available_pumps = sorted(df["machine_id"].unique())

col1, col2, col3 = st.columns(3)

# Sync function for pump selection
def sync_pump_selection():
    """Callback to sync widget selection back to sim_pump_ids AND sort them"""
    st.session_state["sim_pump_ids"] = sorted(st.session_state["pump_selector_widget"])

with col1:
    # Initialize default only if empty or invalid
    if not st.session_state["sim_pump_ids"] or not all(p in available_pumps for p in st.session_state["sim_pump_ids"]):
        st.session_state["sim_pump_ids"] = available_pumps[:1] if available_pumps else []
    
    selected_pumps = st.multiselect(
        "Pumps to simulate (select one or more)",
        options=available_pumps,
        default=st.session_state["sim_pump_ids"],
        key="pump_selector_widget",
        on_change=sync_pump_selection,
        help="Shift+Click to select multiple"
    )

with col2:
    step_hours = st.selectbox(
        "Machine time step (hours)",
        options=[1, 6, 12, 24, 48, 72],
        index=[1, 6, 12, 24, 48, 72].index(st.session_state["sim_step_hours"]),
        help="Sample every N hours (72h = notebook mode)",
    )

with col3:
    steps_per_click = st.selectbox(
        "Steps per cycle",
        options=[1, 2, 5, 10],
        index=[1, 2, 5, 10].index(st.session_state["sim_steps_per_click"]),
        help="Advance N points each cycle",
    )

if not selected_pumps:
    st.warning("Please select at least one pump to simulate.")
    st.stop()

st.session_state["sim_step_hours"] = step_hours
st.session_state["sim_steps_per_click"] = steps_per_click

# Prepare data for all selected pumps
pump_data = {}
min_steps = float('inf')

for pump_id in selected_pumps:
    pump_df_full = df[df["machine_id"] == pump_id].sort_values("timestamp").reset_index(drop=True)
    if pump_df_full.empty:
        st.error(f"No rows found for {pump_id}.")
        continue
    
    total_hourly_rows = len(pump_df_full)
    total_steps = total_hourly_rows // step_hours
    
    pump_data[pump_id] = {
        "df": pump_df_full,
        "hourly_rows": total_hourly_rows,
        "steps": total_steps
    }
    min_steps = min(min_steps, total_steps)

if not pump_data:
    st.error("No valid pumps selected.")
    st.stop()

# Show summary
pump_summary = " | ".join([f"**{pid}**: {pump_data[pid]['hourly_rows']} rows → {pump_data[pid]['steps']} steps" 
                           for pid in selected_pumps])
st.markdown(f"Selected: {pump_summary} (every {step_hours}h)")

# Use minimum steps across all pumps
total_steps = min_steps

# -----------------------------
# Initialize simulators
# -----------------------------
models_folder = "saved_models"

col_reset, col_init = st.columns([1, 2])
with col_reset:
    if st.button("🔄 Reset"):
        st.session_state["simulators"] = {}
        st.session_state["sim_current_idx"] = 0
        st.session_state["sim_log_df"] = None
        st.session_state["sim_autoplay"] = False
        st.rerun()

with col_init:
    need_init = [pid for pid in selected_pumps if pid not in st.session_state["simulators"]]
    
    if need_init:
        try:
            with st.spinner(f"Loading models for {len(need_init)} pump(s)..."):
                for pump_id in need_init:
                    sim = get_simulator(models_folder, pump_id)
                    st.session_state["simulators"][pump_id] = sim
            st.success(f"✅ {len(need_init)} simulator(s) initialized")
        except Exception as e:
            st.error(f"Model loading failed: {e}")
            st.stop()

# -----------------------------
# Playback controls
# -----------------------------
st.markdown("### 2. Playback controls")

current_idx = st.session_state["sim_current_idx"]
progress_pct = (current_idx / total_steps * 100) if total_steps > 0 else 0

st.progress(current_idx / total_steps if total_steps > 0 else 0)
st.markdown(f"**Progress:** {current_idx} / {total_steps} ({progress_pct:.1f}%)")

col_play, col_manual = st.columns([1, 2])

with col_play:
    if current_idx >= total_steps:
        st.success("✅ Complete!")
        st.session_state["sim_autoplay"] = False
    else:
        if st.session_state["sim_autoplay"]:
            if st.button("⏸ Pause"):
                st.session_state["sim_autoplay"] = False
                st.rerun()
        else:
            if st.button("▶ Auto-play"):
                st.session_state["sim_autoplay"] = True
                st.rerun()

with col_manual:
    manual_clicked = st.button(f"⏭ Manual ({steps_per_click}×)")

# -----------------------------
# DISPLAY PLACEHOLDERS
# -----------------------------
log_df = st.session_state["sim_log_df"]

st.markdown("---")
st.markdown("### 3. Current state")

status_placeholders = {}
for pump_id in st.session_state["sim_pump_ids"]:
    status_placeholders[pump_id] = st.empty()

divider_placeholder = st.empty()
table_header_placeholder = st.empty()
table_placeholder = st.empty()
download_placeholder = st.empty()

# Show current state if data exists
if log_df is not None and not log_df.empty:
    for pump_id in st.session_state["sim_pump_ids"]:
        pump_log = log_df[log_df["machine_id"] == pump_id]
        
        if not pump_log.empty:
            latest = pump_log.iloc[-1]
            
            with status_placeholders[pump_id].container():
                st.markdown(f"#### {pump_id}")
                
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    ts = pd.to_datetime(latest.get("timestamp", ""))
                    time_str = ts.strftime("%d/%m/%Y %H:%M")
                    st.metric("Time", time_str)
                with c2:
                    health_label = latest.get("health_label", "")
                    emoji = {"Healthy": "🟢", "Degrading": "🟡", "Critical": "🟠", "Failure": "🔴"}.get(health_label, "")
                    st.metric("Health", f"{emoji} {health_label}")
                with c3:
                    risk = int(latest.get('risk_score', 0))
                    st.metric("Risk", f"{risk}/100", delta=latest.get('risk_band', ''))
                with c4:
                    rul = latest.get("rul_days", None)
                    st.metric("RUL", "N/A" if pd.isna(rul) else f"{rul:.1f} days")

                st.markdown(f"**Drivers:** {latest.get('dominant_sensors', '—')}")
                
                with st.expander("💬 Comment"):
                    st.write(latest.get("comment", ""))
        else:
            with status_placeholders[pump_id].container():
                st.markdown(f"#### {pump_id}")
                st.info("No data yet")
    
    with divider_placeholder.container():
        st.markdown("---")
    
    with table_header_placeholder.container():
        st.markdown("### 4. Simulation log")
    
    with table_placeholder.container():
        # Show separate table for each pump
        for pump_id in st.session_state["sim_pump_ids"]:
            pump_log = log_df[log_df["machine_id"] == pump_id].copy()
            
            if not pump_log.empty:
                st.markdown(f"#### {pump_id}")
                
                # Remove machine_id column for display
                display_cols = [col for col in pump_log.columns if col != "machine_id"]
                st.dataframe(
                    pump_log[display_cols].sort_values("timestamp").reset_index(drop=True),
                    use_container_width=True
                )
            else:
                st.markdown(f"#### {pump_id}")
                st.info("No data logged yet")
    
    with download_placeholder.container():
        csv = log_df.to_csv(index=False)
        pump_names = "_".join(st.session_state["sim_pump_ids"])
        st.download_button(
            label="📥 Download combined log (all pumps)",
            data=csv,
            file_name=f"{pump_names}_combined_log.csv",
            mime="text/csv",
            key=f"download_{current_idx}"
        )
else:
    with status_placeholders[selected_pumps[0]].container():
        st.info("Click **Auto-play** or **Manual** to start")

# -----------------------------
# Step execution
# -----------------------------
def run_simulation_steps(n_steps):
    """Process n_steps for ALL selected pumps (sequential for thread safety)."""
    current = st.session_state["sim_current_idx"]
    
    if current >= total_steps:
        st.session_state["sim_autoplay"] = False
        return
    
    steps_to_run = min(n_steps, total_steps - current)
    
    all_logs = []
    
    # Sequential processing (thread-safe)
    for pump_id in selected_pumps:
        simulator = st.session_state["simulators"][pump_id]
        pump_df = pump_data[pump_id]["df"]
        
        # Process from current to current + steps_to_run
        hourly_start = current * step_hours
        hourly_end = (current + steps_to_run) * step_hours
        
        for hourly_idx in range(hourly_start, min(hourly_end, len(pump_df))):
            row = pump_df.iloc[[hourly_idx]].copy()
            log_entry = simulator.process_streaming_row(row)
            
            # Log every step_hours rows
            if hourly_idx % step_hours == 0:
                log_entry["machine_id"] = pump_id
                all_logs.append(log_entry)
    
    st.session_state["sim_current_idx"] = current + steps_to_run

    if all_logs:
        new_df = pd.DataFrame(all_logs)
        if st.session_state["sim_log_df"] is None:
            st.session_state["sim_log_df"] = new_df
        else:
            st.session_state["sim_log_df"] = pd.concat(
                [st.session_state["sim_log_df"], new_df],
                ignore_index=True
            )

# Manual step
if manual_clicked:
    run_simulation_steps(steps_per_click)
    st.rerun()

# Auto-play step
if st.session_state["sim_autoplay"] and current_idx < total_steps:
    run_simulation_steps(steps_per_click)
    time.sleep(0.5)
    st.rerun()
