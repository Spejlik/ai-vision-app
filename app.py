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
    
    # KROK A: SPRÁVA PRODUKTŮ
    with st.expander("📦 KROK 1: Správa názvů produktů", expanded=True):
        col_new, col_del = st.columns(2)
        with col_new:
            new_p = st.text_input("Název nového produktu")
            if st.button("➕ Přidat produkt"):
                if new_p:
                    database.add_product(new_p)
                    st.success(f"Produkt {new_p} přidán.")
                    st.rerun()
        
        with col_del:
            current_prods = database.get_products()
            p_to_del = st.selectbox("Smazat produkt", [""] + current_prods)
            if st.button("🗑️ Smazat produkt") and p_to_del:
                database.delete_product(p_to_del)
                st.warning(f"Produkt {p_to_del} smazán.")
                st.rerun()

    st.divider()

    # KROK B: VÝBĚR PRODUKTU A KONFIGURACE ROI
    all_prods = database.get_products()
    if all_prods:
        active_p = st.selectbox("🎯 KROK 2: Vyberte produkt pro nastavení kontrol", all_prods)
        
        master_f = st.file_uploader(f"Nahrajte Master snímek pro {active_p}", type=["jpg", "png"])
        if master_f:
            st.session_state.master_image = Image.open(master_f)
        
        if st.session_state.master_image:
            img = st.session_state.master_image
            c_left, c_right = st.columns([3, 1])
            
            with c_left:
                st.write("### 🖱️ 3. Nakreslete oblast (ROI)")
                roi = st_cropper(img, realtime_update=True, box_color='#FF9800', key="cropper")
            
            with c_right:
                st.write("### 📝 4. Uložit")
                roi_name = st.text_input("Název kontroly (např. 'Sroub_1')")
                if st.button("💾 ULOŽIT ROI"):
                    c_data = st.session_state.get('cropper')
                    if c_data and roi_name:
                        box = c_data['coords']
                        cw, ch = c_data['width'], c_data['height']
                        iw, ih = img.size
                        rx, ry = iw/cw, ih/ch
                        
                        database.save_roi_template(
                            active_p, roi_name, 
                            int(box['left']*rx), int(box['top']*ry), 
                            int(box['width']*rx), int(box['height']*ry)
                        )
                        st.success(f"Kontrola '{roi_name}' uložena!")
                        time.sleep(0.5)
                        st.rerun()

            # Zobrazení existujících ROI
            st.subheader(f"Existující kontroly pro {active_p}")
            rois = database.get_roi_templates(active_p)
            for r in rois:
                with st.expander(f"ROI: {r[2]}"):
                    st.write(f"Pozice: {r[3]},{r[4]} Velikost: {r[5]}x{r[6]}")
                    if st.button("Smazat", key=f"del_{r[0]}"):
                        database.delete_roi_template(r[0])
                        st.rerun()
    else:
        st.warning("Nejdříve vytvořte produkt v Kroku 1 výše.")