import streamlit as st
import cv2
import database
import camera_manager
import os
from PIL import Image, ImageDraw

# 1. GLOBÁLNÍ KONFIGURACE
st.set_page_config(layout="wide", page_title="Vision System Terminal")

# 2. INICIALIZACE
database.init_db()
cam = camera_manager.BaslerCam()

# Inicializace Session State (Pojistka proti chybám)
if 'setup_image_buffer' not in st.session_state:
    st.session_state.setup_image_buffer = None
if 'active_project' not in st.session_state:
    st.session_state.active_project = None
if 'editing_id' not in st.session_state:
    st.session_state.editing_id = None
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
    st.title("📂 Projekty")
    projs = database.get_projects()
    project_names = [p[1] for p in projs]
    st.session_state.active_project = st.selectbox("Aktivní projekt", project_names if project_names else ["Žádný"])
    
    with st.expander("✨ Nový / Kopírovat"):
        new_name = st.text_input("Název")
        if st.button("Vytvořit", key="side_btn_new"):
            database.save_project(new_name)
            st.rerun()
    
    if st.button("🗑️ SMAZAT PROJEKT", key="side_btn_del"):
        database.delete_project(st.session_state.active_project)
        st.rerun()

# --- DEFINICE TABŮ ---
tab1, tab2, tab3, tab4 = st.tabs(["🚀 BĚH", "🎯 MASTER", "🔍 ZÓNY", "🔌 I/O"])

# --- TAB 1: BĚH ---
with tab1:
    st.info(f"Systém připraven. Aktivní projekt: {st.session_state.active_project}")

# --- TAB 2: MASTER (Interaktivní ořez) ---
with tab2:
    st.subheader("📸 Nastavení Master snímků")
    col_ctrl, col_img = st.columns([1, 2])
    
    with col_ctrl:
        if st.button("📷 NAČÍST Z KAMERY", key="master_cam_btn", use_container_width=True):
            st.session_state.setup_image_buffer = cam.get_frame()

        if st.session_state.setup_image_buffer is not None:
            # Získáme rozměry originálu
            h, w = st.session_state.setup_image_buffer.shape[:2]
            
            # POSUVNÍKY (Teď budou ovládat kreslení)
            ax = st.slider("X (vlevo/vpravo)", 0, w, 0, key="m_x")
            ay = st.slider("Y (nahoru/dolů)", 0, h, 0, key="m_y")
            aw = st.slider("Šířka výřezu", 100, w, w, key="m_w")
            ah = st.slider("Výška výřezu", 100, h, h, key="m_h")
            
            m_id_name = st.text_input("Název (např. P1, P2)", "P1")
            
            if st.button("💾 ULOŽIT MASTER", key="master_save_btn", type="primary", use_container_width=True):
                # Skutečné oříznutí matice před uložením
                img = st.session_state.setup_image_buffer
                # Ošetření přetečení souřadnic
                cropped = img[ay:min(ay+ah, h), ax:min(ax+aw, w)]
                
                if not os.path.exists("masters"): os.makedirs("masters")
                path = f"masters/{st.session_state.active_project}_{m_id_name}.png"
                cv2.imwrite(path, cv2.cvtColor(cropped, cv2.COLOR_RGB2BGR))
                
                database.add_master(st.session_state.active_project, path, ax, ay, aw, ah)
                st.success(f"Vytvořen výřez a uložen jako {m_id_name}")
                st.rerun()

    with col_img:
        if st.session_state.setup_image_buffer is not None:
            # VYTVOŘENÍ NÁHLEDU S ČERVENÝM RÁMEČKEM
            preview_img = st.session_state.setup_image_buffer.copy()
            # Nakreslíme rámeček přímo do kopie obrazu pro náhled
            cv2.rectangle(preview_img, (ax, ay), (ax+aw, ay+ah), (255, 0, 0), 5)
            
            st.image(preview_img, use_container_width=True, caption="Červený rámeček ukazuje budoucí ořez")

# --- TAB 3: ZÓNY (Elvac Style Compact) ---
with tab3:
    st.subheader("📍 Konfigurace inspekcí")
    all_masters = database.get_masters(st.session_state.active_project)
    
    if not all_masters:
        st.warning("Vytvořte Master v záložce 🎯 MASTER")
    else:
        # Horizontální výběr Masteru
        cols = st.columns(8)
        if st.session_state.selected_master_id is None:
            st.session_state.selected_master_id = all_masters[0][0]

        for i, m in enumerate(all_masters):
            with cols[i % 8]:
                is_act = (m[0] == st.session_state.selected_master_id)
                if st.button(f"{m[1]}", key=f"sel_m_{m[0]}", type="primary" if is_act else "secondary"):
                    st.session_state.selected_master_id = m[0]
                    st.rerun()

        st.divider()

        # Editor
        sel = next((m for m in all_masters if m[0] == st.session_state.selected_master_id), all_masters[0])
        if os.path.exists(sel[2]):
            img = Image.open(sel[2])
            W, H = img.size
            all_rois = database.get_rois(sel[0])
            
            c_left, c_right = st.columns([1, 1.8])
            with c_left:
                curr = next((r for r in all_rois if r[0] == st.session_state.editing_id), None)
                zn = st.text_input("Název zóny", value=curr[1] if curr else "Nová", key="roi_name")
                
                r1, r2 = st.columns(2)
                zx = r1.number_input("X", 0, W, curr[2] if curr else 50)
                zy = r2.number_input("Y", 0, H, curr[3] if curr else 50)
                zw = r1.number_input("Šířka", 10, W, curr[4] if curr else 100)
                zh = r2.number_input("Výška", 10, H, curr[5] if curr else 100)
                
                if st.button("💾 ULOŽIT ZÓNU", key="roi_save_final", type="primary", use_container_width=True):
                    if st.session_state.editing_id: database.delete_roi(st.session_state.editing_id)
                    database.save_roi(sel[0], zn, zx, zy, zw, zh, 1)
                    st.session_state.editing_id = None
                    st.rerun()
                
                st.write("---")
                for r in all_rois:
                    cl, cr = st.columns([3, 1])
                    cl.caption(r[1])
                    if cr.button("✏️", key=f"ed_{r[0]}"):
                        st.session_state.editing_id = r[0]
                        st.rerun()

            with c_right:
                draw = ImageDraw.Draw(img)
                for r in all_rois:
                    color = "#ff4b4b" if r[0] == st.session_state.editing_id else "#deff9a"
                    draw.rectangle([r[2], r[3], r[2]+r[4], r[3]+r[5]], outline=color, width=3)
                
                # Zobrazení s omezenou šířkou
                st.image(img, width=700)

# --- TAB 4: I/O ---
with tab4:
    st.write("Diagnostika PLC")