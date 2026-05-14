import streamlit as st
import cv2
import database
import camera_manager
import os
from PIL import Image, ImageDraw

# Konfigurace stránky
st.set_page_config(layout="wide", page_title="AI Vision Inspection")

# Inicializace DB a Kamery
database.init_db()
cam = camera_manager.BaslerCam()

# Session State inicializace
if 'step' not in st.session_state: st.session_state.step = 1
if 'active_project' not in st.session_state: st.session_state.active_project = None

# Sidebar Menu
st.sidebar.title("📷 Menu")
menu = st.sidebar.radio("Navigace", ["Konfigurace", "Monitoring"])

if menu == "Konfigurace":
    st.title("⚙️ Nastavení systému")
    
    # Navigační tlačítka
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("📁 Projekty"): st.session_state.step = 1
    with c2:
        if st.button("🎯 Master"): st.session_state.step = 2
    with c3:
        if st.button("🔍 Zóny"): st.session_state.step = 3
    
    st.divider()

    # KROK 1: PROJEKTY
    if st.session_state.step == 1:
        st.subheader("📁 Správa projektů")
        new_p = st.text_input("Vytvořit nový projekt:")
        if st.button("Uložit projekt"):
            if new_p:
                database.save_project(new_p)
                st.success(f"Projekt {new_p} vytvořen")
        
        projs = database.get_projects()
        if projs:
            st.session_state.active_project = st.selectbox("Vyberte projekt:", [p[1] for p in projs])

    # KROK 2: MASTER
    elif st.session_state.step == 2:
        st.subheader(f"🖼️ Master pro: {st.session_state.active_project}")
        ax = st.sidebar.number_input("X", 0, 3000, 0)
        ay = st.sidebar.number_input("Y", 0, 3000, 0)
        aw = st.sidebar.number_input("Šířka", 100, 3000, 1280)
        ah = st.sidebar.number_input("Výška", 100, 3000, 1024)
        
        if st.button("📸 VYFOTIT A ULOŽIT"):
            frame = cam.get_frame()
            cropped = frame[ay:ay+ah, ax:ax+aw]
            
            if not os.path.exists("masters"): os.makedirs("masters")
            path = f"masters/{st.session_state.active_project}.png"
            cv2.imwrite(path, cv2.cvtColor(cropped, cv2.COLOR_RGB2BGR))
            
            database.add_master(st.session_state.active_project, path, ax, ay, aw, ah)
            st.success("Master uložen!")
            st.image(cropped)

    # KROK 3: ZÓNY
    elif st.session_state.step == 3:
        st.subheader(f"🔍 Definice zón pro: {st.session_state.active_project}")
        masters = database.get_masters(st.session_state.active_project)
        
        if masters and masters[0][2]:
            img_path = masters[0][2]
            if os.path.exists(img_path):
                img = Image.open(img_path)
                st.image(img, use_container_width=True)
                # Zde můžeš přidat kreslení ROI, pokud ho máš v záloze
            else:
                st.error("Soubor s Masterem nebyl nalezen.")
        else:
            st.warning("Nejdříve uložte Master v kroku 2.")

elif menu == "Monitoring":
    st.title("📊 Živý monitoring")
    st.write("Systém je připraven.")