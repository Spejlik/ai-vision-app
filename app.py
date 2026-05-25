import streamlit as st
import cv2
import database
import camera_manager
import os
import time
from PIL import Image, ImageDraw

# 1. GLOBÁLNÍ KONFIGURACE
st.set_page_config(layout="wide", page_title="Vision System Terminal")

# 2. INICIALIZACE
database.init_db()
# cam = camera_manager.BaslerCam() 

if 'setup_image_buffer' not in st.session_state:
    st.session_state.setup_image_buffer = None
if 'active_project' not in st.session_state:
    st.session_state.active_project = None
if 'selected_master_id' not in st.session_state:
    st.session_state.selected_master_id = None

# CSS pro profesionální vzhled
st.markdown("""
    <style>
        .block-container { padding-top: 1rem; }
        header { visibility: hidden; }
        .stButton>button { border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR: SPRÁVA PROJEKTŮ ---
with st.sidebar:
    st.title("⚙️ Konfigurace")
    
    new_project_name = st.text_input("Název nového projektu", key="new_proj_input")
    if st.button("➕ Vytvořit projekt", use_container_width=True):
        if new_project_name.strip():
            database.add_project(new_project_name.strip())
            st.success(f"Projekt {new_project_name} vytvořen!")
            st.rerun()

    st.divider()

    projects = database.get_projects()
    if projects:
        if 'active_project' not in st.session_state or st.session_state.active_project not in projects:
            st.session_state.active_project = projects[0]
            
        st.session_state.active_project = st.selectbox(
            "Vyberte aktivní projekt", 
            projects,
            index=projects.index(st.session_state.active_project)
        )
    else:
        st.warning("⚠️ Nejdříve vytvořte projekt")
        st.session_state.active_project = None

# --- DEFINICE TABŮ ---
tab1, tab2, tab3, tab4 = st.tabs(["🚀 BĚH", "🎯 MASTER", "🔍 ZÓNY", "🔌 I/O"])

# --- TAB 1: BĚH ---
with tab1:
    st.subheader(f"🚀 Live Inspekce - Projekt: {st.session_state.active_project}")
    
    if st.session_state.active_project:
        active_p = st.session_state.active_project
        all_masters = database.get_all_masters()
        
        if not all_masters:
            st.warning("⚠️ Nemáte vytvořené žádné Mastery. Systém nemá z čeho inspekci spouštět.")
        else:
            col_run_1, col_run_2 = st.columns([2.5, 1])
            
            with col_run_1:
                live_placeholder = st.empty()
                
            with col_run_2:
                st.markdown("### 📊 Výstupy PLC (NOK 1-8)")
                st.write("Indikátory digitálních výstupů do linky:")
                
                io_col1, io_col2 = st.columns(2)
                plc_indicators = {}
                
                for idx in range(1, 9):
                    target_col = io_col1 if idx <= 4 else io_col2
                    with target_col:
                        plc_indicators[idx] = st.empty()
            
            st.divider()
            
            run_engine = st.toggle("▶️ SPUSTIT ŽIVOU INSPEKCI", key="run_engine_toggle")
            current_outputs = {i: False for i in range(1, 9)}

            if run_engine:
                import random
                
                # Použijeme cestu z prvního masteru pro simulaci kamery
                m_path_sim = all_masters[0][2]
                
                if os.path.exists(m_path_sim):
                    live_frame = Image.open(m_path_sim).convert("RGB")
                else:
                    live_frame = Image.new('RGB', (1200, 800), color=(70, 109, 137))
                    
                live_draw = ImageDraw.Draw(live_frame)
                W_live = live_frame.size[0]
                line_w = max(2, int(W_live * 0.007))
                
                # Procházíme zóny pro aktivní projekt
                for m in all_masters:
                    m_id = m[0]
                    rois = database.get_rois(m_id, active_p)
                    
                    for r in rois:
                        rx, ry, rw, rh, r_nok = r[4], r[5], r[6], r[7], r[8]
                        
                        # Simulace kontroly: 85% šance na OK, 15% na chybu
                        is_zone_ok = random.random() > 0.15
                        
                        if not is_zone_ok:
                            current_outputs[r_nok] = True
                        
                        zone_color = "#00FF00" if is_zone_ok else "#FF0000"
                        
                        # Vykreslení obdélníku zóny
                        live_draw.rectangle([rx, ry, rx+rw, ry+rh], outline=zone_color, width=line_w)
                        live_draw.text((rx, ry-15), f"{r[3]} (NOK{r_nok})", fill=zone_color)
                
                live_placeholder.image(live_frame, use_container_width=True, caption="Živý stream (Simulace z Master snímku)")
                
                # Vykreslení barevných kontrolek
                for idx in range(1, 9):
                    if current_outputs.get(idx, False):
                        plc_indicators[idx].markdown(f"<div style='background-color:#FF4B4B; color:white; padding:10px; border-radius:5px; text-align:center; font-weight:bold; margin-bottom:5px;'>🚨 NOK {idx}</div>", unsafe_allow_html=True)
                    else:
                        plc_indicators[idx].markdown(f"<div style='background-color:#00D48A; color:white; padding:10px; border-radius:5px; text-align:center; font-weight:bold; margin-bottom:5px;'>✅ OK {idx}</div>", unsafe_allow_html=True)
            else:
                for idx in range(1, 9):
                    plc_indicators[idx].markdown(f"<div style='background-color:#E0E0E0; color:#666; padding:10px; border-radius:5px; text-align:center; margin-bottom:5px;'>⚫ Výstup {idx}</div>", unsafe_allow_html=True)
                live_placeholder.info("Inspekce je zastavena. Zapněte ji přepínačem níže.")
    else:
        st.warning("⚠️ Nejdříve vyberte nebo vytvořte projekt v levém panelu.")
# --- TAB 2: MASTER ---
with tab2:
    st.subheader("📸 Nastavení Master snímků")
    col_ctrl, col_img = st.columns([1, 2])
    
    with col_ctrl:
        st.write("### ✂️ Definice výřezu")
        m_id_name = st.text_input("Název Masteru (např. Kamera 1)")
        
        # Slidery pro ořez (ax, ay, aw, ah)
        ax = st.slider("X začátek", 0, 2000, 100)
        ay = st.slider("Y začátek", 0, 2000, 100)
        aw = st.slider("Šířka výřezu", 10, 2000, 500)
        ah = st.slider("Výška výřezu", 10, 2000, 500)

        if st.button("💾 ULOŽIT MASTER", type="primary", use_container_width=True):
            if m_id_name and st.session_state.setup_image_buffer:
                if not os.path.exists("masters"):
                    os.makedirs("masters")
                
                filename = f"masters/master_{int(time.time())}.png"
                img = st.session_state.setup_image_buffer
                cropped_img = img.crop((ax, ay, ax + aw, ay + ah))
                cropped_img.save(filename)
                
                database.add_master(m_id_name, filename, ax, ay, aw, ah)
                st.success(f"Master {m_id_name} uložen!")
                st.rerun()
            else:
                st.error("Zadejte název a zachyťte snímek!")

    with col_img:
        if st.button("📸 Zachytit testovací snímek"):
            st.session_state.setup_image_buffer = Image.new('RGB', (1200, 800), color=(73, 109, 137))
        
        if st.session_state.setup_image_buffer is not None:
            preview_img = st.session_state.setup_image_buffer.copy()
            
            # Adaptivní tloušťka pro náhled ořezu
            cam_w = preview_img.size[0]
            master_line_w = max(2, int(cam_w * 0.007))
            
            draw = ImageDraw.Draw(preview_img)
            draw.rectangle([ax, ay, ax+aw, ay+ah], outline="red", width=master_line_w)
            st.image(preview_img, use_container_width=True, caption="Červený rámeček ukazuje budoucí ořez")

# --- TAB 3: ZÓNY ---
with tab3:
    active_p = st.session_state.active_project
    st.info(f"🏗️ Aktuálně nastavujete zóny pro projekt: **{active_p}**")
    
    all_masters = database.get_all_masters()
    
    if not all_masters:
        st.warning("⚠️ Knihovna Masterů je prázdná.")
    else:
        if 'selected_master_id' not in st.session_state:
            st.session_state.selected_master_id = all_masters[0][0]

        # Galerie masterů
        m_cols = st.columns(8)
        for i, m in enumerate(all_masters):
            m_id_loop, m_name_loop, m_path_loop = m[0], m[1], m[2]
            with m_cols[i % 8]:
                if os.path.exists(m_path_loop):
                    st.image(m_path_loop, use_container_width=True)
                
                if st.button(f"{m_name_loop}", key=f"btn_m_{m_id_loop}", use_container_width=True,
                             type="primary" if (m_id_loop == st.session_state.selected_master_id) else "secondary"):
                    st.session_state.selected_master_id = m_id_loop
                    st.rerun()

        st.divider()
        
        # Načtení aktivního masteru
        sel_m = next((m for m in all_masters if m[0] == st.session_state.selected_master_id), all_masters[0])
        m_id, m_name, m_path = sel_m[0], sel_m[1], sel_m[2]
        
        if os.path.exists(m_path):
            img_roi = Image.open(m_path).convert("RGB")
            W, H = img_roi.size
            all_rois = database.get_rois(m_id, active_p)
            
            # Definice sloupců - sjednoceno na c_ctrl a c_viz
            c_ctrl, c_viz = st.columns([1, 1.8])
            
            with c_ctrl:
                st.markdown(f"### 🔧 Nastavení zón: {m_name}")
                zn = st.text_input("Název zóny", value=f"Zóna {len(all_rois)+1}")
                nok_val = st.selectbox("Přiřazení chyby (NOK 1-8)", range(1, 9), index=0)
                
                zx = st.slider("X", 0, W, 50, key="sx")
                zy = st.slider("Y", 0, H, 50, key="sy")
                zw = st.slider("Šířka", 10, W, 100, key="sw")
                zh = st.slider("Výška", 10, H, 100, key="sh")
                
                if st.button("💾 ULOŽIT ZÓNU", type="primary", use_container_width=True):
                    database.save_roi(m_id, active_p, zn, zx, zy, zw, zh, nok_val)
                    st.success("Zóna uložena!")
                    st.rerun()

            with c_viz:
                draw = ImageDraw.Draw(img_roi)
                
                # Výpočet stabilní tloušťky čáry na obrazovce
                line_w = max(2, int(W * 0.007))
                
                # 1. Kreslení už uložených zón
                for r in all_rois:
                    rx, ry, rw, rh = r[4], r[5], r[6], r[7]
                    draw.rectangle([rx, ry, rx+rw, ry+rh], outline="#00FF00", width=line_w)
                    draw.text((rx, ry-15), f"{r[3]} (NOK{r[8]})", fill="#00FF00")

                # 2. Kreslení oranžového náhledu z aktuálních sliderů
                draw.rectangle([zx, zy, zx+zw, zy+zh], outline="orange", width=line_w + 2)
                
                st.image(img_roi, use_container_width=True, caption=f"Pracovní plocha: {m_name}")

# --- TAB 4: I/O ---
with tab4:
    st.write("Diagnostika PLC rozhraní")