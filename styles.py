import streamlit as st

def apply_custom_css():
    st.markdown("""
        <style>
        /* Skrytí systémových lišt */
        header, footer, [data-testid="stDecoration"] { visibility: hidden; }
        
        /* Hlavní barvy aplikace */
        .stApp {
            background-color: #0E1117;
            color: #FFFFFF;
        }

        /* Sidebar - fixní barvy */
        section[data-testid="stSidebar"] {
            background-color: #1A1C24 !important;
        }
        section[data-testid="stSidebar"] * {
            color: #FFFFFF !important;
        }

        /* Tlačítko Spustit kontrolu */
        div.stButton > button {
            background: linear-gradient(90deg, #38bdf8 0%, #0ea5e9 100%) !important;
            color: #000000 !important;
            border: none !important;
            padding: 15px !important;
            font-weight: bold !important;
            font-size: 18px !important;
            border-radius: 10px !important;
            width: 100% !important;
            box-shadow: 0 4px 15px rgba(56, 189, 248, 0.2) !important;
        }

        /* Likvidace otravných nul pod kartami */
        [data-testid="stImageCaption"], 
        div[data-testid="stMarkdownContainer"] p:empty,
        .st-emotion-cache-0, .st-emotion-cache-1wivap2 {
            display: none !important;
        }
        </style>
    """, unsafe_allow_html=True)

def draw_roi_card(name, confidence, status, color, img_path):
    """Vykreslí ROI kartu jako čisté HTML/CSS bez Streamlit náladovosti"""
    st.markdown(f"""
        <div style="
            background-color: #1A1C24;
            border: 1px solid {color}44;
            border-radius: 12px;
            padding: 15px;
            text-align: center;
            margin-bottom: 10px;
        ">
            <div style="opacity: 0.6; font-size: 11px; margin-bottom: 5px;">DETEKCE</div>
            <div style="font-weight: bold; font-size: 16px; color: white;">{name}</div>
            <div style="font-size: 26px; font-weight: bold; color: {color}; margin: 5px 0;">{confidence}%</div>
            <img src="data:image/jpeg;base64,{img_path}" style="width: 100%; border-radius: 6px; margin-top: 5px;">
            <div style="
                margin-top: 10px;
                padding: 4px;
                border-radius: 4px;
                background-color: {color}22;
                color: {color};
                font-size: 12px;
                font-weight: bold;
            ">{status}</div>
        </div>
    """, unsafe_allow_html=True)