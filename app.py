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
                # Převedeme na RGB, aby barvy byly konzistentní
                img = img.convert("RGB")
                draw = ImageDraw.Draw(img)
                old_rois = database.get_rois(curr_m[0])
                
                # BARVA: Valeo Bright Green (PMS 376 / #97BE0D)
                valeo_green = "#97BE0D" 
                
                edit_id = st.session_state.get('edit_roi_id', None)
                
                for r in old_rois:
                    if edit_id == r[0]: continue 
                    # Vykreslení s pevnou tloušťkou 3px
                    shape = [r[2], r[3], r[2]+r[4], r[3]+r[5]]
                    draw.rectangle(shape, outline=valeo_green, width=3)
                    # Text s malým odsazením pro stabilitu
                    draw.text((r[2] + 2, r[3] + 2), f"{r[1]} [NOK {r[6]}]", fill=valeo_green)

                c_l, c_r = st.columns([3, 1])
                with c_l:
                    st.write("📌 " + ("UPRAVUJETE POZICI" if edit_id else "NOVÁ ZÓNA"))
                    # Unikátní klíč pro zabránění posunu (cacheování pozice)
                    cropper_key = f"c_{edit_id if edit_id else 'n'}_{len(old_rois)}"
                    
                    # Fix: vypnutí realtime_update může snížit problikávání při pohybu
                    roi = st_cropper(img, realtime_update=True, box_color='#FF9800', 
                                     aspect_ratio=None, key=cropper_key)

                with c_r:
                    if edit_id:
                        curr_r = next(r for r in old_rois if r[0] == edit_id)
                        st.info(f"Editace: {curr_r[1]}")
                        if st.button("✅ POTVRDIT ZMĚNU", type="primary", use_container_width=True):
                            # Získání souřadnic se zaokrouhlením na celé pixely
                            c = st.session_state[cropper_key]['coords']
                            database.update_roi_position(edit_id, int(c['left']), int(c['top']), 
                                                       int(c['width']), int(c['height']))
                            st.session_state.edit_roi_id = None
                            st.rerun()
                        if st.button("❌ ZRUŠIT"):
                            st.session_state.edit_roi_id = None
                            st.rerun()
                    else:
                        st.write("### ➕ Nová kontrola")
                        new_name = st.text_input("Název:")
                        new_nok = st.selectbox("NOK:", options=range(1, 9), format_func=lambda x: f"NOK {x}")
                        if st.button("💾 ULOŽIT", type="primary", use_container_width=True):
                            c = st.session_state[cropper_key]['coords']
                            database.save_roi(curr_m[0], new_name, int(c['left']), int(c['top']), 
                                             int(c['width']), int(c['height']), new_nok)
                            st.rerun()

                    st.divider()
                    st.write("### ⚙️ Seznam")
                    for r in old_rois:
                        with st.expander(f"{r[1]} (NOK {r[6]})"):
                            if st.button("🎮 Upravit pozici", key=f"ed_{r[0]}"):
                                st.session_state.edit_roi_id = r[0]
                                st.rerun()
                            # ... (zbytek smazání a NOK kódu zůstává stejný)

# ... (zbytek monitoring sekce)

elif menu == "Monitoring":
    st.title("📊 Živý monitoring")
    st.write("Zde se zobrazují výsledky inspekce.")
    # Zde pak doděláme tu mřížku detailů (krok 4)