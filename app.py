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

# 3. Inicializace Session State (aby nic nemizelo a netřáslo se)
if 'setup_image_buffer' not in st.session_state:
    st.session_state.setup_image_buffer = None
if 'active_project' not in st.session_state:
    st.session_state.active_project = None

# CSS Styl pro profesionální vzhled
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
    
    # Hlavní výběr
    st.session_state.active_project = st.selectbox("Aktivní projekt", project_names if project_names else ["Žádný"])
    
    st.divider()
    
    # Sekce pro vytvoření a kopírování
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

    # Sekce pro údržbu
    with st.expander("🛠️ Údržba projektu"):
        if st.session_state.active_project != "Žádný":
            st.warning(f"Akce pro: {st.session_state.active_project}")
            
            # Přejmenování
            new_title = st.text_input("Přejmenovat na:")
            if st.button("Potvrdit přejmenování"):
                # Tady by byla SQL UPDATE masters SET name = new_title WHERE name = active_project
                st.info("Funkce ve vývoji...") 

            st.divider()
            
            # Smazání
            if st.button("🗑️ SMAZAT PROJEKT", type="secondary", use_container_width=True):
                if st.session_state.active_project:
                    database.delete_project(st.session_state.active_project)
                    st.rerun()
                    
    # Záloha (export do JSON/CSV by byl fajn, ale zatím uděláme info)
    if st.button("💾 ZÁLOHOVAT DB"):
        import shutil
        shutil.copy("vision_system.db", "vision_system_backup.db")
        st.success("Záloha vytvořena!")

# --- TAB 3: ZÓNY (ROI S EXPLICITNÍM ZVÝRAZNĚNÍM EDITACE) ---
with tab3:
    st.subheader("📍 Správa inspekčních zón")
    
    if 'editing_id' not in st.session_state:
        st.session_state.editing_id = None

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
                # Najdeme data editované zóny
                current_roi = next((r for r in all_rois if r[0] == st.session_state.editing_id), None)
                
                if st.session_state.editing_id:
                    st.markdown(f"### ✏️ Editace: <span style='color:#ff4b4b'>{current_roi[1] if current_roi else ''}</span>", unsafe_allow_html=True)
                else:
                    st.write("### ➕ Nová zóna")

                # Dynamické hodnoty
                default_name = current_roi[1] if current_roi else "Nová zóna"
                default_x = current_roi[2] if current_roi else W//2
                default_y = current_roi[3] if current_roi else H//2
                default_w = current_roi[4] if current_roi else 150
                default_h = current_roi[5] if current_roi else 150
                default_nok = current_roi[6] if current_roi else 1

                zn = st.text_input("Název zóny", value=default_name)
                zx = st.slider("ROI X", 0, W, default_x)
                zy = st.slider("ROI Y", 0, H, default_y)
                zw = st.slider("ROI Šířka", 10, W, default_w)
                zh = st.slider("ROI Výška", 10, H, default_h)
                nok = st.selectbox("NOK registr", range(1, 11), index=default_nok-1)
                
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
                    # Zvýraznění pozadí v seznamu pomocí Markdownu
                    bg_color = "rgba(255, 75, 75, 0.2)" if is_editing else "transparent"
                    
                    st.markdown(f"<div style='background-color:{bg_color}; padding:5px; border-radius:5px;'>", unsafe_allow_html=True)
                    col_txt, col_ed, col_del = st.columns([3, 1, 1])
                    label = f"🎯 **{r[1]}**" if is_editing else r[1]
                    col_txt.write(label)
                    
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
                        # Editovaná zóna - TUČNÁ ČERVENÁ
                        draw.rectangle([zx, zy, zx+zw, zy+zh], outline="#ff4b4b", width=8)
                        draw.text((zx, zy-25), f"EDITUJI: {zn}", fill="#ff4b4b")
                    else:
                        # Ostatní zóny - TENKÁ ZELENÁ
                        draw.rectangle([r[2], r[3], r[2]+r[4], r[3]+r[5]], outline="#deff9a", width=3)
                        draw.text((r[2], r[3]-20), r[1], fill="#deff9a")
                
                # Pokud vytváříme novou (a nic needitujeme), nakreslíme ji oranžově
                if not st.session_state.editing_id:
                    draw.rectangle([zx, zy, zx+zw, zy+zh], outline="orange", width=3)
                
                st.image(img_roi, use_container_width=True)

# --- TAB 4: I/O ---
with tab4:
    st.subheader("Diagnostika Modbus")
    st.write("Stav PLC registrů...")