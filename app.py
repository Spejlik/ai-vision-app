import streamlit as st
from streamlit_cropper import st_cropper
from PIL import Image, ImageDraw
import database
import camera_manager
import time
import os
import streamlit as st

# Inicializace
st.set_page_config(layout="wide", page_title="AI Vision Inspection")
database.init_db()
cam = camera_manager.BaslerCam()

# TENTO BLOK ODSTRANÍ VOLNÉ MÍSTO NAHOŘE
st.markdown("""
    <style>
        /* Odstranění okrajů hlavní nádoby */
        .block-container {
            padding-top: 1rem;
            padding-bottom: 0rem;
            margin-top: 0rem;
        }
        /* Zmenšení mezery nad nadpisem */
        header {
            visibility: hidden;
        }
        #root > div:nth-child(1) > div > div > div > div > section > div {
            padding-top: 0rem;
        }
        /* Úprava nadpisu, aby nebyl tak vysoký */
        h1 {
            padding-top: 0rem;
            margin-top: -2rem;
        }
    </style>
""", unsafe_allow_html=True)

# ... zbytek tvého kódu (st.sidebar, atd.)

if 'step' not in st.session_state: st.session_state.step = 1
if 'active_project' not in st.session_state: st.session_state.active_project = None
if 'active_master' not in st.session_state: st.session_state.active_master = None

st.sidebar.title("📷 Menu")
menu = st.sidebar.radio("Navigace", ["Konfigurace", "Monitoring"])

if menu == "Konfigurace":
    st.title("⚙️ Nastavení systému")
    
    # Průvodce kroky
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("📁 Projekty"): st.session_state.step = 1
    with c2:
        if st.button("🎯 Master"): st.session_state.step = 2
    with c3:
        if st.button("🔍 Zóny"): st.session_state.step = 3
    with c4:
        if st.button("🔌 I/O"): st.session_state.step = 4 
    
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

    # KROK 2: NASTAVENÍ MASTERU A AOI
    elif st.session_state.step == 2:
        st.subheader(f"🖼️ Master pro: {st.session_state.active_project}")
        
        # Ovládací prvky pro ořez
        ax = st.sidebar.number_input("X", 0, 3000, 0)
        ay = st.sidebar.number_input("Y", 0, 3000, 0)
        aw = st.sidebar.number_input("Šířka", 100, 3000, 1280)
        ah = st.sidebar.number_input("Výška", 100, 3000, 1024)
        m_name = st.text_input("Název Masteru", "P1")

        if st.button("📸 VYFOTIT A ULOŽIT"):
            frame = cam.get_frame() # Přímý odběr z kamery
            # Ořez pomocí numpy (OpenCV standard)
            cropped = frame[ay:ay+ah, ax:ax+aw]
            
            path = f"masters/{st.session_state.active_project}_{m_name}.png"
            cv2.imwrite(path, cv2.cvtColor(cropped, cv2.COLOR_RGB2BGR))
            
            database.add_master(st.session_state.active_project, m_name, ax, ay, aw, ah, path)
            st.success("Uloženo!")
            st.image(cropped)

    # KROK 3: ROI DEFINICE
    elif st.session_state.step == 3:
        masters = database.get_masters(st.session_state.active_project)
        if not masters or masters[0][2] == "":
            st.warning("Nejdříve uložte Master!")
        else:
            master_data = masters[0]
            img_path = master_data[2]
            
            if os.path.exists(img_path):
                img = Image.open(img_path)
                st.image(img, caption="Aktivní Master pro definici zón")
                # Zde pak pokračuje tvůj kód pro kreslení ROI...
            else:
                st.error(f"Soubor {img_path} nebyl nalezen na disku!")

            W, H = img.size
            old_rois = database.get_rois(curr_m[0])

            col_main, col_side = st.columns([1.6, 1.0])

            with col_side:
                st.subheader("➕ Správa zón")
                if st.button("✨ VYTVOŘIT NOVOU ZÓNU", use_container_width=True, type="primary"):
                    st.session_state.manual_add_active = True
                    st.session_state.edit_roi_id = None

                if st.session_state.get('manual_add_active', False):
                    with st.container(border=True):
                        st.write("📍 Nastavení nové zóny")
                        name = st.text_input("Název:", "Zóna 1")
                        rx = st.slider("X", 0, W, W//2)
                        ry = st.slider("Y", 0, H, H//2)
                        rw = st.slider("Šířka", 10, W, 150)
                        rh = st.slider("Výška", 10, H, 150)
                        nok = st.selectbox("Typ vady:", range(1, 11))
                        
                        if st.button("💾 ULOŽIT ZÓNU"):
                            database.save_roi(curr_m[0], name, rx, ry, rw, rh, nok)
                            st.session_state.manual_add_active = False
                            st.rerun()

                st.divider()
                for r in old_rois:
                    st.write(f"✅ {r[1]} (NOK {r[6]})")

            with col_main:
                # Vykreslení zón na Master obrázek
                draw = ImageDraw.Draw(img)
                for r in old_rois:
                    draw.rectangle([r[2], r[3], r[2]+r[4], r[3]+r[5]], outline="#97BE0D", width=5)
                
                # Náhled aktuálně tvořené zóny
                if st.session_state.get('manual_add_active', False):
                    draw.rectangle([rx, ry, rx+rw, ry+rh], outline="orange", width=3)
                
                st.image(img, use_container_width=True, caption=f"Master: {master_path}")

    # KROK 4: I/O MONITOR (PŘIDÁNO)
    elif st.session_state.step == 4:
        st.subheader("🔌 I/O Monitor & PLC Komunikace")
        c1, c2 = st.columns(2)
        with c1:
            st.info("Vstupy z PLC")
            st.toggle("Trigger signál", disabled=True)
        with c2:
            st.info("Výstupy do PLC")
            st.write("🔴 PASS")
            st.write("🔴 FAIL")

# --- KONEC KONFIGURACE, START MONITORINGU ---

elif menu == "Monitoring":
    st.title("📊 Živý monitoring")
    st.write("Zde se zobrazují výsledky inspekce.")