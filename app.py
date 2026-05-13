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
            st.error("Žádné Mastery.")
        else:
            m_names = [m[2] for m in masters]
            sel_m_name = st.selectbox("Vyber Master:", m_names, label_visibility="collapsed")
            curr_m = next(m for m in masters if m[2] == sel_m_name)
            
            # Načtení obrázku a jeho rozměrů
            img_path = curr_m[7]
            img = Image.open(img_path).convert("RGB")
            W, H = img.size
            
            col_main, col_side = st.columns([1.5, 1.0])
            
            with col_side:
                st.subheader("➕ Nová zóna")
                add_mode = st.toggle("REŽIM ÚPRAV", key="add_toggle_manual")
                
                if add_mode:
                    name = st.text_input("Název:", "Zóna 1")
                    # Slidery s rozsahem podle skutečných pixelů fotky
                    rx = st.slider("X pozice", 0, W, W//4)
                    ry = st.slider("Y pozice", 0, H, H//4)
                    rw = st.slider("Šířka", 20, W, 150)
                    rh = st.slider("Výška", 20, H, 150)
                    nok = st.selectbox("NOK kód:", range(1, 11), format_func=lambda x: f"Kód {x}")
                    
                    if st.button("💾 ULOŽIT ZÓNU", type="primary", use_container_width=True):
                        database.save_roi(curr_m[0], name, rx, ry, rw, rh, nok)
                        st.success("Zóna uložena!")
                        st.rerun()
                
                st.divider()
                st.write("🔍 **Uložené zóny v tomto Masteru:**")
                old_rois = database.get_rois(curr_m[0])
                for r in old_rois:
                    c1, c2 = st.columns([4, 1])
                    c1.caption(f"{r[1]} (X:{r[2]}, Y:{r[3]})")
                    if c2.button("🗑️", key=f"del_{r[0]}"):
                        database.delete_roi(r[0])
                        st.rerun()

            with col_main:
                # Kreslení do kopie obrázku
                draw = ImageDraw.Draw(img)
                valeo_green = "#97BE0D"
                orange = "#FF9800"
                
                # 1. Vykresli uložené (Zeleně)
                for r in old_rois:
                    draw.rectangle([r[2], r[3], r[2]+r[4], r[3]+r[5]], outline=valeo_green, width=5)
                    draw.text((r[2]+5, r[3]+5), f"{r[1]} [N{r[6]}]", fill=valeo_green)
                
                # 2. Vykresli aktuální náhled ze sliderů (Oranžově)
                if add_mode:
                    draw.rectangle([rx, ry, rx+rw, ry+rh], outline=orange, width=5)
                    # Přidáme poloprůhledný střed pro lepší viditelnost
                    draw.text((rx+5, ry+5), "NÁHLED ZÓNY", fill=orange)
                
                st.image(img, use_container_width=True)

                # PEVNÝ PANEL SEZNAMU (s vnitřním scrollováním, pokud je dlouhý)
                st.write("📋 Seznam zón")
                list_container = st.container(height=300) # Pevná výška seznamu!
                with list_container:
                    for r in old_rois:
                        c1, c2 = st.columns([3, 1])
                        c1.caption(f"**{r[1]}** (NOK {r[6]})")
                        if c2.button("⚙️", key=f"cfg_{r[0]}", help="Editovat"):
                            st.session_state.edit_roi_id = r[0]
                            st.rerun()

# ... (zbytek monitoring sekce)

elif menu == "Monitoring":
    st.title("📊 Živý monitoring")
    st.write("Zde se zobrazují výsledky inspekce.")
    # Zde pak doděláme tu mřížku detailů (krok 4)