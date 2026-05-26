import streamlit as st
import cv2
import database
import camera_manager
import os
import time
import ai_engine
import glob
import numpy as np
from PIL import Image, ImageDraw

# 1. GLOBÁLNÍ KONFIGURACE
st.set_page_config(layout="wide", page_title="Vision System Terminal")

# 2. INICIALIZACE
database.init_db()

if 'setup_image_buffer' not in st.session_state:
    st.session_state.setup_image_buffer = None
if 'active_project' not in st.session_state:
    st.session_state.active_project = None
if 'selected_master_id' not in st.session_state:
    st.session_state.selected_master_id = None

# CSS pro profesionální průmyslový vzhled
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
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🚀 BĚH", "🎯 MASTER", "🔍 ZÓNY", "🔌 I/O", "📜 HISTORIE"])

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
                # --- PEVNÉ UKLÁDÁNÍ OVLÁDÁNÍ NAHORU ---
                run_engine = st.toggle("▶️ SPUSTIT ŽIVOU INSPEKCI", key="run_engine_toggle")
                st.divider()
                
                col_run_1, col_run_2 = st.columns([2.5, 1])
                
                with col_run_1:
                    st.markdown("### 🔍 Detailní náhledy inspekčních zón (ROI)")
                    roi_placeholders = {}
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
                
                current_outputs = {i: False for i in range(1, 9)}

                if run_engine:
                    for m, r in all_active_rois:
                        m_path = m[3]
                        r_id, r_name, r_nok = r[0], r[3], r[8]
                        r_tolerance = r[9] if len(r) > 9 else 20
                        
                        if os.path.exists(m_path):
                            master_full = Image.open(m_path).convert("RGB")
                        else:
                            master_full = Image.new('RGB', (1200, 800), color=(70, 109, 137))
                        master_crop = master_full.crop((r[4], r[5], r[4]+r[6], r[5]+r[7]))
                        master_roi_np = np.array(master_crop)

                        # CHYTRÉ VYHLEDÁVÁNÍ TESTOVACÍCH FOTEK (Zpátky na tvůj původní dataset)
                        all_extensions = ["*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG"]
                        ok_files = []
                        nok_files = []
                        
                        search_paths = [
                            f"dataset/OK/Zebro_P1",
                            f"dataset/OK/{r_name}",
                            f"dataset/OK"
                        ]
                        
                        for path in search_paths:
                            if ok_files: break
                            for ext in all_extensions:
                                ok_files.extend(glob.glob(f"{path}/{ext}"))
                                
                        for path in search_paths:
                            if nok_files: break
                            for ext in all_extensions:
                                nok_files.extend(glob.glob(f"{path.replace('OK', 'NOK')}/{ext}"))
                        
                        all_test_files = ok_files + nok_files
                        
                        if all_test_files:
                            selected_path = random.choice(all_test_files) if 'random' in globals() else all_test_files[0]
                            # Rychlá oprava náhodného generátoru pro plynulý běh simulace lisu
                            import random as rand_mod
                            selected_path = rand_mod.choice(all_test_files)
                            chosen_file_name = os.path.basename(selected_path)
                            live_roi_img = Image.open(selected_path).convert("RGB")
                            live_roi_img = live_roi_img.resize((r[6], r[7]), Image.Resampling.LANCZOS)
                            live_roi_np = np.array(live_roi_img)
                        else:
                            chosen_file_name = "Fallback_z_Masteru.png"
                            live_roi_img = master_crop.copy()
                            live_roi_np = np.array(live_roi_img)
                            import random as rand_mod
                            if rand_mod.random() > 0.5:
                                live_roi_np = np.clip(live_roi_np.astype(int) - 30, 0, 255).astype(np.uint8)
                                live_roi_img = Image.fromarray(live_roi_np)

                        # INTEGRACE ŽIVÉHO AI VYHODNOCENÍ
                        model_path = f"models/model_ai_{active_p}_{r_name}.pth"
                        
                        if os.path.exists(model_path):
                            is_zone_ok, ai_confidence = ai_engine.predict_with_ai(model_path, live_roi_img)
                            jistota_procenta = int(ai_confidence * 100)
                            status_text = "OK" if is_zone_ok else "NOK"
                            caption_str = f"{chosen_file_name} | 🧠 AI Jistota: {jistota_procenta}% | Stav: {status_text}"
                        else:
                            err = np.sum((master_roi_np.astype("float") - live_roi_np.astype("float")) ** 2)
                            err /= float(master_roi_np.shape[0] * master_roi_np.shape[1] * master_roi_np.shape[2])
                            final_deviation = min(100, int(err / 15))
                            
                            if final_deviation > r_tolerance:
                                is_zone_ok = False
                                status_text = "NOK"
                            else:
                                is_zone_ok = True
                                status_text = "OK"
                            caption_str = f"{chosen_file_name} | ⚠️ Bez AI (Odchylka: {final_deviation}%) | {status_text}"
                        
                        if not is_zone_ok:
                            current_outputs[r_nok] = True
                            
                        zone_color = "#00FF00" if is_zone_ok else "#FF4B4B"
                        
                        # UKLÁDÁNÍ DO HISTORIE
                        base_drive = "D:/" if os.path.exists("D:/") else "C:/"
                        history_dir = os.path.join(base_drive, "Image", "Unsorted", active_p)
                        if not os.path.exists(history_dir):
                            os.makedirs(history_dir)
                            
                        import random as rand_mod
                        history_filename = os.path.join(history_dir, f"{r_name}_{int(time.time())}_{rand_mod.randint(100,999)}.png")
                        Image.fromarray(live_roi_np).save(history_filename)
                        database.save_to_history(active_p, r_name, history_filename, "Neroztříděno")
                        
                        roi_img = Image.fromarray(live_roi_np)
                        desired_square_size = 500
                        roi_square = roi_img.resize((desired_square_size, desired_square_size), Image.Resampling.LANCZOS)
                        
                        draw_sq = ImageDraw.Draw(roi_square)
                        sq_line_w = max(6, int(desired_square_size * 0.015)) 
                        draw_sq.rectangle([0, 0, desired_square_size-1, desired_square_size-1], outline=zone_color, width=sq_line_w)
                        
                        roi_placeholders[r_id].image(roi_square, use_container_width=True, caption=caption_str)
                        
                    # INTELIGENTNÍ AKTUALIZACE KONTROLEK PLC (ZAŠEDNUTÍ NEAKTIVNÍCH)
                    aktivni_plc_vystupy = set(r[1][8] for r in all_active_rois)
                    
                    for idx in range(1, 9):
                        if idx not in aktivni_plc_vystupy:
                            plc_indicators[idx].markdown(
                                f"<div style='background-color:#F5F5F5; color:#9E9E9E; padding:10px; border-radius:5px; text-align:center; font-size:14px; margin-bottom:5px; border: 1px dashed #E0E0E0;'>⚫ Neaktivní {idx}</div>", 
                                unsafe_allow_html=True
                            )
                        elif current_outputs.get(idx, False):
                            plc_indicators[idx].markdown(
                                f"<div style='background-color:#FF4B4B; color:white; padding:10px; border-radius:5px; text-align:center; font-weight:bold; font-size:14px; margin-bottom:5px;'>🚨 NOK {idx}</div>", 
                                unsafe_allow_html=True
                            )
                        else:
                            plc_indicators[idx].markdown(
                                f"<div style='background-color:#00D48A; color:white; padding:10px; border-radius:5px; text-align:center; font-weight:bold; font-size:14px; margin-bottom:5px;'>✅ OK {idx}</div>", 
                                unsafe_allow_html=True
                            )
                else:
                    for idx in range(1, 9):
                        plc_indicators[idx].markdown(f"<div style='background-color:#E0E0E0; color:#666; padding:10px; border-radius:5px; text-align:center; margin-bottom:5px;'>⚫ Výstup {idx}</div>", unsafe_allow_html=True)
                    for m, r in all_active_rois:
                        roi_placeholders[r[0]].info("Čeká...")
    else:
        st.warning("⚠️ Nejdříve vyberte nebo vytvořte projekt v levém panelu.")

# --- TAB 2: MASTER ---
with tab2:
    st.subheader("📸 Nastavení Master Snímků lisu")
    if not st.session_state.active_project:
        st.warning("⚠️ Vyberte aktivní projekt v levém panelu.")
    else:
        active_p = st.session_state.active_project
        col_ctrl, col_img = st.columns([1, 2])
        
        with col_ctrl:
            st.markdown("### 🔌 Zdroj obrázku")
            # Volba zdroje podkladu
            source_type = st.radio(
                "Vyberte, jak chcete nahrát podkladový snímek:",
                ["📷 Simulovat z kamery lisu (Složka OK)", "📁 Nahrát soubor z disku (Příprava dopředu)"]
            )
            
            st.divider()
            st.write("### ✂️ Definice výřezu")
            m_id_name = st.text_input("Název Masteru (např. Pozice 1)")
            
            ax = st.slider("X začátek", 0, 2000, 0)
            ay = st.slider("Y začátek", 0, 2000, 0)
            aw = st.slider("Šířka výřezu", 10, 2000, 500)
            ah = st.slider("Výška výřezu", 10, 2000, 500)

            if st.button("💾 ULOŽIT MASTER", type="primary", use_container_width=True):
                if m_id_name and st.session_state.setup_image_buffer:
                    if not os.path.exists("masters"):
                        os.makedirs("masters")
                    
                    filename = f"masters/master_{active_p}_{int(time.time())}.png"
                    img = st.session_state.setup_image_buffer
                    
                    # Výřez a formátování do čtverce 500x500
                    cropped_img = img.crop((ax, ay, ax + aw, ay + ah))
                    max_side = max(aw, ah)
                    square_img = Image.new('RGB', (max_side, max_side), color=(50, 50, 50))
                    square_img.paste(cropped_img, ((max_side - aw) // 2, (max_side - ah) // 2))
                    
                    square_img = square_img.resize((500, 500), Image.Resampling.LANCZOS)
                    square_img.save(filename)
                    
                    database.add_master(active_p, m_id_name, filename, ax, ay, aw, ah)
                    st.success(f"Master {m_id_name} byl úspěšně uložen pro offline přípravu!")
                    st.rerun()
                else:
                    st.error("❌ Pro uložení musíte zadat název a mít načtený/nahraný obrázek!")

        with col_img:
            # Podle zvoleného rádia zobrazíme správné ovládání
            if "Simulovat z kamery" in source_type:
                if st.button("📸 Zachytit testovací snímek z kamery lisu", use_container_width=True):
                    target_dir = os.path.join(BASE_IMAGE_DIR, "OK", active_p)
                    test_images = []
                    if os.path.exists(target_dir):
                        for ext in ["*.jpg", "*.JPG", "*.png", "*.PNG"]:
                            test_images.extend(glob.glob(os.path.join(target_dir, ext)))
                    
                    if test_images:
                        st.session_state.setup_image_buffer = Image.open(test_images[0]).convert("RGB")
                        st.success("Reálný snímek z lisu úspěšně načten!")
                    else:
                        st.session_state.setup_image_buffer = Image.new('RGB', (640, 480), color=(73, 109, 137))
                        st.warning(f"Složka '{target_dir}' je prázdná. Použita nouzová modrá plocha.")
            else:
                # Klasický průmyslový File Uploader pro nahrání z PC (.jpg, .png)
                uploaded_file = st.file_uploader("Vyberte obrázek formy z disku počítače:", type=["jpg", "jpeg", "png", "JPG", "JPEG", "PNG"])
                if uploaded_file is not None:
                    st.session_state.setup_image_buffer = Image.open(uploaded_file).convert("RGB")
                    st.success("Externí soubor úspěšně nahrán do paměti aplikace!")

            # Vykreslení náhledu s červeným řezacím rámečkem
            if st.session_state.setup_image_buffer is not None:
                preview_img = st.session_state.setup_image_buffer.copy()
                img_w, img_h = preview_img.size
                
                safe_ax = min(ax, img_w - 10)
                safe_ay = min(ay, img_h - 10)
                safe_aw = min(aw, img_w - safe_ax)
                safe_ah = min(ah, img_h - safe_ay)
                
                master_line_w = max(2, int(img_w * 0.01))
                draw = ImageDraw.Draw(preview_img)
                draw.rectangle([safe_ax, safe_ay, safe_ax + safe_aw, safe_ay + safe_ah], outline="red", width=master_line_w)
                st.image(preview_img, use_container_width=True, caption=f"Aktuální podklad ({img_w}x{img_h} px)")

        # Přehled existujících masterů
        st.write("---")
        st.write("📋 **Aktuální Master snímky v tomto projektu:**")
        m_list = database.get_all_masters(active_p)
        if m_list:
            for m_row in m_list:
                m_id, _, m_name, m_path, _, _, _, _ = m_row
                del_c1, del_c2 = st.columns([3, 1])
                with del_c1: st.write(f"• **{m_name}** (`{m_path}`)")
                with del_c2:
                    if st.button("🗑️ Smazat Master", key=f"del_m_{m_id}", use_container_width=True):
                        if m_path and os.path.exists(m_path):
                            try: os.remove(m_path)
                            except: pass
                        database.delete_master(m_id)
                        st.session_state.setup_image_buffer = None
                        st.success("Master smazán!")
                        st.rerun()

# --- TAB 3: ZÓNY ---
with tab3:
    if 'editing_roi_id' not in st.session_state:
        st.session_state.editing_roi_id = None

    active_p = st.session_state.active_project
    st.info(f"🏗️ Aktuálně nastavujete zóny pro projekt: **{active_p}**")
    all_masters = database.get_all_masters(active_p)
    
    if not all_masters:
        st.warning("⚠️ Knihovna Masterů je prázdná. Nejdříve vytvořte Master v Tabu 2.")
    else:
        if 'selected_master_id' not in st.session_state or st.session_state.selected_master_id is None:
            st.session_state.selected_master_id = all_masters[0][0]

        st.write("### 🖼️ Výběr pozice / kamery:")
        m_cols = st.columns(6)
        for idx, m in enumerate(all_masters):
            m_id_loop, m_name_loop, m_path_loop = m[0], m[2], m[3]
            with m_cols[idx % 6]:
                with st.container(border=True):
                    if os.path.exists(m_path_loop):
                        st.image(m_path_loop, use_container_width=True)
                    is_active = (m_id_loop == st.session_state.selected_master_id)
                    if st.button(f"📷 {m_name_loop}", key=f"btn_m_{m_id_loop}", use_container_width=True, type="primary" if is_active else "secondary"):
                        st.session_state.selected_master_id = m_id_loop
                        st.session_state.editing_roi_id = None
                        st.rerun()

        st.divider()
        sel_m = next((m for m in all_masters if m[0] == st.session_state.selected_master_id), None)
        
        if sel_m and os.path.exists(sel_m[3]):
            m_id, m_name, m_path = sel_m[0], sel_m[2], sel_m[3]
            img_roi = Image.open(m_path).convert("RGB")
            W, H = img_roi.size
            all_rois = database.get_rois(m_id, active_p)
            
            c_ctrl, c_viz = st.columns([1, 1.8])
            with c_ctrl:
                st.markdown(f"### 🔧 Nastavení zón: {m_name}")
                current_roi = next((r for r in all_rois if r[0] == st.session_state.editing_roi_id), None)
                
                default_name = current_roi[3] if current_roi else f"Zóna {len(all_rois)+1}"
                default_nok = current_roi[8] if current_roi else 1
                default_x = current_roi[4] if current_roi else 0
                default_y = current_roi[5] if current_roi else 0
                default_w = current_roi[6] if current_roi else W
                default_h = current_roi[7] if current_roi else H
                default_tolerance = current_roi[9] if current_roi and len(current_roi) > 9 else 20
                
                zn = st.text_input("Název zóny", value=default_name)
                nok_val = st.selectbox("Přiřazení chyby (NOK 1-8)", range(1, 9), index=default_nok - 1)
                
                zx = st.slider("X", 0, W, default_x)
                zy = st.slider("Y", 0, H, default_y)
                zw = st.slider("Šířka", 10, W, default_w)
                zh = st.slider("Výška", 10, H, default_h)
                ztol = st.slider("Tolerance odchylky", 1, 100, default_tolerance)
                
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
                
                if all_rois:
                    st.write("---")
                    for r in all_rois:
                        r_id, r_name, r_nok = r[0], r[3], r[8]
                        del_col1, del_col2, del_col3 = st.columns([2.5, 0.8, 0.8])
                        with del_col1: st.write(f"• {r_name} (NOK{r_nok})")
                        with del_col2:
                            if st.button("📝", key=f"edit_roi_{r_id}"):
                                st.session_state.editing_roi_id = r_id
                                st.rerun()
                        with del_col3:
                            if st.button("🗑️", key=f"del_roi_{r_id}"):
                                database.delete_roi(r_id)
                                st.rerun()

            with c_viz:
                draw = ImageDraw.Draw(img_roi)
                line_w = max(2, int(W * 0.007))
                for r in all_rois:
                    rx, ry, rw, rh = r[4], r[5], r[6], r[7]
                    if r[0] != st.session_state.editing_roi_id:
                        draw.rectangle([rx, ry, rx+rw, ry+rh], outline="#00FF00", width=line_w)
                        draw.text((rx, ry-15), f"{r[3]} (NOK{r[8]})", fill="#00FF00")

                draw.rectangle([zx, zy, zx+zw, zy+zh], outline="orange", width=line_w + 2)
                st.image(img_roi, use_container_width=True, caption=f"Pracovní plocha: {m_name}")
                
                # --- AI TRÉNOVÁNÍ PODLE SÍTÍ ---
                st.divider()
                st.markdown("### 🧠 Řízení neuronových sítí (AI)")
                
                active_rois_list = list(set(r_temp[3] for m_temp in all_masters for r_temp in database.get_rois(m_temp[0], active_p)))
                if active_rois_list:
                    selected_net_to_train = st.selectbox("Vyberte neuronovou síť k přetrénování:", active_rois_list)
                    
                    base_drive = "D:/" if os.path.exists("D:/") else "C:/"
                    ok_dir_check = os.path.join(base_drive, "Image", "OK", active_p)
                    nok_dir_check = os.path.join(base_drive, "Image", "NOK", active_p)
                    
                    # Spočítáme všechny fotky bez ohledu na to, zda mají příponu malým nebo velkým písmem
                    count_ok = len(glob.glob("dataset/OK/Zebro_P1/*.jpg")) + len(glob.glob("dataset/OK/Zebro_P1/*.JPG")) + len(glob.glob("dataset/OK/Zebro_P1/*.png")) + len(glob.glob("dataset/OK/Zebro_P1/*.PNG"))
                    count_nok = len(glob.glob("dataset/NOK/Zebro_P1/*.jpg")) + len(glob.glob("dataset/NOK/Zebro_P1/*.JPG")) + len(glob.glob("dataset/NOK/Zebro_P1/*.png")) + len(glob.glob("dataset/NOK/Zebro_P1/*.PNG"))
                    
                    if count_ok < 4 or count_nok < 4:
                        st.warning(f"⚠️ **Nedostatečné množství dat:** Máte pouze **{count_ok}x OK** a **{count_nok}x NOK** snímků. (Vyžadováno aspoň 4x OK a 4x NOK).")
                    else:
                        st.info(f"📊 **Připravený dataset:** Pro učení sítě `{selected_net_to_train}` je k dispozici **{count_ok}x OK** a **{count_nok}x NOK** vzorků.")
                    
                    if st.button(f"🚀 SPUSTIT UČENÍ SÍTÊ: {selected_net_to_train}", use_container_width=True, disabled=(count_ok < 4 or count_nok < 4)):
                        with st.spinner("Učení neuronové sítě běží..."):
                            progress_bar = st.progress(0.0)
                            status_text = st.empty()
                            def update_progress(pct, msg):
                                progress_bar.progress(pct)
                                status_text.text(msg)
                            success, result_msg = ai_engine.train_ai_model(active_p, selected_net_to_train, update_progress)
                            if success:
                                st.success(f"🎉 Síť byla úspěšně naučena! Soubor: {result_msg}")
                                st.rerun()
                            else: st.error(f"❌ Chyba: {result_msg}")

# --- TAB 4: I/O (MODBUS) ---
with tab4:
    st.subheader("🔌 Nastavení komunikace (Modbus TCP / Moxa)")
    st.text_input("IP Adresa Moxa I/O modulu", value="192.168.1.200")
    st.button("🔄 Testovat připojení hardwaru", use_container_width=True)
    
# --- TAB 5: HISTORIE ---
with tab5:
    st.subheader("📋 Správa snímků a anotace pro NN")
    st.write("Proklikáním snímků určíte reálnou jakost. Snímky se následně uloží do datasetu pro učení neuronové sítě.")
    
    # Načtení unikátních projektů a zón z historie pro filtry
    history_projects = database.get_unique_projects_from_history() if hasattr(database, 'get_unique_projects_from_history') else []
    project_options = ["Vše"] + history_projects
    
    default_p_idx = 0
    if st.session_state.active_project in project_options:
        default_p_idx = project_options.index(st.session_state.active_project)
        
    f_col1, f_col2, f_col3 = st.columns(3)
    with f_col1:
        proj_f = st.selectbox("Aktivní projekt (Lis):", project_options, index=default_p_idx)
    with f_col2:
        status_f = st.selectbox("Stav hodnocení zóny:", ["Neroztříděno", "OK", "NOK", "Vše"])
    with f_col3:
        history_rois = database.get_unique_rois_from_history(proj_f) if hasattr(database, 'get_unique_rois_from_history') else []
        roi_options = ["Vše"] + history_rois
        roi_f = st.selectbox("Neuronová síť (Zóna):", roi_options)
        
    # Načtení dat na základě filtrů
    hist_data = database.get_history(proj_f, status_f, roi_f)
    
    if not hist_data:
        st.info("ℹ️ Žádné snímky neodpovídají vybranému filtru nebo jsou již roztříděny.")
    else:
        st.write(f"🔍 Počet snímků k zařazení: **{len(hist_data)}**")
        h_cols = st.columns(3)
        for idx, row in enumerate(hist_data[:12]): # Zobrazíme maximálně 12 snímků na stránku pro plynulost
            with h_cols[idx % 3]:
                with st.container(border=True):
                    st.write(f"**Zóna:** `{row[2]}`")
                    if os.path.exists(row[3]):
                        st.image(row[3], use_container_width=True)
                        b_ok, b_nok = st.columns(2)
                        st.markdown("<p style='margin-bottom:2px; font-size:13px; color:#aaa;'>Uložit do datasetu NN:</p>", unsafe_allow_html=True)
                        btn_ok, btn_nok = st.columns(2)
                        with btn_ok:
                            if st.button("🟢 ok", key=f"ok_h_{row[0]}", use_container_width=True):
                                # 1. Fyzické zkopírování souboru do složky datasetu pro učení sítě
                                src_path = row[3]
                                if os.path.exists(src_path):
                                    dest_dir = "dataset/OK/Zebro_P1"
                                    if not os.path.exists(dest_dir):
                                        os.makedirs(dest_dir)
                                    import shutil
                                    shutil.copy(src_path, os.path.join(dest_dir, os.path.basename(src_path)))
                                
                                # 2. Zápis do DB a smazání z Unsorted, ať to v historii nezavází
                                database.update_image_status(row[0], "OK")
                                try: os.remove(src_path)
                                except: pass
                                st.rerun()
                                
                        with btn_nok:
                            if st.button("🔴 nok", key=f"nok_h_{row[0]}", use_container_width=True):
                                # 1. Fyzické zkopírování souboru do složky datasetu pro učení sítě
                                src_path = row[3]
                                if os.path.exists(src_path):
                                    dest_dir = "dataset/NOK/Zebro_P1"
                                    if not os.path.exists(dest_dir):
                                        os.makedirs(dest_dir)
                                    import shutil
                                    shutil.copy(src_path, os.path.join(dest_dir, os.path.basename(src_path)))
                                
                                # 2. Zápis do DB a smazání z Unsorted
                                database.update_image_status(row[0], "NOK")
                                try: os.remove(src_path)
                                except: pass
                                st.rerun()
                    else:
                        st.error("Soubor snímku nebyl na disku nalezen.")