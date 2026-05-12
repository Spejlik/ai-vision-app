import streamlit as st
from PIL import Image
from streamlit_cropper import st_cropper
import os, time
import database, logic, styles

# 1. Základní nastavení stránky
st.set_page_config(
    page_title="Lis 1300/7A - Kontrola", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# 2. Inicializace databáze a stylů
database.init_db()
styles.apply_custom_css()

# --- SIDEBAR (Levý panel) ---
with st.sidebar:
    st.markdown("### 🔐 PŘIHLÁŠENÍ")
    user = st.text_input("Uživatel", value="Elvac Admin")
    st.divider()
    st.markdown("### 🛠️ MENU")
    menu = st.radio("Navigace", ["🏠 Monitor", "🧠 Učení a Trénink", "📂 Historie inspekcí", "⚙️ Nastavení"])

# --- HORNÍ LIŠTA ---
head_col1, head_col2, head_col3 = st.columns([4, 2, 3])
with head_col1:
    st.markdown("### 🛠️ MQB Skříň ventilátoru L")
with head_col2:
    mode = st.radio("Režim", ["AUTO", "MANUAL"], horizontal=True, label_visibility="collapsed")
with head_col3:
    cycles = database.get_last_cycles(limit=15)
    if cycles:
        dots = "".join([f'<span style="color:{"#22c55e" if c[2]=="OK" else "#ef4444"};">●</span>' for c in cycles])
        st.markdown(f'<div style="font-size:20px;">{dots}</div>', unsafe_allow_html=True)

st.divider()

# --- HLAVNÍ SEKCE ---

# --- 1. MONITOR ---
if menu == "🏠 Monitor":
    col_left, col_right = st.columns([4, 1.2])
    with col_left:
        latest_results = database.get_history(limit=8)
        if latest_results:
            cols = st.columns(4)
            for i, res in enumerate(latest_results):
                with cols[i % 4]:
                    b64 = logic.get_real_image_base64(res[4], res[6])
                    styles.draw_roi_card(res[4], res[5], res[6], "#22c55e" if res[6]=="OK" else "#ef4444", b64)
        else:
            st.info("Systém připraven.")

    with col_right:
        if st.button("🚀 START INSPEKCE", use_container_width=True, type="primary"):
            cur_cycle = str(int(time.time()))
            # Načteme ROI, které jsi nakreslil v nastavení
            rois = database.get_roi_templates("MQB Skříň ventilátoru L")
            for r in rois:
                conf, stat, _ = logic.get_ai_prediction(r[2])
                database.save_result(cur_cycle, "MQB L", r[2], conf, stat, "img/sample.jpg")
            st.rerun()

# --- 2. UČENÍ A TRÉNINK ---
elif menu == "🧠 Učení a Trénink":
    st.markdown("## 🧠 Správa učících dat")
    t1, t2, t3 = st.tabs(["🔄 Z cyklu", "🛠️ Ze seřízení", "📤 Import testů"])
    
    with t3:
        st.subheader("Import a Anotace pro AI")
        upl = st.file_uploader("Nahrajte fotky k doučení", accept_multiple_files=True)
        
        # Načteme ROI z databáze pro výběr
        templates = database.get_roi_templates("MQB Skříň ventilátoru L")
        roi_names = [t[2] for t in templates]
        
        if roi_names:
            c1, c2 = st.columns([3, 1])
            with c1:
                # Simulace galerie - vezmeme první nahraný nebo vzorový
                st.info("Vyberte oblast na fotce a uložte ji jako vzorek pro AI.")
                img_path = "training_data/external/master.jpg" # Ukázka
                if os.path.exists(img_path):
                    master_img = Image.open(img_path)
                    crop = st_cropper(master_img, realtime_update=True, box_color='#FF0000')
            with c2:
                st.image(crop, use_container_width=True)
                sel_roi = st.selectbox("Patří k inspekci:", roi_names)
                label = st.radio("Výsledek:", ["OK", "NOK"])
                if st.button("💾 ULOŽIT DO UČENÍ"):
                    logic.save_cropped_image(crop, sel_roi, label)
                    st.success("Vzorek uložen!")
        else:
            st.warning("Nejdříve vytvořte ROI v Nastavení.")

# --- 3. NASTAVENÍ (KONFIGURÁTOR) ---
elif menu == "⚙️ Nastavení":
    st.title("⚙️ Konfigurace projektu")
    produkt = st.selectbox("Produkt", ["MQB Skříň ventilátoru L", "Octavia III - Kryt"])
    
    master_file = st.file_uploader("Nahrajte Master snímek", type=["jpg", "png"])
    
    if master_file:
        img = Image.open(master_file)
        c_foto, c_form = st.columns([3, 1])
        
        with c_foto:
            st.write("### 🖱️ 1. Nakreslete oblast")
            # Důležité: key="main_cropper" pro session_state
            roi_obj = st_cropper(img, realtime_update=True, box_color='#FF9800', key="main_cropper")
            
        with c_form:
            st.write("### 📝 2. Uložte")
            st.image(roi_obj, use_container_width=True)
            name = st.text_input("Název (např. klapka_1)")
            
            if st.button("➕ PŘIDAT INSPEKCI", use_container_width=True, type="primary"):
                if name and 'main_cropper' in st.session_state:
                    box = st.session_state['main_cropper']['coords']
                    database.save_roi_template(produkt, name, box['left'], box['top'], box['width'], box['height'])
                    st.success("ROI uložena!")
                    st.rerun()

    # VÝPIS SEZNAMU (To, co ti chybělo)
    st.divider()
    st.subheader("📋 Aktivní kontroly v tomto projektu")
    templates = database.get_roi_templates(produkt)
    if templates:
        for t in templates:
            with st.expander(f"🔍 {t[2]}"):
                col1, col2 = st.columns([3, 1])
                col1.write(f"Pozice: {t[3]},{t[4]} | Velikost: {t[5]}x{t[6]}px")
                if col2.button("🗑️ Smazat", key=f"del_{t[0]}"):
                    database.delete_roi_template(t[0])
                    st.rerun()
    else:
        st.info("Zatím žádné ROI.")

# --- 4. HISTORIE ---
elif menu == "📂 Historie inspekcí":
    st.markdown("## 📂 Historie inspekcí")
    # Zde kód pro historii...