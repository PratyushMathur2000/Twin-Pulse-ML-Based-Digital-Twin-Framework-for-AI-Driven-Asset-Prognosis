"""
Shared performance helpers for Twin-Pulse Dashboard.
Consolidates duplicated logic and provides caching for expensive operations.
"""

import streamlit as st
import pandas as pd


def run_auto_advance(active_pumps, step_hours, current_idx, raw_df, total_steps):
    """
    Shared auto-advance simulation logic.
    Returns True if simulation was advanced, False otherwise.

    This replaces the ~35 lines of identical code duplicated across
    Fleet Overview, Detailed View, Sensor Trend, and AI Diagnostic pages.
    """
    if current_idx >= total_steps:
        return False

    for pump_id in active_pumps:
        simulator = st.session_state["simulators"].get(pump_id)

        if simulator:
            pump_data = raw_df[raw_df["machine_id"] == pump_id]

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
    return True


def get_total_steps(active_pumps, raw_df, step_hours):
    """Calculate total simulation steps from first active pump."""
    if not active_pumps:
        return 0
    pump_id = active_pumps[0]
    pump_data_full = raw_df[raw_df["machine_id"] == pump_id]
    return len(pump_data_full) // step_hours if len(pump_data_full) > 0 else 1


def get_sim_status_block():
    """
    Common sidebar simulation control block used by multiple pages.
    Returns (step_hours, current_idx, total_steps, auto_advance_checkbox_value, should_advance_flag).
    """
    active_pumps = st.session_state.get("sim_pump_ids", [])
    raw_df = st.session_state.get("raw_df")

    step_hours = st.session_state.get("sim_step_hours", 72)
    current_idx = st.session_state.get("sim_current_idx", 0)

    total_steps = get_total_steps(active_pumps, raw_df, step_hours) if raw_df is not None else 0

    return step_hours, current_idx, total_steps
