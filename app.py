import streamlit as st
from streamlit_cropper import st_cropper
from PIL import Image, ImageDraw
import database
import camera_manager
import time
import os
import streamlit as st

# Inicializace
st.set_page_config(layout="wide", page_title="AI Vision Inspection")
database.init_db()
cam = camera_manager.BaslerCam()

# TENTO BLOK ODSTRANÍ VOLNÉ MÍSTO NAHOŘE
st.markdown("""
    <style>
        /* Odstranění okrajů hlavní nádoby */
        .block-container {
            padding-top: 1rem;
            padding-bottom: 0rem;
            margin-top: 0rem;
        }
        /* Zmenšení mezery nad nadpisem */
        header {
            visibility: hidden;
        }
        #root > div:nth-child(1) > div > div > div > div > section > div {
            padding-top: 0rem;
        }
        /* Úprava nadpisu, aby nebyl tak vysoký */
        h1 {
            padding-top: 0rem;
            margin-top: -2rem;
        }
    </style>
""", unsafe_allow_html=True)

# ... zbytek tvého kódu (st.sidebar, atd.)

if 'step' not in st.session_state: st.session_state.step = 1
if 'active_project' not in st.session_state: st.session_state.active_project = None
if 'active_master' not in st.session_state: st.session_state.active_master = None

st.sidebar.title("📷 Menu")
menu = st.sidebar.radio("Navigace", ["Konfigurace", "Monitoring"])

if menu == "Konfigurace":
    st.title("⚙️ Nastavení systému")
    
    # Průvodce kroky
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("📁 Projekty"): st.session_state.step = 1
    with c2:
        if st.button("🎯 Master"): st.session_state.step = 2
    with c3:
        if st.button("🔍 Zóny"): st.session_state.step = 3
    with c4:
        if st.button("🔌 I/O"): st.session_state.step = 4 
    
    st.divider()

    # KROK 1: VÝBĚR PROJEKTU
    if st.session_state.step == 1:
        st.subheader("📁 Správa projektů")
        new_p = st.text_input("Vytvořit nový projekt:")
        if st.button("Uložit projekt"):
            if new_p:
                database.save_project(new_p)
                st.success("Projekt vytvořen")
        
        projs = database.get_projects()
        st.session_state.active_project = st.selectbox("Vyberte aktivní projekt:", [p[1] for p in projs])

    # KROK 2: NASTAVENÍ MASTERU A AOI
    elif st.session_state.step == 2:
        st.subheader(f"🖼️ Nastavení Masteru pro: {st.session_state.active_project}")
        
        col_img, col_ctrl = st.columns([1.5, 1.0])
        
        with col_ctrl:
            st.caption("Nastavení ořezu (AOI)")
            ax = st.slider("X pozice", 0, 2000, 0)
            ay = st.slider("Y pozice", 0, 2000, 0)
            aw = st.slider("Šířka", 100, 2500, 1280)
            ah = st.slider("Výška", 100, 2500, 1080)
            m_name = st.text_input("Název Master snímku:", placeholder="např. MQB_P1")
            
            if st.button("📸 VYFOTIT A ULOŽIT", type="primary", use_container_width=True):
                if not m_name:
                    st.error("Zadejte název snímku!")
                else:
                    # 1. Vyfotíme celou scénu
                    raw_frame = cam.get_frame()
                    pil_img = Image.fromarray(raw_frame)
                    
                    # 2. PROVEDEME OŘEZ (Toto je ten odrazový můstek)
                    # Teď už neukládáme celou fotku, ale jen to, co jsi vybral slidery
                    cropped_master = pil_img.crop((ax, ay, ax + aw, ay + ah))
                    
                    # 3. Uložíme oříznutý Master
                    os.makedirs("masters", exist_ok=True)
                    file_path = f"masters/{st.session_state.active_project}_{m_name}.png"
                    cropped_master.save(file_path)
                    
                    # 4. Zapíšeme do DB
                    database.add_master(st.session_state.active_project, m_name, ax, ay, aw, ah, file_path)
                    
                    st.success(f"Master '{m_name}' uložen jako výřez!")
                    st.rerun()

        with col_img:
            # Živý náhled s výřezem
            raw_frame = cam.get_frame()
            pil_raw = Image.fromarray(raw_frame)
            preview_crop = pil_raw.crop((ax, ay, ax + aw, ay + ah))
            
            st.image(preview_crop, caption="Náhled AOI (to, co uvidí AI)", use_container_width=True)
            st.write(f"📏 Rozlišení: {aw} x {ah} px")

    # KROK 3: ROI DEFINICE
    elif st.session_state.step == 3:
        masters = database.get_masters(st.session_state.active_project)
        if masters:
            m_names = [m[2] for m in masters]
            sel_m_name = st.selectbox("Vyber Master:", m_names)
            curr_m = next(m for m in masters if m[2] == sel_m_name)
            
            # --- TADY TO MUSÍ BÝT ---
            # Načteme zóny pro tento konkrétní Master ID (curr_m[0])
            old_rois = database.get_rois(curr_m[0])
            
            img = Image.open(curr_m[7]).convert("RGB")
            # ------------------------

            col_main, col_side = st.columns([1.5, 1.0])
            
            st.divider()
                # ... (zbytek se seznamem zón zůstává stejný)

            # 1. Definujeme rozvržení (vlevo fotka, vpravo veškeré ovládání)
            col_main, col_side = st.columns([1.5, 1.0])
            
            with col_main:
                # Tady zůstává vykreslování obrázku (zelené a oranžové rámečky)
                # ... (tvůj kód pro Drawing a st.image) ...
                st.image(img, use_container_width=True)

            with col_side:
                # HORNÍ ČÁST: Přidávání nových zón
                st.subheader("➕ Správa zón")
                # ... (tvůj kód pro st.button "VYTVOŘIT NOVOU ZÓNU" a slidery) ...

                st.divider()

                # SPODNÍ ČÁST: Seznam zón (přesunuto zespodu sem)
                st.subheader("📋 Seznam zón")
                
                # Uděláme seznam kompaktnější, aby se jich tam vešlo hodně
                for r in old_rois:
                    # Použijeme kontejner s ohraničením pro každou zónu
                    with st.container(border=True):
                        c1, c2 = st.columns([4, 1])
                        c1.markdown(f"**{r[1]}**")
                        c1.caption(f"Typ: NOK {r[6]}")
                        if c2.button("🗑️", key=f"del_{r[0]}", help="Smazat zónu"):
                            database.delete_roi(r[0])
                            st.rerun()
                            
    elif st.session_state.step == 4:
        st.title("🔌 I/O Monitor - Rozhraní stroje")
        st.info("Zde můžete sledovat reálný stav komunikace s lisem a robotem.")

        # Hlavní rozdělení na Vstupy a Výstupy
        col_vstupy, col_vystupy = st.columns(2)

        with col_vstupy:
            st.markdown("### 📥 VSTUPY (Input)")
            st.write("Signály přicházející z lisu do programu.")
            
            # Simulace stavů vstupů (v reálu čtení z HW)
            col_led1, col_text1 = st.columns([1, 4])
            lis_provoz = st.toggle("LIS V PROVOZU (S1)", value=True)
            if lis_provoz:
                col_led1.markdown("🟢")
                col_text1.success("LIS BĚŽÍ - Světla svítí")
            else:
                col_led1.markdown("🔴")
                col_text1.error("LIS ZASTAVEN - Světla vypnuta")

            col_led2, col_text2 = st.columns([1, 4])
            trigger_active = st.button("📸 TRIGGER (S2) - Vyfotit")
            if trigger_active:
                col_led2.markdown("🟡")
                col_text2.warning("TRIGGER AKTIVNÍ - Probíhá inspekce")
            else:
                col_led2.markdown("⚫")
                col_text2.info("ČEKÁM NA TRIGGER")

        with col_vystupy:
            st.markdown("### 📤 VÝSTUPY (Output)")
            st.write("Signály odesílané z programu do robotu.")

            # Tady simulujeme rozhodovací logiku
            # Pro test si zde můžeš přepnout výsledek:
            vysledek_test = st.radio("Simulovat výsledek:", ["Čekání", "Vše OK", "NOK 1", "NOK 2"], horizontal=True)

            st.divider()

            if vysledek_test == "Vše OK":
                st.success("✅ VÝSLEDEK: OK")
                st.write("🤖 **VÝSTUP: ROBOTE ODJEĎ** (Pin Y0 -> HIGH)")
                st.progress(100)
            elif "NOK" in vysledek_test:
                st.error(f"❌ VÝSLEDEK: {vysledek_test}")
                st.write("🤖 **VÝSTUP: VYŘADIT KUS** (Pin Y1/Y2 -> HIGH)")
                st.progress(0)
            else:
                st.info("⚪ SYSTÉM PŘIPRAVEN")
                st.write("🤖 Čekám na dokončení cyklu lisu...")

            # Přehledná tabulka digitálních výstupů pro údržbu
            st.table({
                "Digitální výstup": ["Y0 (Celkově OK)", "Y1 (Chyba NOK 1)", "Y2 (Chyba NOK 2)", "Y3 (Systém Ready)"],
                "Logický stav": [
                    "1 (Zapnuto)" if vysledek_test == "Vše OK" else "0",
                    "1 (Zapnuto)" if vysledek_test == "NOK 1" else "0",
                    "1 (Zapnuto)" if vysledek_test == "NOK 2" else "0",
                    "1 (Zapnuto)" if vysledek_test == "Čekání" else "0"
                ]
            })                        

# ... (zbytek monitoring sekce)

elif menu == "Monitoring":
    st.title("📊 Živý monitoring")
    st.write("Zde se zobrazují výsledky inspekce.")
    # Zde pak doděláme tu mřížku detailů (krok 4)