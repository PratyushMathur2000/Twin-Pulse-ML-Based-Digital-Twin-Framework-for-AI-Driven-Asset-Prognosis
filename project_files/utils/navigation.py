"""
Horizontal tab navigation system - OPTIMIZED FOR SPEED
"""
import streamlit as st
from utils.themes import get_current_theme, THEMES

# ===== PROFESSIONAL GRADIENT DEFINITIONS =====
NAV_GRADIENTS = {
    "Orange": "linear-gradient(135deg, #f97316 0%, #ea580c 100%)",
    "Blue": "linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)",
    "Purple": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
    "Green": "linear-gradient(135deg, #10b981 0%, #047857 100%)",
    "Teal": "linear-gradient(135deg, #14b8a6 0%, #0f766e 100%)",
    "Red": "linear-gradient(135deg, #ef4444 0%, #b91c1c 100%)"
}

@st.cache_data
def get_navigation_css(theme_name: str):
    """Cache CSS per theme to update when theme changes"""
    theme = THEMES[theme_name]
    nav_gradient = NAV_GRADIENTS.get(theme_name, NAV_GRADIENTS["Purple"])
    
    return f"""
    <style>
        /* ========== HIDE DEFAULT STREAMLIT UI ========== */
        section[data-testid="stSidebar"] {{
            display: none !important;
        }}
        
        header[data-testid="stHeader"] {{
            display: none !important;
        }}
        
        .main .block-container {{
            padding-top: 1rem !important;
        }}
        
        /* ========== HORIZONTAL TAB NAVIGATION ========== */
        .stHorizontalBlock {{
            gap: 6px !important;
            background: rgba(255, 255, 255, 0.08) !important;
            backdrop-filter: blur(20px) !important;
            padding: 14px !important;
            border-radius: 12px !important;
            box-shadow: 0 4px 16px rgba(0,0,0,0.3) !important;
            margin-bottom: 8px !important;
            border: 1px solid rgba(255, 255, 255, 0.15) !important;
        }}
        
        div[data-testid="column"] {{
            padding: 0 2px !important;
        }}
        
        /* Reset ALL buttons first */
        div[data-testid="column"] button {{
            border-radius: 10px !important;
            font-weight: 500 !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            padding: 14px 18px !important;
            border: none !important;
            font-size: 15px !important;
        }}
        
        /* Inactive tabs (secondary type) */
        div[data-testid="column"] button[kind="secondary"] {{
            background-color: transparent !important;
            color: #cbd5e1 !important;
        }}
        
        div[data-testid="column"] button[kind="secondary"]:hover {{
            background: rgba(255, 255, 255, 0.1) !important;
            color: #ffffff !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2) !important;
        }}
        
        /* ========== ACTIVE TAB WITH GRADIENT ========== */
        button[kind="primary"],
        button[type="primary"],
        div[data-testid="column"] button[kind="primary"],
        div[data-testid="column"] button[data-baseweb="button"][kind="primary"],
        .stButton > button[kind="primary"] {{
            background: {nav_gradient} !important;
            background-color: transparent !important;
            background-image: {nav_gradient} !important;
            color: #ffffff !important;
            font-weight: 600 !important;
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4) !important;
            transform: translateY(-3px) scale(1.02) !important;
            border: none !important;
        }}
        
        /* Disabled primary buttons (active tab when disabled) */
        button[kind="primary"]:disabled,
        button[kind="primary"][disabled],
        div[data-testid="column"] button[kind="primary"]:disabled,
        div[data-testid="column"] button[kind="primary"][disabled],
        div[data-testid="column"] button[disabled] {{
            background: {nav_gradient} !important;
            background-color: transparent !important;
            background-image: {nav_gradient} !important;
            color: #ffffff !important;
            font-weight: 600 !important;
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4) !important;
            transform: translateY(-3px) scale(1.02) !important;
            opacity: 1 !important;
            cursor: default !important;
            border: none !important;
        }}
        
        /* Force white text in ALL primary/disabled buttons */
        button[kind="primary"] p,
        button[kind="primary"] span,
        button[kind="primary"]:disabled p,
        button[kind="primary"]:disabled span,
        button[disabled] p,
        button[disabled] span,
        div[data-testid="column"] button[kind="primary"] p,
        div[data-testid="column"] button[disabled] p {{
            color: #ffffff !important;
            opacity: 1 !important;
            font-weight: 600 !important;
        }}
        
        /* Smooth gradient animation on hover for active tab */
        button[kind="primary"]:not(:disabled):hover,
        div[data-testid="column"] button[kind="primary"]:not(:disabled):hover {{
            box-shadow: 0 8px 24px rgba(102, 126, 234, 0.5) !important;
            transform: translateY(-4px) scale(1.03) !important;
        }}
    </style>
    """

def render_horizontal_navigation():
    """Render horizontal tab navigation - OPTIMIZED VERSION"""
    
    pages = {
        "Home": {"icon": "🏠", "file": "App.py"},
        "Simulator": {"icon": "⚙️", "file": "pages/0_Production_Simulator.py"},
        "Fleet Overview": {"icon": "🚀", "file": "pages/1_Fleet_Overview.py"},
        "Detailed View": {"icon": "🔍", "file": "pages/2_Detailed_View.py"},
        "Sensor Trend": {"icon": "📈", "file": "pages/4_Sensor_Trend.py"},
        "Digital Twin": {"icon": "🔮", "file": "pages/3_Digital_Twin_Sandbox.py"},
        "AI Diagnostic": {"icon": "🤖", "file": "pages/5_AI_Diagnostic_Agent.py"},
        "Settings": {"icon": "⚙️", "file": "pages/6_Settings.py"}
    }
    
    current_page = st.session_state.get("current_page", "Home")
    current_theme = get_current_theme()
    
    st.markdown(get_navigation_css(current_theme), unsafe_allow_html=True)
    
    cols = st.columns(len(pages))
    for idx, (page_name, page_info) in enumerate(pages.items()):
        with cols[idx]:
            is_current = (page_name == current_page)
            
            if st.button(
                f"{page_info['icon']} {page_name}",
                key=f"nav_{page_name}",
                use_container_width=True,
                disabled=is_current,
                type="primary" if is_current else "secondary"
            ):
                st.session_state["current_page"] = page_name
                st.switch_page(page_info["file"])


def should_auto_refresh():
    """Check if auto-refresh should happen"""
    return st.session_state.get("sim_autoplay", False)

def clear_transition_flag():
    """Placeholder for compatibility"""
    pass
