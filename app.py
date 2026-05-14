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

# --- TAB: NASTAVENÍ (SETUP) ---
with tab_setup:
    st.subheader("Konfigurace Master snímku a AOI")
    
    # Inicializace paměti pro snímek, aby se netřásl
    if 'setup_frame' not in st.session_state:
        st.session_state.setup_frame = None

    col_ctrl, col_img = st.columns([1, 2])
    
    with col_ctrl:
        # Tlačítko, které pořídí snímek jen když chceš (zastaví třesení)
        if st.button("📸 NAČÍST / AKTUALIZOVAT ŽIVÝ NÁHLED", use_container_width=True):
            st.session_state.setup_frame = cam.get_frame()

        if st.session_state.setup_frame is not None:
            st.divider()
            # Slidery nyní pracují se statickým snímkem v paměti
            ax = st.number_input("X pozice", 0, 4000, 0)
            ay = st.number_input("Y pozice", 0, 4000, 0)
            aw = st.number_input("Šířka (px)", 100, 4000, 1280)
            ah = st.number_input("Výška (px)", 100, 4000, 1024)
            
            st.divider()
            m_name = st.text_input("ID Masteru", "P1")
            
            if st.button("💾 VYFOTIT A ULOŽIT MASTER", type="primary", use_container_width=True):
                # Ořez ze snímku, který máme v paměti
                cropped = st.session_state.setup_frame[ay:ay+ah, ax:ax+aw]
                
                path = f"masters/{st.session_state.active_project}_{m_name}.png"
                if not os.path.exists("masters"): os.makedirs("masters")
                cv2.imwrite(path, cv2.cvtColor(cropped, cv2.COLOR_RGB2BGR))
                database.add_master(st.session_state.active_project, path, ax, ay, aw, ah)
                st.success("✅ Master uložen!")
        else:
            st.info("Klikněte na tlačítko nahoře pro načtení obrazu z kamery.")

    with col_img:
        if st.session_state.setup_frame is not None:
            # Vykreslení rámečku nad statickým snímkem
            preview = st.session_state.setup_frame.copy()
            cv2.rectangle(preview, (ax, ay), (ax+aw, ay+ah), (255, 0, 0), 8)
            st.image(preview, caption="Nastavení AOI (statický náhled)", use_container_width=True)
            
# --- TAB: BĚH (Sledování inspekce) ---
with tab_run:
    if st.session_state.active_project:
        c1, c2 = st.columns([3, 1])
        with c1:
            st.subheader("Poslední inspekce")
            # Zde bude obraz z reálného triggeru
            st.image("https://via.placeholder.com/1280x720.png?text=Waiting+for+Trigger", use_container_width=True)
        with c2:
            st.subheader("Výsledek")
            st.markdown("<h1 style='text-align: center; color: green;'>PASS</h1>", unsafe_allow_html=True)
            st.metric("Celkem OK", "1245 ks")
            st.metric("Celkem NOK", "12 ks")
    else:
        st.info("Vyberte nebo vytvořte projekt v záložce Nastavení.")

# --- TAB: I/O (Diagnostika registrů) ---
with tab_io:
    st.subheader("Stav Modbus registrů")
    ci, co = st.columns(2)
    with ci:
        st.write("**Vstupy (PLC -> PC)**")
        st.checkbox("Trigger (Reg 8)", value=False, disabled=True)
    with co:
        st.write("**Výstupy (PC -> PLC)**")
        st.checkbox("Ready (Reg 7)", value=True, disabled=True)
        st.checkbox("Result OK (Reg 0)", value=False, disabled=True)