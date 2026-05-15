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
# cam = camera_manager.BaslerCam() # Odkomentuj, až budeš mít připojenou kameru

# Inicializace Session State
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
    st.info(f"Systém připraven. Aktivní projekt: {st.session_state.active_project}")

# --- TAB 2: MASTER ---
with tab2:
    st.subheader("📸 Nastavení Master snímků")
    col_ctrl, col_img = st.columns([1, 2])
    
    with col_ctrl:
                st.markdown(f"### 🔧 Nastavení pro: {m_name}")
                
                zn = st.text_input("Název / Označení zóny", value=f"Zóna {len(all_rois)+1}")
                
                # Výběr NOK výstupu pro PLC
                nok_val = st.selectbox("Přiřazení chyby (NOK 1-8)", range(1, 9), index=0)
                
                # Slidery
                zx = st.slider("Pozice X", 0, W, 100)
                zy = st.slider("Pozice Y", 0, H, 100)
                zw = st.slider("Šířka", 10, W, 150)
                zh = st.slider("Výška", 10, H, 150)
                
                if st.button("💾 ULOŽIT ZÓNU", type="primary", use_container_width=True):
                    # Tady posíláme vše do databáze (včetně projektu a nok)
                    database.save_roi(m_id, active_p, zn, zx, zy, zw, zh, nok_val)
                    st.success(f"Zóna {zn} uložena!")
                    st.rerun()

    with col_img:
        # Tlačítko pro simulaci snímku (dokud není kamera)
        if st.button("📸 Zachytit testovací snímek"):
            st.session_state.setup_image_buffer = Image.new('RGB', (1200, 800), color=(73, 109, 137))
        
        if st.session_state.setup_image_buffer is not None:
            preview_img = st.session_state.setup_image_buffer.copy()
            draw = ImageDraw.Draw(preview_img)
            draw.rectangle([ax, ay, ax+aw, ay+ah], outline="red", width=5)
            st.image(preview_img, use_container_width=True, caption="Náhled s budoucím ořezem")

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

        m_cols = st.columns(8)
        for i, m in enumerate(all_masters):
            m_id, m_name, m_path = m[0], m[1], m[2]
            with m_cols[i % 8]:
                if os.path.exists(m_path):
                    st.image(m_path, use_container_width=True)
                
                is_active = (m_id == st.session_state.selected_master_id)
                if st.button(f"{m_name}", key=f"btn_m_{m_id}", use_container_width=True,
                             type="primary" if is_active else "secondary"):
                    st.session_state.selected_master_id = m_id
                    st.rerun()

        st.divider()
        
        sel_m = next((m for m in all_masters if m[0] == st.session_state.selected_master_id), all_masters[0])
        m_id, m_name, m_path = sel_m[0], sel_m[1], sel_m[2]
        
        if os.path.exists(m_path):
            img_roi = Image.open(m_path).convert("RGB")
            W, H = img_roi.size
            all_rois = database.get_rois(m_id, active_p)
            
            c_ctrl, c_viz = st.columns([1, 1.8])
            with c_ctrl:
                st.markdown(f"### 🔧 Zóny: {m_name}")
                # Slidery pro ROI
                zx = st.slider("X", 0, W, 100, key="sx")
                zy = st.slider("Y", 0, H, 100, key="sy")
                zw = st.slider("Šířka", 10, W, 150, key="sw")
                zh = st.slider("Výška", 10, H, 150, key="sh")
                
                if st.button("💾 ULOŽIT ZÓNU", type="primary", use_container_width=True):
                    database.save_roi(m_id, active_p, "Nová zóna", zx, zy, zw, zh, 1)
                    st.rerun()

            with col_viz:
                from PIL import ImageDraw
                draw = ImageDraw.Draw(img_roi)
                
                # 1. Vykreslení UŽ ULOŽENÝCH zón ze seznamu all_rois
                # Tato část zajistí, že uvidíš zelené rámečky s popisky
                for r in all_rois:
                    # Indexy podle nové tabulky: 3=název, 4=x, 5=y, 6=w, 7=h, 8=nok
                    x_r, y_r, w_r, h_r = r[4], r[5], r[6], r[7]
                    name_r, nok_r = r[3], r[8]
                    
                    # Zelený rámeček pro uloženou zónu
                    draw.rectangle([x_r, y_r, x_r + w_r, y_r + h_r], outline="#00FF00", width=3)
                    # Popisek nad rámečkem
                    draw.text((x_r, y_r - 15), f"{name_r} (NOK{nok_r})", fill="#00FF00")

                # 2. Vykreslení ORANŽOVÉHO NÁHLEDU (aktuální pozice sliderů)
                draw.rectangle([zx, zy, zx + zw, zy + zh], outline="orange", width=5)
                draw.text((zx, zy - 25), "NÁHLED NOVÉ ZÓNY", fill="orange")

                # Zobrazení výsledného obrázku
                st.image(img_roi, width=700, caption=f"Pracovní plocha: {m_name}")

# --- TAB 4: I/O ---
with tab4:
    st.write("Diagnostika PLC rozhraní")