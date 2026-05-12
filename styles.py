import streamlit as st

def apply_custom_css():
    st.markdown("""
        <style>
        /* 1. ZÁKAZ SCROLLU A PEVNÁ VÝŠKA */
        html, body, [data-testid="stAppViewContainer"] {
            overflow: hidden !important;
            height: 100vh !important;
            background-color: #f0f2f6; /* Světle šedé průmyslové pozadí */
        }
        
        .main .block-container {
            padding-top: 1rem !important;
            max-width: 98% !important;
        }

        /* 2. SIDEBAR - Tmavě modrý (profesionální kontrast) */
        [data-testid="stSidebar"] {
            background-color: #1e293b !important;
            color: white !important;
        }
        [data-testid="stSidebar"] * {
            color: white !important;
        }

        /* 3. KARTY ROI - Světlé s výrazným okrajem */
        .roi-card {
            background-color: white;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            padding: 10px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        
        /* 4. SKRYTÍ DEPLOY TLAČÍTKA A MENU */
        #MainMenu, footer, header {visibility: hidden;}
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