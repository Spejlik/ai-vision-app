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

    # KROK 3: ROI DEFINICE (Finální verze pro novou knihovnu)
    elif st.session_state.step == 3:
        masters = database.get_masters(st.session_state.active_project)
        if not masters:
            st.error("Žádné Mastery.")
        else:
            m_names = [m[2] for m in masters]
            sel_m_name = st.selectbox("Master:", m_names, label_visibility="collapsed")
            curr_m = next(m for m in masters if m[2] == sel_m_name)
            
            if os.path.exists(curr_m[8]):
                img = Image.open(curr_m[8]).convert("RGB")
                draw = ImageDraw.Draw(img)
                old_rois = database.get_rois(curr_m[0])
                valeo_green = "#97BE0D"
                edit_id = st.session_state.get('edit_roi_id', None)

                # 1. Vykreslení uložených zelených zón do obrázku
                for r in old_rois:
                    if edit_id == r[0]: continue
                    draw.rectangle([r[2], r[3], r[2]+r[4], r[3]+r[5]], outline=valeo_green, width=3)
                    draw.text((r[2]+5, r[3]-20), f"{r[1]} [N{r[6]}]", fill=valeo_green)

                c_l, c_r = st.columns([2, 1])
                
                with c_r:
                    st.write("### ➕ Akce")
                    add_mode = st.toggle("PŘIDAT NOVOU", key="add_toggle") if not edit_id else False
                    
                    if add_mode or edit_id:
                        st.divider()
                        d_name, d_nok = "", 0
                        if edit_id:
                            curr_r = next(r for r in old_rois if r[0] == edit_id)
                            d_name, d_nok = curr_r[1], curr_r[6] - 1

                        name = st.text_input("Název:", value=d_name, placeholder="Název zóny", label_visibility="collapsed")
                        nok = st.selectbox("NOK:", range(1, 9), index=d_nok, format_func=lambda x: f"NOK {x}")
                        
                        c_key = f"c_{edit_id if edit_id else 'new'}_{len(old_rois)}"
                        if st.button("💾 ULOŽIT", type="primary", use_container_width=True):
                            c = st.session_state[c_key]['coords']
                            if edit_id:
                                database.update_roi_position(edit_id, int(c['left']), int(c['top']), int(c['width']), int(c['height']))
                                database.update_roi_nok(edit_id, nok + 1) # +1 protože selectbox indexuje od 0
                                st.session_state.edit_roi_id = None
                            else:
                                database.save_roi(curr_m[0], name, int(c['left']), int(c['top']), int(c['width']), int(c['height']), nok + 1)
                                if 'add_toggle' in st.session_state: del st.session_state['add_toggle']
                            st.rerun()
                        
                        if edit_id and st.button("❌ ZRUŠIT EDITACI", use_container_width=True):
                            st.session_state.edit_roi_id = None
                            st.rerun()

                with c_l:
    # Obalíme cropper do dalšího sloupce nebo kontejneru pro fixaci šířky
    roi = st_cropper(img, realtime_update=True, box_color='#FF9800', key=c_key)
                    else:
                        st_cropper(img, realtime_update=True, box_color='#FF9800', key=c_key, width=550)

                # Seznam zón (Správa)
                st.divider()
                st.caption("⚙️ Správa uložených zón")
                m_cols = st.columns(4)
                for idx, r in enumerate(old_rois):
                    with m_cols[idx % 4]:
                        with st.expander(f"{r[1]} (N{r[6]})"):
                            if st.button("🎮 Edit", key=f"e_{r[0]}", use_container_width=True):
                                st.session_state.edit_roi_id = r[0]
                                st.rerun()
                            if st.button("🗑️ Smazat", key=f"d_{r[0]}", use_container_width=True):
                                database.delete_roi(r[0])
                                st.rerun()

# ... (zbytek monitoring sekce)

elif menu == "Monitoring":
    st.title("📊 Živý monitoring")
    st.write("Zde se zobrazují výsledky inspekce.")
    # Zde pak doděláme tu mřížku detailů (krok 4)