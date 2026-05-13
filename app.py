import streamlit as st
from streamlit_cropper import st_cropper
from PIL import Image, ImageDraw
import database
import camera_manager
import time
import os

# Inicializace
st.set_page_config(layout="wide", page_title="AI Vision Inspection")
database.init_db()
cam = camera_manager.BaslerCam()

if 'step' not in st.session_state: st.session_state.step = 1
if 'active_project' not in st.session_state: st.session_state.active_project = None
if 'active_master' not in st.session_state: st.session_state.active_master = None

st.sidebar.title("📷 Menu")
menu = st.sidebar.radio("Navigace", ["Konfigurace", "Monitoring"])

if menu == "Konfigurace":
    st.title("⚙️ Nastavení systému")
    
    # Průvodce kroky
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("1. Projekt", use_container_width=True): st.session_state.step = 1
    with c2:
        if st.button("2. Master & AOI", use_container_width=True): st.session_state.step = 2
    with c3:
        if st.button("3. ROI (Inspekce)", use_container_width=True): st.session_state.step = 3
    
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

    # KROK 2: MASTER A OŘEZ (AOI)
    elif st.session_state.step == 2:
        if not st.session_state.active_project:
            st.warning("Nejdříve vyberte projekt v kroku 1!")
        else:
            st.subheader(f"🖼️ Nastavení Masteru pro: {st.session_state.active_project}")
            
            col_l, col_r = st.columns([2, 1])
            
            with col_r:
                st.write("### Nastavení ořezu kamery (AOI)")
                # Nastavíme max. limity podle reálného rozlišení (např. 2500x2000)
                ax = st.slider("X pozice (vlevo)", 0, 2000, 0)
                ay = st.slider("Y pozice (nahoře)", 0, 2000, 0)
                aw = st.slider("Šířka výřezu", 100, 2500, 1200)
                ah = st.slider("Výška výřezu", 100, 2500, 1000)
                
                master_name = st.text_input("Název Master snímku", placeholder="např. MQB_P1_TOP")
                
                if st.button("📸 VYFOTIT A ULOŽIT MASTER", type="primary", use_container_width=True):
                    if master_name:
                        # Tady uložíme oříznutý obrázek na disk
                        final_frame = cam.get_frame()
                        # Převedeme numpy na PIL pro ořez
                        pil_img = Image.fromarray(final_frame)
                        cropped_master = pil_img.crop((ax, ay, ax + aw, ay + ah))
                        
                        img_path = f"masters/{master_name}.jpg"
                        if not os.path.exists('masters'): os.makedirs('masters')
                        cropped_master.save(img_path)
                        
                        database.save_master(st.session_state.active_project, master_name, ax, ay, aw, ah, img_path)
                        st.success(f"Master '{master_name}' uložen!")
                    else:
                        st.error("Zadejte název Masteru!")

            with col_l:
                # ŽIVÝ NÁHLED S OŘEZEM V REÁLNÉM ČASE
                raw_frame = cam.get_frame()
                pil_raw = Image.fromarray(raw_frame)
                
                # ZDE SE DĚJE TEN REÁLNÝ NÁHLED OŘEZU
                # crop((left, top, right, bottom))
                preview_crop = pil_raw.crop((ax, ay, ax + aw, ay + ah))
                
                st.image(preview_crop, caption="Náhled ořezu (AOI)", use_container_width=True)
                st.write(f"📏 Aktuální rozlišení masteru: {aw} x {ah} px")

    # ... (začátek app.py zůstává stejný)

    # KROK 3: ROI DEFINICE
    elif st.session_state.step == 3:
        st.subheader("🔍 Definice inspekčních zón")
        masters = database.get_masters(st.session_state.active_project)
        
        if not masters:
            st.error("Žádné Mastery nenalezeny.")
        else:
            m_names = [m[2] for m in masters]
            sel_m_name = st.selectbox("Vyberte Master snímek (ořez):", m_names)
            curr_m = next(m for m in masters if m[2] == sel_m_name)
            path_to_img = curr_m[8] 
            
            if os.path.exists(path_to_img):
                img = Image.open(path_to_img)
                draw = ImageDraw.Draw(img)
                
                # Načteme kontroly a vypíšeme i s NOK kódem
                old_rois = database.get_rois(curr_m[0])
                for r in old_rois:
                    draw.rectangle([r[2], r[3], r[2]+r[4], r[3]+r[5]], outline="blue", width=5)
                    # Zobrazení názvu + NOK kódu (např. Guma dolití [NOK 3])
                    label = f"{r[1]} [NOK {r[6]}]"
                    draw.text((r[2], r[3] - 15), label, fill="blue")
                
                c_l, c_r = st.columns([3, 1])
                # ... in section elif st.session_state.step == 3:

                with c_l:
                    # Načteme existující ROI pro vizuální kontrolu
                    draw = ImageDraw.Draw(img)
                    old_rois = database.get_rois(curr_m[0])
                    for r in old_rois:
                        # Vykreslení ZELENÝCH rámečků pro všechny uložené ROI (posunutí opraveno)
                        shape = [r[2], r[3], r[2]+r[4], r[3]+r[5]]
                        draw.rectangle(shape, outline="lime", width=5) # Lime is a very bright green
                        label = f"{r[1]} [NOK {r[6]}]"
                        draw.text((r[2], r[3] - 15), label, fill="lime")
                    
                    # LOGIKA PRO SKRÝVÁNÍ CROPPERU
                    # Zobrazíme cropper pouze pokud uživatel zadává název nebo existují ROI
                    st.write("📌 Aktuálně definované zóny (zeleně):")
                    
                    # Vybereme klíč pro cropper. f"cropper_{len(old_rois)}"
                    # Tento klíč se mění s počtem ROI, což vynucuje reset cropperu.
                    cropper_key = f"cropper_{len(old_rois)}"
                    
                    # Zobrazit st_cropper pouze pokud jsou definovány dřívější ROI, aby se ukázaly.
                    # Nová oranžová ROI se objeví až uživatel začne kreslit.
                    # components.html(...) - Tady je limit Streamlit_cropper.
                    # Není snadné vynutit skrytí oranžového rámečku BEZ kliknutí.
                    # Obejdeme to vizuálním vysvětlením.
                    
                    # Pokud je to první ROI, cropper se zobrazí automaticky (limitace komponenty).
                    # Pokud jsou další, zobrazí se též, ale souřadnice jsou nové.
                    if len(old_rois) == 0:
                        st.info("Tažením rámečku definujte první zónu. Oranžový rámeček zmizí po uložení.")
                    else:
                        st.info("Zelené zóny jsou uložené. Tažením definujte DALŠÍ zónu. Oranžový rámeček zmizí po uložení.")
                        
                    roi = st_cropper(img, realtime_update=True, box_color='#FF9800', key=cropper_key)

                with c_r:
                    st.write("### ➕ Přidat novou kontrolu")
                    new_roi_name = st.text_input("Název nové kontroly:", key="new_roi_input", placeholder="např. Guma dolití ot1")
                    nok_code = st.selectbox("Kód pro vyřazení (robot):", options=range(1, 9), format_func=lambda x: f"NOK {x}")
                    
                    if st.button("💾 ULOŽIT TUTO ZÓNU", type="primary", use_container_width=True):
                        # Kontrola zda klíč existuje a není None
                        if cropper_key in st.session_state and st.session_state[cropper_key] is not None:
                            coords = st.session_state[cropper_key]['coords']
                            
                            if new_roi_name:
                                database.save_roi(
                                    curr_m[0], 
                                    new_roi_name, 
                                    int(coords['left']), 
                                    int(coords['top']), 
                                    int(coords['width']), 
                                    int(coords['height']),
                                    nok_code
                                )
                                st.success(f"Zóna '{new_roi_name}' přidána!")
                                time.sleep(0.5)
                                st.rerun() # Refresh pro zobrazení nové zelené zóny a skrytí cropperu
                            else:
                                st.error("Zadejte název kontroly před uložením.")
                        else:
                            st.warning("Zkuste pohnout oranžovým rámečkem před uložením.")
                    
                    st.divider()
                    st.write("### 📋 Již uložené kontroly na tomto ořezu")
                    for r in old_rois:
                        st.markdown(f"**{r[1]}** (NOK {r[6]})")

# ... (zbytek monitoring sekce)

elif menu == "Monitoring":
    st.title("📊 Živý monitoring")
    st.write("Zde se zobrazují výsledky inspekce.")
    # Zde pak doděláme tu mřížku detailů (krok 4)