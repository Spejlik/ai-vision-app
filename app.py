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
    
    # 1. Inicializace stavu kroků a dat, pokud neexistují
    if 'set_step' not in st.session_state:
        st.session_state.set_step = 1
    if 'active_p' not in st.session_state:
        st.session_state.active_p = None

    # 2. Horní navigace (Tlačítka)
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
        st.subheader("📦 KROK 1: Výběr a správa produktů")
        
        # Přidání nového
        new_p = st.text_input("Název nového produktu")
        if st.button("➕ VYTVOŘIT PROJEKT", use_container_width=True):
            if new_p:
                database.add_product(new_p)
                st.success(f"Produkt {new_p} vytvořen!")
                st.rerun()
        
        st.write("---")
        # Výběr aktivního (Ukládáme do session_state!)
        all_prods = database.get_products()
        if all_prods:
            st.session_state.active_p = st.selectbox(
                "Zvolte aktivní produkt pro konfiguraci:", 
                all_prods, 
                index=all_prods.index(st.session_state.active_p) if st.session_state.active_p in all_prods else 0
            )
            st.info(f"Aktuálně vybráno: **{st.session_state.active_p}**")
        else:
            st.warning("Seznam projektů je prázdný.")

    # --- STRÁNKA 2: NAHRÁNÍ MASTER SNÍMKU ---
    elif st.session_state.set_step == 2:
        st.subheader("🖼️ KROK 2: Nahrání Master snímku")
        if st.session_state.active_p:
            st.write(f"Konfigurujete produkt: **{st.session_state.active_p}**")
            master_f = st.file_uploader("Nahrajte referenční fotografii", type=["jpg", "png"])
            if master_f:
                st.session_state.master_image = Image.open(master_f)
                st.success("Snímek nahrán do paměti. Přejděte na Krok 3.")
        else:
            st.error("Chyba: Nejdříve vyberte produkt v Kroku 1!")

    # --- STRÁNKA 3: DEFINICE ROI ---
    elif st.session_state.set_step == 3:
        active_p = st.session_state.get('active_p')
        img = st.session_state.get('master_image')

        if active_p and img:
            st.subheader(f"🔍 KROK 3: Nastavení kontrol pro {active_p}")
            col_l, col_r = st.columns([2, 1])
            
            with col_l:
                # Cropper vrací i souřadnice v reálném čase
                roi_data = st_cropper(img, realtime_update=True, box_color='#FF9800', key="cropper_v3")
            
            with col_r:
                st.write("### 📝 Uložit novou ROI")
                
                # Používáme klíč pro automatické uložení do session_state
                roi_name = st.text_input("Název kontroly", key="roi_name_buffer")
                
                if st.button("💾 ULOŽIT DO DATABÁZE", use_container_width=True, type="primary"):
                    # Vyzvedneme data z cropperu
                    c_state = st.session_state.get('cropper_v3')
                    
                    if c_state and roi_name:
                        box = c_state.get('coords')
                        cw, ch = c_state.get('width'), c_state.get('height')
                        
                        if box and cw and ch:
                            iw, ih = img.size
                            rx, ry = iw/cw, ih/ch
                            
                            # Volání databáze
                            database.save_roi_template(
                                active_p, roi_name,
                                int(box['left']*rx), int(box['top']*ry),
                                int(box['width']*rx), int(box['height']*ry)
                            )
                            st.success(f"Uloženo: {roi_name}")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Chyba souřadnic! Pohněte rámečkem.")
                    else:
                        st.warning("Musíte zadat název a mít aktivní rámeček!")

            st.divider()
            # SEZNAM S NÁHLEDY (Aby uživatel viděl, že se to skutečně uložilo)
            st.subheader("📋 Aktuálně nastavené kontroly")
            saved_rois = database.get_roi_templates(active_p)
            
            if saved_rois:
                for r in saved_rois:
                    with st.expander(f"📍 {r[2]}"):
                        c1, c2 = st.columns([1, 2])
                        # Zobrazení výřezu přímo z master snímku pro kontrolu
                        crop_view = img.crop((r[3], r[4], r[3]+r[5], r[4]+r[6]))
                        c1.image(crop_view, use_container_width=True)
                        if c2.button("Odstranit", key=f"del_{r[0]}"):
                            database.delete_roi_template(r[0])
                            st.rerun()
            else:
                st.info("Zatím žádné kontroly.")
        else:
            st.warning("⚠️ Data chybí! Vraťte se ke Kroku 1 a 2.")

            st.divider()
            # Výpis již uložených ROI
            saved_rois = database.get_roi_templates(active_p)
            if saved_rois:
                for r in saved_rois:
                    col_name, col_del = st.columns([3, 1])
                    col_name.write(f"📍 {r[2]}")
                    if col_del.button("Smazat", key=f"del_{r[0]}"):
                        database.delete_roi_template(r[0])
                        st.rerun()
        else:
            st.warning("⚠️ Data chybí! Musíte mít vybraný produkt (Krok 1) a nahraný snímek (Krok 2).")