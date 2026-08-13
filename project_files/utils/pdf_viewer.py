import base64
import os
import streamlit as st
import streamlit.components.v1 as components

def render_pdf_horizontal(pdf_path):
    """Render PDF using native browser PDF viewer - no Poppler needed"""
    if not os.path.exists(pdf_path):
        st.info("📄 Presentation file not found.")
        return
    
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    
    b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
    
    st.markdown("""
        <div style="text-align: center; margin-bottom: 20px;">
            <h2 style="color: #ffffff; margin-bottom: 5px;">📊 Project Presentation</h2>
            <p style="color: #888888; font-style: italic;">Predict before failure. Perform without interruption.</p>
        </div>
    """, unsafe_allow_html=True)
    
    pdf_display_html = f"""
    <div style="background-color: rgba(20, 20, 20, 0.6); padding: 20px; border-radius: 16px; border: 1px solid rgba(255,255,255,0.1); backdrop-filter: blur(10px);">
        <iframe src="data:application/pdf;base64,{b64_pdf}" 
                width="100%" height="750" 
                style="border: none; border-radius: 8px;"
                type="application/pdf">
        </iframe>
    </div>
    """
    
    components.html(pdf_display_html, height=800, scrolling=False)
