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
        templates = database.get_roi_templates("MQB Skříň ventilátoru L")
        roi_names = [t[2] for t in templates]
        
        if roi_names:
            sel_roi = st.selectbox("Vyberte součástku k doučení", roi_names)
            upl_test = st.file_uploader("Nahrajte novou fotku z výroby", type=["jpg", "png"])
            
            if upl_test:
                img_test = Image.open(upl_test)
                # Najdeme souřadnice vybrané ROI
                for t in templates:
                    if t[2] == sel_roi:
                        # Vyřízneme kousek podle souřadnic z Nastavení
                        crop = img_test.crop((t[3], t[4], t[3]+t[5], t[4]+t[6]))
                        
                        col_a, col_b = st.columns(2)
                        col_a.image(crop, caption="Výřez z nové fotky", use_container_width=True)
                        with col_b:
                            if st.button("✅ ULOŽIT JAKO OK"):
                                # Tady zavoláme logic pro uložení do složky 'training_data/OK'
                                st.success("Uloženo do OK vzorků")
                            if st.button("❌ ULOŽIT JAKO NOK"):
                                st.error("Uloženo do NOK vzorků")
        else:
            st.warning("Nejdříve musíte vytvořit ROI v sekci Nastavení!")

elif menu == "⚙️ Nastavení":
    st.title("⚙️ Konfigurace projektu")
    produkt = st.selectbox("Aktivní produkt", ["MQB Skříň ventilátoru L", "Octavia III - Kryt"])
    
    # 1. Nahrání a uložení do paměti
    master_file = st.file_uploader("Nahrajte Master snímek", type=["jpg", "png"], key="master_upl")
    if master_file:
        st.session_state.master_image = Image.open(master_file)

    if 'master_image' in st.session_state:
        img_pil = st.session_state.master_image
        col_foto, col_form = st.columns([3, 1])
        
        with col_foto:
            st.write("### 🖱️ 1. Definice nové ROI")
            roi_obj = st_cropper(img_pil, realtime_update=True, box_color='#FF9800', aspect_ratio=None, key="main_cropper")
            
        with col_form:
            st.write("### 📝 2. Uložit")
            if roi_obj:
                st.image(roi_obj, use_container_width=True)
            
            name = st.text_input("Název ROI", key="roi_name_input")
            
            # TLAČÍTKO: Musí být takto odsazené, aby bylo v pravém sloupci
            if st.button("➕ ULOŽIT DO PROJEKTU", use_container_width=True, type="primary"):
                # Kontrola, zda cropper už poslal data
                if 'main_cropper' in st.session_state and st.session_state['main_cropper'] is not None:
                    cropper_data = st.session_state['main_cropper']
                    
                    # Bezpečné vytažení souřadnic a rozměrů plátna
                    box = cropper_data.get('coords')
                    canvas_w = cropper_data.get('width')
                    canvas_h = cropper_data.get('height')

                    if box and canvas_w and canvas_h and name:
                        orig_w, orig_h = img_pil.size
                        
                        # Výpočet poměru (ratio)
                        rx, ry = orig_w / canvas_w, orig_h / canvas_h
                        
                        # Přepočet na reálné pixely fotky
                        real_x = int(box['left'] * rx)
                        real_y = int(box['top'] * ry)
                        real_w = int(box['width'] * rx)
                        real_h = int(box['height'] * ry)

                        database.save_roi_template(produkt, name, real_x, real_y, real_w, real_h)
                        st.success(f"ROI '{name}' uložena!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Chybí název nebo nebyla správně zaměřena oblast!"))

    # --- SEZNAM ROI POD ČAROU ---
    st.divider()
    templates = database.get_roi_templates(produkt)
    if templates and 'master_image' in st.session_state:
        for r in templates:
            with st.expander(f"🔍 {r[2]} (ID: {r[0]})"):
                c1, c2, c3 = st.columns([1, 2, 1])
                # Tady vyřízneme náhled, aby byl vidět v seznamu
                preview = st.session_state.master_image.crop((r[3], r[4], r[3]+r[5], r[4]+r[6]))
                c1.image(preview, use_container_width=True)
                c2.write(f"Pozice: [{r[3]}, {r[4]}]")
                if c3.button("🗑️ Smazat", key=f"del_{r[0]}"):
                    database.delete_roi_template(r[0])
                    st.rerun()
    else:
        st.info("Nahrajte Master snímek pro zobrazení seznamu s náhledy.")

# --- 4. HISTORIE ---
elif menu == "📂 Historie inspekcí":
    st.markdown("## 📂 Historie inspekcí")
    # Zde kód pro historii...