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
        st.subheader(f"🖼️ Nastavení Masteru pro: {st.session_state.active_project}")
        
        # --- INICIALIZACE SNÍMKU ---
        if 'master_setup_frame' not in st.session_state:
            st.session_state.master_setup_frame = None

        col_img, col_ctrl = st.columns([1.5, 1.0])
        
        with col_ctrl:
            st.write("### 🎮 Ovládání")
            # Tlačítko pro nový snímek - jen toto volá kameru
            if st.button("📸 SNÍMAT NOVÝ OBRAZ", type="primary", use_container_width=True):
                with st.spinner("Snímám..."):
                    st.session_state.master_setup_frame = cam.get_frame()
            
            st.divider()
            st.caption("📍 Nastavení ořezu (AOI)")
            
            # Slidery s klíči, aby se netřásly
            # Pokud nemáme snímek, použijeme výchozí rozlišení 2500x2000
            max_w = st.session_state.master_setup_frame.shape[1] if st.session_state.master_setup_frame is not None else 2500
            max_h = st.session_state.master_setup_frame.shape[0] if st.session_state.master_setup_frame is not None else 2000

            ax = st.slider("X pozice", 0, max_w - 100, 0, key="aoi_x")
            ay = st.slider("Y pozice", 0, max_h - 100, 0, key="aoi_y")
            aw = st.slider("Šířka", 100, max_w - ax, 1280, key="aoi_w")
            ah = st.slider("Výška", 100, max_h - ay, 1080, key="aoi_h")
            
            m_name = st.text_input("Název Master snímku:", placeholder="např. MQB_P1")
            
            if st.button("💾 ULOŽIT MASTER", use_container_width=True):
                if st.session_state.master_setup_frame is None:
                    st.error("Nejdříve musíte pořídit snímek!")
                elif not m_name:
                    st.error("Zadejte název snímku!")
                else:
                    # PROVEDEME OŘEZ PRO ULOŽENÍ
                    pil_img = Image.fromarray(st.session_state.master_setup_frame)
                    cropped_master = pil_img.crop((ax, ay, ax + aw, ay + ah))
                    
                    os.makedirs("masters", exist_ok=True)
                    file_path = f"masters/{st.session_state.active_project}_{m_name}.png"
                    cropped_master.save(file_path)
                    
                    # Zápis do DB (předpokládáme, že tvůj database.py přijímá tyto parametry)
                    database.add_master(st.session_state.active_project, m_name, ax, ay, aw, ah, file_path)
                    
                    st.success(f"Master '{m_name}' uložen!")
                    time.sleep(1)
                    st.rerun()

        with col_img:
            if st.session_state.master_setup_frame is not None:
                # Výřez pro náhled
                pil_raw = Image.fromarray(st.session_state.master_setup_frame)
                preview_crop = pil_raw.crop((ax, ay, ax + aw, ay + ah))
                
                # Zmenšíme náhled pro web, aby byl plynulý (max šířka 800px)
                st.image(preview_crop, caption="Náhled AOI (to, co uvidí AI)", use_container_width=True)
                st.write(f"📏 Aktuální rozlišení výřezu: **{aw} x {ah} px**")
            else:
                # Placeholder, pokud ještě není nic vyfoceno
                st.warning("Klikněte na 'SNÍMAT NOVÝ OBRAZ' pro zobrazení náhledu z kamery.")

    # KROK 3: ROI DEFINICE
    elif st.session_state.step == 3:
        if 'edit_roi_id' not in st.session_state: st.session_state.edit_roi_id = None
        if 'manual_add_active' not in st.session_state: st.session_state.manual_add_active = False

        masters = database.get_masters(st.session_state.active_project)
        if not masters:
            st.error("Žádné Mastery nenalezeny.")
        else:
            m_names = [m[2] for m in masters]
            sel_m_name = st.selectbox("Vyber Master:", m_names, label_visibility="collapsed")
            curr_m = next(m for m in masters if m[2] == sel_m_name)
            
            old_rois = database.get_rois(curr_m[0])
            img = Image.open(curr_m[7]).convert("RGB")
            W, H = img.size

            col_main, col_side = st.columns([1.6, 1.0])

            with col_side:
                st.subheader("➕ Správa zón")
                
                if not st.session_state.manual_add_active:
                    if st.button("✨ VYTVOŘIT NOVOU ZÓNU", use_container_width=True, type="primary"):
                        st.session_state.manual_add_active = True
                        st.session_state.edit_roi_id = None
                        st.rerun()

                rx, ry, rw, rh = 0, 0, 100, 100
                if st.session_state.manual_add_active:
                    with st.container(border=True):
                        d_name, d_x, d_y, d_w, d_h = "Zóna", W//3, H//3, 150, 150
                        if st.session_state.edit_roi_id:
                            e_roi = next((r for r in old_rois if r[0] == st.session_state.edit_roi_id), None)
                            if e_roi:
                                d_name, d_x, d_y, d_w, d_h = e_roi[1], e_roi[2], e_roi[3], e_roi[4], e_roi[5]

                        name = st.text_input("Název:", d_name, key="roi_name_field")
                        rx = st.slider("X pozice", 0, W, d_x)
                        ry = st.slider("Y pozice", 0, H, d_y)
                        rw = st.slider("Šířka", 10, 800, d_w)
                        rh = st.slider("Výška", 10, 800, d_h)
                        nok = st.selectbox("Typ vady:", range(1, 11), format_func=lambda x: f"NOK {x}")
                        
                        c1, c2 = st.columns(2)
                        if c1.button("💾 ULOŽIT", type="primary", use_container_width=True):
                            database.save_roi(curr_m[0], name, rx, ry, rw, rh, nok, st.session_state.edit_roi_id)
                            st.session_state.manual_add_active = False
                            st.session_state.edit_roi_id = None
                            st.rerun()
                        if c2.button("✖ ZRUŠIT", use_container_width=True):
                            st.session_state.manual_add_active = False
                            st.session_state.edit_roi_id = None
                            st.rerun()

                st.divider()
                st.subheader("📋 Seznam zón")
                for r in old_rois:
                    with st.container(border=True):
                        cols = st.columns([3, 1, 1])
                        cols[0].write(f"**{r[1]}** (NOK {r[6]})")
                        if cols[1].button("📝", key=f"ed_{r[0]}"):
                            st.session_state.edit_roi_id = r[0]
                            st.session_state.manual_add_active = True
                            st.rerun()
                        if cols[2].button("🗑️", key=f"de_{r[0]}"):
                            database.delete_roi(r[0])
                            st.rerun()

            with col_main:
                draw = ImageDraw.Draw(img)
                for r in old_rois:
                    if r[0] != st.session_state.edit_roi_id:
                        draw.rectangle([r[2], r[3], r[2]+r[4], r[3]+r[5]], outline="#97BE0D", width=5)
                
                if st.session_state.manual_add_active:
                    draw.rectangle([rx, ry, rx+rw, ry+rh], outline="#FF9800", width=6)
                
                st.image(img, use_container_width=True)

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