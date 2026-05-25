import streamlit as st
import cv2
import database
import camera_manager
import os
import time
from PIL import Image, ImageDraw

# 1. GLOBÁLNÍ KONFIGURACE
st.set_page_config(layout="wide", page_title="Vision System Terminal")

# 2. INICIALIZACE
database.init_db()
# cam = camera_manager.BaslerCam() 

if 'setup_image_buffer' not in st.session_state:
    st.session_state.setup_image_buffer = None
if 'active_project' not in st.session_state:
    st.session_state.active_project = None
if 'selected_master_id' not in st.session_state:
    st.session_state.selected_master_id = None

# CSS pro profesionální vzhled
st.markdown("""
    <style>
        .block-container { padding-top: 1rem; }
        header { visibility: hidden; }
        .stButton>button { border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR: SPRÁVA PROJEKTŮ ---
with st.sidebar:
    st.title("⚙️ Konfigurace")
    
    new_project_name = st.text_input("Název nového projektu", key="new_proj_input")
    if st.button("➕ Vytvořit projekt", use_container_width=True):
        if new_project_name.strip():
            database.add_project(new_project_name.strip())
            st.success(f"Projekt {new_project_name} vytvořen!")
            st.rerun()

    st.divider()

    projects = database.get_projects()
    if projects:
        if 'active_project' not in st.session_state or st.session_state.active_project not in projects:
            st.session_state.active_project = projects[0]
            
        st.session_state.active_project = st.selectbox(
            "Vyberte aktivní projekt", 
            projects,
            index=projects.index(st.session_state.active_project)
        )
    else:
        st.warning("⚠️ Nejdříve vytvořte projekt")
        st.session_state.active_project = None

# --- DEFINICE TABŮ ---
tab1, tab2, tab3, tab4 = st.tabs(["🚀 BĚH", "🎯 MASTER", "🔍 ZÓNY", "🔌 I/O"])

# --- TAB 1: BĚH ---
with tab1:
    st.subheader(f"🚀 Live Inspekce - Projekt: {st.session_state.active_project}")
    
    if st.session_state.active_project:
        active_p = st.session_state.active_project
        all_masters = database.get_all_masters(active_p)
        
        if not all_masters:
            st.warning("⚠️ Nemáte vytvořené žádné Mastery. Systém nemá z čeho inspekci spouštět.")
        else:
            all_active_rois = []
            for m in all_masters:
                rois = database.get_rois(m[0], active_p)
                for r in rois:
                    all_active_rois.append((m, r))
            
            if not all_active_rois:
                st.warning("⚠️ Nemáte definované žádné zóny (ROI). Vytvořte je v Tabu 3.")
            else:
                col_run_1, col_run_2 = st.columns([2.5, 1])
                
                with col_run_1:
                    st.markdown("### 🔍 Detailní náhledy inspekčních zón (ROI)")
                    roi_placeholders = {}
                    # Zobrazíme max 4 čtvercové ROI vedle sebe
                    roi_cols = st.columns(4)
                    
                    for i, (m, r) in enumerate(all_active_rois):
                        m_name, r_id, r_name = m[2], r[0], r[3]
                        with roi_cols[i % 4]:
                            with st.container(border=True):
                                st.markdown(f"**{r_name}** <br><span style='font-size:0.8em; color:gray;'>📷 {m_name}</span>", unsafe_allow_html=True)
                                roi_placeholders[r_id] = st.empty()
                
                with col_run_2:
                    st.markdown("### 📊 Výstupy PLC (NOK 1-8)")
                    io_col1, io_col2 = st.columns(2)
                    plc_indicators = {}
                    for idx in range(1, 9):
                        target_col = io_col1 if idx <= 4 else io_col2
                        with target_col:
                            plc_indicators[idx] = st.empty()
                
                st.divider()
                run_engine = st.toggle("▶️ SPUSTIT ŽIVOU INSPEKCI", key="run_engine_toggle")
                current_outputs = {i: False for i in range(1, 9)}

                if run_engine:
                    import random
                    import glob
                    import numpy as np
                    
                    # Procházíme nadefinované zóny v aplikaci
                    for m, r in all_active_rois:
                        m_path = m[3]
                        # r[3] je název zóny (např. Zebro_P1), r[8] je NOK kód, r[9] je tolerance citlivosti
                        r_id, r_name, r_nok = r[0], r[3], r[8]
                        r_tolerance = r[9] if len(r) > 9 else 20
                        
                        # 1. NAČTENÍ MASTER ŠABLONY (Reference pro porovnání)
                        if os.path.exists(m_path):
                            master_full = Image.open(m_path).convert("RGB")
                        else:
                            master_full = Image.new('RGB', (1200, 800), color=(70, 109, 137))
                        master_crop = master_full.crop((r[4], r[5], r[4]+r[6], r[5]+r[7]))
                        master_roi_np = np.array(master_crop)

                        # 2. ŽIVÝ AUTOMATICKÝ SBĚR REÁLNÝCH FOTEK Z DISKU
                        # Vyhledáme všechny .jpg snímky ve složkách OK a NOK pro danou zónu
                        ok_files = glob.glob(f"dataset/OK/{r_name}/*.jpg")
                        nok_files = glob.glob(f"dataset/NOK/{r_name}/*.jpg")
                        
                        # Spojíme je do jednoho listu, ze kterého budeme náhodně losovat "živý kus" z linky
                        all_test_files = ok_files + nok_files
                        
                        live_roi_np = None
                        chosen_file_name = "Simulace (Chybí lokální soubory)"
                        
                        if all_test_files:
                            # Losujeme jeden náhodný snímek z datasetu jako simulaci průjezdu kusu na lince
                            selected_path = random.choice(all_test_files)
                            chosen_file_name = os.path.basename(selected_path)
                            
                            # Načteme reálnou testovací fotku
                            live_roi_img = Image.open(selected_path).convert("RGB")
                            # Vynutíme stejný rozměr matice jako má Master pro korektní matematické porovnání
                            live_roi_img = live_roi_img.resize((r[6], r[7]), Image.Resampling.LANCZOS)
                            live_roi_np = np.array(live_roi_img)
                        else:
                            # Záložní varianta, pokud by skript nenašel složku dataset
                            live_roi_np = np.array(master_crop)

                        # 3. VÝPOČET REÁLNÉ MATEMATICKÉ ODCHYLKY (MSE)
                        err = np.sum((master_roi_np.astype("float") - live_roi_np.astype("float")) ** 2)
                        err /= float(master_roi_np.shape[0] * master_roi_np.shape[1] * master_roi_np.shape[2])
                        
                        # Škálování odchylky pro přehlednost na slideru
                        final_deviation = min(100, int(err / 15))
                        
                        # Vyhodnocení limitu
                        if final_deviation > r_tolerance:
                            is_zone_ok = False
                            current_outputs[r_nok] = True
                        else:
                            is_zone_ok = True
                            
                        zone_color = "#00FF00" if is_zone_ok else "#FF4B4B"
                        
                        # 4. Úprava na čtvercovou dlaždici a vykreslení orámování stavu
                        roi_img = Image.fromarray(live_roi_np)
                        desired_square_size = 500
                        roi_square = roi_img.resize((desired_square_size, desired_square_size), Image.Resampling.LANCZOS)
                        
                        draw_sq = ImageDraw.Draw(roi_square)
                        sq_line_w = max(6, int(desired_square_size * 0.015)) 
                        draw_sq.rectangle([0, 0, desired_square_size-1, desired_square_size-1], outline=zone_color, width=sq_line_w)
                        
                        # Zobrazení výsledku na Dashboardu
                        status_text = "OK" if is_zone_ok else "NOK!"
                        caption_str = f"Snímek: {chosen_file_name} | Odchylka: {final_deviation}% (Limit: {r_tolerance}%) | {status_text}"
                        roi_placeholders[r_id].image(roi_square, use_container_width=True, caption=caption_str)
                        
                    # Aktualizace PLC kontrolek
                    for idx in range(1, 9):
                        if current_outputs.get(idx, False):
                            plc_indicators[idx].markdown(f"<div style='background-color:#FF4B4B; color:white; padding:10px; border-radius:5px; text-align:center; font-weight:bold; margin-bottom:5px;'>🚨 NOK {idx}</div>", unsafe_allow_html=True)
                        else:
                            plc_indicators[idx].markdown(f"<div style='background-color:#00D48A; color:white; padding:10px; border-radius:5px; text-align:center; font-weight:bold; margin-bottom:5px;'>✅ OK {idx}</div>", unsafe_allow_html=True)
                else:
                    # Tento else patří k "if run_engine:" když je inspekce vypnutá
                    for idx in range(1, 9):
                        plc_indicators[idx].markdown(f"<div style='background-color:#E0E0E0; color:#666; padding:10px; border-radius:5px; text-align:center; margin-bottom:5px;'>⚫ Výstup {idx}</div>", unsafe_allow_html=True)
                    for m, r in all_active_rois:
                        roi_placeholders[r[0]].info("Čeká...")
    else:
        st.warning("⚠️ Nejdříve vyberte nebo vytvořte projekt v levém panelu.")
# --- TAB 2: MASTER ---
with tab2:
    st.subheader("📸 Nastavení Master snímků")
    col_ctrl, col_img = st.columns([1, 2])
    
    with col_ctrl:
        st.write("### ✂️ Definice výřezu")
        m_id_name = st.text_input("Název Masteru (např. Kamera 1)")
        
        # Slidery pro ořez (ax, ay, aw, ah)
        ax = st.slider("X začátek", 0, 2000, 100)
        ay = st.slider("Y začátek", 0, 2000, 100)
        aw = st.slider("Šířka výřezu", 10, 2000, 500)
        ah = st.slider("Výška výřezu", 10, 2000, 500)

        if st.button("💾 ULOŽIT MASTER", type="primary", use_container_width=True):
            if m_id_name and st.session_state.setup_image_buffer:
                if not os.path.exists("masters"):
                    os.makedirs("masters")
                
                filename = f"masters/master_{int(time.time())}.png"
                img = st.session_state.setup_image_buffer
                
                # 1. Klasický ořez ze sliderů
                cropped_img = img.crop((ax, ay, ax + aw, ay + ah))
                
                # 2. Úprava na čtverec (Square Padding), aby mřížka držela tvar
                max_side = max(aw, ah)
                square_img = Image.new('RGB', (max_side, max_side), color=(50, 50, 50))
                
                offset_x = (max_side - aw) // 2
                offset_y = (max_side - ah) // 2
                square_img.paste(cropped_img, (offset_x, offset_y))
                
                # Zmenšení na jednotný rozměr pro rychlé náhledy
                square_img = square_img.resize((500, 500), Image.Resampling.LANCZOS)
                square_img.save(filename)
                
                # TADY BYLA CHYBA: Musíme poslat aktivní projekt jako PRVNÍ parametr!
                database.add_master(st.session_state.active_project, m_id_name, filename, ax, ay, aw, ah)
                st.success(f"Master {m_id_name} uložen pro projekt {st.session_state.active_project}!")
                st.rerun()

    with col_img:
        if st.button("📸 Zachytit testovací snímek"):
            st.session_state.setup_image_buffer = Image.new('RGB', (1200, 800), color=(73, 109, 137))
        
        if st.session_state.setup_image_buffer is not None:
            preview_img = st.session_state.setup_image_buffer.copy()
            
            # Adaptivní tloušťka pro náhled ořezu
            cam_w = preview_img.size[0]
            master_line_w = max(2, int(cam_w * 0.007))
            
            draw = ImageDraw.Draw(preview_img)
            draw.rectangle([ax, ay, ax+aw, ay+ah], outline="red", width=master_line_w)
            st.image(preview_img, use_container_width=True, caption="Červený rámeček ukazuje budoucí ořez")

# --- TAB 3: ZÓNY ---
with tab3:
    if 'editing_roi_id' not in st.session_state:
        st.session_state.editing_roi_id = None

    active_p = st.session_state.active_project
    st.info(f"🏗️ Aktuálně nastavujete zóny pro projekt: **{active_p}**")
    
    all_masters = database.get_all_masters(active_p)
    
    if not all_masters:
        st.warning("⚠️ Knihovna Masterů je pro tento projekt prázdná. Nejdříve vytvořte Master v Tabu 2.")
    else:
        if 'selected_master_id' not in st.session_state or st.session_state.selected_master_id is None:
            st.session_state.selected_master_id = all_masters[0][0]

        # --- DOKONALÁ ČTVERCOVÁ MŘÍŽKA GALERIE (S RÁMEČKY) ---
        st.write("### 🖼️ Výběr pozice / kamery:")
        
        COLUMNS_PER_ROW = 6
        m_rows = [all_masters[i:i + COLUMNS_PER_ROW] for i in range(0, len(all_masters), COLUMNS_PER_ROW)]
        
        for row in m_rows:
            cols = st.columns(COLUMNS_PER_ROW)
            for idx, m in enumerate(row):
                m_id_loop, m_name_loop, m_path_loop = m[0], m[2], m[3]
                
                with cols[idx]:
                    # Použijeme kontejner s rámečkem, aby se obrázky a tlačítka neslily dohromady
                    with st.container(border=True):
                        if os.path.exists(m_path_loop):
                            st.image(m_path_loop, use_container_width=True)
                        
                        is_active = (m_id_loop == st.session_state.selected_master_id)
                        
                        if st.button(
                            f"📸 {m_name_loop}", 
                            key=f"btn_m_{m_id_loop}", 
                            use_container_width=True,
                            type="primary" if is_active else "secondary"
                        ):
                            st.session_state.selected_master_id = m_id_loop
                            st.session_state.editing_roi_id = None
                            st.rerun()

        st.divider()
        
        # Načtení aktivního masteru ze seznamu
        sel_m = next((m for m in all_masters if m[0] == st.session_state.selected_master_id), None)
        
        if sel_m is None and all_masters:
            st.session_state.selected_master_id = all_masters[0][0]
            sel_m = all_masters[0]

        if sel_m and os.path.exists(sel_m[3]):
            m_id, m_name, m_path = sel_m[0], sel_m[2], sel_m[3]
            
            img_roi = Image.open(m_path).convert("RGB")
            W, H = img_roi.size
            all_rois = database.get_rois(m_id, active_p)
            
            # Rozvržení: Ovládání vlevo, obraz vpravo
            c_ctrl, c_viz = st.columns([1, 1.8])
            
            with c_ctrl:
                st.markdown(f"### 🔧 Nastavení zón: {m_name}")
                
                # Načtení dat pokud jsme v režimu editace
                current_roi = None
                if st.session_state.editing_roi_id:
                    current_roi = next((r for r in all_rois if r[0] == st.session_state.editing_roi_id), None)
                
                # Výchozí hodnoty pro formulář
                default_name = current_roi[3] if current_roi else f"Zóna {len(all_rois)+1}"
                default_nok = current_roi[8] if current_roi else 1
                default_x = current_roi[4] if current_roi else 50
                default_y = current_roi[5] if current_roi else 50
                default_w = current_roi[6] if current_roi else 100
                default_h = current_roi[7] if current_roi else 100
                
                zn = st.text_input("Název zóny", value=default_name)
                nok_val = st.selectbox("Přiřazení chyby (NOK 1-8)", range(1, 9), index=default_nok - 1)
                
                # Načtení výchozí tolerance z DB (r[9]), pokud editujeme, jinak výchozí 20
                default_tolerance = current_roi[9] if current_roi and len(current_roi) > i else 20
                
                zx = st.slider("X", 0, W, default_x, key="sx")
                zy = st.slider("Y", 0, H, default_y, key="sy")
                zw = st.slider("Šířka", 10, W, default_w, key="sw")
                zh = st.slider("Výška", 10, H, default_h, key="sh")
                
                # NOVÝ SLIDER: Čím menší číslo, tím je kontrola přísnější
                ztol = st.slider("Tolerance odchylky (čím méně, tím přísnější)", 1, 100, default_tolerance, key="stol")
                
                if st.session_state.editing_roi_id:
                    col_save_1, col_save_2 = st.columns(2)
                    with col_save_1:
                        if st.button("🔄 AKTUALIZOVAT", type="primary", use_container_width=True):
                            database.update_roi(st.session_state.editing_roi_id, zn, zx, zy, zw, zh, nok_val, ztol)
                            st.session_state.editing_roi_id = None
                            st.success("Zóna aktualizována!")
                            st.rerun()
                    with col_save_2:
                        if st.button("❌ ZRUŠIT", use_container_width=True):
                            st.session_state.editing_roi_id = None
                            st.rerun()
                else:
                    if st.button("💾 ULOŽIT NOVOU ZÓNU", type="primary", use_container_width=True):
                        database.save_roi(m_id, active_p, zn, zx, zy, zw, zh, nok_val, ztol)
                        st.success("Zóna uložena!")
                        st.rerun()
                
                # --- SPRÁVA ZÓN (EDITACE / MAZÁNÍ) ---
                if all_rois:
                    st.write("---")
                    st.write("📋 **Uložené zóny (Správa):**")
                    for r in all_rois:
                        r_id, r_name, r_nok = r[0], r[3], r[8]
                        
                        del_col1, del_col2, del_col3 = st.columns([2.5, 0.8, 0.8])
                        with del_col1:
                            st.write(f"• {r_name} (NOK{r_nok})")
                        with del_col2:
                            if st.button("📝", key=f"edit_roi_{r_id}", help=f"Editovat {r_name}"):
                                st.session_state.editing_roi_id = r_id
                                st.rerun()
                        with del_col3:
                            if st.button("🗑️", key=f"del_roi_{r_id}", help=f"Smazat {r_name}"):
                                database.delete_roi(r_id)
                                if st.session_state.editing_roi_id == r_id:
                                    st.session_state.editing_roi_id = None
                                st.rerun()

                # --- SMAZÁNÍ CELÉHO MASTERU ---
                st.write("---")
                if st.button("🚨 SMAZAT TENTO MASTER", key="del_master_btn", use_container_width=True):
                    database.delete_master(m_id)
                    st.session_state.selected_master_id = None
                    st.session_state.editing_roi_id = None
                    st.warning("Master i jeho zóny smazány.")
                    st.rerun()

            with c_viz:
                draw = ImageDraw.Draw(img_roi)
                line_w = max(2, int(W * 0.007))
                
                # 1. Kreslení uložených zón
                for r in all_rois:
                    rx, ry, rw, rh = r[4], r[5], r[6], r[7]
                    # Pokud zónu zrovna editujeme, nevykreslíme ji zeleně (překrývala by oranžový náhled)
                    if r[0] != st.session_state.editing_roi_id:
                        draw.rectangle([rx, ry, rx+rw, ry+rh], outline="#00FF00", width=line_w)
                        draw.text((rx, ry-15), f"{r[3]} (NOK{r[8]})", fill="#00FF00")

                # 2. Kreslení oranžového náhledu z aktuálních sliderů
                draw.rectangle([zx, zy, zx+zw, zy+zh], outline="orange", width=line_w + 2)
                draw.text((zx, zy-25), "NÁHLED / EDITACE ZÓNY", fill="orange")
                
                st.image(img_roi, use_container_width=True, caption=f"Pracovní plocha: {m_name}")

# --- TAB 4: I/O ---
with tab4:
    st.subheader("🔌 Nastavení komunikace (Modbus TCP / Moxa)")
    st.write("Zde bude konfigurace IP adresy a registru pro odesílání NOK signálů do linky.")
    
    # Rychlý testovací status pro kontrolu spojení
    st.text_input("IP Adresa Moxa I/O modulu", value="192.168.1.200")
    st.button("🔄 Testovat připojení hardwaru", use_container_width=True)