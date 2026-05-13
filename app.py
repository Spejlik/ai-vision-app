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
    
    # 1. Inicializace stavu kroků
    if 'set_step' not in st.session_state:
        st.session_state.set_step = 1
    if 'active_p' not in st.session_state:
        st.session_state.active_p = None

    # 2. Horní navigace - Velká tlačítka pro dotykový displej
    c1, c2, c3 = st.columns(3)
    if c1.button("📦 1. PROJEKTY", use_container_width=True): 
        st.session_state.set_step = 1
    if c2.button("🖼️ 2. MASTER", use_container_width=True): 
        st.session_state.set_step = 2
    if c3.button("🔍 3. ROI", use_container_width=True): 
        st.session_state.set_step = 3

    st.divider()

    # --- STRÁNKA 1: SPRÁVA PRODUKTŮ ---
    if st.session_state.set_step == 1:
        st.subheader("📦 KROK 1: Správa produktů")
        
        new_p = st.text_input("Název nového produktu")
        if st.button("➕ VYTVOŘIT PROJEKT", use_container_width=True):
            if new_p:
                database.add_product(new_p)
                st.success(f"Produkt {new_p} vytvořen!")
                st.rerun()
        
        st.write("---")
        all_prods = database.get_products()
        if all_prods:
            st.session_state.active_p = st.selectbox(
                "Zvolte aktivní produkt:", 
                all_prods, 
                index=all_prods.index(st.session_state.active_p) if st.session_state.active_p in all_prods else 0
            )
        else:
            st.info("Seznam projektů je prázdný.")

    # --- STRÁNKA 2: NAHRÁNÍ MASTER SNÍMKU ---
    elif st.session_state.set_step == 2:
        st.subheader("🖼️ KROK 2: Nahrání Master snímku")
        if st.session_state.active_p:
            st.info(f"Konfigurujete: **{st.session_state.active_p}**")
            master_f = st.file_uploader("Nahrajte referenční fotografii", type=["jpg", "png"])
            if master_f:
                st.session_state.master_image = Image.open(master_f)
                st.success("Snímek uložen v paměti. Přejděte na Krok 3.")
        else:
            st.warning("⚠️ Nejdříve vyberte produkt v Kroku 1!")

    # --- STRÁNKA 3: DEFINICE ROI (Zde byla chyba odsazení) ---
    elif st.session_state.set_step == 3:
        active_p = st.session_state.get('active_p')
        img = st.session_state.get('master_image')

        if active_p and img:
            st.subheader(f"🔍 KROK 3: Nastavení ROI pro {active_p}")
            col_l, col_r = st.columns([2, 1])
            
            with col_l:
                # Cropper pro dotykový monitor
                roi_data = st_cropper(img, realtime_update=True, box_color='#FF9800', key="cropper_final")
            
            with col_r:
                st.write("### 📝 Uložit novou ROI")
                roi_name = st.text_input("Název kontroly", key="roi_name_buffer")
                
                if st.button("💾 ULOŽIT DO DATABÁZE", use_container_width=True, type="primary"):
                    c_state = st.session_state.get('cropper_final')
                    
                    if c_state and 'coords' in c_state:
                        # Reálná velikost originálního souboru
                        iw, ih = img.size 
                        
                        # Rozměry, které cropper viděl v prohlížeči
                        cw = c_state.get('width')
                        ch = c_state.get('height')
                        
                        # Souřadnice z rámečku na webu
                        box = c_state.get('coords')

                        # Pokud cw/ch chybí, nepokračujeme ve výpočtu
                        if cw and ch:
                            # Výpočet koeficientu zvětšení
                            # Musíme zajistit, aby poměr stran odpovídal
                            scale_x = iw / cw
                            scale_y = ih / ch

                            # Přepočet na reálné pixely souboru
                            real_x = int(box['left'] * scale_x)
                            real_y = int(box['top'] * scale_y)
                            real_w = int(box['width'] * scale_x)
                            real_h = int(box['height'] * scale_y)

                            # Kontrola přetečení (nesmíme říznout mimo fotku)
                            real_x = max(0, min(real_x, iw))
                            real_y = max(0, min(real_y, ih))

                            if roi_name:
                                database.save_roi_template(
                                    st.session_state.active_p, 
                                    roi_name, 
                                    real_x, real_y, real_w, real_h
                                )
                                st.success(f"ROI '{roi_name}' uložena!")
                                time.sleep(0.5)
                                st.rerun()
                        else:
                            st.error("Chyba inicializace cropperu. Pohněte s ním prosím.")
                    else:
                        st.error("Nejdříve pohněte rámečkem na fotce!")

            st.divider()
            st.subheader("📋 Seznam nastavených kontrol")
            saved_rois = database.get_roi_templates(active_p)
            if saved_rois:
                for r in saved_rois:
                    with st.expander(f"📍 {r[2]}"):
                        c1, c2 = st.columns([1, 2])
                        # Zobrazení náhledu přímo z databáze
                        crop_view = img.crop((r[3], r[4], r[3]+r[5], r[4]+r[6]))
                        c1.image(crop_view, use_container_width=True)
                        if c2.button("Odstranit", key=f"del_{r[0]}"):
                            database.delete_roi_template(r[0])
                            st.rerun()
            else:
                st.info("Zatím žádné kontroly.")
        else:
            st.warning("⚠️ Chybí data! Vraťte se ke Kroku 1 (Produkt) a Kroku 2 (Master).")