import streamlit as st

def apply_custom_css():
    # Čisté CSS bez f-stringu pro stabilitu
    st.markdown("""
        <style>
        header { visibility: hidden; }
        .stApp { background-color: #0E1117; color: white; }
        
        /* SIDEBAR */
        section[data-testid="stSidebar"] {
            background-color: #1A1C24 !important;
        }
        section[data-testid="stSidebar"] * {
            color: white !important;
        }
        
        /* TLAČÍTKO */
        div.stButton > button {
            background-color: #38bdf8 !important;
            color: black !important;
            border: none !important;
            padding: 10px 20px !important;
            font-weight: bold !important;
            border-radius: 8px !important;
            width: 100% !important;
        }
        
        /* ROI KARTA */
        .roi-card {
            background-color: #1A1C24;
            border: 1px solid #38bdf833;
            border-radius: 12px;
            padding: 15px;
            text-align: center;
        }
        
        /* SKRÝT NULY */
        [data-testid="stImageCaption"], .st-emotion-cache-0 {
            display: none !important;
        }
        </style>
    """, unsafe_allow_html=True)

def draw_roi_card(name, confidence, status, color, img_path):
    img_html = f'<img src="data:image/jpeg;base64,{img_path}" style="width:100%; border-radius:6px; margin-top:10px;">' if img_path else ""
    st.markdown(f"""
        <div class="roi-card">
            <div style="color: #888; font-size: 11px;">DETEKCE</div>
            <div style="font-weight: bold;">{name}</div>
            <div style="font-size: 28px; color: {color}; font-weight: bold;">{confidence}%</div>
            <div style="background-color: {color}22; color: {color}; padding: 3px; border-radius: 4px; font-weight: bold;">
                {status}
            </div>
            {img_html}
        </div>
    """, unsafe_allow_html=True)