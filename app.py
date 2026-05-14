import streamlit as st
import cv2
import database
import camera_manager
import os
from PIL import Image, ImageDraw

# 1. Globální konfigurace (MUSÍ BÝT PRVNÍ)
st.set_page_config(layout="wide", page_title="Vision System Terminal")

# 2. Inicializace databáze a hardwaru
database.init_db()
cam = camera_manager.BaslerCam()

# 3. Inicializace Session State
if 'setup_image_buffer' not in st.session_state:
    st.session_state.setup_image_buffer = None
if 'active_project' not in st.session_state:
    st.session_state.active_project = None
if 'editing_id' not in st.session_state:
    st.session_state.editing_id = None

# CSS Styl
st.markdown("""
    <style>
        .block-container { padding-top: 1rem; padding-bottom: 0rem; }
        header { visibility: hidden; }
        .stTabs [data-baseweb="tab-list"] { gap: 10px; }
        .stTabs [data-baseweb="tab"] {
            height: 50px; background-color: #f0f2f6; border-radius: 5px;
        }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR: SPRÁVA PROJEKTŮ ---
with st.sidebar:
    st.title("📂 Správa projektů")
    projs = database.get_projects()
    project_names = [p[1] for p in projs]
    
    st.session_state.active_project = st.selectbox("Aktivní projekt", project_names if project_names else ["Žádný"])
    st.divider()
    
    with st.expander("✨ Nový / Kopírovat"):
        new_p_name = st.text_input("Název nového projektu")
        col_new, col_copy = st.columns(2)
        if col_new.button("Vytvořit prázdný", use_container_width=True):
            if new_p_name:
                database.save_project(new_p_name)
                st.rerun()
        if col_copy.button("Kopírovat akt.", use_container_width=True):
            if new_p_name and st.session_state.active_project != "Žádný":
                database.duplicate_project(st.session_state.active_project, new_p_name)
                st.rerun()

    with st.expander("🛠️ Údržba projektu"):
        if st.session_state.active_project != "Žádný":
            st.warning(f"Akce pro: {st.session_state.active_project}")
            if st.button("🗑️ SMAZAT PROJEKT", type="secondary", use_container_width=True):
                database.delete_project(st.session_state.active_project)
                st.rerun()
                    
    if st.button("💾 ZÁLOHOVAT DB"):
        import shutil
        shutil.copy("vision_system.db", "vision_system_backup.db")
        st.success("Záloha vytvořena!")

# --- DEFINICE TABŮ ---
tab1, tab2, tab3, tab4 = st.tabs(["🚀 BĚH", "🎯 MASTER", "🔍 ZÓNY", "🔌 I/O"])

# --- TAB 1: BĚH ---
with tab1:
    st.subheader("Živý monitoring")
    st.info(f"Aktivní projekt: {st.session_state.active_project}. Systém připraven.")

# --- TAB 2: MASTER ---
with tab2:
    st.subheader(f"Nastavení Masteru pro: {st.session_state.active_project}")
    col_ctrl, col_img = st.columns([1, 2])
    
    with col_ctrl:
        if st.button("📸 NAČÍST OBRAZ Z KAMERY", use_container_width=True):
            st.session_state.setup_image_buffer = cam.get_frame()

        if st.session_state.setup_image_buffer is not None:
            h, w = st.session_state.setup_image_buffer.shape[:2]
            ax = st.slider("X pozice", 0, w-100, 0)
            ay = st.slider("Y pozice", 0, h-100, 0)
            aw = st.slider("Šířka", 100, w, 1280)
            ah = st.slider("Výška", 100, h, 1024)
            m_name = st.text_input("Název Masteru", "P1")
            
            if st.button("💾 ULOŽIT MASTER", type="primary", use_container_width=True):
                img_to_crop = st.session_state.setup_image_buffer
                cropped = img_to_crop[ay:ay+ah, ax:ax+aw]
                if not os.path.exists("masters"): os.makedirs("masters")
                path = f"masters/{st.session_state.active_project}_{m_name}.png"
                cv2.imwrite(path, cv2.cvtColor(cropped, cv2.COLOR_RGB2BGR))
                database.add_master(st.session_state.active_project, path, ax, ay, aw, ah)
                st.success("Master uložen!")
                st.rerun()

    with col_img:
        if st.session_state.setup_image_buffer is not None:
            preview = st.session_state.setup_image_buffer.copy()
            cv2.rectangle(preview, (ax, ay), (ax+aw, ay+ah), (255, 0, 0), 10)
            st.image(preview, use_container_width=True)

# --- TAB 3: ZÓNY ---
with tab3:
    st.subheader("📍 Správa inspekčních zón")
    masters = database.get_masters(st.session_state.active_project)
    
    if not masters or not masters[0][2]:
        st.warning("Nejdříve uložte Master v záložce 🎯 MASTER")
    else:
        m_id, m_name, m_path = masters[0][0], masters[0][1], masters[0][2]
        if os.path.exists(m_path):
            img_roi = Image.open(m_path).convert("RGB")
            W, H = img_roi.size
            all_rois = database.get_rois(m_id)
            c_z1, c_z2 = st.columns([1, 2])
            
            with c_z1:
                current_roi = next((r for r in all_rois if r[0] == st.session_state.editing_id), None)
                if st.session_state.editing_id:
                    st.markdown(f"### ✏️ Editace: <span style='color:#ff4b4b'>{current_roi[1] if current_roi else ''}</span>", unsafe_allow_html=True)
                else:
                    st.write("### ➕ Nová zóna")

                zn = st.text_input("Název zóny", value=current_roi[1] if current_roi else "Nová zóna")
                zx = st.slider("ROI X", 0, W, current_roi[2] if current_roi else W//2)
                zy = st.slider("ROI Y", 0, H, current_roi[3] if current_roi else H//2)
                zw = st.slider("ROI Šířka", 10, W, current_roi[4] if current_roi else 150)
                zh = st.slider("ROI Výška", 10, H, current_roi[5] if current_roi else 150)
                nok = st.selectbox("NOK registr", range(1, 11), index=(current_roi[6]-1) if current_roi else 0)
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("💾 ULOŽIT", type="primary", use_container_width=True):
                        if st.session_state.editing_id:
                            database.delete_roi(st.session_state.editing_id)
                        database.save_roi(m_id, zn, zx, zy, zw, zh, nok)
                        st.session_state.editing_id = None
                        st.rerun()
                with col_btn2:
                    if st.button("✖️ ZRUŠIT", use_container_width=True):
                        st.session_state.editing_id = None
                        st.rerun()

                st.divider()
                st.write("### 📋 Seznam zón")
                for r in all_rois:
                    is_editing = (r[0] == st.session_state.editing_id)
                    bg_color = "rgba(255, 75, 75, 0.2)" if is_editing else "transparent"
                    st.markdown(f"<div style='background-color:{bg_color}; padding:5px; border-radius:5px;'>", unsafe_allow_html=True)
                    col_txt, col_ed, col_del = st.columns([3, 1, 1])
                    col_txt.write(f"🎯 **{r[1]}**" if is_editing else r[1])
                    if col_ed.button("✏️", key=f"ed_{r[0]}"):
                        st.session_state.editing_id = r[0]
                        st.rerun()
                    if col_del.button("🗑️", key=f"del_{r[0]}"):
                        database.delete_roi(r[0])
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

            with c_z2:
                draw = ImageDraw.Draw(img_roi)
                for r in all_rois:
                    if r[0] == st.session_state.editing_id:
                        draw.rectangle([zx, zy, zx+zw, zy+zh], outline="#ff4b4b", width=8)
                        draw.text((zx, zy-25), f"EDITUJI: {zn}", fill="#ff4b4b")
                    else:
                        draw.rectangle([r[2], r[3], r[2]+r[4], r[3]+r[5]], outline="#deff9a", width=3)
                        draw.text((r[2], r[3]-20), r[1], fill="#deff9a")
                if not st.session_state.editing_id:
                    draw.rectangle([zx, zy, zx+zw, zy+zh], outline="orange", width=3)
                st.image(img_roi, use_container_width=True)
        else:
            st.error(f"Soubor {m_path} nenalezen.")

# --- TAB 4: I/O ---
with tab4:
    st.subheader("Diagnostika Modbus")
    st.write("Stav PLC registrů...")