import streamlit as st
from streamlit_cropper import st_cropper
from PIL import Image, ImageDraw
import database
import camera_manager
import time
import os

# Inicializace
st.set_page_config(layout="wide", page_title="AI Vision Inspection")
database.init_db()
cam = camera_manager.BaslerCam()

if 'step' not in st.session_state: st.session_state.step = 1
if 'active_project' not in st.session_state: st.session_state.active_project = None
if 'active_master' not in st.session_state: st.session_state.active_master = None

st.sidebar.title("📷 Menu")
menu = st.sidebar.radio("Navigace", ["Konfigurace", "Monitoring"])

if menu == "Konfigurace":
    st.title("⚙️ Nastavení systému")
    
    # Průvodce kroky
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("1. Projekt", use_container_width=True): st.session_state.step = 1
    with c2:
        if st.button("2. Master & AOI", use_container_width=True): st.session_state.step = 2
    with c3:
        if st.button("3. ROI (Inspekce)", use_container_width=True): st.session_state.step = 3
    
    st.divider()

    # KROK 1: VÝBĚR PROJEKTU
    if st.session_state.step == 1:
        st.subheader("📁 Správa projektů")
        new_p = st.text_input("Vytvořit nový projekt:")
        if st.button("Uložit projekt"):
            if new_p:
                database.save_project(new_p)
                st.success("Projekt vytvořen")
        
        projs = database.get_projects()
        st.session_state.active_project = st.selectbox("Vyberte aktivní projekt:", [p[1] for p in projs])

    # KROK 2: MASTER A OŘEZ (AOI)
    elif st.session_state.step == 2:
        if not st.session_state.active_project:
            st.warning("Nejdříve vyberte projekt v kroku 1!")
        else:
            st.subheader(f"🖼️ Nastavení Masteru pro: {st.session_state.active_project}")
            
            col_l, col_r = st.columns([2, 1])
            
            with col_r:
                st.write("### Nastavení ořezu kamery (AOI)")
                ax = st.slider("X pozice", 0, 2000, 0)
                ay = st.slider("Y pozice", 0, 2000, 0)
                aw = st.slider("Šířka", 100, 2500, 1200)
                ah = st.slider("Výška", 100, 2500, 1000)
                
                master_name = st.text_input("Název Master snímku (např. MQB_P1_TOP)")
                if st.button("📸 VYFOTIT A ULOŽIT MASTER", type="primary", use_container_width=True):
                    # Tady se v reálu uloží snímek s AOI
                    img_path = f"masters/{master_name}.jpg"
                    if not os.path.exists('masters'): os.makedirs('masters')
                    # Simulace uložení
                    database.save_master(st.session_state.active_project, master_name, ax, ay, aw, ah, img_path)
                    st.success("Master uložen!")

            with col_l:
                # Živý náhled (nebo dummy)
                frame = cam.get_frame()
                st.image(frame, caption="Živý náhled z kamery", use_container_width=True)

    # KROK 3: ROI DEFINICE
    elif st.session_state.step == 3:
        st.subheader("🔍 Definice inspekčních zón")
        
        # Výběr masteru
        masters = database.get_masters(st.session_state.active_project)
        if not masters:
            st.error("Žádné Mastery nenalezeny. Vytvořte je v kroku 2.")
        else:
            m_names = [m[2] for m in masters]
            sel_m_name = st.selectbox("Vyberte Master snímek:", m_names)
            curr_m = next(m for m in masters if m[2] == sel_m_name)
            
            img = Image.open('master_dummy.jpg') # Tady by byl curr_m[8]
            
            c_l, c_r = st.columns([3, 1])
            
            with c_l:
                # Vykreslení stávajících ROI (modře)
                draw = ImageDraw.Draw(img)
                old_rois = database.get_rois(curr_m[0])
                for r in old_rois:
                    draw.rectangle([r[2], r[3], r[2]+r[4], r[3]+r[5]], outline="blue", width=5)
                
                # Cropper pro novou ROI
                roi = st_cropper(img, realtime_update=True, box_color='#FF9800', key="cropper")
            
            with c_r:
                new_roi_name = st.text_input("Název kontroly:")
                if st.button("💾 ULOŽIT KONTROLU", use_container_width=True):
                    coords = st.session_state['cropper']['coords']
                    database.save_roi(curr_m[0], new_roi_name, int(coords['left']), int(coords['top']), int(coords['width']), int(coords['height']))
                    st.toast("ROI uložena!")
                    time.sleep(0.5)
                    st.rerun()

elif menu == "Monitoring":
    st.title("📊 Živý monitoring")
    st.write("Zde se zobrazují výsledky inspekce.")
    # Zde pak doděláme tu mřížku detailů (krok 4)