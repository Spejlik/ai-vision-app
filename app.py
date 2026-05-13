import streamlit as st
from streamlit_cropper import st_cropper
from PIL import Image, ImageDraw
import database
import camera_manager
import time

st.set_page_config(layout="wide", page_title="AI Vision Inspection")
database.init_db()

if 'step' not in st.session_state: st.session_state.step = 1

st.sidebar.title("📷 Menu")
menu = st.sidebar.radio("Navigace", ["Konfigurace", "Monitoring"])

if menu == "Konfigurace":
    st.title("⚙️ Nastavení systému")
    
    # JEDNODUCHÝ PRŮVODCE
    col1, col2, col3 = st.columns(3)
    if col1.button("1. Projekt"): st.session_state.step = 1
    if col2.button("2. Master & AOI"): st.session_state.step = 2
    if col3.button("3. ROI (Inspekce)"): st.session_state.step = 3
    
    st.divider()

    if st.session_state.step == 3:
        st.subheader("🔍 Definice inspekčních zón")
        # TADY BUDE TVOJE KRESLENÍ ROI S MODRÝMI RÁMEČKY
        img = Image.open('master_dummy.jpg') # Pro test
        
        c_left, c_right = st.columns([3, 1])
        with c_left:
            # Překreslení stávajících ROI (modře)
            draw = ImageDraw.Draw(img)
            # draw.rectangle(...) - tady načteme z DB
            
            roi = st_cropper(img, realtime_update=True, box_color='#FF9800', key="main_cropper")
            
        with c_right:
            roi_name = st.text_input("Název kontroly")
            if st.button("💾 ULOŽIT"):
                # Výpočet a uložení
                st.success("ROI uložena!")
                st.rerun()

elif menu == "Monitoring":
    st.title("📊 Živý monitoring")
    # Tady bude ta mřížka 3-5 kamer pod sebou
    st.info("Zde uvidíte výsledky z kamer Basler v reálném čase.")