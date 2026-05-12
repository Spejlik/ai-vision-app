import streamlit as st
import database
import logic
import time
from PIL import Image
from streamlit_cropper import st_cropper

# --- KONFIGURACE STRÁNKY ---
st.set_page_config(page_title="Inspekce Kvality AI", layout="wide")

# --- SESSION STATE INICIALIZACE ---
if 'master_image' not in st.session_state:
    st.session_state.master_image = None

# --- BOČNÍ PANEL (NAVIGACE) ---
with st.sidebar:
    st.title("🔍 Menu")
    menu = st.radio("Přejít na:", ["📊 Monitoring", "🧠 Učení a Trénink", "⚙️ Nastavení"])

# --- 1. MONITORING (Zjednodušená verze) ---
if menu == "📊 Monitoring":
    st.title("📊 Monitoring výroby")
    st.info("Zde probíhá automatická kontrola podle definovaných ROI.")

# --- 2. UČENÍ A TRÉNINK ---
elif menu == "🧠 Učení a Trénink":
    st.title("🧠 Správa učících dat")
    
    t1, t2, t3 = st.tabs(["🔄 Z cyklu", "🛠️ Ze zařízení", "📥 Import testů"])
    
    with t3:
        st.subheader("Import a Anotace pro AI")
        produkt = st.selectbox("Produkt pro učení", ["MQB Skříň ventilátoru L", "Octavia III - Kryt"], key="train_prod")
        
        upl_files = st.file_uploader("Nahrajte fotky k doučení", accept_multiple_files=True)
        
        # Načteme ROI z databáze pro tento produkt
        templates = database.get_roi_templates(produkt)
        roi_names = [t[2] for t in templates]
        
        if upl_files and roi_names:
            current_img = Image.open(upl_files[0])
            sel_roi = st.selectbox("Vyberte součástku na fotce:", roi_names)
            
            # Najdeme souřadnice vybrané ROI
            for t in templates:
                if t[2] == sel_roi:
                    # Výřez ROI (t[3]=x, t[4]=y, t[5]=w, t[6]=h)
                    crop = current_img.crop((t[3], t[4], t[3]+t[5], t[4]+t[6]))
                    
                    c1, c2 = st.columns(2)
                    c1.image(crop, caption=f"Výřez: {sel_roi}", use_container_width=True)
                    
                    with c2:
                        st.write(f"Označte kvalitu pro: **{sel_roi}**")
                        if st.button("✅ OK - V pořádku", use_container_width=True):
                            logic.save_cropped_image(crop, sel_roi, "OK")
                            st.success("Uloženo jako OK")
                        if st.button("❌ NOK - Chyba", use_container_width=True):
                            logic.save_cropped_image(crop, sel_roi, "NOK")
                            st.error("Uloženo jako NOK")
        elif not roi_names:
            st.warning("Nejdříve vytvořte ROI v sekci Nastavení!")

# --- 3. NASTAVENÍ (S OPRAVENÝM UKLÁDÁNÍM) ---
elif menu == "⚙️ Nastavení":
    st.title("⚙️ Konfigurace projektu")
    produkt = st.selectbox("Aktivní produkt", ["MQB Skříň ventilátoru L", "Octavia III - Kryt"])
    
    master_file = st.file_uploader("Nahrajte Master snímek", type=["jpg", "png"])
    if master_file:
        st.session_state.master_image = Image.open(master_file)

    if st.session_state.master_image:
        img_pil = st.session_state.master_image
        col_foto, col_form = st.columns([3, 1])
        
        with col_foto:
            st.write("### 🖱️ 1. Definice nové ROI")
            # Základní cropper bez problematických parametrů
            roi_obj = st_cropper(
                img_pil, 
                realtime_update=True, 
                box_color='#FF9800', 
                aspect_ratio=None, 
                key="main_cropper"
            )
            
        with col_form:
            st.write("### 📝 2. Uložit")
            if roi_obj:
                st.image(roi_obj, use_container_width=True, caption="Náhled výřezu")
            
            name = st.text_input("Název ROI (např. količek_vlevo)", key="roi_name_input")
            
            if st.button("➕ ULOŽIT DO PROJEKTU", use_container_width=True, type="primary"):
                cropper_state = st.session_state.get('main_cropper')
                
                if cropper_state and name:
                    box = cropper_state.get('coords')
                    cw = cropper_state.get('width', img_pil.size[0])
                    ch = cropper_state.get('height', img_pil.size[1])
                    
                    if box:
                        # Přepočet na reálné pixely fotky
                        orig_w, orig_h = img_pil.size
                        rx, ry = orig_w/cw, orig_h/ch
                        
                        real_x = int(box['left'] * rx)
                        real_y = int(box['top'] * ry)
                        real_w = int(box['width'] * rx)
                        real_h = int(box['height'] * ry)
                        
                        database.save_roi_template(produkt, name, real_x, real_y, real_w, real_h)
                        st.success(f"ROI '{name}' uložena!")
                        time.sleep(0.5)
                        st.rerun()
                else:
                    st.error("Chyba: Zadejte název a pohněte rámečkem!")

        # --- SEZNAM ULOŽENÝCH ROI ---
        st.divider()
        st.subheader(f"📋 Aktivní ROI pro: {produkt}")
        
        templates = database.get_roi_templates(produkt)
        if templates:
            for t in templates:
                with st.expander(f"🔍 {t[2]} (ID: {t[0]})"):
                    c1, c2 = st.columns([1, 3])
                    
                    # Vyřízneme náhled z masteru pro zobrazení v seznamu
                    preview = st.session_state.master_image.crop((t[3], t[4], t[3]+t[5], t[4]+t[6]))
                    c1.image(preview, use_container_width=True)
                    
                    c2.write(f"**Pozice:** [{t[3]}, {t[4]}]")
                    c2.write(f"**Rozměr:** {t[5]}x{t[6]} px")
                    
                    if c2.button("🗑️ Smazat", key=f"del_{t[0]}"):
                        database.delete_roi_template(t[0])
                        st.rerun()
        else:
            st.info("Zatím žádné ROI nejsou definovány.")
    else:
        st.warning("Nahrajte Master snímek pro zahájení konfigurace.")