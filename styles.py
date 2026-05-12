import streamlit as st

def apply_custom_css():
    # POUŽÍVÁME ČISTÝ STRING (bez f na začátku), aby Python neřešil složené závorky {}
    st.markdown("""
        <style>
        /* Skrytí systémových prvků */
        header { visibility: hidden; }
        footer { visibility: hidden; }
        
        /* Oprava textu v segmented_control (přepínač AUTO/MANUAL) */
        div[data-testid="stBaseButton-segmented_control"] p {
            color: white !important;
        }
        
        /* Odstranění okrajů a scrollbarů pro čistý vzhled */
        .main .block-container {
            padding-top: 2rem !important;
            padding-bottom: 0rem !important;
            max-width: 95% !important;
        }

        /* Zákaz rolování v aplikaci pro "kiosk" vzhled */
        body {
            overflow: hidden;
        }
        
        /* Hlavní barvy - Dark Mode */
        .stApp {
            background-color: #0E1117;
            color: #FFFFFF;
        }

        /* Sidebar styling */
        section[data-testid="stSidebar"] {
            background-color: #1A1C24 !important;
        }
        section[data-testid="stSidebar"] * {
            color: #FFFFFF !important;
        }

        /* Karty ROI */
        .roi-card {
            background-color: #1A1C24;
            border: 1px solid #38bdf844;
            border-radius: 12px;
            padding: 15px;
            text-align: center;
            margin-bottom: 10px;
        }
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