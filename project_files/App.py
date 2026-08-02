import streamlit as st
import os
import zipfile
from pathlib import Path

# Ensure model is unzipped (required for Streamlit Cloud)
MODEL_DIR = Path(__file__).parent / "saved_models"
MODEL_PKL = MODEL_DIR / "health_stage_ensemble.pkl"
MODEL_ZIP = MODEL_DIR / "health_stage_ensemble.zip"

if not MODEL_PKL.exists() and MODEL_ZIP.exists():
    with zipfile.ZipFile(MODEL_ZIP, 'r') as zip_ref:
        zip_ref.extractall(MODEL_DIR)

from utils.themes import apply_theme
from utils.navigation import render_horizontal_navigation
from utils.pdf_viewer import render_pdf_horizontal

st.set_page_config(
    page_title="Twin-Pulse Dashboard",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

apply_theme()
render_horizontal_navigation()

# ===== DISPLAY PDF REPORT IN HORIZONTAL SLIDER =====
render_pdf_horizontal("Presentation.pdf")  # Replace with your actual PDF filename

# ===== DEMO VIDEO PLAYER =====
import os

DEMO_VIDEO = "demo_compressed.mp4"

if os.path.exists(DEMO_VIDEO):
    st.markdown(
        '<div style="text-align:center; margin-top:1.5rem;">'
        '<h2 style="color:#ffffff; font-weight:600; font-size:1.4rem; margin-bottom:4px;">'
        '🎬 Live Dashboard Demo</h2>'
        '<p style="color:rgba(255,255,255,0.5); font-style:italic; font-size:0.95rem;">'
        'Pre-recorded simulator run</p></div>',
        unsafe_allow_html=True
    )
    st.video(DEMO_VIDEO)
else:
    st.markdown(
        '<div style="text-align:center; padding:40px; opacity:0.4;">'
        '<p style="font-size:1.2rem;">🎬 Demo video placeholder</p>'
        '<p style="font-size:0.9rem;">Place <code>demo_compressed.mp4</code> in the Dashboard folder</p>'
        '</div>',
        unsafe_allow_html=True
    )
