import streamlit as st

import streamlit as st

def apply_custom_css():
    st.markdown("""
        <style>
        /* 1. TOTÁLNÍ ZÁKAZ SCROLLU A ROZTAŽENÍ */
        html, body, [data-testid="stAppViewContainer"] {
            overflow: hidden !important;
            height: 100vh !important;
        }
        
        /* Úprava hlavního kontejneru, aby vyplnil obrazovku bez mezer */
        .main .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 0rem !important;
            max-width: 98% !important;
        }

        /* 2. VIDITELNOST TEXTU V SIDEBARU */
        [data-testid="stSidebar"] {
            background-color: #1A1C24 !important;
        }
        /* Vynucení bílé barvy pro popisky (Uživatel, PIN, Navigace) */
        [data-testid="stSidebar"] label p, [data-testid="stSidebar"] stMarkdown p {
            color: white !important;
            font-weight: bold !important;
            font-size: 16px !important;
        }
        /* Barva textu v menu navigace */
        [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
            color: white !important;
        }

        /* 3. HORNÍ LIŠTA - AUTO/MANUAL TEXT */
        /* Oprava pro radio buttony, aby byly jasně vidět */
        [data-testid="stHorizontalBlock"] label p {
            color: #38bdf8 !important; /* Světle modrá pro lepší kontrast */
            font-size: 18px !important;
            font-weight: bold !important;
        }
        
        /* 4. ÚPRAVA INPUTŮ (aby nebyly zářivě bílé, ale čitelné) */
        input {
            background-color: #262730 !important;
            color: white !important;
            border: 1px solid #38bdf844 !important;
        }

        /* Skrytí nuly/titulků u obrázků */
        [data-testid="stImageCaption"] { display: none !important; }
        </style>
    """, unsafe_allow_html=True)

def draw_roi_card(name, confidence, status, color, img_path):
    # Tady f-string nevadí, protože proměnné jsou v jednoduchých uvozovkách
    img_html = f'<img src="data:image/jpeg;base64,{img_path}" style="width:100%; border-radius:6px; margin-top:10px;">' if img_path else ""
    st.markdown(f"""
        <div class="roi-card">
            <div style="color: #888; font-size: 11px;">DETEKCE</div>
            <div style="font-weight: bold; font-size: 16px;">{name}</div>
            <div style="font-size: 28px; color: {color}; font-weight: bold;">{confidence}%</div>
            <div style="background-color: {color}22; color: {color}; padding: 3px; border-radius: 4px; font-weight: bold;">{status}</div>
            {img_html}
        </div>
    """, unsafe_allow_html=True)