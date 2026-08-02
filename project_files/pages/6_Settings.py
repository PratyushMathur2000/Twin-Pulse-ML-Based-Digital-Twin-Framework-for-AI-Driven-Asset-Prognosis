import streamlit as st
from utils.themes import apply_theme, get_current_theme, THEMES  # ← FIXED
from utils.navigation import render_horizontal_navigation

st.set_page_config(
    page_title="Settings",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Set current page BEFORE navigation
st.session_state["current_page"] = "Settings"

apply_theme()

# Custom styling for uniform theme cards
st.markdown("""
<style>
    /* Uniform theme card styling */
    .theme-card-container {
        height: 180px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    
    /* Make theme buttons full width and consistent */
    div[data-testid="column"] button[kind="secondary"] {
        width: 100% !important;
        padding: 0 !important;
        border: none !important;
        background: transparent !important;
    }
    
    div[data-testid="column"] button[kind="secondary"]:hover {
        background: transparent !important;
    }
</style>
""", unsafe_allow_html=True)

# Navigation
render_horizontal_navigation()

# Header
st.title("⚙️ Settings")
st.markdown("*Configure your Twin-Pulse dashboard preferences*")

st.markdown("---")

# ===== THEME SETTINGS =====
st.markdown("## 🎨 Appearance")
st.markdown("### Color Themes")
st.markdown("*Click on a theme to apply it instantly*")

current_theme = get_current_theme()  # ← Now this will work


# Create 3 columns for theme cards (2 rows of 3)
theme_keys = list(THEMES.keys())

# Row 1 (first 3 themes)
col1, col2, col3 = st.columns(3)
cols_row1 = [col1, col2, col3]

for idx in range(3):
    if idx < len(theme_keys):
        key = theme_keys[idx]
        theme = THEMES[key]
        is_current = (key == current_theme)
        
        with cols_row1[idx]:
            # Create clickable theme card
            border = "3px solid #10b981" if is_current else "1px solid #e5e7eb"
            
            # Display the card HTML
            st.markdown(f"""
            <div class="theme-card-container">
                <div style="padding: 20px; border-radius: 12px; border: {border}; 
                            background: {theme['gradient']}; color: white; text-align: center;
                            box-shadow: 0 2px 8px {theme['shadow']}; cursor: pointer;
                            transition: transform 0.2s ease, box-shadow 0.2s ease;
                            height: 160px; display: flex; flex-direction: column; justify-content: center;">
                    <div style="font-size: 32px; margin-bottom: 8px;">{theme['name'].split()[0]}</div>
                    <div style="font-size: 16px; font-weight: 500; margin-bottom: 8px;">
                        {theme['name'].split(' ', 1)[1] if ' ' in theme['name'] else ''}
                    </div>
                    {'<div style="font-size: 14px; font-weight: 600; margin-top: 4px;">✓ Active</div>' if is_current else '<div style="font-size: 14px; opacity: 0.8;">Click to Apply</div>'}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Invisible button overlay for click detection
            if st.button(f"Apply {theme['name']}", key=f"theme_btn_{key}", use_container_width=True, disabled=is_current):
                st.session_state["app_theme"] = key
                st.success(f"✅ Theme changed to {theme['name']}")
                st.rerun()

# Row 2 (next 3 themes)
col4, col5, col6 = st.columns(3)
cols_row2 = [col4, col5, col6]

for idx in range(3, 6):
    if idx < len(theme_keys):
        key = theme_keys[idx]
        theme = THEMES[key]
        is_current = (key == current_theme)
        
        with cols_row2[idx - 3]:
            border = "3px solid #10b981" if is_current else "1px solid #e5e7eb"
            
            st.markdown(f"""
            <div class="theme-card-container">
                <div style="padding: 20px; border-radius: 12px; border: {border}; 
                            background: {theme['gradient']}; color: white; text-align: center;
                            box-shadow: 0 2px 8px {theme['shadow']}; cursor: pointer;
                            transition: transform 0.2s ease, box-shadow 0.2s ease;
                            height: 160px; display: flex; flex-direction: column; justify-content: center;">
                    <div style="font-size: 32px; margin-bottom: 8px;">{theme['name'].split()[0]}</div>
                    <div style="font-size: 16px; font-weight: 500; margin-bottom: 8px;">
                        {theme['name'].split(' ', 1)[1] if ' ' in theme['name'] else ''}
                    </div>
                    {'<div style="font-size: 14px; font-weight: 600; margin-top: 4px;">✓ Active</div>' if is_current else '<div style="font-size: 14px; opacity: 0.8;">Click to Apply</div>'}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button(f"Apply {theme['name']}", key=f"theme_btn_{key}", use_container_width=True, disabled=is_current):
                st.session_state["app_theme"] = key
                st.success(f"✅ Theme changed to {theme['name']}")
                st.rerun()

st.markdown("---")

# ===== DASHBOARD SETTINGS =====
st.markdown("## 📊 Dashboard Settings")

col3, col4 = st.columns(2)

with col3:
    st.markdown("### Auto-Refresh")
    auto_refresh_default = st.checkbox(
        "Enable auto-refresh by default",
        value=st.session_state.get("default_auto_refresh", True),
        help="Automatically refresh pages when simulation advances"
    )
    st.session_state["default_auto_refresh"] = auto_refresh_default
    
    st.markdown("### Simulation")
    show_live_indicator = st.checkbox(
        "Show live indicator",
        value=st.session_state.get("show_live_indicator", True),
        help="Display pulsing indicator when simulation is running"
    )
    st.session_state["show_live_indicator"] = show_live_indicator

with col4:
    st.markdown("### Notifications")
    enable_notifications = st.checkbox(
        "Enable notifications",
        value=st.session_state.get("enable_notifications", False),
        help="Show desktop notifications for critical alerts (coming soon)"
    )
    st.session_state["enable_notifications"] = enable_notifications
    
    st.markdown("### Data Display")
    decimal_places = st.slider(
        "Decimal places for sensor values",
        min_value=1,
        max_value=4,
        value=st.session_state.get("decimal_places", 2),
        help="Number of decimal places to display"
    )
    st.session_state["decimal_places"] = decimal_places

st.markdown("---")

# ===== ABOUT =====
st.markdown("## ℹ️ About")

col5, col6 = st.columns(2)

with col5:
    st.markdown("""
    **Twin-Pulse Dashboard**  
    Version 1.0.0  
    
    A digital twin platform for predictive maintenance and intelligent pump health monitoring.
    
    **Features:**
    - Real-time sensor monitoring
    - AI-powered diagnostics
    - Remaining Useful Life (RUL) predictions
    - Multi-pump fleet management
    """)

with col6:
    st.markdown("""
    **Technology Stack:**
    - Streamlit
    - Python 3.x
    - LM Studio (AI)
    - Plotly (Visualizations)
    
    **Support:**
    - Documentation: [Coming Soon]
    - Issues: [Coming Soon]
    """)

st.markdown("---")

# Reset button
if st.button("🔄 Reset All Settings to Default", type="secondary"):
    st.session_state["app_theme"] = "Orange"
    st.session_state["default_auto_refresh"] = True
    st.session_state["show_live_indicator"] = True
    st.session_state["enable_notifications"] = False
    st.session_state["decimal_places"] = 2
    st.success("✅ Settings reset to default values")
    st.rerun()
