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

# --- JEDNORÁZOVÁ PRŮMYSLOVÁ POJISTKA PRO ROZŠÍŘENÍ DATABÁZE (ELVAC STANDARD) ---
def check_database_structure():
    import sqlite3
    try:
        # Připojíme se k naší lokální SQL databázi
        conn = sqlite3.connect("vision_system.db")
        cursor = conn.cursor()
        # Pokusíme se přidat sloupec pro číslo pozice sekvence lisu
        cursor.execute("ALTER TABLE rois ADD COLUMN position_num INTEGER DEFAULT 1")
        conn.commit()
        conn.close()
        print("📊 Databáze úspěšně rozšířena o sloupec position_num.")
    except Exception:
        # Pokud sloupec už existuje, SQLite vyhodí chybu a kód bezpečně pokračuje dál
        pass

# Spustíme kontrolu hned při startu aplikace
check_database_structure()

# 1. GLOBÁLNÍ KONFIGURACE A CESTY
st.set_page_config(layout="wide", page_title="Vision System Terminal")

# Definice základní průmyslové cesty k obrázkům na disku C:
BASE_IMAGE_DIR = "C:/Image"

# 2. INICIALIZACE DATABÁZE
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
    if st.session_state.active_project:
        active_p = st.session_state.active_project
        
        # --- HORNÍ LIŠTA: VOLBA POZICE SEKVENCE (ELVAC STANDARD) ---
        if "current_run_position" not in st.session_state:
            st.session_state.current_run_position = 1
            
        avail_pos = st.session_state.get("available_positions", [1, 2])
        
        # Vodorovný panel pro výběr aktuálního kroku sekvence
        run_pos_cols = st.columns(len(avail_pos) + 2)
        with run_pos_cols[0]:
            st.markdown("<p style='padding-top:25px; font-weight:bold; margin:0;'>📍 Krok sekvence:</p>", unsafe_allow_html=True)
            
        for idx, pos in enumerate(avail_pos):
            with run_pos_cols[idx + 1]:
                st.write("") # Zarovnání
                is_active = (st.session_state.current_run_position == pos)
                if st.button(f"Pozice {pos}", key=f"run_pos_{pos}", type="primary" if is_active else "secondary", use_container_width=True):
                    st.session_state.current_run_position = pos
                    st.rerun()
                    
        st.divider()

        # Načtení masterů a zón filtrovaných podle AKTIVNÍ pozice sekvence
        all_masters = database.get_all_masters(active_p)
        all_active_rois = []
        
        if all_masters:
            for m in all_masters:
                rois = database.get_rois(m[0], active_p)
                for r in rois:
                    # Filtrujeme zóny, které patří do aktuálně zvolené pozice (index 10 nebo session state)
                    r_pos = r[10] if len(r) > 10 else 1
                    if r_pos == st.session_state.current_run_position:
                        all_active_rois.append((m, r))

        # HLAVNÍ ROZVRŽENÍ 2:1 (Mřížka kamer vlevo vs. Výsledky a PLC vpravo)
        col_run_1, col_run_2 = st.columns([2.2, 1])
        
        with col_run_1:
            st.markdown("### 📺 Živé náhledy kamer lisu")
            run_engine = st.toggle("▶️ SPUSTIT ŽIVOU INSPEKCI VÝLISKŮ", key="run_engine_toggle")
            st.write("")
            
            roi_placeholders = {}
            if not all_active_rois:
                st.info(f"ℹ️ Pro Pozici {st.session_state.current_run_position} nejsou v tomto kroku sekvence definovány žádné zóny.")
            else:
                # Vytvoření čisté průmyslové mřížky 3x3 nebo 3x2
                roi_cols = st.columns(3)
                for i, (m, r) in enumerate(all_active_rois):
                    r_id, r_name = r[0], r[3]
                    with roi_cols[i % 3]:
                        # Použijeme tmavé průmyslové ohraničení kontejneru
                        with st.container(border=True):
                            roi_placeholders[r_id] = st.empty()

        with col_run_2:
            st.markdown("### 📋 Výsledky inspekce")
            global_status_placeholder = st.empty()
            st.write("")
            
            st.markdown("**🛡️ Stav jednotlivých kontrol:**")
            control_placeholders = {}
            for i, (m, r) in enumerate(all_active_rois):
                r_name = r[3]
                control_placeholders[r[0]] = st.empty()
                
        # --- VYHODNOCOVACÍ SMYČKA ZA BĚHU (PROPOJENÍ MOXA -> KAMERA -> AI) ---
        current_outputs = {i: False for i in range(1, 9)}
        
        if run_engine:
            import communication_manager
            
            # 1. Inicializace Modbus manažera z haly (pokud ještě neběží)
            if "lis_modbus" not in st.session_state:
                st.session_state.lis_modbus = communication_manager.LisModbusManager(ip_address="10.42.0.167")
                if st.session_state.lis_modbus.connect():
                    st.toast("🔌 Úspěšně připojeno k Moxa I/O modulu lisu!", icon="✅")
                else:
                    st.toast("⚠️ Moxa neodpovídá. Systém běží v simulačním režimu.", icon="ℹ️")

            # Maximální počet kroků sekvence podle nadefinovaných pozic
            max_pos_count = len(st.session_state.get("available_positions", [1, 2]))
            
            # 2. Kontrola triggeru z lisu (náběžná hrana z registru 0x08)
            is_triggered, target_pos = st.session_state.lis_modbus.check_trigger_and_sequence(max_pos_count)
            
            if is_triggered:
                st.session_state.current_run_position = target_pos
                st.toast(f"⚡ Lis odtriggeroval! Spouštím kontrolu pro Pozici {target_pos}", icon="📸")
                
                is_entire_mold_ok = True
                
                # Projedeme zóny přiřazené k této konkrétní pozici lisu
                for m, r in all_active_rois:
                    m_path = m[3]
                    r_id, r_name, r_nok = r[0], r[3], r[8]
                    r_tolerance = r[9] if len(r) > 9 else 20
                    
                    # Zachycení reálného snímku z Basler kamery přes tvůj camera_manager
                    live_full_img, pylon_camera_name = camera_manager.capture_live_frame(0)
                    
                    if live_full_img is not None:
                        # Uložení surového snímku z kamery do historie (Unsorted) pro pozdější učení
                        timestamp = int(time.time())
                        ulozeny_raw_soubor = f"C:/Image/Unsorted/{active_p}/basler_{pylon_camera_name}_{timestamp}.jpg"
                        os.makedirs(os.path.dirname(ulozeny_raw_soubor), exist_ok=True)
                        live_full_img.save(ulozeny_raw_soubor, "JPEG", quality=95)
                        
                        # Zápis do SQLite historie jako 'Neroztříděno'
                        database.save_to_history(active_p, r_name, ulozeny_raw_soubor, "Neroztříděno")
                        
                        # Ořez zóny (ROI) pro vyhodnocení AI
                        try:
                            live_crop = live_full_img.crop((r[4], r[5], r[4]+r[6], r[5]+r[7]))
                            live_roi_img = live_crop.resize((500, 500), Image.Resampling.LANCZOS)
                        except Exception:
                            live_roi_img = Image.new('RGB', (500, 500), color=(30, 30, 30))
                    else:
                        pylon_camera_name = "Chyba Kamery"
                        live_roi_img = Image.new('RGB', (500, 500), color=(30, 30, 30))
                    
                    # Spuštění AI modelu na oříznutou zónu
                    model_path = f"models/model_ai_{active_p}_{r_name}.pth"
                    universal_model_path = f"models/model_ai_{active_p}_Univerzalni_Sit.pth"
                    active_model = model_path if os.path.exists(model_path) else (universal_model_path if os.path.exists(universal_model_path) else None)
                    
                    if active_model:
                        is_zone_ok, ai_confidence = ai_engine.predict_with_ai(active_model, live_roi_img)
                        status_text = "OK" if is_zone_ok else "NOK"
                        caption_str = f"✨ AI Jistota: {int(ai_confidence * 100)}%"
                    else:
                        # Fallback na pixelovou odchylku, pokud model ještě není naučený
                        is_zone_ok = True
                        status_text = "OK (Bez AI)"
                        caption_str = "📐 Čeká na model"
                    
                    if not is_zone_ok:
                        current_outputs[r_nok] = True
                        is_entire_mold_ok = False
                    
                    # Vykreslení výsledku do mřížky Streamlitu (Zelená / Červená)
                    zone_color = "#00FF00" if is_zone_ok else "#FF4B4B"
                    roi_square = live_roi_img.copy()
                    draw_sq = ImageDraw.Draw(roi_square)
                    draw_sq.rectangle([0, 0, 499, 499], outline=zone_color, width=12)
                    
                    html_label = f"""
                        <div style='background-color:#1E1E1E; padding:5px; border-radius:3px; margin-bottom:5px;'>
                            <span style='color:#FFF; font-weight:bold;'>{r_name}</span><br>
                            <span style='color:#FFA500; font-size:0.85em;'>{pylon_camera_name}</span> | 
                            <span style='color:{zone_color}; font-size:0.85em; font-weight:bold;'>{status_text}</span>
                        </div>
                    """
                    roi_placeholders[r_id].markdown(html_label, unsafe_allow_html=True)
                    roi_placeholders[r_id].image(roi_square, use_container_width=True, caption=caption_str)
                    
                    # Aktualizace pravého sloupce (Seznam kontrol)
                    if is_zone_ok:
                        control_placeholders[r_id].markdown(f"🍏 **Kontrola {r_name}** — `OK`", unsafe_allow_html=True)
                    else:
                        control_placeholders[r_id].markdown(f"🍎 <span style='color:#FF4B4B;'>**Kontrola {r_name}** — `NOK (Výstup {r_nok})`</span>", unsafe_allow_html=True)

                # Zápis finálního výsledku zpět do lisu přes Modbus (Moxa)
                if st.session_state.lis_modbus.client and st.session_state.lis_modbus.client.is_socket_open():
                    stav_pro_moxu = 1 if is_entire_mold_ok else 2
                    st.session_state.lis_modbus.client.write_single_register(address=0, value=stav_pro_moxu)
                
                # Aktualizace velkého statusu (OK/NOK banner)
                if is_entire_mold_ok:
                    global_status_placeholder.markdown("<div style='background-color:#007D2F; color:white; padding:30px; border-radius:8px; text-align:center; font-size:55px; font-weight:bold;'>OK</div>", unsafe_allow_html=True)
                else:
                    global_status_placeholder.markdown("<div style='background-color:#C80000; color:white; padding:30px; border-radius:8px; text-align:center; font-size:55px; font-weight:bold;'>NOK</div>", unsafe_allow_html=True)
            
            # Krátká pauza smyčky, aby nedošlo k přetížení CPU
            time.sleep(0.1)
            st.rerun()
        else:
            # KLIDOVÝ STAV - Pokud je přepínač vypnutý, odpojíme klienta lisu a vypíšeme status
            if "lis_modbus" in st.session_state:
                st.session_state.lis_modbus.close()
                del st.session_state.lis_modbus
                
            global_status_placeholder.markdown("""
                <div style='background-color:#333333; color:#888888; padding:25px; border-radius:8px; text-align:center; font-size:35px; font-weight:bold;'>
                    ČEKÁ NA LIS
                </div>
            """, unsafe_allow_html=True)
            
            for m, r in all_active_rois:
                roi_placeholders[r[0]].info(f"⏳ Zóna {r[3]} připravena...")

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
            if "Simulovat z kamery" in source_type:
                if st.button("📸 Zachytit testovací snímek z kamery lisu", use_container_width=True):
                    target_dir = os.path.join("C:/Image", "OK", active_p)
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
                uploaded_file = st.file_uploader("Vyberte obrázek formy z disku počítače:", type=["jpg", "jpeg", "png", "JPG", "JPEG", "PNG"])
                if uploaded_file is not None:
                    st.session_state.setup_image_buffer = Image.open(uploaded_file).convert("RGB")
                    st.success("Externí soubor úspěšně nahrán do paměti aplikace!")

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
    active_p = st.session_state.active_project
    st.info(f"🏗️ Nastavení zón pro projekt: **{active_p}**")
    
    # --- VODOROVNÝ PÁS POZIC PODLE ELVACU ---
    st.write("---")
    st.markdown("### 🗺️ Vyberte pozici pro úpravu (Sekvence lisu)")
    
    if "available_positions" not in st.session_state:
        st.session_state.available_positions = [1, 2]
    if "current_position" not in st.session_state:
        st.session_state.current_position = 1

    # Vykreslení tlačítek vedle sebe
    pos_count = len(st.session_state.available_positions)
    cols = st.columns(pos_count + 1)
    
    for i, pos in enumerate(st.session_state.available_positions):
        with cols[i]:
            is_active = (st.session_state.current_position == pos)
            if st.button(f" Pozice {pos}", key=f"pos_btn_{pos}", type="primary" if is_active else "secondary", use_container_width=True):
                st.session_state.current_position = pos
                st.rerun()
                
    with cols[-1]:
        if st.button("➕", key="add_pos_btn", use_container_width=True):
            new_pos_id = max(st.session_state.available_positions) + 1
            st.session_state.available_positions.append(new_pos_id)
            st.session_state.current_position = new_pos_id
            st.success(f"🎉 Přidána nová pozice {new_pos_id}!")
            time.sleep(0.4)
            st.rerun()

    if pos_count > 1:
        if st.button(f"🗑️ Smazat Pozici {st.session_state.current_position} ze sekvence", use_container_width=True):
            curr = st.session_state.current_position
            st.session_state.available_positions.remove(curr)
            st.session_state.current_position = st.session_state.available_positions[0]
            st.warning(f"⚠️ Pozice {curr} smazána.")
            time.sleep(0.4)
            st.rerun()
            
    st.info(f"📍 Aktuálně konfigurujete zóny pro: **Pozice {st.session_state.current_position}**")
    st.write("---")

    all_masters = database.get_all_masters(active_p) if active_p else []
    
    if not all_masters:
        st.warning("⚠️ Knihovna Masterů je prázdná. Nejdříve vytvořte Master v Tabu 2.")
    else:
        if 'selected_master_id' not in st.session_state or st.session_state.selected_master_id is None:
            st.session_state.selected_master_id = all_masters[0][0]

        st.write("### 🖼️ Výběr podkladového Masteru / kamery:")
        m_cols = st.columns(6)
        for idx, m in enumerate(all_masters):
            m_id_loop, m_name_loop, m_path_loop = m[0], m[2], m[3]
            with m_cols[idx % 6]:
                with st.container(border=True):
                    if os.path.exists(m_path_loop): st.image(m_path_loop, use_container_width=True)
                    is_active = (m_id_loop == st.session_state.selected_master_id)
                    if st.button(f"📷 {m_name_loop}", key=f"btn_m_{m_id_loop}", use_container_width=True, type="primary" if is_active else "secondary"):
                        st.session_state.selected_master_id = m_id_loop
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
                zn = st.text_input("Název zóny", value=f"Zóna {len(all_rois)+1}")
                nok_val = st.selectbox("Přiřazení chyby (NOK 1-8)", range(1, 9))
                
                zx = st.slider("X", 0, W, 0)
                zy = st.slider("Y", 0, H, 0)
                zw = st.slider("Šířka", 10, W, W)
                zh = st.slider("Výška", 10, H, H)
                ztol = st.slider("Tolerance odchylky", 1, 100, 20)
                
                if st.button("💾 ULOŽIT NOVOU ZÓNU", type="primary", use_container_width=True):
                    # Použijeme stávající uložení a v database.py pak zajistíme uložení position_num
                    database.save_roi(m_id, active_p, zn, zx, zy, zw, zh, nok_val, ztol, st.session_state.current_position)
                    st.success(f"Zóna {zn} úspěšně uložena do Pozice {st.session_state.current_position}!")
                    time.sleep(0.4)
                    st.rerun()
                
                if all_rois:
                    st.write("---")
                    for r in all_rois:
                        del_col1, del_col2 = st.columns([3, 1])
                        with del_col1: st.write(f"• {r[3]} (NOK{r[8]})")
                        with del_col2:
                            if st.button("🗑️", key=f"del_roi_{r[0]}"):
                                database.delete_roi(r[0])
                                st.rerun()

            with c_viz:
                draw = ImageDraw.Draw(img_roi)
                line_w = max(2, int(W * 0.007))
                for r in all_rois:
                    draw.rectangle([r[4], r[5], r[4]+r[6], r[5]+r[7]], outline="#00FF00", width=line_w)
                draw.rectangle([zx, zy, zx+zw, zy+zh], outline="orange", width=line_w + 2)
                st.image(img_roi, use_container_width=True)
                
                st.divider()
                st.markdown("### 🧠 Řízení sítě projektu")
                
                ok_dir_check = os.path.join("C:/Image", "OK", active_p)
                nok_dir_check = os.path.join("C:/Image", "NOK", active_p)
                
                count_ok = 0
                count_nok = 0
                if os.path.exists(ok_dir_check):
                    for ext in ["*.jpg", "*.JPG", "*.png", "*.PNG"]:
                        count_ok += len(glob.glob(os.path.join(ok_dir_check, ext)))
                if os.path.exists(nok_dir_check):
                    for ext in ["*.jpg", "*.JPG", "*.png", "*.PNG"]:
                        count_nok += len(glob.glob(os.path.join(nok_dir_check, ext)))
                
                if count_ok < 4 or count_nok < 4:
                    st.warning(f"⚠️ **Nedostatečné množství dat:** V adresáři `C:/Image/` pro projekt `{active_p}` máte pouze **{count_ok}x OK** a **{count_nok}x NOK** snímků. (Vyžadováno aspoň 4x OK a 4x NOK).")
                else:
                    st.info(f"📊 **Množství dat:** Pro učení projektu `{active_p}` je k dispozici **{count_ok}x OK** a **{count_nok}x NOK** reálných vzorků.")
                
                # Odstraněno blokování tlačítka, teď půjde spustit vždy
                if st.button(f"🚀 SPUSTIT UČENÍ PRO PROJEKT: {active_p}", use_container_width=True):
                    with st.spinner("Učení neuronové sítě běží..."):
                        progress_bar = st.progress(0.0)
                        status_text = st.empty()
                        def update_progress(pct, msg):
                            progress_bar.progress(pct)
                            status_text.text(msg)
                        
                        # Změna: Posíláme prázdný název zóny, aby si ai_engine načetl čistě celou složku z disku
                        success, result_msg = ai_engine.train_ai_model(active_p, "", update_progress)
                        if success: st.success(f"🎉 Úspěšně naučeno! {result_msg}")
                        else: st.error(f"❌ Chyba: {result_msg}")

# --- TAB 4: I/O ---
with tab4:
    st.subheader("🔌 Nastavení komunikace (Modbus TCP / Moxa)")
    st.text_input("IP Adresa Moxa I/O modulu", value="192.168.1.200")
    st.button("🔄 Testovat připojení hardwaru", use_container_width=True)
    
# --- TAB 5: HISTORIE ---
with tab5:
    st.subheader("📋 Správa snímků a anotace pro NN")
    active_p = st.session_state.active_project
    
    if not active_p:
        st.warning("⚠️ Nejdříve vyberte nebo vytvořte projekt v levém panelu.")
    else:
        # --- FILTRY (NÁVRAT ROLETEK NAHORU) ---
        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1:
            # Projekt předvybereme podle sidebar výběru, ale dá se přepnout
            history_projects = database.get_unique_projects_from_history() if hasattr(database, 'get_unique_projects_from_history') else []
            project_options = list(set(["Vše", active_p] + history_projects))
            proj_f = st.selectbox("Aktivní projekt (Lis):", project_options, index=project_options.index(active_p) if active_p in project_options else 0)
        with f_col2:
            status_f = st.selectbox("Stav hodnocení zóny:", ["Neroztříděno", "OK", "NOK", "Vše"])
        with f_col3:
            history_rois = database.get_unique_rois_from_history(proj_f) if hasattr(database, 'get_unique_rois_from_history') else []
            roi_options = ["Vše"] + history_rois
            roi_f = st.selectbox("Neuronová síť (Zóna):", roi_options)

        st.write("")

        # HROMADNÝ IMPORT ZE SOUBORŮ
        with st.expander("📥 Hromadný import testovacích fotek ze souborů (Příprava offline)", expanded=False):
            st.write(f"Vyberte jednu nebo více fotek z disku/flashky. Systém je vloží do historie aktivního projektu: **{active_p}**")
            uploaded_hist_files = st.file_uploader(
                "Vybrat fotky pro import:", 
                type=["jpg", "jpeg", "png", "JPG", "JPEG", "PNG"], 
                accept_multiple_files=True,
                key="hist_uploader"
            )
            
            if uploaded_hist_files:
                if st.button("🚀 IMPORTOVAT DO HISTORIE", use_container_width=True):
                    with st.spinner("💾 Kopíruji a zapisuji fotky do historie lisu... Počkejte prosím."):
                        unsorted_dir = os.path.join("C:/Image", "Unsorted", active_p)
                        if not os.path.exists(unsorted_dir):
                            os.makedirs(unsorted_dir)
                        
                        imported_count = 0
                        import random as rand_mod
                        
                        for f in uploaded_hist_files:
                            base_name = os.path.splitext(f.name)[0]
                            ext = os.path.splitext(f.name)[1]
                            new_filename = os.path.join(unsorted_dir, f"{base_name}_import_{int(time.time())}_{rand_mod.randint(100,999)}{ext}")
                            
                            img = Image.open(f).convert("RGB")
                            img.save(new_filename)
                            
                            database.save_to_history(active_p, "Importováno", new_filename, "Neroztříděno")
                            imported_count += 1
                            
                        st.success(f"🎉 Úspěšně importováno {imported_count} snímků do historie!")
                        time.sleep(0.5)
                        st.rerun()
        
        st.divider()
        
        # NAČTENÍ DAT PODLE VYBRANÝCH FILTRŮ
        hist_data = database.get_history(proj_f, status_f, roi_f)
        
        if not hist_data:
            st.info("ℹ️ Žádné snímky neodpovídají vybranému filtru nebo je vše roztříděno.")
        else:
            st.write(f"🔍 Počet nalezených snímků podle filtrů: **{len(hist_data)}**")
            
            # VÝPOČET STRÁNKOVÁNÍ
            ITEMS_PER_PAGE = 12
            total_items = len(hist_data)
            total_pages = max(1, (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
            
            if "history_page" not in st.session_state:
                st.session_state.history_page = 1
                
            if st.session_state.history_page > total_pages:
                st.session_state.history_page = total_pages
                
            start_idx = (st.session_state.history_page - 1) * ITEMS_PER_PAGE
            end_idx = start_idx + ITEMS_PER_PAGE
            page_items = hist_data[start_idx:end_idx]
            
            # Vykreslení mřížky fotek
            h_cols = st.columns(3)
            for idx, row in enumerate(page_items):
                with h_cols[idx % 3]:
                    with st.container(border=True):
                        st.write(f"**Zdroj:** `{os.path.basename(row[3])}`")
                        if os.path.exists(row[3]):
                            st.image(row[3], use_container_width=True)
                            
                            # Tlačítka se zobrazují pouze pokud třídíme Neroztříděné vzorky
                            if status_f == "Neroztříděno" or row[4] == "Neroztříděno":
                                b_ok, b_nok = st.columns(2)
                                with b_ok:
                                    if st.button("🟢 ok", key=f"ok_h_{row[0]}", use_container_width=True):
                                        src_path = row[3]
                                        dest_dir = os.path.join("C:/Image", "OK", active_p)
                                        if not os.path.exists(dest_dir): os.makedirs(dest_dir)
                                        import shutil
                                        shutil.copy(src_path, os.path.join(dest_dir, os.path.basename(src_path)))
                                        database.update_image_status(row[0], "OK")
                                        try: os.remove(src_path)
                                        except: pass
                                        st.rerun()
                                with b_nok:
                                    if st.button("🔴 nok", key=f"nok_h_{row[0]}", use_container_width=True):
                                        src_path = row[3]
                                        dest_dir = os.path.join("C:/Image", "NOK", active_p)
                                        if not os.path.exists(dest_dir): os.makedirs(dest_dir)
                                        import shutil
                                        shutil.copy(src_path, os.path.join(dest_dir, os.path.basename(src_path)))
                                        database.update_image_status(row[0], "NOK")
                                        try: os.remove(src_path)
                                        except: pass
                                        st.rerun()
                            else:
                                st.info(f"Označeno jako: **{row[4]}**")
                        else: 
                            st.error("Snímek smazán nebo přesunut.")
            
            # --- ROZŠÍŘENÉ OVLÁDÁNÍ STRÁNEK (RYCHLÉ SKOKY ZAČÁTEK/KONEC) ---
            st.write("")
            p_col1, p_col2, p_col3, p_col4, p_col5 = st.columns([1, 1.5, 2, 1.5, 1])
            
            with p_col1:
                if st.button("« První", use_container_width=True, disabled=(st.session_state.history_page == 1)):
                    st.session_state.history_page = 1
                    st.rerun()
                    
            with p_col2:
                if st.button("⬅️ Předchozí", use_container_width=True, disabled=(st.session_state.history_page == 1)):
                    st.session_state.history_page -= 1
                    st.rerun()
                    
            with p_col3:
                st.markdown(f"<p style='text-align:center; padding-top:5px; font-weight:bold; font-size:15px;'>Stránka {st.session_state.history_page} z {total_pages}</p>", unsafe_allow_html=True)
                
            with p_col4:
                if st.button("Další ➡️", use_container_width=True, disabled=(st.session_state.history_page == total_pages)):
                    st.session_state.history_page += 1
                    st.rerun()
                    
            with p_col5:
                if st.button("Poslední »", use_container_width=True, disabled=(st.session_state.history_page == total_pages)):
                    st.session_state.history_page = total_pages
                    st.rerun()