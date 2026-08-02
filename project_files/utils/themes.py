"""
Centralized theme management for Twin-Pulse Dashboard
Professional color schemes - OPTIMIZED FOR MINIMAL FLICKER
"""

import streamlit as st

# ===== THEME DEFINITIONS =====
THEMES = {
    "Orange": {
        "name": "🟠 Orange Sunset",
        "primary": "#f97316",
        "primary_dark": "#ea580c",
        "primary_darker": "#c2410c",
        "primary_light": "rgba(249, 115, 22, 0.2)",
        "shadow": "rgba(249, 115, 22, 0.3)",
        "gradient": "linear-gradient(135deg, #f97316 0%, #ea580c 100%)",
        "gradient_dark": "linear-gradient(135deg, #ea580c 0%, #c2410c 100%)"
    },
    "Blue": {
        "name": "🔵 Ocean Blue",
        "primary": "#3b82f6",
        "primary_dark": "#2563eb",
        "primary_darker": "#1d4ed8",
        "primary_light": "rgba(59, 130, 246, 0.2)",
        "shadow": "rgba(59, 130, 246, 0.3)",
        "gradient": "linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)",
        "gradient_dark": "linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)"
    },
    "Purple": {
        "name": "🟣 Royal Purple",
        "primary": "#8b5cf6",
        "primary_dark": "#7c3aed",
        "primary_darker": "#6d28d9",
        "primary_light": "rgba(139, 92, 246, 0.2)",
        "shadow": "rgba(139, 92, 246, 0.3)",
        "gradient": "linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)",
        "gradient_dark": "linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%)"
    },
    "Green": {
        "name": "🟢 Forest Green",
        "primary": "#10b981",
        "primary_dark": "#059669",
        "primary_darker": "#047857",
        "primary_light": "rgba(16, 185, 129, 0.2)",
        "shadow": "rgba(16, 185, 129, 0.3)",
        "gradient": "linear-gradient(135deg, #10b981 0%, #059669 100%)",
        "gradient_dark": "linear-gradient(135deg, #059669 0%, #047857 100%)"
    },
    "Teal": {
        "name": "🔷 Modern Teal",
        "primary": "#14b8a6",
        "primary_dark": "#0d9488",
        "primary_darker": "#0f766e",
        "primary_light": "rgba(20, 184, 166, 0.2)",
        "shadow": "rgba(20, 184, 166, 0.3)",
        "gradient": "linear-gradient(135deg, #14b8a6 0%, #0d9488 100%)",
        "gradient_dark": "linear-gradient(135deg, #0d9488 0%, #0f766e 100%)"
    },
    "Red": {
        "name": "🔴 Crimson Red",
        "primary": "#ef4444",
        "primary_dark": "#dc2626",
        "primary_darker": "#b91c1c",
        "primary_light": "rgba(239, 68, 68, 0.2)",
        "shadow": "rgba(239, 68, 68, 0.3)",
        "gradient": "linear-gradient(135deg, #ef4444 0%, #dc2626 100%)",
        "gradient_dark": "linear-gradient(135deg, #dc2626 0%, #b91c1c 100%)"
    }
}

def get_current_theme():
    """Get current theme from session state (Purple as default)"""
    if "app_theme" not in st.session_state:
        st.session_state["app_theme"] = "Purple"
    return st.session_state["app_theme"]


@st.cache_data
def _build_theme_css(theme_name: str):
    """Cache the entire theme CSS string — only rebuilt when theme changes."""
    theme = THEMES[theme_name]
    return f"""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap">
    <style>
        /* ===== BACKGROUND GRADIENT + PCB CIRCUIT PATTERN ===== */
        [data-testid="stAppViewContainer"], .stApp, body {{
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%) !important;
        }}

        /* PCB / Circuit Board overlay */
        [data-testid="stAppViewContainer"]::before {{
            content: "";
            position: fixed;
            inset: 0;
            z-index: 0;
            pointer-events: none;
            opacity: 0.04;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='400'%3E%3Cdefs%3E%3Cstyle%3E line,circle,rect %7B stroke:%23ffffff; fill:none; stroke-width:1; %7D circle.node %7B fill:%23ffffff; stroke:none; %7D%3C/style%3E%3C/defs%3E%3C!-- horizontal traces --%3E%3Cline x1='0' y1='40' x2='120' y2='40'/%3E%3Cline x1='160' y1='40' x2='400' y2='40'/%3E%3Cline x1='0' y1='120' x2='80' y2='120'/%3E%3Cline x1='200' y1='120' x2='400' y2='120'/%3E%3Cline x1='0' y1='200' x2='180' y2='200'/%3E%3Cline x1='220' y1='200' x2='320' y2='200'/%3E%3Cline x1='0' y1='280' x2='100' y2='280'/%3E%3Cline x1='300' y1='280' x2='400' y2='280'/%3E%3Cline x1='0' y1='360' x2='260' y2='360'/%3E%3C!-- vertical traces --%3E%3Cline x1='80' y1='0' x2='80' y2='120'/%3E%3Cline x1='80' y1='160' x2='80' y2='280'/%3E%3Cline x1='200' y1='0' x2='200' y2='80'/%3E%3Cline x1='200' y1='120' x2='200' y2='200'/%3E%3Cline x1='320' y1='200' x2='320' y2='400'/%3E%3Cline x1='160' y1='40' x2='160' y2='120'/%3E%3Cline x1='260' y1='280' x2='260' y2='360'/%3E%3C!-- angled bends --%3E%3Cline x1='120' y1='40' x2='160' y2='80'/%3E%3Cline x1='160' y1='80' x2='160' y2='120'/%3E%3Cline x1='80' y1='280' x2='100' y2='280'/%3E%3Cline x1='100' y1='280' x2='140' y2='320'/%3E%3Cline x1='140' y1='320' x2='260' y2='320'/%3E%3Cline x1='260' y1='320' x2='260' y2='280'/%3E%3Cline x1='260' y1='280' x2='300' y2='280'/%3E%3Cline x1='180' y1='200' x2='220' y2='200'/%3E%3C!-- solder pads / nodes --%3E%3Ccircle class='node' cx='80' cy='120' r='3'/%3E%3Ccircle class='node' cx='200' cy='120' r='3'/%3E%3Ccircle class='node' cx='160' cy='40' r='3'/%3E%3Ccircle class='node' cx='320' cy='200' r='3'/%3E%3Ccircle class='node' cx='260' cy='360' r='3'/%3E%3Ccircle class='node' cx='100' cy='280' r='3'/%3E%3Ccircle class='node' cx='260' cy='280' r='3'/%3E%3Ccircle class='node' cx='140' cy='320' r='3'/%3E%3C!-- IC chip pads --%3E%3Crect x='150' y='150' width='20' height='20' rx='2'/%3E%3Crect x='270' y='70' width='16' height='16' rx='2'/%3E%3Crect x='340' y='310' width='18' height='18' rx='2'/%3E%3C/svg%3E");
            background-repeat: repeat;
            background-size: 400px 400px;
        }}

        /* Ensure content stays above the pattern */
        .main, .main .block-container,
        [data-testid="stVerticalBlock"] {{
            position: relative;
            z-index: 1;
        }}

        .main, .main .block-container {{
            background: transparent !important;
            padding-top: 0 !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            max-width: 100% !important;
            animation: fadeInPage 0.25s ease-out;
        }}

        @keyframes fadeInPage {{
            from {{ opacity: 0; transform: translateY(6px); }}
            to   {{ opacity: 1; transform: translateY(0); }}
        }}

        /* ===== THEME VARIABLES ===== */
        :root {{
            --primary-color: {theme['primary']};
            --primary-dark: {theme['primary_dark']};
            --primary-gradient: {theme['gradient']};
        }}

        /* ===== HIDE STREAMLIT UI ===== */
        .stAppDeployButton, .stStatusWidget, footer, header {{
            display: none !important;
        }}

        /* ===== TYPOGRAPHY ===== */
        html, body, [class*="css"] {{
            font-family: 'Inter', sans-serif;
        }}

        .stApp, .stApp p, .stApp span, .stApp label, .stApp div {{
            color: #f8fafc !important;
        }}

        h1, h2, h3, h4, h5, h6 {{
            color: #ffffff !important;
            font-weight: 600;
        }}

        /* ===== BUTTONS ===== */
        .stButton>button {{
            background: rgba(255, 255, 255, 0.05);
            color: #f8fafc;
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 8px;
            font-weight: 500;
            transition: all 0.2s ease;
        }}

        .stButton>button:hover {{
            border-color: {theme['primary']};
            color: {theme['primary']};
            background: rgba(255, 255, 255, 0.08);
            transform: translateY(-1px);
            box-shadow: 0 2px 8px {theme['shadow']};
        }}

        .stButton>button[kind="primary"] {{
            background: {theme['gradient']} !important;
            color: white !important;
            border: none !important;
        }}

        .stButton>button[kind="primary"]:hover {{
            background: {theme['gradient_dark']} !important;
            box-shadow: 0 4px 12px {theme['shadow']} !important;
        }}

        /* ===== INPUTS ===== */
        .stSelectbox [data-baseweb="select"],
        .stTextInput input,
        .stNumberInput input,
        .stTextArea textarea {{
            background: rgba(255, 255, 255, 0.08) !important;
            color: #f8fafc !important;
            border: 1px solid rgba(255, 255, 255, 0.15) !important;
            border-radius: 8px;
        }}

        /* ===== DROPDOWNS ===== */
        [data-baseweb="menu"] {{
            background: #1e293b !important;
        }}

        [data-baseweb="menu"] li {{
            color: #f8fafc !important;
        }}

        [data-baseweb="menu"] li:hover {{
            background: rgba(255, 255, 255, 0.15) !important;
        }}

        /* ===== TABS ===== */
        .stTabs [data-baseweb="tab-list"] {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 12px;
            gap: 8px;
        }}

        .stTabs [data-baseweb="tab"] {{
            border-radius: 8px;
            padding: 12px 24px;
            color: #cbd5e1;
            transition: all 0.2s ease;
        }}

        .stTabs [data-baseweb="tab"]:hover {{
            background: {theme['primary_light']};
            color: {theme['primary_dark']};
        }}

        .stTabs [data-baseweb="tab"][aria-selected="true"] {{
            background: {theme['gradient']} !important;
            color: white !important;
            box-shadow: 0 2px 8px {theme['shadow']};
        }}

        /* ===== METRICS ===== */
        [data-testid="stMetricValue"] {{
            color: #ffffff !important;
            font-size: 2rem;
            font-weight: 700;
        }}

        [data-testid="stMetricLabel"] {{
            color: #cbd5e1 !important;
        }}

        [data-testid="stMetricDelta"] svg {{
            fill: {theme['primary']} !important;
        }}

        /* ===== DATAFRAMES ===== */
        .stDataFrame {{
            background: rgba(255, 255, 255, 0.05) !important;
            border: 1px solid rgba(255, 255, 255, 0.15) !important;
            border-radius: 8px;
            content-visibility: auto;
        }}

        .stDataFrame table {{
            color: #f8fafc !important;
        }}

        .stDataFrame th {{
            background: rgba(255, 255, 255, 0.1) !important;
            color: #ffffff !important;
        }}

        .stDataFrame td {{
            color: #e2e8f0 !important;
        }}

        /* ===== CARDS ===== */
        [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] {{
            background: rgba(255, 255, 255, 0.05) !important;
            backdrop-filter: blur(20px);
            border-radius: 8px;
            border: 1px solid rgba(255, 255, 255, 0.15);
        }}

        /* ===== PROGRESS BAR ===== */
        .stProgress > div > div {{
            background: rgba(255, 255, 255, 0.1) !important;
            border-radius: 8px;
        }}

        .stProgress > div > div > div {{
            background: {theme['primary']} !important;
        }}

        /* ===== EXPANDERS ===== */
        .streamlit-expanderHeader {{
            background: rgba(255, 255, 255, 0.08) !important;
            color: #f8fafc !important;
            border: 1px solid rgba(255, 255, 255, 0.15) !important;
        }}

        /* ===== MULTISELECT ===== */
        .stMultiSelect [data-baseweb="select"] {{
            background: rgba(255, 255, 255, 0.08) !important;
            color: #f8fafc !important;
            border: 1px solid rgba(255, 255, 255, 0.15) !important;
        }}

        .stMultiSelect [data-baseweb="tag"] {{
            background: rgba(255, 255, 255, 0.15) !important;
            color: #f8fafc !important;
        }}

        /* ===== MISC ===== */
        .stAlert {{
            border-radius: 8px;
            border-left: 4px solid;
        }}

        .stCheckbox input[type="checkbox"]:checked + label::before {{
            background: {theme['primary']} !important;
            border-color: {theme['primary']} !important;
        }}

        .stSpinner > div {{
            border-top-color: {theme['primary']} !important;
        }}

        .stRadio label, .stSlider {{
            color: #f8fafc !important;
        }}

        .stDateInput input {{
            background: rgba(255, 255, 255, 0.08) !important;
            color: #f8fafc !important;
            border: 1px solid rgba(255, 255, 255, 0.15) !important;
        }}

        [data-testid="stFileUploader"] {{
            background: rgba(255, 255, 255, 0.05) !important;
            border: 1px solid rgba(255, 255, 255, 0.15) !important;
        }}

        [data-testid="stSidebar"] {{
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%) !important;
        }}

        .js-plotly-plot .plotly .main-svg {{
            background: transparent !important;
        }}

        /* ===== PERFORMANCE: skip off-screen rendering ===== */
        .js-plotly-plot {{
            content-visibility: auto;
        }}
    </style>
    """


def apply_theme():
    """Apply theme - OPTIMIZED with cached CSS"""
    current_theme = get_current_theme()
    st.markdown(_build_theme_css(current_theme), unsafe_allow_html=True)
