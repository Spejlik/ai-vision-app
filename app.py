import streamlit as st
import database
import logic
import time
from PIL import Image
from streamlit_cropper import st_cropper

st.set_page_config(page_title="AI Inspekce", layout="wide")
database.init_db()

# Inicializace session_state
if 'master_image' not in st.session_state:
    st.session_state.master_image = None

with st.sidebar:
    st.title("🔍 Menu")
    menu = st.radio("Přejít na:", ["📊 Monitoring", "🧠 Učení a Trénink", "⚙️ Nastavení"])

# --- 1. MONITORING ---
if menu == "📊 Monitoring":
    st.title("📊 Monitoring výroby")
    prods = database.get_products()
    if prods:
        st.selectbox("Vyberte aktivní produkt pro kontrolu", prods)
    else:
        st.info("Nejsou definovány žádné produkty.")

# --- 2. UČENÍ ---
elif menu == "🧠 Učení a Trénink":
    st.title("🧠 Správa učících dat")
    st.info("Zde budeme později přidávat fotky pro AI.")

# --- 3. NASTAVENÍ (Systematický přístup) ---
elif menu == "⚙️ Nastavení":
    st.title("⚙️ Konfigurace projektů")
    
    # Vnitřní navigace pro dotykový displej
    if 'set_step' not in st.session_state:
        st.session_state.set_step = 1

    c1, c2, c3 = st.columns(3)
    if c1.button("📦 1. PROJEKTY", use_container_width=True): st.session_state.set_step = 1
    if c2.button("🖼️ 2. MASTER", use_container_width=True): st.session_state.set_step = 2
    if c3.button("🔍 3. ROI", use_container_width=True): st.session_state.set_step = 3

    st.divider()

    # --- STRÁNKA 1: SPRÁVA PRODUKTŮ ---
    if st.session_state.set_step == 1:
        st.subheader("📦 Správa produktů")
        new_p = st.text_input("Název nového produktu")
        if st.button("➕ PŘIDAT PRODUKT", use_container_width=True, type="primary"):
            if new_p:
                database.add_product(new_p)
                st.success("Přidáno")
                st.rerun()
        
        st.write("---")
        current_prods = database.get_products()
        for p in current_prods:
            col_p, col_d = st.columns([4, 1])
            col_p.write(f"📁 {p}")
            if col_d.button("🗑️", key=f"del_{p}"):
                database.delete_product(p)
                st.rerun()

    # --- STRÁNKA 2: VÝBĚR A MASTER ---
    elif st.session_state.set_step == 2:
        all_prods = database.get_products()
        if all_prods:
            st.session_state.active_p = st.selectbox("Vyberte produkt", all_prods)
            master_f = st.file_uploader("Nahrajte Master snímek", type=["jpg", "png"])
            if master_f:
                st.session_state.master_image = Image.open(master_f)
                st.success("Snímek nahrán. Přejděte na krok 3.")
        else:
            st.warning("Nejdříve vytvořte produkt v kroku 1.")

    # --- STRÁNKA 3: DEFINICE ROI ---
    elif st.session_state.set_step == 3:
        # Kontrola, zda máme data z předchozích kroků
        active_p = st.session_state.get('active_p')
        img = st.session_state.get('master_image')

        if active_p and img:
            st.subheader(f"🔍 Nastavení kontrol pro: {active_p}")
            
            c_foto, c_form = st.columns([2, 1])
            
            with c_foto:
                # Cropper musí mít unikátní klíč a přístup k img
                roi = st_cropper(img, realtime_update=True, box_color='#FF9800', key="cropper_main")
            
            with c_form:
                st.write("### 📝 Uložit novou ROI")
                roi_name = st.text_input("Název součástky/kontroly", key="input_roi_name")
                
                if st.button("💾 ULOŽIT DO DATABÁZE", use_container_width=True, type="primary"):
                    c_data = st.session_state.get('cropper_main')
                    if c_data and roi_name:
                        box = c_data.get('coords')
                        cw = c_data.get('width')
                        ch = c_data.get('height')
                        
                        if box and cw and ch:
                            iw, ih = img.size
                            rx, ry = iw/cw, ih/ch
                            
                            database.save_roi_template(
                                active_p, roi_name, 
                                int(box['left']*rx), int(box['top']*ry), 
                                int(box['width']*rx), int(box['height']*ry)
                            )
                            st.success(f"ROI '{roi_name}' uložena!")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("Pohněte rámečkem na fotce!")
                    else:
                        st.warning("Zadejte název kontroly!")

            st.divider()
            # Seznam už uložených věcí
            st.subheader("📋 Již nastavené kontroly")
            rois = database.get_roi_templates(active_p)
            if rois:
                for r in rois:
                    col_t, col_b = st.columns([3, 1])
                    col_t.write(f"📍 **{r[2]}** (ID: {r[0]})")
                    if col_b.button("Smazat", key=f"del_roi_{r[0]}"):
                        database.delete_roi_template(r[0])
                        st.rerun()
            else:
                st.info("Zatím žádné kontroly pro tento produkt.")
        
        else:
            # Tohle se zobrazí, pokud uživatel přeskočil krok 1 nebo 2
            st.warning("⚠️ Chybí data! Nejdříve vyberte produkt (Krok 1) a nahrajte Master snímek (Krok 2).")
            if st.button("⬅️ Zpět na nahrávání snímku"):
                st.session_state.set_step = 2
                st.rerun()