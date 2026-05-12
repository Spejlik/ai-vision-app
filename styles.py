import streamlit as st

def apply_custom_css():
    st.markdown("""
        <style>
        /* 1. SIDEBAR - ČITELNOST */
        [data-testid="stSidebar"] {
            background-color: #1e293b !important;
        }
        /* Vynucení bílé barvy pro všechny texty v sidebaru */
        [data-testid="stSidebar"] *, [data-testid="stSidebarLabel"] {
            color: white !important;
        }
        /* Zvýraznění aktivní navigace */
        [data-testid="stSidebarNav"] li {
            background-color: transparent !important;
        }

        /* 2. TEČKY V HLAVIČCE - FIX OŘEZÁVÁNÍ */
        .dots-container {
            font-size: 28px;
            text-align: right;
            line-height: 1;
            white-space: nowrap;
            overflow: visible !important; /* Důležité: aby tečky nebyly půlky */
            padding: 10px 0;
            display: flex;
            justify-content: flex-end;
            gap: 4px;
        }
        
        /* 3. ZÁKAZ SCROLLU A ROZLOŽENÍ */
        html, body, [data-testid="stAppViewContainer"] {
            overflow: hidden !important;
            height: 100vh !important;
        }
        .main .block-container {
            padding-top: 1.5rem !important;
            max-width: 98% !important;
        }

        /* 4. KARTY ROI */
        .roi-card {
            background-color: white;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 8px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        </style>
    """, unsafe_allow_html=True)

def draw_roi_card(name, confidence, status, color, img_path, size="normal"):
    img_height = "100px" if size == "small" else "140px"
    img_html = f'<img src="data:image/jpeg;base64,{img_path}" style="max-height:{img_height}; width:auto; border-radius:4px;">' if img_path else ""
    
    st.markdown(f"""
        <div class="roi-card">
            <div style="font-size: 11px; color: #64748b; font-weight: bold;">{name}</div>
            <div style="font-size: 24px; color: {color}; font-weight: bold; margin: 4px 0;">{confidence}%</div>
            <div style="background:{color}22; color:{color}; font-size:12px; font-weight:bold; border-radius:4px; padding:2px;">{status}</div>
            <div style="margin-top:8px;">{img_html}</div>
        </div>
    """, unsafe_allow_html=True)