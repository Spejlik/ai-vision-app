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

    # KROK 2: MASTER A OŘEZ (AOI)
    elif st.session_state.step == 2:
        st.subheader(f"🖼️ Nastavení Masteru pro: {st.session_state.active_project}")
        
        # Rozdělíme na sloupce, aby sliders nezabíraly celou šířku
        col_img, col_ctrl = st.columns([2, 1])
        
        with col_ctrl:
            st.caption("Nastavení ořezu (AOI)")
            ax = st.slider("X pozice", 0, 2000, 0, key="slider_x")
            ay = st.slider("Y pozice", 0, 2000, 0, key="slider_y")
            aw = st.slider("Šířka", 100, 2500, 1280, key="slider_w")
            ah = st.slider("Výška", 100, 2500, 1080, key="slider_h")
            m_name = st.text_input("Název Master snímku:", placeholder="např. P1_TOP")
            
            if st.button("📸 VYFOTIT A ULOŽIT", type="primary", use_container_width=True):
                # ... (zde nechat tvůj stávající kód pro focení a ukládání)
                pass

        with col_img:
            # Tady bude náhled kamery (zmenšený automaticky sloupcem)
            st.image("https://via.placeholder.com/640x480.png?text=Nahled+Kamery", use_container_width=True)

            with col_l:
                # ŽIVÝ NÁHLED S OŘEZEM V REÁLNÉM ČASE
                raw_frame = cam.get_frame()
                pil_raw = Image.fromarray(raw_frame)
                
                # ZDE SE DĚJE TEN REÁLNÝ NÁHLED OŘEZU
                # crop((left, top, right, bottom))
                preview_crop = pil_raw.crop((ax, ay, ax + aw, ay + ah))
                
                st.image(preview_crop, caption="Náhled ořezu (AOI)", use_container_width=True)
                st.write(f"📏 Aktuální rozlišení masteru: {aw} x {ah} px")

    # ... (začátek app.py zůstává stejný)

    # KROK 3: ROI DEFINICE (Dashboard layout)
    elif st.session_state.step == 3:
        masters = database.get_masters(st.session_state.active_project)
        if not masters:
            st.error("Žádné Mastery.")
        else:
            # 1. Horní lišta - pevná výška
            m_names = [m[2] for m in masters]
            sel_m_name = st.selectbox("Vyberte Master snímek:", m_names, label_visibility="collapsed")
            curr_m = next(m for m in masters if m[2] == sel_m_name)
            
            img = Image.open(curr_m[8]).convert("RGB")
            draw = ImageDraw.Draw(img)
            old_rois = database.get_rois(curr_m[0])
            valeo_green = "#97BE0D"
            edit_id = st.session_state.get('edit_roi_id', None)

            # Vykreslení zón do podkladu
            for r in old_rois:
                if edit_id == r[0]: continue
                draw.rectangle([r[2], r[3], r[2]+r[4], r[3]+r[5]], outline=valeo_green, width=3)
                draw.text((r[2]+5, r[3]-20), f"{r[1]} [N{r[6]}]", fill=valeo_green)

            # --- HLAVNÍ MŘÍŽKA ---
            col_main, col_side = st.columns([1.5, 1.0])

            with col_main:
                # PEVNÝ KONTEJNER PRO OBRAZ
                image_container = st.container(border=True)
                with image_container:
                    if not (st.session_state.get('add_toggle') or edit_id):
                        st.image(img, use_container_width=True)
                    else:
                        c_key = f"c_{edit_id if edit_id else 'new'}_{len(old_rois)}"
                        # Uprav řádek s cropperem takto:
                        st_cropper(img, realtime_update=True, box_color='#FF9800', key=c_key, should_resize_canvas=False)

            with col_side:
                # PEVNÝ PANEL AKCÍ
                action_panel = st.container(border=True)
                with action_panel:
                    st.subheader("➕ Akce")
                    if not edit_id:
                        add_mode = st.toggle("PŘIDAT NOVOU KONTROLU", key="add_toggle")
                    
                    if st.session_state.get('add_toggle') or edit_id:
                        d_name, d_nok = ("", 0) if not edit_id else (next(r[1] for r in old_rois if r[0] == edit_id), next(r[6]-1 for r in old_rois if r[0] == edit_id))
                        
                        name = st.text_input("Název:", value=d_name)
                        nok = st.selectbox("NOK:", range(1, 9), index=d_nok, format_func=lambda x: f"NOK {x}")
                        
                        if st.button(btn_label, type="primary", use_container_width=True):
                            # Získání dat z cropperu
                            cropper_data = st.session_state[c_key]
                            
                            if cropper_data:
                                # VÝPOČET POMĚRU (Scaling factor)
                                # Zjistíme, jak moc Streamlit fotku zmenšil pro displej
                                canvas_width = cropper_data['width']  # Šířka plátna v prohlížeči
                                actual_width = img.width              # Skutečná šířka souboru
                                ratio = actual_width / canvas_width   # Přepočítací koeficient
                                
                                coords = cropper_data['coords']
                                
                                # Přepočet na skutečné pixely s koeficientem ratio
                                real_left = int(coords['left'] * ratio)
                                real_top = int(coords['top'] * ratio)
                                real_width = int(coords['width'] * ratio)
                                real_height = int(coords['height'] * ratio)

                                if edit_id:
                                    database.update_roi_position(edit_id, real_left, real_top, real_width, real_height)
                                    database.update_roi_nok(edit_id, nok + 1)
                                    st.session_state.edit_roi_id = None
                                else:
                                    database.save_roi(curr_m[0], name, real_left, real_top, real_width, real_height, nok + 1)
                                    if 'add_toggle' in st.session_state: del st.session_state['add_toggle']
                                
                                st.rerun()

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