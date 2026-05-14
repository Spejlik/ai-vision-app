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

# 3. Inicializace Session State (Pojistka proti AttributeError)
if 'setup_image_buffer' not in st.session_state:
    st.session_state.setup_image_buffer = None
if 'active_project' not in st.session_state:
    st.session_state.active_project = None
if 'editing_id' not in st.session_state:
    st.session_state.editing_id = None
# --- TENTO ŘÁDEK CHYBĚL ---
if 'selected_master_id' not in st.session_state:
    st.session_state.selected_master_id = None
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

# --- TAB 3: SPRÁVA ZÓN (ELVAC STYLE) ---
with tab3:
    st.markdown("### 🛠️ Konfigurace inspekčních pozic")
    
    # Načtení všech dostupných Masterů pro projekt
    all_masters = database.get_masters(st.session_state.active_project)
    
    if not all_masters:
        st.warning("⚠️ Seznam Masterů je prázdný. Vytvořte nový v záložce MASTER.")
    else:
        # --- HORNÍ LIŠTA MINIATUR (Scrollable Selection) ---
        # Vytvoříme úhlednou řadu tlačítek s náhledy
        st.write("📂 **Dostupné pozice:**")
        
        # Inicializace výběru, pokud nic není zvoleno
        if st.session_state.selected_master_id is None:
            st.session_state.selected_master_id = all_masters[0][0]

        # Kompaktní zobrazení miniatur vedle sebe
        cols = st.columns(len(all_masters) if len(all_masters) < 8 else 8)
        for i, m in enumerate(all_masters):
            m_id, m_name, m_path = m[0], m[1], m[2]
            with cols[i % 8]:
                if os.path.exists(m_path):
                    # Malá miniatura s pevnou šířkou
                    st.image(m_path, use_container_width=True)
                    
                    is_active = (m_id == st.session_state.selected_master_id)
                    if st.button(f"{m_name}", key=f"sel_{m_id}", use_container_width=True, 
                                 type="primary" if is_active else "secondary"):
                        st.session_state.selected_master_id = m_id
                        st.rerun()

        st.divider()

        # --- HLAVNÍ EDITOR ---
        # Získání dat pro aktuálně vybraný Master (P1, P2...)
        sel_master = next((m for m in all_masters if m[0] == st.session_state.selected_master_id), all_masters[0])
        m_id, m_name, m_path = sel_master[0], sel_master[1], sel_master[2]
        
        if os.path.exists(m_path):
            img_roi = Image.open(m_path).convert("RGB")
            W, H = img_roi.size
            all_rois = database.get_rois(m_id)
            
            # Rozdělení: Levý panel (ovládání) | Pravý panel (fotka)
            col_ctrl, col_img = st.columns([1, 1.8])
            
            with col_ctrl:
                st.info(f"📍 Pozice: **{m_name}**")
                
                # Formulář pro zónu
                curr_roi = next((r for r in all_rois if r[0] == st.session_state.editing_id), None)
                zn = st.text_input("Název zóny", value=curr_roi[1] if curr_roi else f"Zóna {len(all_rois)+1}")
                
                c1, c2 = st.columns(2)
                zx = c1.number_input("X", 0, W, curr_roi[2] if curr_roi else W//2)
                zy = c2.number_input("Y", 0, H, curr_roi[3] if curr_roi else H//2)
                zw = c1.number_input("Šířka", 10, W, curr_roi[4] if curr_roi else 150)
                zh = c2.number_input("Výška", 10, H, curr_roi[5] if curr_roi else 150)
                
                nok = st.selectbox("PLC Chyba", range(1, 11), index=(curr_roi[6]-1) if curr_roi else 0)
                
                if st.button("💾 ULOŽIT ZÓNU", type="primary", use_container_width=True):
                    if st.session_state.editing_id:
                        database.delete_roi(st.session_state.editing_id)
                    database.save_roi(m_id, zn, zx, zy, zw, zh, nok)
                    st.session_state.editing_id = None
                    st.rerun()
                
                st.write("---")
                st.caption("Seznam aktivních inspekcí:")
                for r in all_rois:
                    col_t, col_b = st.columns([3, 1])
                    col_t.write(f"• {r[1]} (PLC {r[6]})")
                    if col_b.button("✏️", key=f"ed_{r[0]}"):
                        st.session_state.editing_id = r[0]
                        st.rerun()
            
            with col_img:
                # Kreslení ROI do obrázku
                draw = ImageDraw.Draw(img_roi)
                for r in all_rois:
                    is_ed = (r[0] == st.session_state.editing_id)
                    draw.rectangle([r[2], r[3], r[2]+r[4], r[3]+r[5]], 
                                   outline="#ff4b4b" if is_ed else "#deff9a", width=5 if is_ed else 2)
                
                # Náhled aktuálně rozdělané zóny
                if not st.session_state.editing_id:
                    draw.rectangle([zx, zy, zx+zw, zy+zh], outline="orange", width=2)
                
                # Zobrazení fotky - OMEZENÍ VELIKOSTI
                # use_container_width zajistí, že nepřeteče sloupec
                st.image(img_roi, use_container_width=True, caption=f"Pracovní náhled: {m_name}")
        else:
            st.error(f"Soubor {m_path} nenalezen.")

# --- TAB 4: I/O ---
with tab4:
    st.subheader("Diagnostika Modbus")
    st.write("Stav PLC registrů...")