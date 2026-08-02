"""
PDF to Horizontal Slider Converter
Converts PDF pages to images and displays in horizontal navigation
WITH CACHING FOR FASTER LOADING
"""

from pdf2image import convert_from_path
import base64
from io import BytesIO
import streamlit.components.v1 as components
import streamlit as st
import os
import sys

def get_poppler_path():
    """Get poppler path for Windows"""
    # Your specific poppler path
    user_poppler_path = r"C:\Users\mrmat\Downloads\Release-25.12.0-0\poppler-25.12.0\Library\bin"
    
    if os.path.exists(user_poppler_path):
        return user_poppler_path
    
    # Fallback to common paths
    possible_paths = [
        r"C:\Program Files\poppler\Library\bin",
        r"C:\Program Files (x86)\poppler\Library\bin",
        r"C:\poppler\Library\bin",
        r"D:\poppler\Library\bin",
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    # If not found, return None (will use PATH)
    return None

@st.cache_data(show_spinner="Loading presentation...")
def convert_pdf_to_images(pdf_path):
    """Convert PDF to base64 images - CACHED for instant loading"""
    
    # Get poppler path for Windows
    poppler_path = get_poppler_path() if sys.platform == "win32" else None
    
    # Convert PDF pages to images
    if poppler_path:
        pages = convert_from_path(pdf_path, dpi=150, poppler_path=poppler_path)
    else:
        pages = convert_from_path(pdf_path, dpi=150)
    
    # Convert images to base64
    image_b64_list = []
    for page in pages:
        buffered = BytesIO()
        page.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        image_b64_list.append(img_str)
    
    return image_b64_list

def pdf_to_horizontal_slider(pdf_path):
    """Convert PDF to horizontal image slider"""
    
    # Get cached images (only converts once!)
    image_b64_list = convert_pdf_to_images(pdf_path)
    
    # Generate HTML with horizontal scroll
    images_html = ""
    for idx, img_b64 in enumerate(image_b64_list):
        images_html += f'<div class="pdf-slide"><img src="data:image/png;base64,{img_b64}" alt="Page {idx+1}"/></div>'
    
    dots_html = ""
    for idx in range(len(image_b64_list)):
        active = "active" if idx == 0 else ""
        dots_html += f'<div class="dot {active}" onclick="goToSlide({idx})"></div>'
    
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ 
                overflow: hidden; 
                background: transparent;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            }}
            
            .slider-container {{
                display: flex;
                width: {len(image_b64_list) * 100}vw;
                height: calc(100vh - 100px);
                transition: transform 0.8s cubic-bezier(0.77, 0, 0.175, 1);
                margin-top: 20px;
            }}
            
            .pdf-slide {{
                width: 100vw;
                height: calc(100vh - 100px);
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 40px;
                opacity: 0;
                animation: fadeIn 0.5s ease forwards;
            }}
            
            @keyframes fadeIn {{
                to {{ opacity: 1; }}
            }}
            
            .pdf-slide img {{
                max-width: 95%;
                max-height: 95%;
                object-fit: contain;
                border-radius: 12px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.4);
                transition: transform 0.3s ease;
            }}
            
            .pdf-slide img:hover {{
                transform: scale(1.02);
            }}
            
            /* Navigation Dots */
            .nav-dots {{
                position: fixed;
                right: 40px;
                top: 50%;
                transform: translateY(-50%);
                z-index: 1000;
                display: flex;
                flex-direction: column;
                gap: 12px;
            }}
            
            .dot {{
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background: rgba(255, 255, 255, 0.3);
                cursor: pointer;
                transition: all 0.4s cubic-bezier(0.77, 0, 0.175, 1);
            }}
            
            .dot:hover {{
                background: rgba(255, 255, 255, 0.6);
                transform: scale(1.5);
            }}
            
            .dot.active {{
                background: white;
                height: 32px;
                border-radius: 4px;
            }}
            
            /* Navigation Arrows */
            .nav-arrow {{
                position: fixed;
                top: 50%;
                transform: translateY(-50%);
                background: rgba(255, 255, 255, 0.05);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.2);
                color: white;
                font-size: 24px;
                width: 48px;
                height: 48px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                z-index: 1000;
                transition: all 0.3s ease;
                opacity: 0.7;
            }}
            
            .nav-arrow:hover {{
                background: rgba(255, 255, 255, 0.15);
                border-color: rgba(255, 255, 255, 0.5);
                opacity: 1;
                transform: translateY(-50%) scale(1.1);
            }}
            
            .nav-arrow.left {{ left: 30px; }}
            .nav-arrow.right {{ right: 80px; }}
            .nav-arrow.disabled {{
                opacity: 0.2;
                cursor: not-allowed;
                pointer-events: none;
            }}
            
            /* Page Counter */
            .page-counter {{
                position: fixed;
                top: 30px;
                left: 50%;
                transform: translateX(-50%);
                background: rgba(102, 126, 234, 0.15);
                backdrop-filter: blur(20px);
                border: 1px solid rgba(102, 126, 234, 0.3);
                padding: 12px 24px;
                border-radius: 24px;
                color: white;
                font-size: 14px;
                font-weight: 600;
                z-index: 1000;
                letter-spacing: 0.5px;
            }}
            
            /* Scroll Hint */
            .scroll-hint {{
                position: fixed;
                bottom: 40px;
                left: 50%;
                transform: translateX(-50%);
                font-size: 12px;
                opacity: 0.5;
                color: white;
                z-index: 1000;
                text-transform: uppercase;
                letter-spacing: 0.15em;
                animation: pulse 2s infinite;
            }}
            
            @keyframes pulse {{
                0%, 100% {{ opacity: 0.5; }}
                50% {{ opacity: 0.8; }}
            }}

            /* Tagline */
            .tagline {{
                position: fixed;
                bottom: 65px;
                left: 50%;
                transform: translateX(-50%);
                font-size: 1.5rem;
                font-style: italic;
                color: rgba(255, 255, 255, 1);
                z-index: 1000;
                letter-spacing: 0.04em;
                white-space: nowrap;
            }}
        </style>
    </head>
    <body>
        <div class="page-counter" id="pageCounter">Page 1 of {len(image_b64_list)}</div>
        
        <div class="nav-dots">
            {dots_html}
        </div>
        
        <div class="nav-arrow left disabled" onclick="prevSlide()">←</div>
        <div class="nav-arrow right" onclick="nextSlide()">→</div>
        
        <div class="tagline">Predict before failure. Perform without interruption.</div>
        <div class="scroll-hint">USE ARROW KEYS OR SCROLL</div>
        
        <div class="slider-container" id="sliderContainer">
            {images_html}
        </div>
        
        <script>
            let currentSlide = 0;
            const totalSlides = {len(image_b64_list)};
            const container = document.getElementById('sliderContainer');
            const dots = document.querySelectorAll('.dot');
            const leftArrow = document.querySelector('.nav-arrow.left');
            const rightArrow = document.querySelector('.nav-arrow.right');
            const pageCounter = document.getElementById('pageCounter');
            
            function goToSlide(index) {{
                if (index < 0 || index >= totalSlides) return;
                currentSlide = index;
                container.style.transform = `translateX(-${{currentSlide * 100}}vw)`;
                
                dots.forEach((dot, i) => {{
                    dot.classList.toggle('active', i === currentSlide);
                }});
                
                leftArrow.classList.toggle('disabled', currentSlide === 0);
                rightArrow.classList.toggle('disabled', currentSlide === totalSlides - 1);
                pageCounter.textContent = `Page ${{currentSlide + 1}} of ${{totalSlides}}`;
            }}
            
            function nextSlide() {{
                if (currentSlide < totalSlides - 1) goToSlide(currentSlide + 1);
            }}
            
            function prevSlide() {{
                if (currentSlide > 0) goToSlide(currentSlide - 1);
            }}
            
            // Keyboard navigation
            document.addEventListener('keydown', (e) => {{
                if (e.key === 'ArrowRight') nextSlide();
                if (e.key === 'ArrowLeft') prevSlide();
            }});
            
            // Mouse wheel navigation
            let scrollTimeout;
            document.addEventListener('wheel', (e) => {{
                clearTimeout(scrollTimeout);
                scrollTimeout = setTimeout(() => {{
                    if (e.deltaY > 0) nextSlide();
                    else prevSlide();
                }}, 50);
            }});
            
            // Touch swipe navigation
            let touchStartX = 0;
            document.addEventListener('touchstart', (e) => {{
                touchStartX = e.changedTouches[0].screenX;
            }});
            document.addEventListener('touchend', (e) => {{
                const touchEndX = e.changedTouches[0].screenX;
                if (touchStartX - touchEndX > 50) nextSlide();
                if (touchEndX - touchStartX > 50) prevSlide();
            }});
        </script>
    </body>
    </html>
    """
    
    return html_template

def render_pdf_horizontal(pdf_path):
    """Render PDF in horizontal slider"""
    html_content = pdf_to_horizontal_slider(pdf_path)
    components.html(html_content, height=900, scrolling=False)
