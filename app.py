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
        upl = st.file_uploader("Nahrajte fotky k doučení", accept_multiple_files=True, key="u_upl")
        
        templates = database.get_roi_templates(produkt)
        roi_names = [t[2] for t in templates]
        
        if upl and roi_names:
            # Vezmeme první nahraný obrázek ze seznamu
            current_img = Image.open(upl[0])
            
            sel_roi = st.selectbox("Patří k inspekci:", roi_names)
            
            # Najdeme souřadnice vybrané ROI
            for t in templates:
                if t[2] == sel_roi:
                    # Vyřízneme ROI z právě nahrané fotky
                    crop = current_img.crop((t[3], t[4], t[3]+t[5], t[4]+t[6]))
                    
                    c1, c2 = st.columns(2)
                    c1.image(crop, caption="Výřez z nahrané fotky", use_container_width=True)
                    
                    with c2:
                        st.write(f"Anotace pro: **{sel_roi}**")
                        if st.button("✅ OK - Správně", use_container_width=True):
                            logic.save_cropped_image(crop, sel_roi, "OK")
                            st.success("Uloženo jako OK")
                        if st.button("❌ NOK - Chyba", use_container_width=True):
                            logic.save_cropped_image(crop, sel_roi, "NOK")
                            st.error("Uloženo jako NOK")
        elif not roi_names:
            st.warning("Nejdříve vytvořte ROI v Nastavení.")
        else:
            st.info("Nahrajte fotku pro začátek anotace.")

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
            
            if st.button("➕ ULOŽIT DO PROJEKTU", use_container_width=True, type="primary"):
                # 1. Zkontrolujeme, jestli máme data v session_state
                cropper_state = st.session_state.get('main_cropper')
                
                if cropper_state and name:
                    box = cropper_state.get('coords')
                    # Pokud nemáme cw/ch z cropperu, použijeme rozměry obrázku (poměr 1:1)
                    cw = cropper_state.get('width', img_pil.size[0])
                    ch = cropper_state.get('height', img_pil.size[1])
                    
                    if box:
                        orig_w, orig_h = img_pil.size
                        rx, ry = orig_w/cw, orig_h/ch
                        
                        # Vypočítáme reálné souřadnice
                        real_x = int(box['left'] * rx)
                        real_y = int(box['top'] * ry)
                        real_w = int(box['width'] * rx)
                        real_h = int(box['height'] * ry)
                        
                        database.save_roi_template(produkt, name, real_x, real_y, real_w, real_h)
                        st.success(f"ROI '{name}' byla úspěšně uložena!")
                        time.sleep(0.6)
                        st.rerun()
                else:
                    st.error("Chyba: Nejdříve pohněte rámečkem nebo zadejte název!")

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