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
    
    # 1. Volba produktu
    produkt = st.selectbox("Aktivní produkt", ["MQB Skříň ventilátoru L", "Octavia III - Kryt"])
    
    # 2. Správa Master snímku v paměti (aby nezmizel při uložení)
    master_file = st.file_uploader("Nahrajte Master snímek", type=["jpg", "png"], key="master_upl")
    
    if master_file:
        st.session_state.master_image = Image.open(master_file)
    
    if 'master_image' in st.session_state:
        img_pil = st.session_state.master_image
        
        col_foto, col_form = st.columns([3, 1])
        
        with col_foto:
            st.write("### 🖱️ 1. Definice nové ROI")
            # Použijeme edit_name ze session_state pokud existuje (pro editaci)
            default_name = st.session_state.get('edit_name', "")
            
            roi_obj = st_cropper(
                img_pil, 
                realtime_update=True, 
                box_color='#FF9800', 
                aspect_ratio=None, 
                key="main_cropper",
                should_resize_out=False,
                use_container_width=True
            )
            
        with col_form:
            st.write("### 📝 2. Uložit / Upravit")
            if roi_obj:
                st.image(roi_obj, use_container_width=True, caption="Náhled")
            
            name = st.text_input("Název ROI", value=default_name, key="roi_name_input")
            
            if st.button("➕ ULOŽIT DO PROJEKTU", use_container_width=True, type="primary"):
                if 'main_cropper' in st.session_state and name:
                    coords = st.session_state['main_cropper']['coords']
                    # Uložíme do DB
                    database.save_roi_template(
                        produkt, name, 
                        int(coords['left']), int(coords['top']), 
                        int(coords['width']), int(coords['height'])
                    )
                    # Vyčistíme editační pole a restartujeme
                    if 'edit_name' in st.session_state:
                        del st.session_state.edit_name
                    st.success(f"ROI '{name}' uložena!")
                    time.sleep(0.5)
                    st.rerun()

    # --- 3. SEZNAM S FOTKAMI A EDITACÍ ---
    st.divider()
    st.subheader(f"📋 Aktivní ROI pro: {produkt}")
    
    templates = database.get_roi_templates(produkt)
    
    if templates and 'master_image' in st.session_state:
        for r in templates:
            # Unikátní klíče pro Streamlit prvky
            with st.expander(f"🔍 {r[2]} (ID: {r[0]})"):
                c_img, c_txt, c_btn = st.columns([1, 2, 1])
                
                # Zobrazení fotky výřezu
                with c_img:
                    left, top, w, h = r[3], r[4], r[5], r[6]
                    # Vyřízneme náhled z obrázku v paměti
                    roi_preview = st.session_state.master_image.crop((left, top, left+w, top+h))
                    st.image(roi_preview, use_container_width=True)
                
                with c_txt:
                    st.write(f"**Pozice:** [{left}, {top}]")
                    st.write(f"**Rozměr:** {w}x{h} px")
                
                with c_btn:
                    # Tlačítko SMAZAT
                    if st.button("🗑️ Smazat", key=f"del_{r[0]}", use_container_width=True):
                        database.delete_roi_template(r[0])
                        st.rerun()
                    
                    # Tlačítko UPRAVIT (Smaže původní a hodí název do text_inputu)
                    if st.button("📝 Upravit", key=f"ed_{r[0]}", use_container_width=True):
                        st.session_state.edit_name = r[2]
                        database.delete_roi_template(r[0])
                        st.rerun()
    else:
        if 'master_image' not in st.session_state:
            st.info("Nahrajte Master snímek pro zobrazení náhledů.")
        else:
            st.info("Zatím žádné ROI.")

# --- 4. HISTORIE ---
elif menu == "📂 Historie inspekcí":
    st.markdown("## 📂 Historie inspekcí")
    # Zde kód pro historii...