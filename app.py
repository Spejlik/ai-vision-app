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
                
                database.add_master(st.session_state.active_project, m_id_name, path, ax, ay, aw, ah)
                st.success(f"Vytvořen výřez a uložen jako {m_id_name}")
                st.rerun()

    with col_img:
        if st.session_state.setup_image_buffer is not None:
            # VYTVOŘENÍ NÁHLEDU S ČERVENÝM RÁMEČKEM
            preview_img = st.session_state.setup_image_buffer.copy()
            # Nakreslíme rámeček přímo do kopie obrazu pro náhled
            cv2.rectangle(preview_img, (ax, ay), (ax+aw, ay+ah), (255, 0, 0), 5)
            
            st.image(preview_img, use_container_width=True, caption="Červený rámeček ukazuje budoucí ořez")

# --- TAB 3: ZÓNY (OPRAVENÝ COMPACT LAYOUT) ---
with tab3:
    all_masters = database.get_masters(st.session_state.active_project)
    
    if not all_masters:
        st.warning("⚠️ Nejdříve vytvořte Master v záložce MASTER.")
    else:
        st.write("### 🗂️ Galerie Masterů")
        
        # Inicializace session state pro výběr, pokud neexistuje
        if 'selected_master_id' not in st.session_state or st.session_state.selected_master_id is None:
            st.session_state.selected_master_id = all_masters[0][0]

        # VYTVOŘENÍ HORIZONTÁLNÍ GALERIE (vše v jedné řadě)
        num_masters = len(all_masters)
        # Vytvoříme sloupce (max 6-8, aby se to vešlo na obrazovku)
        cols = st.columns(num_masters if num_masters < 8 else 8)
        
        for i, m in enumerate(all_masters):
            m_id, m_name, m_path = m[0], m[1], m[2]
            with cols[i % 8]:
                # Malý náhled (aby to nebylo obří)
                if os.path.exists(m_path):
                    st.image(m_path, use_container_width=True)
                
                # Tlačítko pro výběr
                is_active = (m_id == st.session_state.selected_master_id)
                if st.button(f"🎯 {m_name}", key=f"sel_m_{m_id}", use_container_width=True, 
                             type="primary" if is_active else "secondary"):
                    st.session_state.selected_master_id = m_id
                    st.rerun()

        st.divider()

        # NAČTENÍ DAT PRO VYBRANÝ MASTER
        sel_m = next((m for m in all_masters if m[0] == st.session_state.selected_master_id), all_masters[0])
        m_id, m_name, m_path = sel_m[0], sel_m[1], sel_m[2]
        
        # Dál už pokračuje tvůj kód pro col_ctrl a col_viz (editor)...
            
            with col_ctrl:
                st.markdown(f"### 🔧 Nastavení pro: {m_name}")
                
                # Načteme existující ROI pro tento Master z DB
                all_rois = database.get_rois(m_id)
                
                # Zjistíme, zda právě něco editujeme
                curr_roi = next((r for r in all_rois if r[0] == st.session_state.editing_id), None)
                
                # --- FORMULÁŘ ---
                with st.container(border=True):
                    st.write("📝 **Detail zóny**")
                    zn = st.text_input("Název / Označení", value=curr_roi[2] if curr_roi else f"Zóna {len(all_rois)+1}")
                    
                    r1, r2 = st.columns(2)
                    zx = r1.number_input("X", 0, W, curr_roi[3] if curr_roi else 100)
                    zy = r2.number_input("Y", 0, H, curr_roi[4] if curr_roi else 100)
                    zw = r1.number_input("Šířka", 10, W, curr_roi[5] if curr_roi else 150)
                    zh = r2.number_input("Výška", 10, H, curr_roi[6] if curr_roi else 150)
                    
                    # Výběr NOK (1 až 8)
                    nok_list = [f"NOK {i}" for i in range(1, 9)]
                    selected_nok = st.selectbox("Přiřazení chyby", nok_list, 
                                                index=(curr_roi[7]-1) if curr_roi else 0)
                    nok_val = int(selected_nok.split()[1])

                    # Tlačítka akcí
                    b1, b2 = st.columns(2)
                    if b1.button("💾 ULOŽIT", type="primary", use_container_width=True):
                        if st.session_state.editing_id:
                            database.update_roi(st.session_state.editing_id, zn, zx, zy, zw, zh, nok_val)
                        else:
                            database.save_roi(m_id, zn, zx, zy, zw, zh, nok_val)
                        st.session_state.editing_id = None
                        st.rerun()
                    
                    if st.session_state.editing_id:
                        if b2.button("🚫 ZRUŠIT", use_container_width=True):
                            st.session_state.editing_id = None
                            st.rerun()

                st.divider()
                
                # --- SEZNAM ROI (Mazání a přejmenování) ---
                st.write("📋 **Seznam inspekcí**")
                for r in all_rois:
                    with st.expander(f"{r[2]} (NOK {r[7]})"):
                        e1, e2 = st.columns(2)
                        if e1.button("✏️ Editovat", key=f"ed_roi_{r[0]}", use_container_width=True):
                            st.session_state.editing_id = r[0]
                            st.rerun()
                        if e2.button("🗑️ Smazat", key=f"del_roi_{r[0]}", use_container_width=True):
                            database.delete_roi(r[0])
                            st.rerun()

            with col_viz:
                # Kreslení ROI zůstává stejné...
                # ... (kód pro draw.rectangle)

                # VÝPOČET PRO KOMPAKTNÍ ZOBRAZENÍ:
                # Pokud je obrázek široký, omezíme ho na 700px. 
                # Pokud je menší (výřez), necháme ho v původní velikosti.
                display_width = min(W, 700) 

                st.image(
                    img_roi, 
                    width=display_width, 
                    caption=f"Pracovní plocha: {m_name} ({W}x{H} px)"
                )
                
                st.image(img_roi, use_container_width=True)

# --- TAB 4: I/O ---
with tab4:
    st.write("Diagnostika PLC")