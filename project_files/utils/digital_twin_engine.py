"""
utils/digital_twin_engine.py

Digital Twin Scenario Engine — Clean Architecture
══════════════════════════════════════════════════

CONCEPT
───────
Pump is currently running (day X in the production simulator).
Question: "What if I replace the bearing on Day X+10?"

We answer by forking TWO independent simulation runs from the current
live state, replaying the raw sensor data hour by hour through the exact
same production ML pipeline (PumpSimulator.process_streaming_row):

  BASELINE fork  →  no changes        → what will happen if you do nothing
  SCENARIO fork  →  with intervention → what happens if you act on Day X+10

The comparison table is hourly (one row per hour) showing:
  Timestamp | Health | RUL | Risk | 8 sensor readings

Charts show two trend lines (baseline red-dashed vs scenario green).

MAINTENANCE IMPLEMENTATION
──────────────────────────
When the scenario fork crosses the maintenance day it:
  1. Modifies the raw sensor reading for that row (physical effect)
  2. Resets the simulator's mutable internal state so the ML models
     can actually respond to the improved sensor values
     (latched_health, rul_raw_buffer, risk_history, risk_engine buffer)

This is the only correct way — the EWMA and latching mechanisms in the
production simulator are designed to be conservative (never auto-improve),
so a maintenance event MUST explicitly reset them.
"""

import copy
import numpy as np
import pandas as pd
from pathlib import Path

MODEL_DIR = Path("saved_models")

# ─────────────────────────────────────────────────────────────────────────────
# SENSOR COLUMN MAPPINGS  (CSV raw names  ↔  display/standard names)
# ─────────────────────────────────────────────────────────────────────────────

CSV_TO_STD = {
    'radial_vibration_rms': 'radial_vibration_mm_s',
    'axial_vibration_rms':  'axial_vibration_mm_s',
    'high_freq_vibration':  'high_freq_vibration_g',
    'bearing_temperature':  'bearing_temperature_c',
    'casing_temperature':   'casing_temperature_c',
    'discharge_pressure':   'discharge_pressure_bar',
    'power_consumption':    'power_consumption_kw',
    'acoustic_emission':    'acoustic_emission_db',
}
STD_TO_CSV      = {v: k for k, v in CSV_TO_STD.items()}
SENSOR_COLS_STD = list(CSV_TO_STD.values())
SENSOR_COLS_CSV = list(CSV_TO_STD.keys())

HEALTH_INT_TO_STR = {0: "Healthy", 1: "Degrading", 2: "Critical", 3: "Failure"}
HEALTH_STR_TO_INT = {v: k for k, v in HEALTH_INT_TO_STR.items()}


# ─────────────────────────────────────────────────────────────────────────────
# MACHINE-TIME HELPER
# ─────────────────────────────────────────────────────────────────────────────

def get_current_machine_day() -> dict:
    """
    Convert production simulator step index × step hours → machine days elapsed.
    Returns: step_idx, step_hours, machine_hours, machine_days, machine_days_int
    """
    import streamlit as st
    step_idx   = st.session_state.get("sim_current_idx", 0)
    step_hours = st.session_state.get("sim_step_hours",  72)
    machine_hours = step_idx * step_hours
    machine_days  = machine_hours / 24.0
    return {
        "step_idx":         step_idx,
        "step_hours":       step_hours,
        "machine_hours":    machine_hours,
        "machine_days":     machine_days,
        "machine_days_int": int(machine_days),
    }


# ─────────────────────────────────────────────────────────────────────────────
# SIMULATOR FAST-COPY
# ─────────────────────────────────────────────────────────────────────────────

def _copy_simulator(sim):
    """
    Fast copy of a warmed PumpSimulator for scenario forking.

    ML models (classifier, rul_model) are SHARED by reference — they are
    stateless after training so sharing is safe and avoids a 30s deepcopy
    of large sklearn ensembles.

    Only the mutable streaming state is copied:
        buffer, latched_health, last_rul, risk_history, rul_raw_buffer,
        risk_engine (has its own EWMA/buffer state)
    """
    new = sim.__class__.__new__(sim.__class__)

    # Shared (stateless) ─────────────────────────────────────────────────────
    new.pump_id           = sim.pump_id
    new.models_folder     = sim.models_folder
    new.classifier        = sim.classifier
    new.health_feat_order = sim.health_feat_order
    new.failure_threshold = sim.failure_threshold
    new.rul_model         = sim.rul_model
    new.rul_feat_order    = sim.rul_feat_order
    new.buffer_max        = sim.buffer_max
    new.first_timestamp   = sim.first_timestamp

    # Mutable runtime state ──────────────────────────────────────────────────
    new.buffer         = sim.buffer.copy()
    new.latched_health = sim.latched_health
    new.last_rul       = sim.last_rul
    new.risk_history   = list(sim.risk_history)
    new.rul_raw_buffer = list(sim.rul_raw_buffer)
    new.log            = []

    # Deep-copy risk engine (holds machine_buffers dict + EWMA state) ────────
    new.risk_engine = copy.deepcopy(sim.risk_engine)

    return new


# ─────────────────────────────────────────────────────────────────────────────
# MAINTENANCE PHYSICAL EFFECTS  (applied to raw CSV-column sensor values)
# ─────────────────────────────────────────────────────────────────────────────

MAINTENANCE_SENSOR_EFFECTS = {
    'bearing_replacement': {
        'bearing_temperature':  0.65,
        'radial_vibration_rms': 0.55,
        'axial_vibration_rms':  0.55,
        'high_freq_vibration':  0.60,
        'acoustic_emission':    0.60,
    },
    'seal_replacement': {
        'discharge_pressure':   1.08,
        'power_consumption':    0.92,
    },
    'derate_pump': {
        **{s: 0.80 for s in SENSOR_COLS_CSV}
    },
}


def _apply_maintenance_to_row(row_df: pd.DataFrame, action_type: str) -> pd.DataFrame:
    """Apply physical sensor effects of a maintenance action to one raw row."""
    row_df = row_df.copy()
    effects = MAINTENANCE_SENSOR_EFFECTS.get(action_type, {})
    for csv_col, factor in effects.items():
        if csv_col in row_df.columns:
            row_df[csv_col] = row_df[csv_col] * factor
    return row_df


def _reset_simulator_state_after_maintenance(sim, action_type: str) -> None:
    """
    Reset the simulator's internal streaming state to reflect a maintenance event.

    WHY THIS IS NECESSARY
    ─────────────────────
    The production simulator uses conservative mechanisms that NEVER
    auto-improve on their own:

      1. latched_health = max(latched_health, new_prediction)
         → once Critical, always at least Critical, even if all sensors improve
      2. EWMA smoother on risk_score with max_step_change=20
         → even with perfect sensors, risk can only drop 20 points per step
      3. risk_engine.machine_buffers stores the last 168 hours of rows
         → dwell_fraction stays high because buffer is full of pre-maintenance rows

    A real bearing replacement physically resets the machine to a near-new
    bearing state. The simulator must be told this explicitly.

    CRITICAL: Always write a real numeric score (never NaN) into the
    risk_score buffer column. NaN would be passed as `prev` into the
    production simulator's _smooth() → round(NaN) → crash.
    """
    recovery = {
        'bearing_replacement': 2,
        'seal_replacement':    1,
        'derate_pump':         1,
    }
    drop = recovery.get(action_type, 1)
    sim.latched_health = max(0, sim.latched_health - drop)

    # Clear RUL smoothing buffers
    sim.last_rul       = None
    sim.rul_raw_buffer = []

    # Trim risk history so EWMA can recover quickly after repair
    sim.risk_history = sim.risk_history[-6:] if len(sim.risk_history) > 6 else []

    # Reset the risk engine's machine buffer
    if sim.pump_id in sim.risk_engine.machine_buffers:
        buf = sim.risk_engine.machine_buffers[sim.pump_id].copy()

        # Overwrite predicted_health_state for last 48 rows
        reset_rows = min(48, len(buf))
        if 'predicted_health_state' in buf.columns:
            buf.iloc[
                -reset_rows:,
                buf.columns.get_loc('predicted_health_state')
            ] = sim.latched_health

        # ── Write a real numeric risk score — NEVER NaN ──────────────────────
        # NaN here would flow into _smooth(raw, prev=NaN) in the production
        # simulator and crash with "cannot convert float NaN to integer".
        # Use a realistic low score matching the post-maintenance health state.
        if 'risk_score' in buf.columns:
            reset_score = float({0: 10, 1: 25, 2: 40}.get(sim.latched_health, 10))
            n_clear = min(12, len(buf))
            buf.iloc[
                -n_clear:,
                buf.columns.get_loc('risk_score')
            ] = reset_score

        sim.risk_engine.machine_buffers[sim.pump_id] = buf


# ─────────────────────────────────────────────────────────────────────────────
# ENVIRONMENT EFFECTS
# ─────────────────────────────────────────────────────────────────────────────

def _apply_env_to_row(row_df: pd.DataFrame, env_changes: dict) -> pd.DataFrame:
    """Apply environmental changes to one raw row (CSV column names)."""
    row_df = row_df.copy()

    delta = env_changes.get('ambient_temp_delta', 0)
    if delta != 0:
        if 'bearing_temperature' in row_df.columns:
            row_df['bearing_temperature'] += delta * 0.6
        if 'casing_temperature' in row_df.columns:
            row_df['casing_temperature']  += delta * 0.8

    viscosity = env_changes.get('fluid_viscosity_factor', 1.0)
    if viscosity != 1.0:
        if 'power_consumption' in row_df.columns:
            row_df['power_consumption']  *= viscosity
        if 'discharge_pressure' in row_df.columns:
            row_df['discharge_pressure'] *= (1.0 / viscosity)

    load = env_changes.get('load_factor', 1.0)
    if load != 1.0:
        for col in SENSOR_COLS_CSV:
            if col in row_df.columns:
                row_df[col] *= load

    return row_df


def _apply_sensor_change_to_row(
    row_df:      pd.DataFrame,
    changes:     list,
    machine_day: float,
) -> pd.DataFrame:
    """Apply day-gated sensor override changes to one raw row."""
    row_df = row_df.copy()
    for chg in changes:
        if machine_day < chg.get('from_day', 0):
            continue
        std_name = chg['sensor']
        csv_name = STD_TO_CSV.get(std_name, std_name)
        col = csv_name if csv_name in row_df.columns else std_name
        if col not in row_df.columns:
            continue
        v, ct = chg['value'], chg['change_type']
        if   ct == 'add':      row_df[col] += v
        elif ct == 'multiply': row_df[col] *= v
        elif ct == 'set':      row_df[col]  = v
    return row_df


# ─────────────────────────────────────────────────────────────────────────────
# CORE FORK RUNNER
# ─────────────────────────────────────────────────────────────────────────────

def _run_fork(
    sim,
    raw_rows:            pd.DataFrame,
    t0_machine:          pd.Timestamp,
    sensor_changes:      list,
    maintenance_actions: list,
    env_changes:         dict,
    hourly:              bool = False,
    step_hours:          int  = 72,
) -> pd.DataFrame:
    """
    Replay raw_rows through a simulator fork, applying scenario changes.

    Hourly mode:  returns one record per CSV row   → comparison table
    Sampled mode: returns one record per step_hours → trend charts (fast)

    Maintenance resets fire exactly ONCE when the action day is first crossed.
    """
    applied_resets: set = set()
    records = []

    rows_to_process = (
        raw_rows.reset_index(drop=True)
        if hourly
        else raw_rows.iloc[::step_hours].reset_index(drop=True)
    )

    for _, raw_row in rows_to_process.iterrows():
        ts          = pd.to_datetime(raw_row['timestamp'])
        machine_day = (ts - t0_machine).total_seconds() / 86400.0
        row_df      = pd.DataFrame([raw_row])

        # Apply environment changes
        if env_changes:
            row_df = _apply_env_to_row(row_df, env_changes)

        # Apply sensor overrides
        if sensor_changes:
            row_df = _apply_sensor_change_to_row(row_df, sensor_changes, machine_day)

        # Apply maintenance: sensor effect + simulator state reset
        for idx, action in enumerate(maintenance_actions or []):
            action_day = float(action.get('day', 0))
            if idx not in applied_resets and machine_day >= action_day:
                row_df = _apply_maintenance_to_row(row_df, action['action_type'])
                _reset_simulator_state_after_maintenance(sim, action['action_type'])
                applied_resets.add(idx)
            elif idx in applied_resets:
                # Keep sensor effects active on all future rows after maintenance
                row_df = _apply_maintenance_to_row(row_df, action['action_type'])

        # Run through production ML pipeline
        log_entry = sim.process_streaming_row(row_df)

        # Collect standardised sensor values for display
        std_sensors = {}
        for csv_name, std_name in CSV_TO_STD.items():
            if csv_name in row_df.columns:
                std_sensors[std_name] = round(float(row_df[csv_name].iloc[0]), 4)

        record = {
            'timestamp':              ts,
            'days_in_operation':      round(machine_day, 4),
            'risk_score':             log_entry['risk_score'],
            'rul_days':               log_entry.get('rul_days'),
            'health_label':           log_entry['health_label'],
            'predicted_health_state': log_entry['predicted_health_state'],
            'dominant_sensors':       log_entry.get('dominant_sensors', '—'),
            'risk_band':              log_entry.get('risk_band', ''),
            'rul_band':               log_entry.get('rul_band', 'N/A'),
        }
        record.update(std_sensors)
        records.append(record)

    return pd.DataFrame(records) if records else pd.DataFrame()


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API — run_scenario
# ─────────────────────────────────────────────────────────────────────────────

def run_scenario(
    pump_id:             str,
    sensor_changes:      list  = None,
    maintenance_actions: list  = None,
    env_changes:         dict  = None,
    use_live_data:       bool  = False,
    current_day:         float = 0.0,
) -> tuple:
    """
    Run a complete what-if scenario for a pump.

    Both BASELINE and SCENARIO are run through the SAME production ML pipeline
    (PumpSimulator.process_streaming_row) using independent simulator forks.

    Returns: (baseline_df, scenario_df, summary)
    """
    import streamlit as st

    simulators  = st.session_state.get("simulators", {})
    raw_df_full = st.session_state.get("raw_df")
    step_hours  = st.session_state.get("sim_step_hours", 72)
    current_idx = st.session_state.get("sim_current_idx", 0)

    if pump_id not in simulators or raw_df_full is None:
        raise ValueError(
            f"No warmed simulator or raw data found for '{pump_id}'. "
            "Please run the Production Simulator for this pump first."
        )

    raw_pump_df = (
        raw_df_full[raw_df_full['machine_id'] == pump_id]
        .sort_values('timestamp')
        .reset_index(drop=True)
    )
    raw_pump_df['timestamp'] = pd.to_datetime(raw_pump_df['timestamp'])
    t0_machine = raw_pump_df['timestamp'].iloc[0]

    start_row   = (current_idx * step_hours) if use_live_data else 0
    rows_to_run = raw_pump_df.iloc[start_row:].copy().reset_index(drop=True)

    if rows_to_run.empty:
        rows_to_run = raw_pump_df.tail(step_hours * 2).copy().reset_index(drop=True)

    live_sim = simulators[pump_id]

    # BASELINE fork — no changes
    baseline_df = _run_fork(
        sim                 = _copy_simulator(live_sim),
        raw_rows            = rows_to_run,
        t0_machine          = t0_machine,
        sensor_changes      = [],
        maintenance_actions = [],
        env_changes         = {},
        hourly              = False,
        step_hours          = step_hours,
    )

    # SCENARIO fork — with changes
    scenario_df = _run_fork(
        sim                 = _copy_simulator(live_sim),
        raw_rows            = rows_to_run,
        t0_machine          = t0_machine,
        sensor_changes      = sensor_changes      or [],
        maintenance_actions = maintenance_actions or [],
        env_changes         = env_changes         or {},
        hourly              = False,
        step_hours          = step_hours,
    )

    # Summary metrics
    def _first_failure_day(df: pd.DataFrame) -> float:
        candidates = []
        if 'risk_score' in df.columns:
            high = df[df['risk_score'] >= 90]
            if not high.empty:
                candidates.append(float(high['days_in_operation'].iloc[0]))
        if 'predicted_health_state' in df.columns:
            fail = df[df['predicted_health_state'] >= 3]
            if not fail.empty:
                candidates.append(float(fail['days_in_operation'].iloc[0]))
        return min(candidates) if candidates else float(df['days_in_operation'].max())

    b_fail = _first_failure_day(baseline_df)
    s_fail = _first_failure_day(scenario_df)

    summary = {
        'baseline_failure_day': round(b_fail, 1),
        'scenario_failure_day': round(s_fail, 1),
        'rul_extension':        round(s_fail - b_fail, 1),
        'baseline_avg_risk':    round(float(baseline_df['risk_score'].mean()), 1)
                                if 'risk_score' in baseline_df.columns else 0.0,
        'scenario_avg_risk':    round(float(scenario_df['risk_score'].mean()), 1)
                                if 'risk_score' in scenario_df.columns else 0.0,
        'max_risk':             round(float(scenario_df['risk_score'].max()), 1)
                                if 'risk_score' in scenario_df.columns else 0.0,
        'current_day':          current_day if use_live_data else 0.0,
        'is_live':              use_live_data,
        'used_real_simulator':  True,
    }

    return baseline_df, scenario_df, summary


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API — run_hourly_comparison
# ─────────────────────────────────────────────────────────────────────────────

def run_hourly_comparison(
    pump_id:             str,
    maintenance_actions: list,
    sensor_changes:      list  = None,
    env_changes:         dict  = None,
    use_live_data:       bool  = False,
    window_days_before:  float = 5.0,
    window_days_after:   float = 15.0,
) -> pd.DataFrame:
    """
    Generate an HOURLY side-by-side comparison table around the maintenance event.

    Columns: Timestamp, Day, Event, Health (baseline), Health (scenario),
             RUL baseline, RUL scenario, Risk baseline, Risk scenario,
             + 8 sensor readings (scenario values)
    """
    import streamlit as st

    simulators  = st.session_state.get("simulators", {})
    raw_df_full = st.session_state.get("raw_df")
    step_hours  = st.session_state.get("sim_step_hours", 72)
    current_idx = st.session_state.get("sim_current_idx", 0)

    if pump_id not in simulators or raw_df_full is None:
        raise ValueError(
            f"No warmed simulator or raw data found for '{pump_id}'. "
            "Run the Production Simulator first."
        )

    raw_pump_df = (
        raw_df_full[raw_df_full['machine_id'] == pump_id]
        .sort_values('timestamp')
        .reset_index(drop=True)
    )
    raw_pump_df['timestamp'] = pd.to_datetime(raw_pump_df['timestamp'])
    t0_machine = raw_pump_df['timestamp'].iloc[0]

    start_row = (current_idx * step_hours) if use_live_data else 0

    action_days = [float(a.get('day', 0)) for a in (maintenance_actions or [])]
    anchor_day  = min(action_days) if action_days else 0.0

    window_start_day = max(0.0, anchor_day - window_days_before)
    window_end_day   = anchor_day + window_days_after

    all_days = raw_pump_df['timestamp'].apply(
        lambda ts: (ts - t0_machine).total_seconds() / 86400.0
    )

    window_rows = raw_pump_df[
        (all_days >= window_start_day) & (all_days <= window_end_day)
    ].copy()

    if window_rows.empty:
        window_rows = raw_pump_df.iloc[start_row:start_row + 480].copy()

    live_sim = simulators[pump_id]

    base_records = _run_fork(
        sim                 = _copy_simulator(live_sim),
        raw_rows            = window_rows,
        t0_machine          = t0_machine,
        sensor_changes      = [],
        maintenance_actions = [],
        env_changes         = {},
        hourly              = True,
        step_hours          = step_hours,
    )

    scen_records = _run_fork(
        sim                 = _copy_simulator(live_sim),
        raw_rows            = window_rows,
        t0_machine          = t0_machine,
        sensor_changes      = sensor_changes      or [],
        maintenance_actions = maintenance_actions or [],
        env_changes         = env_changes         or {},
        hourly              = True,
        step_hours          = step_hours,
    )

    if base_records.empty or scen_records.empty:
        return pd.DataFrame()

    n = min(len(base_records), len(scen_records))
    b = base_records.iloc[:n].reset_index(drop=True)
    s = scen_records.iloc[:n].reset_index(drop=True)

    def _rul_str(val):
        if val is None:
            return '—'
        try:
            f = float(val)
            return '—' if np.isnan(f) else f"{f:.1f}"
        except (TypeError, ValueError):
            return '—'

    rows = []
    for i in range(n):
        br, sr = b.iloc[i], s.iloc[i]
        day = br['days_in_operation']
        ts  = br['timestamp']

        is_maint_row = any(
            abs(day - float(a.get('day', 0))) < (1.0 / 24.0)
            for a in (maintenance_actions or [])
        )

        row = {
            'Timestamp':           (pd.to_datetime(ts).strftime('%Y-%m-%d %H:%M')
                                    if pd.notna(ts) else '—'),
            'Day':                 f"{day:.2f}",
            'Event':               '🔧 MAINTENANCE' if is_maint_row else '',
            'Health (Baseline)':   br.get('health_label', '—'),
            'Health (Scenario)':   sr.get('health_label', '—'),
            'RUL Baseline (days)': _rul_str(br.get('rul_days')),
            'RUL Scenario (days)': _rul_str(sr.get('rul_days')),
            'Risk (Baseline)':     int(br.get('risk_score', 0)),
            'Risk (Scenario)':     int(sr.get('risk_score', 0)),
            'Radial Vib (mm/s)':   f"{sr.get('radial_vibration_mm_s',  0):.3f}",
            'Axial Vib (mm/s)':    f"{sr.get('axial_vibration_mm_s',   0):.3f}",
            'Hi-Freq Vib (g)':     f"{sr.get('high_freq_vibration_g',  0):.3f}",
            'Bearing Temp (°C)':   f"{sr.get('bearing_temperature_c',  0):.1f}",
            'Casing Temp (°C)':    f"{sr.get('casing_temperature_c',   0):.1f}",
            'Discharge P (bar)':   f"{sr.get('discharge_pressure_bar', 0):.2f}",
            'Power (kW)':          f"{sr.get('power_consumption_kw',   0):.1f}",
            'Acoustic (dB)':       f"{sr.get('acoustic_emission_db',   0):.1f}",
        }
        rows.append(row)

    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# DISPLAY TABLE HELPER
# ─────────────────────────────────────────────────────────────────────────────

def get_sensor_ranges_table(df: pd.DataFrame, days_to_show=None) -> pd.DataFrame:
    """Sensor readings at evenly-spaced day checkpoints."""
    if df.empty:
        return pd.DataFrame()

    min_day = float(df['days_in_operation'].min())
    max_day = float(df['days_in_operation'].max())
    span    = max_day - min_day

    if days_to_show is None:
        n_points     = 7
        days_to_show = (
            [min_day + i * span / (n_points - 1) for i in range(n_points)]
            if span > 0 else [min_day]
        )

    rows = []
    for target_day in days_to_show:
        tolerance  = max(span / 30, 1.0)
        candidates = df[
            (df['days_in_operation'] >= target_day - tolerance) &
            (df['days_in_operation'] <= target_day + tolerance)
        ]
        if candidates.empty:
            continue
        closest = candidates.iloc[
            (candidates['days_in_operation'] - target_day).abs().argmin()
        ]

        def _g(std, raw=None, default=0):
            v = closest.get(std, closest.get(raw, default) if raw else default)
            return v if pd.notna(v) else default

        ts_str = ''
        if 'timestamp' in closest.index and pd.notna(closest.get('timestamp')):
            try:
                ts_str = pd.to_datetime(closest['timestamp']).strftime('%Y-%m-%d %H:%M')
            except Exception:
                ts_str = str(closest.get('timestamp', ''))[:16]

        rows.append({
            'Day':          f"{closest['days_in_operation']:.1f}",
            'Timestamp':    ts_str or 'N/A',
            'Health':       closest.get('health_label', '—'),
            'RUL (days)':   f"{_g('rul_days', 'remaining_useful_life'):.1f}",
            'Risk Score':   int(_g('risk_score')),
            'Radial Vib':   f"{_g('radial_vibration_mm_s', 'radial_vibration_rms'):.3f}",
            'Bearing Temp': f"{_g('bearing_temperature_c', 'bearing_temperature'):.1f}°C",
            'Discharge P':  f"{_g('discharge_pressure_bar', 'discharge_pressure'):.2f} bar",
            'Power (kW)':   f"{_g('power_consumption_kw', 'power_consumption'):.1f}",
        })

    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# BULK WRAPPERS
# ─────────────────────────────────────────────────────────────────────────────

def apply_sensor_changes(df: pd.DataFrame, changes: list) -> pd.DataFrame:
    df = df.copy()
    for chg in changes:
        col  = chg['sensor'] if chg['sensor'] in df.columns else STD_TO_CSV.get(chg['sensor'], chg['sensor'])
        mask = df['days_in_operation'] >= chg.get('from_day', 0)
        if col not in df.columns:
            continue
        v, ct = chg['value'], chg['change_type']
        if   ct == 'add':      df.loc[mask, col] += v
        elif ct == 'multiply': df.loc[mask, col] *= v
        elif ct == 'set':      df.loc[mask, col]  = v
    return df


def apply_maintenance_action(df: pd.DataFrame, action: dict) -> pd.DataFrame:
    df    = df.copy()
    mask  = df['days_in_operation'] >= action['day']
    atype = action['action_type']
    effects = MAINTENANCE_SENSOR_EFFECTS.get(atype, {})
    for csv_col, factor in effects.items():
        std_col = CSV_TO_STD.get(csv_col, csv_col)
        col = std_col if std_col in df.columns else csv_col
        if col in df.columns:
            df.loc[mask, col] *= factor
    return df


def apply_environment_changes(df: pd.DataFrame, env_changes: dict) -> pd.DataFrame:
    df = df.copy()
    delta = env_changes.get('ambient_temp_delta', 0)
    if delta != 0:
        if 'bearing_temperature_c' in df.columns:
            df['bearing_temperature_c'] += delta * 0.6
        if 'casing_temperature_c' in df.columns:
            df['casing_temperature_c']  += delta * 0.8
    viscosity = env_changes.get('fluid_viscosity_factor', 1.0)
    if viscosity != 1.0:
        if 'power_consumption_kw'   in df.columns:
            df['power_consumption_kw']   *= viscosity
        if 'discharge_pressure_bar' in df.columns:
            df['discharge_pressure_bar'] *= (1.0 / viscosity)
    load = env_changes.get('load_factor', 1.0)
    if load != 1.0:
        for col in SENSOR_COLS_STD:
            if col in df.columns:
                df[col] *= load
    return df
