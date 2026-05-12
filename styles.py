import streamlit as st

def apply_custom_css():
    st.markdown("""
        <style>
        header { visibility: hidden; }
        .stApp { background-color: #0E1117; color: white; }
        
        .roi-card {
            background-color: #1A1C24;
            border: 1px solid #38bdf844;
            border-radius: 12px;
            padding: 15px;
            text-align: center;
        }
        </style>
    """, unsafe_allow_html=True)

def draw_roi_card(name, confidence, status, color, img_path):
    # Pokud obrázek existuje, vykreslíme ho, jinak jen text
    img_html = f'<img src="data:image/jpeg;base64,{img_path}" style="width:100%; border-radius:6px;">' if img_path else ""
    st.markdown(f"""
        <div class="roi-card">
            <div style="color: gray; font-size: 10px;">ROI</div>
            <div style="font-weight: bold;">{name}</div>
            <div style="font-size: 24px; color: {color}; font-weight: bold;">{confidence}%</div>
            {img_html}
            <div style="margin-top: 10px; font-weight: bold; color: {color};">{status}</div>
        </div>
    """, unsafe_allow_html=True)