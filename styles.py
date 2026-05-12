import streamlit as st

def apply_custom_css():
    st.markdown("""
        <style>
        /* 1. GLOBÁLNÍ ZÁKAZ SCROLLU NA VŠECH VRSTVÁCH */
        html, body, [data-testid="stAppViewContainer"], 
        [data-testid="stMainViewContainer"], 
        .main .block-container,
        [data-testid="stVerticalBlock"] {
            overflow: hidden !important;
            height: 100vh !important;
            max-height: 100vh !important;
        }

        /* 2. ODSTRANĚNÍ VNĚJŠÍCH OKRAJŮ A MEZER */
        .main .block-container {
            padding-top: 1rem !important;
            padding-bottom: 0rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            max-width: 98% !important;
        }

        /* 3. DESIGN KARET (Zmenšení, aby se vešly) */
        .roi-card {
            background-color: white;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            padding: 8px; /* Méně paddingu pro úsporu místa */
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            margin-bottom: 5px;
        }
        
        .roi-card img {
            max-height: 120px; /* Limit výšky obrázku */
            object-fit: contain;
        }

        /* 4. SIDEBAR - Kontrastní vzhled */
        [data-testid="stSidebar"] {
            background-color: #1e293b !important;
            min-width: 250px !important;
        }

        /* 5. SKRYTÍ MENU A DEPLOY TLAČÍTKA */
        #MainMenu, footer, header, [data-testid="stHeader"] {
            display: none !important;
        }
        </style>
    """, unsafe_allow_html=True)

def draw_roi_card(name, confidence, status, color, img_path, size="normal"):
    # Dynamické nastavení výšky podle počtu karet
    img_height = "80px" if size == "small" else "120px"
    font_size = "18px" if size == "small" else "24px"
    
    img_html = f'<img src="data:image/jpeg;base64,{img_path}" style="max-height:{img_height}; width:auto; border-radius:4px;">' if img_path else ""
    
    st.markdown(f"""
        <div class="roi-card">
            <div style="font-size: 10px; color: gray;">{name}</div>
            <div style="font-size: {font_size}; color: {color}; font-weight: bold; line-height:1;">{confidence}%</div>
            <div style="background:{color}22; color:{color}; font-size:10px; font-weight:bold; border-radius:3px; margin:2px 0;">{status}</div>
            {img_html}
        </div>
    """, unsafe_allow_html=True)