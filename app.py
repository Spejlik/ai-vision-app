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
        if c1.button("📁", help="Projekty"): st.session_state.step = 1
    with c2:
        if c2.button("🎯", help="Master"): st.session_state.step = 2
    with c3:
        if c3.button("🔍", help="ROI"): st.session_state.step = 3
    with c4:    
        if c4.button("🔌", help="I/O"): st.session_state.step = 4  
    
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
        if not masters:
            st.error("Žádné Mastery.")
        else:
            m_names = [m[2] for m in masters]
            sel_m_name = st.selectbox("Vyber Master:", m_names, label_visibility="collapsed")
            curr_m = next(m for m in masters if m[2] == sel_m_name)
            
            img_path = curr_m[7]
            img = Image.open(img_path).convert("RGB")
            W, H = img.size

            # --- TADY JE TA OPRAVA: Definuj old_rois hned na začátku ---
            old_rois = database.get_rois(curr_m[0]) 
            # ---------------------------------------------------------

            col_main, col_side = st.columns([1.5, 1.0])
            
            with col_side:
                st.subheader("➕ Správa zón")
                
                # Pokud zrovna needitujeme, ukážeme tlačítko pro novou zónu
                if not st.session_state.get('manual_add_active', False):
                    if st.button("✨ VYTVOŘIT NOVOU ZÓNU", use_container_width=True):
                        st.session_state.manual_add_active = True
                        st.rerun()
                
                if st.session_state.get('manual_add_active', False):
                    with st.expander("Nastavení nové zóny", expanded=True):
                        name = st.text_input("Název zóny:", f"Zóna {len(old_rois)+1}")
                        
                        # Slidery pro přesné polohování
                        rx = st.slider("X pozice", 0, W, W//2)
                        ry = st.slider("Y pozice", 0, H, H//2)
                        rw = st.slider("Šířka", 10, 500, 100)
                        rh = st.slider("Výška", 10, 500, 100)
                        
                        # Oprava bodu 2: NOK kódy
                        nok_val = st.selectbox("Typ vady:", 
                                             options=range(1, 11), 
                                             format_func=lambda x: f"NOK {x}")
                        
                        c1, c2 = st.columns(2)
                        if c1.button("💾 ULOŽIT", type="primary", use_container_width=True):
                            database.save_roi(curr_m[0], name, rx, ry, rw, rh, nok_val)
                            # Necháme menu otevřené pro další kousek, ale resetujeme jméno
                            st.success("Uloženo!")
                            st.rerun()
                            
                        if c2.button("✖ ZAVŘÍT", use_container_width=True):
                            st.session_state.manual_add_active = False
                            st.rerun()
                
                st.divider()
                # ... (zbytek se seznamem zón zůstává stejný)

            with col_main:
                # Kreslení do kopie obrázku
                draw = ImageDraw.Draw(img)
                valeo_green = "#97BE0D"
                orange = "#FF9800"
                
                # 1. Vykresli uložené (Zeleně)
                for r in old_rois:
                    draw.rectangle([r[2], r[3], r[2]+r[4], r[3]+r[5]], outline=valeo_green, width=5)
                    draw.text((r[2]+5, r[3]+5), f"{r[1]} [N{r[6]}]", fill=valeo_green)
                
                # 2. Vykresli aktuální náhled ze sliderů (Oranžově)
                # OPRAVA: Místo 'if add_mode:' použijeme kontrolu session_state
                if st.session_state.get('manual_add_active', False):
                    draw.rectangle([rx, ry, rx+rw, ry+rh], outline=orange, width=5)
                    draw.text((rx+5, ry+5), "NÁHLED ZÓNY", fill=orange)
                
                st.image(img, use_container_width=True)

                # PEVNÝ PANEL SEZNAMU (s vnitřním scrollováním, pokud je dlouhý)
                st.write("📋 Seznam zón")
                list_container = st.container(height=300) # Pevná výška seznamu!
                with list_container:
                    for r in old_rois:
                        c1, c2 = st.columns([3, 1])
                        c1.caption(f"**{r[1]}** (NOK {r[6]})")
                        if c2.button("⚙️", key=f"cfg_{r[0]}", help="Editovat"):
                            st.session_state.edit_roi_id = r[0]
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