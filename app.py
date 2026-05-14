import streamlit as st
import cv2
import database
import camera_manager
import os
from PIL import Image

# 1. Globální konfigurace a styl
st.set_page_config(layout="wide", page_title="Vision System Terminal")

# CSS pro minimalizaci okrajů a profesionální vzhled
st.markdown("""
    <style>
        .block-container { padding-top: 1rem; padding-bottom: 0rem; }
        header { visibility: hidden; }
        .stTabs [data-baseweb="tab-list"] { gap: 10px; }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            white-space: pre-wrap;
            background-color: #f0f2f6;
            border-radius: 5px;
            gap: 1px;
            padding-left: 20px;
            padding-right: 20px;
        }
    </style>
""", unsafe_allow_html=True)

# Inicializace hardwaru
database.init_db()
cam = camera_manager.BaslerCam()

# 2. Sidebar - Statické informace a výběr projektu
with st.sidebar:
    st.title("🎛️ Ovládací panel")
    
    projs = database.get_projects()
    project_names = [p[1] for p in projs] if projs else []
    
    if project_names:
        active_p = st.selectbox("Aktivní projekt", project_names)
        st.session_state.active_project = active_p
    else:
        st.warning("Vytvořte projekt v sekci Nastavení.")
        st.session_state.active_project = None

    st.divider()
    st.subheader("📡 Status linky")
    st.success("SYSTÉM READY")
    st.metric("Takt", "1.2 s")

# 3. Hlavní rozhraní pomocí Záložek (Tabs)
tab_run, tab_setup, tab_io = st.tabs(["🚀 BĚH (RUNTIME)", "⚙️ NASTAVENÍ (SETUP)", "🔌 I/O DIAGNOSTIKA"])

# --- TAB 2: SETUP MASTER ---
with tab2:
    if 'setup_image_buffer' not in st.session_state:
        st.session_state.setup_image_buffer = None

    col_ctrl, col_img = st.columns([1, 2])
    
    with col_ctrl:
        if st.button("📸 NAČÍST OBRAZ PRO MASTER", use_container_width=True):
            st.session_state.setup_image_buffer = cam.get_frame()

        if st.session_state.setup_image_buffer is not None:
            h, w = st.session_state.setup_image_buffer.shape[:2]
            ax = st.slider("X pozice", 0, w, 0, key="m_x")
            ay = st.slider("Y pozice", 0, h, 0, key="m_y")
            aw = st.slider("Šířka", 100, w, 1280, key="m_w")
            ah = st.slider("Výška", 100, h, 1024, key="m_h")
            
            m_name = st.text_input("Název Masteru", "P1")
            
            if st.button("💾 ULOŽIT OŘEZANÝ MASTER", type="primary", use_container_width=True):
                # KLÍČOVÁ OPRAVA: Skutečné oříznutí matice
                cropped = st.session_state.setup_image_buffer[ay:ay+ah, ax:ax+aw]
                path = f"masters/{st.session_state.active_project}_{m_name}.png"
                if not os.path.exists("masters"): os.makedirs("masters")
                cv2.imwrite(path, cv2.cvtColor(cropped, cv2.COLOR_RGB2BGR))
                
                # Uložíme do DB i informaci o tom, že toto je ořez
                database.add_master(st.session_state.active_project, path, ax, ay, aw, ah)
                st.success(f"Uloženo a oříznuto na {aw}x{ah}")
                st.rerun()

    with col_img:
        if st.session_state.setup_frame is None and st.session_state.setup_image_buffer is not None:
             preview = st.session_state.setup_image_buffer.copy()
             cv2.rectangle(preview, (ax, ay), (ax+aw, ay+ah), (255, 0, 0), 10)
             st.image(preview, use_container_width=True)

# --- TAB 3: ZÓNY (ROI & NOK) ---
with tab3:
    masters = database.get_masters(st.session_state.active_project)
    if not masters or masters[0][2] == "":
        st.warning("⚠️ Nejdříve uložte Master v předchozí záložce!")
    else:
        m_id, m_name, m_path = masters[0][0], masters[0][1], masters[0][2]
        img = Image.open(m_path).convert("RGB")
        W, H = img.size
        
        col_z_ctrl, col_z_img = st.columns([1, 2])
        
        with col_z_ctrl:
            st.subheader("📍 Nová inspekční zóna")
            zn = st.text_input("Název zóny:", "Spona_L")
            zx = st.slider("ROI X", 0, W, W//2, key="roi_x")
            zy = st.slider("ROI Y", 0, H, H//2, key="roi_y")
            zw = st.slider("ROI Šířka", 10, W, 100, key="roi_w")
            zh = st.slider("ROI Výška", 10, H, 100, key="roi_h")
            nok = st.selectbox("Přiřadit NOK (PLC registr):", range(1, 11))
            
            if st.button("💾 ULOŽIT ZÓNU A NOK", use_container_width=True, type="primary"):
                database.save_roi(m_id, zn, zx, zy, zw, zh, nok)
                st.success(f"Zóna {zn} (NOK {nok}) uložena!")
                st.rerun()

            st.divider()
            rois = database.get_rois(m_id)
            for r in rois:
                st.write(f"✅ {r[1]} -> NOK {r[6]}")

        with col_z_img:
            from PIL import ImageDraw
            draw = ImageDraw.Draw(img)
            # Vykreslení uložených
            for r in rois:
                draw.rectangle([r[2], r[3], r[2]+r[4], r[3]+r[5]], outline="#deff9a", width=5)
            # Aktivní náhled
            draw.rectangle([zx, zy, zx+zw, zy+zh], outline="orange", width=3)
            st.image(img, use_container_width=True)