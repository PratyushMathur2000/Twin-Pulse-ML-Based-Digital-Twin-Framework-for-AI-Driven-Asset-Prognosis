import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import time
from openai import OpenAI
from utils.themes import apply_theme
from utils.navigation import render_horizontal_navigation, should_auto_refresh
from utils.digital_twin_engine import (
    run_scenario, run_hourly_comparison,
    get_sensor_ranges_table,
    SENSOR_COLS_STD, get_current_machine_day
)
from utils.cache_helpers import run_auto_advance, get_total_steps

# ===== PAGE CONFIG =====
st.set_page_config(
    page_title="Digital Twin Sandbox",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="collapsed"
)

apply_theme()
render_horizontal_navigation()
st.session_state["current_page"] = "Digital Twin"

# ===== STYLES =====
st.markdown("""
<style>
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
        50%       { opacity: 0.5; }
    }
    span[data-baseweb="tag"] {
        background-color: var(--primary-color, #f97316) !important;
        border: none !important;
    }
    span[data-baseweb="tag"] span { color: white !important; }
    span[data-baseweb="tag"] svg  { fill: white !important; }
</style>
""", unsafe_allow_html=True)

# ===== PAGE HEADER =====
st.title("🔮 Digital Twin Sandbox")
st.markdown("**What-If Scenario Simulator** – Test pump behavior under different conditions")

if st.session_state.get("sim_autoplay", False):
    st.markdown(
        '<div style="text-align:center; padding:10px; '
        'background:linear-gradient(135deg,#667eea 0%,#764ba2 100%); '
        'border-radius:10px; margin-bottom:20px;">'
        '<span class="live-indicator"></span>'
        '<span style="color:white; font-weight:600; font-size:16px;">'
        'LIVE – Production Simulator Running</span>'
        '</div>',
        unsafe_allow_html=True
    )

st.markdown("---")

# ===== SESSION STATE DEFAULTS =====
_defaults = {
    'dt_baseline_df':         None,
    'dt_scenario_df':         None,
    'dt_summary':             None,
    'dt_ai_chat_history':     [],
    'dt_sensor_changes':      [],
    'dt_maintenance_actions': [],
    'dt_env_changes':         {},
    'dt_last_pump':           None,
    'dt_last_run_time':       None,
    'dt_auto_refresh':        False,
    'dt_scenario_name':       "Custom Scenario",
    'dt_data_source':         "Synthetic Dataset",
}
for k, v in _defaults.items():
    st.session_state.setdefault(k, v)

# ===== AUTO-ADVANCE LOGIC =====
active_pumps  = st.session_state.get("sim_pump_ids", [])
raw_df_exists = st.session_state.get("raw_df") is not None
should_advance_flag = False

if raw_df_exists and active_pumps:
    _step_h  = st.session_state.get("sim_step_hours", 72)
    _cur_idx = st.session_state.get("sim_current_idx", 0)
    _total   = get_total_steps(active_pumps, st.session_state["raw_df"], _step_h)

    if (st.session_state['dt_auto_refresh']
            and st.session_state.get("sim_autoplay", False)
            and _cur_idx < _total):
        should_advance_flag = run_auto_advance(
            active_pumps, _step_h, _cur_idx,
            st.session_state["raw_df"], _total
        )

# ===== DERIVE AVAILABLE PUMP IDS =====
_raw_df = st.session_state.get("raw_df")
if _raw_df is not None:
    available_pumps = sorted(_raw_df['machine_id'].unique().tolist())
else:
    available_pumps = []

# ===== TOP CONTROLS =====
col1, col2, col3, col4 = st.columns([2, 2, 1, 1])

with col1:
    prod_sim_available = raw_df_exists and bool(st.session_state.get("sim_pump_ids"))

    if prod_sim_available:
        data_source = st.radio(
            "Data Source",
            options=['Synthetic Dataset', 'Live Simulation'],
            horizontal=True,
            key='dt_data_source_radio',
            help=(
                "Synthetic: Replays full pump lifecycle from Day 0 through the ML pipeline | "
                "Live: Continues from current Production Simulator position (today → future)"
            )
        )
        st.session_state['dt_data_source'] = data_source
    else:
        data_source = 'Synthetic Dataset'
        st.session_state['dt_data_source'] = data_source
        st.info("💡 Start Production Simulator to use live pump data")

    if data_source == 'Synthetic Dataset':
        pump_options = available_pumps if available_pumps else ['(No data loaded)']
        _help = None
        if _raw_df is not None and available_pumps:
            _help = f"{len(available_pumps)} pumps available from uploaded dataset"
        pump_id = st.selectbox(
            "🎯 Select Pump",
            options=pump_options,
            key='dt_pump_selector',
            help=_help
        )
    else:
        live_pumps = st.session_state.get("sim_pump_ids", [])
        pump_id = st.selectbox(
            "🎯 Select Pump (live)",
            options=live_pumps if live_pumps else available_pumps if available_pumps else ['(No data loaded)'],
            key='dt_pump_selector_live',
            help="Pumps actively running in the Production Simulator"
        )

    # ── Simulator availability warning ──────────────────────────────────────
    simulators = st.session_state.get("simulators", {})
    if prod_sim_available and pump_id not in simulators:
        st.warning(
            f"⚠️ No warmed simulator for **{pump_id}**. "
            "Run the Production Simulator for this pump first."
        )
    elif not prod_sim_available:
        st.warning(
            "⚠️ Digital Twin requires the Production Simulator to be running. "
            "Go to **Production Simulator** and run at least one step first."
        )

with col2:
    scenario_name = st.text_input(
        "📝 Scenario Name",
        value=st.session_state['dt_scenario_name'],
        key='dt_scenario_name_input'
    )
    st.session_state['dt_scenario_name'] = scenario_name

with col3:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 Reset All", use_container_width=True):
        st.session_state['dt_sensor_changes']      = []
        st.session_state['dt_maintenance_actions'] = []
        st.session_state['dt_env_changes']         = {}
        st.session_state['dt_baseline_df']         = None
        st.session_state['dt_scenario_df']         = None
        st.session_state['dt_summary']             = None
        st.session_state['dt_last_pump']           = None
        st.session_state['dt_last_run_time']       = None
        st.rerun()

with col4:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.session_state.get('dt_scenario_df') is not None:
        st.download_button(
            label="💾 Download",
            data=st.session_state['dt_scenario_df'].to_csv(index=False),
            file_name=f"{scenario_name}_{pump_id}.csv",
            mime="text/csv",
            key="dt_download_btn"
        )

# ── Live mode info banner ────────────────────────────────────────────────────
if data_source == 'Live Simulation':
    mday = get_current_machine_day()

    st.session_state['dt_auto_refresh'] = st.checkbox(
        "🔄 Auto-refresh when simulation advances",
        value=st.session_state['dt_auto_refresh'],
        key='dt_auto_refresh_check',
        help="Automatically re-run scenario when Production Simulator advances"
    )

    st.info(
        f"🔴 **LIVE MODE** – Step {mday['step_idx']} × {mday['step_hours']}h = "
        f"**Day {mday['machine_days_int']}** (Production Simulator)"
    )

st.markdown("---")

# ===== MAIN LAYOUT =====
left_col, right_col = st.columns([1, 2])

# ─────────────────────────────────────────────────────────────────────────────
# LEFT PANEL — SCENARIO BUILDER
# ─────────────────────────────────────────────────────────────────────────────
with left_col:
    st.subheader("⚙️ Scenario Builder")

    # === SENSOR CHANGES ===
    with st.expander("📊 Sensor Changes", expanded=True):
        st.markdown("**Modify sensor values from a specific day**")

        sensor_to_change = st.selectbox(
            "Sensor",
            options=SENSOR_COLS_STD,
            format_func=lambda x: x.replace('_', ' ').title(),
            key='dt_sensor_select'
        )

        col_a, col_b = st.columns(2)
        with col_a:
            from_day = st.number_input(
                "From Day", min_value=0, max_value=180,
                value=10, step=10, key='dt_from_day_input'
            )
        with col_b:
            change_type = st.selectbox(
                "Change Type",
                options=['add', 'multiply', 'set'],
                key='dt_change_type_select'
            )

        if change_type == 'add':
            change_value = st.number_input("Add Value",   value=5.0,  step=0.5,          key='dt_change_value_add')
        elif change_type == 'multiply':
            change_value = st.number_input("Multiply By", value=1.2,  step=0.1, min_value=0.1, key='dt_change_value_mult')
        else:
            change_value = st.number_input("Set To",      value=50.0, step=1.0,           key='dt_change_value_set')

        if st.button("➕ Add Sensor Change", use_container_width=True, key='dt_add_sensor_btn'):
            st.session_state['dt_sensor_changes'].append({
                'sensor':      sensor_to_change,
                'from_day':    from_day,
                'change_type': change_type,
                'value':       change_value
            })
            st.success(f"Added: {sensor_to_change} from day {from_day}")
            st.rerun()

        if st.session_state['dt_sensor_changes']:
            st.markdown("**Active Sensor Changes:**")
            for idx, change in enumerate(st.session_state['dt_sensor_changes']):
                c1, c2 = st.columns([5, 1])
                with c1:
                    st.markdown(
                        f"`{idx+1}.` {change['sensor'].replace('_',' ').title()} "
                        f"(Day {change['from_day']}): **{change['change_type']}** {change['value']}"
                    )
                with c2:
                    if st.button("❌", key=f"dt_del_s_{idx}_{change['from_day']}_{change['sensor']}"):
                        st.session_state['dt_sensor_changes'].pop(idx)
                        st.rerun()

    # === MAINTENANCE ACTIONS ===
    with st.expander("🔧 Maintenance Actions", expanded=True):
        st.markdown("**Schedule maintenance interventions**")
        st.info("💡 Charts show Baseline (no maintenance) vs Scenario (with maintenance)")

        action_type = st.selectbox(
            "Action Type",
            options=['bearing_replacement', 'seal_replacement', 'derate_pump'],
            format_func=lambda x: x.replace('_', ' ').title(),
            key='dt_action_type_select'
        )
        action_day = st.number_input(
            "At Day", min_value=0, max_value=180,
            value=40, step=10, key='dt_action_day_input'
        )

        if st.button("➕ Add Maintenance", use_container_width=True, key='dt_add_maint_btn'):
            st.session_state['dt_maintenance_actions'].append({
                'action_type': action_type,
                'day':         action_day,
                'effect':      'reset_degradation'
            })
            st.success(f"Added: {action_type.replace('_', ' ').title()} at day {action_day}")
            st.rerun()

        if st.session_state['dt_maintenance_actions']:
            st.markdown("**Scheduled Actions:**")
            for idx, action in enumerate(st.session_state['dt_maintenance_actions']):
                c1, c2 = st.columns([5, 1])
                with c1:
                    st.markdown(
                        f"`{idx+1}.` {action['action_type'].replace('_',' ').title()} "
                        f"@ **Day {action['day']}**"
                    )
                with c2:
                    if st.button("❌", key=f"dt_del_m_{idx}_{action['day']}_{action['action_type']}"):
                        st.session_state['dt_maintenance_actions'].pop(idx)
                        st.rerun()

    # === ENVIRONMENT CONDITIONS ===
    with st.expander("🌡️ Environment Conditions"):
        st.markdown("**Simulate environmental changes**")
        saved_env = st.session_state['dt_env_changes']

        ambient_temp_delta = st.slider(
            "Ambient Temperature Change (°C)",
            min_value=-30, max_value=30,
            value=saved_env.get('ambient_temp_delta', 0), step=5,
            help="Winter: -15°C | Summer: +10°C",
            key='dt_ambient_temp_slider'
        )
        fluid_viscosity = st.slider(
            "Fluid Viscosity Factor",
            min_value=0.5, max_value=2.0,
            value=float(saved_env.get('fluid_viscosity_factor', 1.0)), step=0.1,
            help="Cold weather: 1.3x | Thin fluid: 0.8x",
            key='dt_viscosity_slider'
        )
        load_factor = st.slider(
            "Load Factor",
            min_value=0.5, max_value=1.2,
            value=float(saved_env.get('load_factor', 1.0)), step=0.05,
            help="Reduced load: 0.85 | High load: 1.15",
            key='dt_load_slider'
        )

        st.session_state['dt_env_changes'] = {
            'ambient_temp_delta':     ambient_temp_delta,
            'fluid_viscosity_factor': fluid_viscosity,
            'load_factor':            load_factor
        }

    # === RUN BUTTON ===
    st.markdown("---")
    if st.button("▶️ Run Simulation", type="primary", use_container_width=True, key='dt_run_btn'):
        with st.spinner("Running digital twin simulation..."):
            use_live    = (data_source == 'Live Simulation')
            current_day = float(get_current_machine_day()["machine_days"]) if use_live else 0.0

            try:
                baseline_df, scenario_df, summary = run_scenario(
                    pump_id             = pump_id,
                    sensor_changes      = st.session_state.get('dt_sensor_changes',      []),
                    maintenance_actions = st.session_state.get('dt_maintenance_actions', []),
                    env_changes         = st.session_state.get('dt_env_changes',         {}),
                    use_live_data       = use_live,
                    current_day         = current_day,
                )

                st.session_state['dt_baseline_df']   = baseline_df
                st.session_state['dt_scenario_df']   = scenario_df
                st.session_state['dt_summary']       = summary
                st.session_state['dt_last_pump']     = pump_id
                st.session_state['dt_last_run_time'] = datetime.now()

                st.success("✅ Simulation complete!")
                st.rerun()

            except Exception as e:
                st.error(f"❌ Simulation failed: {str(e)}")
                st.exception(e)

# ─────────────────────────────────────────────────────────────────────────────
# RIGHT PANEL — RESULTS
# ─────────────────────────────────────────────────────────────────────────────
with right_col:
    if st.session_state['dt_scenario_df'] is not None:

        baseline_df = st.session_state['dt_baseline_df']
        scenario_df = st.session_state['dt_scenario_df']
        summary     = st.session_state['dt_summary']
        last_run_dt = st.session_state.get('dt_last_run_time')

        # ── Timestamp badge ──────────────────────────────────────────────────
        if data_source == 'Live Simulation':
            sim_log = st.session_state.get("sim_log_df")
            if sim_log is not None and not sim_log.empty:
                pump_log = sim_log[sim_log["machine_id"] == pump_id]
                ts_str = (
                    pd.to_datetime(pump_log["timestamp"].max()).strftime("%Y-%m-%d %H:%M:%S")
                    if not pump_log.empty
                    else (last_run_dt.strftime("%Y-%m-%d %H:%M:%S") if last_run_dt else "—")
                )
            else:
                ts_str = last_run_dt.strftime("%Y-%m-%d %H:%M:%S") if last_run_dt else "—"

            st.markdown(
                f'### 📈 Simulation Results '
                f'<span class="timestamp-badge">'
                f'<span class="live-indicator"></span>🕒 {ts_str}</span>',
                unsafe_allow_html=True
            )
        else:
            if last_run_dt:
                ts_str = last_run_dt.strftime("%Y-%m-%d %H:%M:%S")
                st.markdown(
                    f'### 📈 Simulation Results '
                    f'<span class="timestamp-badge">🕒 Last run: {ts_str}</span>',
                    unsafe_allow_html=True
                )
            else:
                st.subheader("📈 Simulation Results")

        # ── Stale result warning ─────────────────────────────────────────────
        if st.session_state.get('dt_last_pump') != pump_id:
            st.warning(
                f"⚠️ Showing results for **{st.session_state.get('dt_last_pump')}**. "
                f"Click **Run Simulation** to update for **{pump_id}**."
            )

        # ── Summary metrics ──────────────────────────────────────────────────
        m1, m2, m3, m4 = st.columns(4)

        with m1:
            label      = "Projected Failure" if summary.get('is_live') else "Failure Day"
            delta_days = int(summary['scenario_failure_day'] - summary['baseline_failure_day'])
            st.metric(
                label,
                f"Day {int(summary['scenario_failure_day'])}",
                delta=f"{delta_days:+d} days vs baseline",
                help="Day when risk ≥ 90 or health reaches Failure"
            )
        with m2:
            delta_risk = summary['scenario_avg_risk'] - summary['baseline_avg_risk']
            st.metric(
                "Avg Risk",
                f"{summary['scenario_avg_risk']:.1f}/100",
                delta=f"{delta_risk:+.1f} vs baseline",
                delta_color="inverse"
            )
        with m3:
            st.metric("Peak Risk", f"{summary['max_risk']:.1f}/100")

        with m4:
            if summary.get('is_live'):
                mday = get_current_machine_day()
                st.metric(
                    "Starting Day",
                    f"Day {int(summary['current_day'])}",
                    delta=f"Step {mday['step_idx']} × {mday['step_hours']}h",
                    help="Current production simulator machine day"
                )
            else:
                st.metric(
                    "Cycle Length",
                    f"{int(scenario_df['days_in_operation'].max())} days"
                )

        # ── Context banner ───────────────────────────────────────────────────
        has_maintenance = bool(st.session_state['dt_maintenance_actions'])
        has_sensor      = bool(st.session_state['dt_sensor_changes'])
        has_env         = any(
            v != (0 if k == 'ambient_temp_delta' else 1.0)
            for k, v in st.session_state['dt_env_changes'].items()
        )
        if has_maintenance:
            st.info(
                "📊 **Baseline** (dashed red) = Pump continues as-is, no intervention &nbsp;|&nbsp; "
                "**Scenario** (solid green) = Pump after your intervention &nbsp;|&nbsp; "
                "🔵 Vertical lines = Maintenance events &nbsp;|&nbsp; "
                "🔬 See **Before vs After** tab for hourly detail"
            )
        elif has_sensor or has_env:
            st.info(
                "📊 **Baseline** (dashed red) = Original pump state &nbsp;|&nbsp; "
                "**Scenario** (solid green) = With your changes applied"
            )

        st.markdown("---")

        # ── TABS ─────────────────────────────────────────────────────────────
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Risk & RUL", "🌡️ Sensors", "💊 Health State", "🔬 Before vs After"
        ])

        # ── TAB 1: Risk & RUL ─────────────────────────────────────────────────
        with tab1:
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=(
                    "Risk Score – Baseline vs Scenario",
                    "Remaining Useful Life – Baseline vs Scenario"
                ),
                vertical_spacing=0.14
            )

            fig.add_trace(go.Scatter(
                x=baseline_df['days_in_operation'], y=baseline_df['risk_score'],
                name='Baseline (No Changes)',
                line=dict(color='rgba(255,80,80,0.8)', dash='dash', width=2),
                mode='lines'
            ), row=1, col=1)

            fig.add_trace(go.Scatter(
                x=scenario_df['days_in_operation'], y=scenario_df['risk_score'],
                name='Scenario (With Changes)',
                line=dict(color='#10b981', width=3),
                mode='lines'
            ), row=1, col=1)

            fig.add_hline(
                y=90, line_dash="dot", line_color="red",
                annotation_text="Failure Threshold (90)",
                annotation_position="top right",
                row=1, col=1
            )

            for action in st.session_state.get('dt_maintenance_actions', []):
                fig.add_vline(
                    x=action['day'], line_dash="dot", line_color="cyan",
                    annotation_text=f"🔧 {action['action_type'].replace('_',' ').title()}",
                    annotation_position="top left",
                    row=1, col=1
                )

            b_rul = (baseline_df['rul_days']
                     if 'rul_days' in baseline_df.columns
                     else baseline_df.get('remaining_useful_life',
                          baseline_df['days_in_operation'].max() - baseline_df['days_in_operation']))

            s_rul = (scenario_df['rul_days']
                     if 'rul_days' in scenario_df.columns
                     else scenario_df.get('remaining_useful_life',
                          scenario_df['days_in_operation'].max() - scenario_df['days_in_operation']))

            fig.add_trace(go.Scatter(
                x=baseline_df['days_in_operation'], y=b_rul,
                name='Baseline RUL',
                line=dict(color='rgba(255,80,80,0.8)', dash='dash', width=2),
                mode='lines', showlegend=False
            ), row=2, col=1)

            fig.add_trace(go.Scatter(
                x=scenario_df['days_in_operation'], y=s_rul,
                name='Scenario RUL',
                line=dict(color='#10b981', width=3),
                mode='lines', showlegend=False
            ), row=2, col=1)

            for action in st.session_state.get('dt_maintenance_actions', []):
                fig.add_vline(
                    x=action['day'], line_dash="dot",
                    line_color="cyan", row=2, col=1
                )

            fig.update_layout(
                height=700, template='plotly_dark',
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                showlegend=True, hovermode='x unified',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            fig.update_xaxes(title_text="Days in Operation", row=2, col=1)
            fig.update_yaxes(title_text="Risk Score (0–100)", row=1, col=1)
            fig.update_yaxes(title_text="RUL (days)",         row=2, col=1)

            st.plotly_chart(fig, use_container_width=True, key="dt_chart_risk_rul")

        # ── TAB 2: Sensors ────────────────────────────────────────────────────
        with tab2:
            sensors_to_plot = [
                ('bearing_temperature_c',  'Bearing Temperature (°C)'),
                ('radial_vibration_mm_s',  'Radial Vibration (mm/s)'),
                ('discharge_pressure_bar', 'Discharge Pressure (bar)'),
                ('power_consumption_kw',   'Power Consumption (kW)')
            ]

            fig2 = make_subplots(
                rows=2, cols=2,
                subplot_titles=[name for _, name in sensors_to_plot],
                vertical_spacing=0.15, horizontal_spacing=0.10
            )

            for idx, (sensor, _) in enumerate(sensors_to_plot):
                row = idx // 2 + 1
                col = idx % 2 + 1

                if sensor not in baseline_df.columns or sensor not in scenario_df.columns:
                    continue

                fig2.add_trace(go.Scatter(
                    x=baseline_df['days_in_operation'], y=baseline_df[sensor],
                    name='Baseline', showlegend=(idx == 0),
                    line=dict(color='rgba(255,80,80,0.8)', dash='dash', width=2),
                    mode='lines'
                ), row=row, col=col)

                fig2.add_trace(go.Scatter(
                    x=scenario_df['days_in_operation'], y=scenario_df[sensor],
                    name='Scenario', showlegend=(idx == 0),
                    line=dict(color='#10b981', width=2),
                    mode='lines'
                ), row=row, col=col)

                for action in st.session_state.get('dt_maintenance_actions', []):
                    fig2.add_vline(
                        x=action['day'], line_dash="dot",
                        line_color="cyan", line_width=1,
                        row=row, col=col
                    )

            fig2.update_layout(
                height=620, template='plotly_dark',
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                hovermode='x unified',
                legend=dict(orientation="h", yanchor="top", y=-0.08, xanchor="center", x=0.5)
            )
            fig2.update_xaxes(title_text="Days", row=2, col=1)
            fig2.update_xaxes(title_text="Days", row=2, col=2)

            st.plotly_chart(fig2, use_container_width=True, key="dt_chart_sensors")

        # ── TAB 3: Health State ───────────────────────────────────────────────
        with tab3:
            health_colors = {
                'Healthy':   '#10b981',
                'Degrading': '#f59e0b',
                'Critical':  '#ef4444',
                'Failure':   '#7f1d1d'
            }

            health_col = (
                'health_label'     if 'health_label'     in scenario_df.columns else
                'predicted_health' if 'predicted_health' in scenario_df.columns else
                None
            )

            if health_col:
                col_base, col_scen = st.columns(2)

                def _health_bar(df, title, chart_key):
                    hc = df[health_col].value_counts()
                    fig_h = go.Figure(go.Bar(
                        x=hc.index, y=hc.values,
                        marker_color=[health_colors.get(h, 'gray') for h in hc.index],
                        text=hc.values, textposition='auto'
                    ))
                    fig_h.update_layout(
                        xaxis_title="Health State", yaxis_title="Steps",
                        height=320, template='plotly_dark',
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        showlegend=False
                    )
                    st.markdown(f"#### {title}")
                    st.plotly_chart(fig_h, use_container_width=True, key=chart_key)
                    return hc

                with col_base:
                    hc_base = _health_bar(
                        baseline_df, "📉 Baseline (No Maintenance)",
                        "dt_chart_health_base"
                    )
                with col_scen:
                    hc_scen = _health_bar(
                        scenario_df, "📈 Scenario (With Changes)",
                        "dt_chart_health_scen"
                    )

                st.markdown("#### Health State Comparison")
                all_states = ['Healthy', 'Degrading', 'Critical', 'Failure']
                st.dataframe(
                    pd.DataFrame([{
                        'State':            state,
                        'Baseline (steps)': int(hc_base.get(state, 0)),
                        'Scenario (steps)': int(hc_scen.get(state, 0)),
                        'Change':           int(hc_scen.get(state, 0)) - int(hc_base.get(state, 0))
                    } for state in all_states]),
                    use_container_width=True, hide_index=True
                )
            else:
                st.info(
                    "Health state predictions not available. "
                    "Run the Production Simulator first for accurate predictions."
                )

        # ── TAB 4: Before vs After Comparison Table ───────────────────────────
        with tab4:
            st.markdown("### 🔬 Hourly Before vs After Comparison")
            st.caption(
                "Shows hour-by-hour readings in a window around the maintenance event. "
                "Red baseline = pump with no intervention. Green scenario = pump after maintenance."
            )

            has_maintenance = bool(st.session_state['dt_maintenance_actions'])

            if not has_maintenance:
                st.info(
                    "💡 Add a **Maintenance Action** (e.g. Bearing Replacement at Day 40) "
                    "in the left panel, then run the simulation. "
                    "This table will show hourly readings **before and after** the intervention — "
                    "so you can see exactly how much the bearing replacement improves "
                    "Health, RUL, Risk and all 8 sensor values."
                )
            else:
                action_days = [a['day'] for a in st.session_state['dt_maintenance_actions']]
                anchor      = min(action_days)

                col_w1, col_w2 = st.columns(2)
                with col_w1:
                    days_before = st.number_input(
                        "Days to show BEFORE maintenance",
                        min_value=1, max_value=30,
                        value=5, step=1, key='dt_window_before'
                    )
                with col_w2:
                    days_after = st.number_input(
                        "Days to show AFTER maintenance",
                        min_value=1, max_value=60,
                        value=15, step=1, key='dt_window_after'
                    )

                st.info(
                    f"📅 Window: **Day {anchor - days_before:.0f} → Day {anchor + days_after:.0f}** "
                    f"· Maintenance event at **Day {anchor:.0f}** · "
                    f"Total: **{int(days_before + days_after) * 24} hourly rows**"
                )

                run_table = st.button(
                    "🔬 Generate Hourly Comparison Table",
                    use_container_width=True,
                    key='dt_run_compare_btn',
                    type="primary"
                )

                if run_table:
                    with st.spinner(
                        f"Running hourly forks for {int((days_before + days_after) * 24)} rows... "
                        "this may take 10–20 seconds."
                    ):
                        try:
                            compare_df = run_hourly_comparison(
                                pump_id             = st.session_state.get('dt_last_pump', pump_id),
                                maintenance_actions = st.session_state['dt_maintenance_actions'],
                                sensor_changes      = st.session_state.get('dt_sensor_changes', []),
                                env_changes         = st.session_state.get('dt_env_changes', {}),
                                use_live_data       = (data_source == 'Live Simulation'),
                                window_days_before  = float(days_before),
                                window_days_after   = float(days_after),
                            )
                            st.session_state['dt_compare_df'] = compare_df
                        except Exception as e:
                            st.error(f"❌ Could not generate comparison table: {str(e)}")
                            st.exception(e)
                            st.session_state['dt_compare_df'] = None

                # Show cached table (survives reruns without re-running)
                compare_df = st.session_state.get('dt_compare_df')

                if compare_df is not None and not compare_df.empty:

                    # ── Impact summary at the maintenance point ──────────────
                    maint_rows = compare_df[compare_df['Event'] == '🔧 MAINTENANCE']
                    if not maint_rows.empty:
                        st.markdown("#### 📊 Impact at Maintenance Point")
                        mi = maint_rows.iloc[0]
                        c1, c2, c3, c4 = st.columns(4)
                        with c1:
                            st.metric(
                                "Health Before → After",
                                mi['Health (Scenario)'],
                                delta=f"was {mi['Health (Baseline)']}"
                            )
                        with c2:
                            try:
                                rb = float(mi['RUL Baseline (days)'])
                                rs = float(mi['RUL Scenario (days)'])
                                st.metric(
                                    "RUL at Maintenance",
                                    f"{rs:.1f} days",
                                    delta=f"+{rs - rb:.1f} days vs baseline"
                                )
                            except Exception:
                                st.metric("RUL Scenario", mi.get('RUL Scenario (days)', '—'))
                        with c3:
                            try:
                                st.metric(
                                    "Risk at Maintenance",
                                    f"{int(mi['Risk (Scenario)'])}/100",
                                    delta=f"{int(mi['Risk (Scenario)']) - int(mi['Risk (Baseline)'])}/100 vs baseline",
                                    delta_color="inverse"
                                )
                            except Exception:
                                st.metric("Risk (Scenario)", mi.get('Risk (Scenario)', '—'))
                        with c4:
                            try:
                                # Look at the last row to show end-of-window impact
                                last_b = float(compare_df['Risk (Baseline)'].iloc[-1])
                                last_s = float(compare_df['Risk (Scenario)'].iloc[-1])
                                st.metric(
                                    f"Risk at Day {anchor + days_after:.0f}",
                                    f"{int(last_s)}/100",
                                    delta=f"{int(last_s) - int(last_b)}/100 vs baseline",
                                    delta_color="inverse"
                                )
                            except Exception:
                                pass

                    st.markdown("---")

                    # ── Full hourly table ────────────────────────────────────
                    st.markdown("#### 📋 Hour-by-Hour Detail")
                    st.caption(
                        "🔴 Baseline columns = no maintenance &nbsp;|&nbsp; "
                        "🟢 Scenario columns = with maintenance &nbsp;|&nbsp; "
                        "🔧 Highlighted row = maintenance event"
                    )

                    def _highlight_maint(row):
                        if row.get('Event', '') == '🔧 MAINTENANCE':
                            return ['background-color: rgba(99,255,132,0.15)'] * len(row)
                        return [''] * len(row)

                    st.dataframe(
                        compare_df.style.apply(_highlight_maint, axis=1),
                        use_container_width=True,
                        height=520
                    )

                    st.download_button(
                        label="⬇️ Download Hourly Comparison CSV",
                        data=compare_df.to_csv(index=False),
                        file_name=f"hourly_comparison_{pump_id}_day{anchor:.0f}.csv",
                        mime="text/csv",
                        key="dt_download_compare"
                    )

                elif compare_df is not None and compare_df.empty:
                    st.warning(
                        "⚠️ No hourly data returned for this window. "
                        "Try increasing the 'Days after maintenance' window, "
                        "or check that the maintenance day is within the pump's data range."
                    )

    else:
        # ── Empty state ───────────────────────────────────────────────────────
        st.info("👈 Configure your scenario in the left panel, then click **▶️ Run Simulation**")
        st.markdown("---")
        st.markdown("""
        ### How it works

        1. **Pick a data source**
           - **Synthetic Dataset** → replays full pump lifecycle from Day 0 through the ML pipeline
           - **Live Simulation** → continues from current Production Simulator position (today → future)

        2. **Select a pump** and give your scenario a name

        3. **Build your scenario** using any combination of:
           - Sensor changes (e.g. +5°C bearing temp from day 60)
           - Maintenance actions (bearing replacement, seal replacement, etc.)
           - Environment conditions (winter, high load, viscous fluid)

        4. **Run Simulation** to compare trends

        5. Open **🔬 Before vs After** tab to see the hourly detail table

        ---

        ### Reading the charts

        | Line | Meaning |
        |------|---------|
        | 🔴 Dashed red    | **Baseline** – pump continues as-is, no intervention |
        | 🟢 Solid green   | **Scenario** – pump after your intervention on the chosen day |
        | 🔵 Vertical cyan | Maintenance event (bearing replacement, seal, etc.) |

        ### Before vs After Tab

        | Column | Meaning |
        |--------|---------|
        | Health / RUL / Risk (Baseline) | What would happen with NO maintenance |
        | Health / RUL / Risk (Scenario) | What happens WITH your maintenance action |
        | 8 sensor columns | Sensor readings under scenario conditions |
        | 🔧 MAINTENANCE row | The exact hour the intervention fires |

        **Example:** Add Bearing Replacement at Day 40 →
        the green scenario line will show lower vibration and temperature
        AFTER Day 40. The Before vs After table shows you hour by hour
        exactly how much RUL increased and risk dropped.
        """)

st.markdown("---")

# ===== AI ASSISTANT =====
st.markdown("## 🤖 AI Scenario Assistant")
st.markdown("*Ask AI to help build scenarios or interpret your results*")

lm_studio_url       = "http://localhost:1234/v1"
lm_studio_available = False
available_models    = []

try:
    import requests
    r = requests.get(lm_studio_url.replace('/v1', '/v1/models'), timeout=2)
    if r.status_code == 200:
        models = r.json().get('data', [])
        if models:
            lm_studio_available = True
            available_models    = [m.get('id', 'Unknown') for m in models]
except Exception:
    pass

if lm_studio_available:
    selected_model = available_models[0]
    client = OpenAI(base_url=lm_studio_url, api_key="not-needed")

    st.success(f"✅ Connected to LM Studio – Model: `{selected_model}`")

    for msg in st.session_state["dt_ai_chat_history"]:
        with st.chat_message("user"):
            st.write(msg["question"])
        with st.chat_message("assistant"):
            st.write(msg["answer"])

    user_question = st.chat_input(
        "Ask AI… (e.g. 'Simulate winter conditions', 'What if bearing fails at day 60?')",
        key="dt_chat_input"
    )

    if user_question:
        with st.spinner("AI thinking..."):
            mday = get_current_machine_day()
            ctx  = {
                "pump":           pump_id,
                "data_source":    data_source,
                "sensor_changes": st.session_state.get('dt_sensor_changes', []),
                "maintenance":    st.session_state.get('dt_maintenance_actions', []),
                "environment":    st.session_state.get('dt_env_changes', {}),
                "has_results":    st.session_state.get('dt_scenario_df') is not None,
                "machine_day":    mday["machine_days_int"],
                "step_idx":       mday["step_idx"],
                "step_hours":     mday["step_hours"],
            }

            if ctx["has_results"] and st.session_state['dt_summary']:
                s = st.session_state['dt_summary']
                ctx["results"] = {
                    "failure_day":   s['scenario_failure_day'],
                    "avg_risk":      s['scenario_avg_risk'],
                    "max_risk":      s['max_risk'],
                    "rul_extension": s['rul_extension'],
                    "is_live":       s.get('is_live', False),
                    "current_day":   s.get('current_day', 0),
                }

            system_prompt = """You are an expert pump maintenance engineer helping with digital twin scenario planning.
Output ONLY the final answer. Do NOT show reasoning or thinking tags.

Available sensors: radial_vibration_mm_s, axial_vibration_mm_s, high_freq_vibration_g,
bearing_temperature_c, casing_temperature_c, discharge_pressure_bar, power_consumption_kw, acoustic_emission_db

Maintenance actions: bearing_replacement, seal_replacement, derate_pump

Environment sliders: ambient_temp_delta (-30 to +30), fluid_viscosity_factor (0.5 to 2.0), load_factor (0.5 to 1.2)

Risk score is 0-100 (NOT a percentage). Higher = worse.
RUL = Remaining Useful Life in days.

IMPORTANT: machine_day = step_idx × step_hours ÷ 24. Never use step_idx directly as days."""

            try:
                resp = client.chat.completions.create(
                    model=selected_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": f"Config: {ctx}\n\nQuestion: {user_question}"}
                    ],
                    temperature=0.5,
                    max_tokens=800
                )
                answer = resp.choices[0].message.content
                if "</think>" in answer:
                    answer = answer.split("</think>")[-1].strip()
                answer = answer.replace("<think>", "").replace("</think>", "").strip()
            except Exception as e:
                answer = f"Error: {str(e)}"

        st.session_state["dt_ai_chat_history"].append({
            "question":  user_question,
            "answer":    answer,
            "timestamp": datetime.now()
        })
        st.rerun()

    if st.session_state["dt_ai_chat_history"]:
        if st.button("🗑️ Clear Chat", key="dt_clear_chat"):
            st.session_state["dt_ai_chat_history"] = []
            st.rerun()

else:
    with st.expander("🤖 AI Assistant (Setup Required)", expanded=False):
        st.warning("⚠️ LM Studio not detected on port 1234")
        st.markdown("""
        **Quick Setup:**
        1. Download [LM Studio](https://lmstudio.ai)
        2. Download a model (Qwen 2.5 14B recommended)
        3. Load model → go to **Local Server** tab → Start server
        4. Refresh this page
        """)
        if st.button("🔄 Retry Connection", key="dt_retry_conn"):
            st.rerun()

st.markdown("---")
st.caption(
    "💡 Baseline (dashed red) = no intervention &nbsp;|&nbsp; "
    "Scenario (solid green) = with your changes &nbsp;|&nbsp; "
    "Risk Score is 0–100 (not a percentage)"
)

# ===== AUTO-REFRESH (MUST BE LAST) =====
if should_auto_refresh():
    if data_source == 'Live Simulation' and st.session_state.get('dt_auto_refresh', False):
        time.sleep(2.0)
        st.rerun()
