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

# --- 1. MONITORING (Hlavní obrazovka) ---
if menu == "📊 Monitoring":
    st.title("📊 Monitoring výroby v reálném čase")
    
    # Horní řada: Statistiky
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    with col_stat1:
        st.metric("Dnešní cykly", "1,284", "+12")
    with col_stat2:
        st.metric("Úspěšnost (Yield)", "98.2 %", "-0.4 %")
    with col_stat3:
        # Zobrazení posledních 10 výsledků jako barevná kolečka
        cycles = database.get_last_cycles(limit=10) # Předpokládám funkci v DB
        dots = "".join([f" {'🟢' if c[2]=='OK' else '🔴'}" for c in cycles]) if cycles else "Zatím žádná data"
        st.write(f"Poslední cykly: {dots}")

    st.divider()

    # Hlavní část: Rozvržení vlevo obraz, vpravo tabulka
    col_cam, col_res = st.columns([2, 1])

    with col_cam:
        st.subheader("📸 Živý náhled / Poslední snímek")
        # Pokud máme master snímek, ukážeme ho jako podklad
        if st.session_state.master_image:
            st.image(st.session_state.master_image, use_container_width=True, caption="Kamera 1 - MQB Skříň ventilátoru")
        else:
            st.warning("Není k dispozici žádný snímek z kamery. Nahrajte Master v Nastavení.")

    with col_res:
        st.subheader("✅ Aktuální výsledky")
        
        # Načteme ROI, které máme hlídat
        produkt = "MQB Skříň ventilátoru L"
        active_rois = database.get_roi_templates(produkt)
        
        if active_rois:
            for r in active_rois:
                # Simulace výsledku - později zde bude volání AI modelu
                status = "OK" # Simulace
                confidence = "99.8%"
                
                # Barevný box pro výsledek
                color = "#dcfce7" if status == "OK" else "#fee2e2"
                st.markdown(f"""
                    <div style="background-color:{color}; padding:10px; border-radius:5px; margin-bottom:10px; border: 1px solid #ccc;">
                        <span style="font-weight:bold;">{r[2]}</span>: <span style="float:right;">{status} ({confidence})</span>
                    </div>
                """, unsafe_allow_html=True)
            
            if st.button("🚀 SPUSTIT RUČNÍ TEST", use_container_width=True):
                st.toast("Inspekce probíhá...")
                time.sleep(1)
                st.success("Inspekce dokončena.")
        else:
            st.info("Nejsou definovány žádné kontrolní zóny (ROI).")

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
    st.title("⚙️ Konfigurace projektů")
    
    # --- SEKCE A: SPRÁVA PRODUKTŮ ---
    with st.expander("📦 Správa produktů (Přidat/Smazat projekt)", expanded=False):
        new_prod = st.text_input("Název nového produktu/projektu")
        if st.button("➕ Vytvořit projekt"):
            if new_prod:
                database.add_product(new_prod)
                st.success(f"Projekt {new_prod} vytvořen!")
                st.rerun()

    # --- SEKCE B: VÝBĚR AKTIVNÍHO PROJEKTU ---
    available_products = database.get_products()
    
    if not available_products:
        st.warning("Seznam projektů je prázdný. Nejdříve vytvořte produkt v sekci výše.")
    else:
        produkt = st.selectbox("Vyberte projekt, který chcete konfigurovat", available_products)
        
        st.divider()
        
        # --- SEKCE C: KONFIGURACE ROI PRO VYBRANÝ PRODUKT ---
        master_file = st.file_uploader(f"Nahrajte Master snímek pro: {produkt}", type=["jpg", "png"])
        
        if master_file:
            st.session_state.master_image = Image.open(master_file)
            # ... zde pokračuje zbytek kódu s cropperem a ukládáním ROI ...

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