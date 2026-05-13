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
    
    active_p = st.session_state.get('active_p')
    img = st.session_state.get('master_image')

    if active_p and img:
        st.write(f"Snímání produktu: **{active_p}**")
        
        # Načteme všechny ROI pro tento produkt
        rois = database.get_roi_templates(active_p)
        
        if rois:
            # Vytvoříme mřížku (např. 3 sloupce) jako na image_57c352.jpg
            cols = st.columns(3)
            for i, r in enumerate(rois):
                with cols[i % 3]:
                    # Tady se děje to kouzlo: oříznutí podle uložených dat
                    # r[3]=x, r[4]=y, r[5]=w, r[6]=h
                    crop = img.crop((r[3], r[4], r[3]+r[5], r[4]+r[6]))
                    
                    st.image(crop, use_container_width=True)
                    st.caption(f"🔍 {r[2]}")
                    
                    # Simulace OK/NOK stavu
                    st.markdown("🟢 **Stav: OK**")
        else:
            st.info("Nejdříve definujte ROI v nastavení.")
    else:
        st.warning("⚠️ Chybí data! Vyberte produkt a Master snímek v nastavení.")

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

    # --- STRÁNKA 3: DEFINICE ROI (Čistá verze bez náhledů) ---
    elif st.session_state.set_step == 3:
        active_p = st.session_state.get('active_p')
        img = st.session_state.get('master_image')

        if active_p and img:
            st.subheader(f"🔍 Konfigurace inspekcí pro: {active_p}")
            
            col_foto, col_menu = st.columns([3, 1])
            
            with col_foto:
                # Velký náhled pro zaměření
                roi_data = st_cropper(img, realtime_update=True, box_color='#FF9800', key="cropper_final")
            
            with col_menu:
                st.write("### Přidat inspekci")
                
                # Vytvoření formuláře pro stabilní odeslání dat
                with st.form("roi_form", clear_on_submit=True):
                    roi_name = st.text_input("Název kontroly", placeholder="např. količek P1")
                    submit_button = st.form_submit_button("➕ ULOŽIT INSPEKCI", use_container_width=True)
                    
                    if submit_button:
                        c_state = st.session_state.get('cropper_final')
                        if c_state and roi_name:
                            box = c_state.get('coords')
                            # Přímé uložení do databáze
                            database.save_roi_template(
                                active_p, 
                                roi_name,
                                int(box['left']), int(box['top']), 
                                int(box['width']), int(box['height'])
                            )
                            st.toast(f"Inspekce '{roi_name}' uložena!")
                            # Tady nepoužíváme st.rerun(), formulář to udělá sám
                        else:
                            st.error("Chyba: Zadejte název a pohněte rámečkem!")

            st.divider()
            # SEZNAM INSPEKCÍ - Textový přehled bez obrázků
            st.subheader("📋 Aktivní kontroly v projektu")
            saved_rois = database.get_roi_templates(active_p)
            
            if saved_rois:
                for r in saved_rois:
                    with st.expander(f"⚙️ {r[2]}"):
                        c1, c2 = st.columns([3, 1])
                        c1.write(f"**Typ:** Klasifikátor | **Snímek:** Master | **ID:** {r[0]}")
                        if c2.button("SMAZAT", key=f"del_{r[0]}", use_container_width=True):
                            database.delete_roi_template(r[0])
                            st.rerun()
            else:
                st.info("Zatím nejsou definovány žádné inspekce.")
        else:
            st.warning("⚠️ Chybí data! Vyberte produkt (Krok 1) a nahrajte Master (Krok 2).")