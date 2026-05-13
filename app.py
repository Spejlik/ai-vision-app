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
        
        col_img, col_ctrl = st.columns([1.5, 1.0])
        
        with col_ctrl:
            st.caption("Nastavení ořezu (AOI)")
            ax = st.slider("X pozice", 0, 2000, 0)
            ay = st.slider("Y pozice", 0, 2000, 0)
            aw = st.slider("Šířka", 100, 2500, 1280)
            ah = st.slider("Výška", 100, 2500, 1080)
            m_name = st.text_input("Název Master snímku:", placeholder="např. MQB_P1")
            
            if st.button("📸 VYFOTIT A ULOŽIT", type="primary", use_container_width=True):
                if not m_name:
                    st.error("Zadejte název snímku!")
                else:
                    # 1. Vyfotíme celou scénu
                    raw_frame = cam.get_frame()
                    pil_img = Image.fromarray(raw_frame)
                    
                    # 2. PROVEDEME OŘEZ (Toto je ten odrazový můstek)
                    # Teď už neukládáme celou fotku, ale jen to, co jsi vybral slidery
                    cropped_master = pil_img.crop((ax, ay, ax + aw, ay + ah))
                    
                    # 3. Uložíme oříznutý Master
                    os.makedirs("masters", exist_ok=True)
                    file_path = f"masters/{st.session_state.active_project}_{m_name}.png"
                    cropped_master.save(file_path)
                    
                    # 4. Zapíšeme do DB
                    database.add_master(st.session_state.active_project, m_name, ax, ay, aw, ah, file_path)
                    
                    st.success(f"Master '{m_name}' uložen jako výřez!")
                    st.rerun()

        with col_img:
            # Živý náhled s výřezem
            raw_frame = cam.get_frame()
            pil_raw = Image.fromarray(raw_frame)
            preview_crop = pil_raw.crop((ax, ay, ax + aw, ay + ah))
            
            st.image(preview_crop, caption="Náhled AOI (to, co uvidí AI)", use_container_width=True)
            st.write(f"📏 Rozlišení: {aw} x {ah} px")

    # KROK 3: ROI DEFINICE
    elif st.session_state.step == 3:
        masters = database.get_masters(st.session_state.active_project)
        if not masters:
            st.error("Žádné Mastery nenalezeny.")
        else:
            # 1. Výběr Masteru a načtení dat
            m_names = [m[2] for m in masters]
            sel_m_name = st.selectbox("Vyber Master:", m_names, label_visibility="collapsed")
            curr_m = next(m for m in masters if m[2] == sel_m_name)
            
            old_rois = database.get_rois(curr_m[0])
            img = Image.open(curr_m[7]).convert("RGB")
            W, H = img.size

            # 2. Definice rozložení
            col_main, col_side = st.columns([1.6, 1.0])

            with col_side:
                st.subheader("➕ Správa zón")
                
                # Inicializace stavu pro editaci, pokud neexistuje
                if 'edit_roi_id' not in st.session_state:
                    st.session_state.edit_roi_id = None

                # TLAČÍTKO PRO NOVOU ZÓNU
                if not st.session_state.get('manual_add_active', False):
                    if st.button("✨ VYTVOŘIT NOVOU ZÓNU", use_container_width=True, type="primary"):
                        st.session_state.manual_add_active = True
                        st.session_state.edit_roi_id = None
                        st.rerun()

                # FORMULÁŘ (SLIDERY)
                rx, ry, rw, rh = 0, 0, 100, 100 # Výchozí hodnoty
                if st.session_state.get('manual_add_active', False):
                    with st.container(border=True):
                        # Pokud editujeme, načteme původní hodnoty
                        default_name = "Zóna 1"
                        if st.session_state.edit_roi_id:
                            e_roi = next(r for r in old_rois if r[0] == st.session_state.edit_roi_id)
                            default_name, rx_d, ry_d, rw_d, rh_d = e_roi[1], e_roi[2], e_roi[3], e_roi[4], e_roi[5]
                        else:
                            rx_d, ry_d, rw_d, rh_d = W//3, H//3, 150, 150

                        name = st.text_input("Název:", default_name)
                        rx = st.slider("X pozice", 0, W, rx_d)
                        ry = st.slider("Y pozice", 0, H, ry_d)
                        rw = st.slider("Šířka", 10, 800, rw_d)
                        rh = st.slider("Výška", 10, 800, rh_d)
                        nok = st.selectbox("Typ vady:", range(1, 11), format_func=lambda x: f"NOK {x}")
                        
                        c1, c2 = st.columns(2)
                        if c1.button("💾 ULOŽIT", type="primary", use_container_width=True):
                            database.save_roi(curr_m[0], name, rx, ry, rw, rh, nok, st.session_state.edit_roi_id)
                            st.session_state.manual_add_active = False
                            st.session_state.edit_roi_id = None
                            st.rerun()
                        if c2.button("✖ ZRUŠIT", use_container_width=True):
                            st.session_state.manual_add_active = False
                            st.rerun()

                st.divider()
                st.subheader("📋 Seznam zón")
                for r in old_rois:
                    with st.container(border=True):
                        c1, c2, c3 = st.columns([3, 1, 1])
                        c1.markdown(f"**{r[1]}** (NOK {r[6]})")
                        if c2.button("📝", key=f"edit_{r[0]}"):
                            st.session_state.edit_roi_id = r[0]
                            st.session_state.manual_add_active = True
                            st.rerun()
                        if c3.button("🗑️", key=f"del_{r[0]}"):
                            database.delete_roi(r[0])
                            st.rerun()

            with col_main:
                # 3. KRESLENÍ (Tady se děje to kouzlo, proběhne to až po nastavení sliderů)
                draw = ImageDraw.Draw(img)
                # Uložené zóny (Zelená)
                for r in old_rois:
                    if r[0] != st.session_state.edit_roi_id: # Nekreslit zeleně tu, kterou zrovna editujeme
                        draw.rectangle([r[2], r[3], r[2]+r[4], r[3]+r[5]], outline="#97BE0D", width=5)
                        draw.text((r[2]+5, r[3]+5), r[1], fill="#97BE0D")
                
                # Aktuálně laděná zóna (Oranžová)
                if st.session_state.get('manual_add_active', False):
                    draw.rectangle([rx, ry, rx+rw, ry+rh], outline="#FF9800", width=6)
                    draw.text((rx+5, ry-25), "UPRAVUJI...", fill="#FF9800")

                # 4. TEPRVE TEĎ ZOBRAZ FINÁLNÍ OBRÁZEK
                st.image(img, use_container_width=True)
                
                # FORMULÁŘ PRO EDITACI / PŘIDÁVÁNÍ
                if st.session_state.get('manual_add_active', False):
                    with st.container(border=True):
                        st.write("**Nastavení zóny**")
                        name = st.text_input("Název:", f"Zóna {len(old_rois)+1}")
                        rx = st.slider("X pozice", 0, W, W//3)
                        ry = st.slider("Y pozice", 0, H, H//3)
                        rw = st.slider("Šířka", 10, 500, 150)
                        rh = st.slider("Výška", 10, 500, 150)
                        nok = st.selectbox("Typ vady:", range(1, 11), format_func=lambda x: f"NOK {x}")
                        
                        # Vykreslení oranžového náhledu (vynucený překres)
                        draw.rectangle([rx, ry, rx+rw, ry+rh], outline=orange, width=6)
                        
                        c1, c2 = st.columns(2)
                        if c1.button("💾 ULOŽIT", type="primary", use_container_width=True):
                            database.save_roi(curr_m[0], name, rx, ry, rw, rh, nok)
                            st.session_state.manual_add_active = False
                            st.rerun()
                        if c2.button("✖ ZRUŠIT", use_container_width=True):
                            st.session_state.manual_add_active = False
                            st.rerun()

                st.divider()
                st.subheader("📋 Seznam zón")
                if not old_rois:
                    st.caption("Žádné zóny nenalezeny.")
                else:
                    for r in old_rois:
                        with st.container(border=True):
                            c1, c2, c3 = st.columns([3, 1, 1])
                            c1.markdown(f"**{r[1]}**")
                            c1.caption(f"NOK {r[6]}")
                            
                            # TLAČÍTKO EDITACE (Tužka)
                            if c2.button("📝", key=f"edit_{r[0]}", help="Upravit zónu"):
                                # Načteme hodnoty zóny do session_state pro slidery
                                st.session_state.manual_add_active = True
                                st.session_state.edit_id = r[0] # Uložíme si, kterou zónu ladíme
                                # Přednastavíme hodnoty pro slidery (pokud je v kódu používáš jako defaulty)
                                st.rerun()

                            # TLAČÍTKO SMAZÁNÍ (Koš)
                            if c3.button("🗑️", key=f"del_{r[0]}", help="Smazat"):
                                database.delete_roi(r[0])
                                st.rerun()                        

# ... (zbytek monitoring sekce)

elif menu == "Monitoring":
    st.title("📊 Živý monitoring")
    st.write("Zde se zobrazují výsledky inspekce.")
    # Zde pak doděláme tu mřížku detailů (krok 4)