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
                st.info("Vyberte oblast na fotce a uložte ji jako vzorek pro AI.")
                img_path = "training_data/external/master.jpg" # Cesta k tvému master obrázku
                
                if os.path.exists(img_path):
                    master_img = Image.open(img_path)
                    # Tady definujeme 'crop' pomocí st_cropper
                    crop = st_cropper(master_img, realtime_update=True, box_color='#FF0000')
                else:
                    st.error("Soubor master.jpg nebyl nalezen ve složce training_data/external/")
                    crop = None # Definujeme jako None, aby program nespadl
            
            with c2:
                # Kontrola: Pokud crop existuje, zobrazíme ho a umožníme uložit
                if crop is not None:
                    st.image(crop, use_container_width=True)
                    sel_roi = st.selectbox("Patří k inspekci:", roi_names)
                    label = st.radio("Výsledek:", ["OK", "NOK"])
                    
                    if st.button("💾 ULOŽIT DO UČENÍ"):
                        import logic
                        logic.save_cropped_image(crop, sel_roi, label)
                        st.success(f"Vzorek pro {sel_roi} uložen jako {label}!")
        else:
            st.warning("Nejdříve vytvořte ROI v sekci Nastavení, aby AI věděla, co má učit.")

elif menu == "⚙️ Nastavení":
    st.title("⚙️ Konfigurace projektu")
    
    # Výběr produktu
    produkt = st.selectbox("Aktivní produkt", ["MQB Skříň ventilátoru L", "Octavia III - Kryt"])
    
    st.divider()
    
    # Nahrání Master snímku
    master_file = st.file_uploader("Nahrajte Master snímek z kamery", type=["jpg", "png"], key="master_upl")
    
    if master_file:
        img_pil = Image.open(master_file)
        # Převedeme na OpenCV formát pro kreslení
        import cv2
        import numpy as np
        img_cv = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
        
        # Načteme už uložené ROI z databáze
        templates = database.get_roi_templates(produkt)
        
        # --- KRESLENÍ VŠECH ULOŽENÝCH ROI (PRO PŘEHLED) ---
        if templates:
            for t in templates:
                # t[3-6] jsou x, y, w, h
                x, y, w, h = t[3], t[4], t[5], t[6]
                # Nakreslíme červený obdélník přímo do OpenCV obrázku
                cv2.rectangle(img_cv, (x, y), (x + w, y + h), (0, 0, 255), 3)
                # Přidáme název ROI
                cv2.putText(img_cv, t[2], (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
        
        # Převedeme zpět na PIL pro zobrazení ve Streamlitu
        img_overview_pil = Image.fromarray(cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB))
        
        # Rozhraní: Levý sloupec (Přehled), Pravý sloupec (Editor)
        col_view, col_edit = st.columns([2, 1])
        
        with col_view:
            st.write("### 🗺️ Přehled všech aktivních ROI")
            # Zobrazíme obrázek se všemi nakreslenými ROI
            st.image(img_overview_pil, use_container_width=True)
            
        with col_edit:
            st.write("### ➕ Přidat/Editovat")
            
            # Tlačítko pro spuštění editoru
            if st.button("➕ Kreslit novou oblast", use_container_width=True):
                st.session_state.show_editor = True
            
            if st.session_state.get('show_editor', False):
                st.info("🖱️ Nakresli novou oblast na master snímku.")
                # TADY je ten samostatný st_cropper pro kreslení
                roi_crop = st_cropper(img_pil, realtime_update=True, box_color='#FF9800', aspect_ratio=None, key="new_roi_cropper")
                
                name = st.text_input("Název nové inspekce", placeholder="klapka_P1", key="new_roi_name")
                
                # Uložíme souřadnice ze st_cropperu do session_state
                if 'new_roi_cropper' in st.session_state:
                    coords = st.session_state['new_roi_cropper']['coords']
                    
                    if st.button("💾 ULOŽIT NOVOU OBLAST", use_container_width=True, type="primary"):
                        if name:
                            # Uložíme skutečné souřadnice (x, y, w, h) do DB
                            database.save_roi_template(produkt, name, coords['left'], coords['top'], coords['width'], coords['height'])
                            st.success(f"Zóna {name} byla přidána do projektu.")
                            # Vyčistíme editor a obnovíme stránku
                            st.session_state.show_editor = False
                            st.rerun()
                        else:
                            st.error("Zadejte název!")
                
                if st.button("❌ Zrušit", use_container_width=True):
                    st.session_state.show_editor = False
                    st.rerun()

    # --- SEZNAM ROI POD ČAROU ---
    st.divider()
    st.subheader(f"📋 Seznam definovaných ROI pro: {produkt}")
    current_rois = database.get_roi_templates(produkt)
    
    if current_rois:
        for r in current_rois:
            with st.expander(f"🟢 {r[2]}"):
                c1, c2 = st.columns([3, 1])
                c1.write(f"Pozice: {r[3]},{r[4]} | Rozměr: {r[5]}x{r[6]}")
                if c2.button("🗑️ Smazat", key=f"del_{r[0]}"):
                    database.delete_roi_template(r[0])
                    st.rerun()
    else:
        st.info("Zatím žádné ROI.")

# --- 4. HISTORIE ---
elif menu == "📂 Historie inspekcí":
    st.markdown("## 📂 Historie inspekcí")
    # Zde kód pro historii...