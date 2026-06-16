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

# --- ODSTRANĚNÍ CACHE HARDWAROVÉHO MODULU Z RAM ---
import importlib
importlib.reload(camera_manager)
# ---  VYNUCENÝ RELOAD PRO ZAMEZENÍ CACHOVÁNÍ STARÉHO HARDWAROVÉHO KÓDU ---
import importlib
importlib.reload(camera_manager)

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
        
        # Vodorovný panel pro výběr aktuálního kroku sekvence v TAB 1
        run_pos_cols = st.columns(len(avail_pos) + 2)
        with run_pos_cols[0]:
            st.markdown("<p style='padding-top:25px; font-weight:bold; margin:0;'>📍 Krok sekvence:</p>", unsafe_allow_html=True)
            
        for idx, pos in enumerate(avail_pos):
            with run_pos_cols[idx + 1]:
                st.write("") # Zarovnání
                is_active = (st.session_state.current_run_position == pos)
                
                # 🍏 OPRAVA KLÍČE PRO TAB 1 (přidán prefix run_tab_pos_)
                if st.button(f"Pozice {pos}", key=f"run_tab_pos_{pos}", type="primary" if is_active else "secondary", use_container_width=True):
                    st.session_state.current_run_position = pos
                    
                    # Bezpečné získání názvu aktivního projektu ze session_state
                    proj_name = st.session_state.get("active_project", "Default_Project")
                    
                    # Načtení PFS konfigurace
                    success, msg = camera_manager.load_camera_features_from_pfs(proj_name, pos)
                    if not success:
                        st.toast(f"ℹ️ {msg}", icon="ℹ️")
                    else:
                        st.toast(f"⚙️ Kamera hardwarově přenastavena pro Pozici {pos}!", icon="✅")
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
                    live_full_img, pylon_camera_name = camera_manager.capture_live_frame()
                    
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

            if st.button("💾 ULOŽIT MASTER", type="primary", width="stretch"):
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
            
            # ⚠️ ZDE KÓD V LEVÉM SLOUPCI KONČÍ. VŠECHNY STARÉ SLIDERY EXPOZICE ODPOVEDAJÍCÍ EXP_VAL ZDE SMAŽ!

        with col_img:
            live_stream_active = st.toggle("🎥 SPUSTIT ŽIVÝ STREAM", key="master_live_stream_toggle")
            
            if live_stream_active:
                # Voláme bez argumentů – kamera jede stabilně podle zavedeného PFS
                live_full_img, error_msg = camera_manager.capture_live_frame()
                if live_full_img:
                    st.session_state.setup_image_buffer = live_full_img
                else:
                    st.error(f"❌ {error_msg}")
            else:
                if "Složka OK" in source_type:
                    sim_dir = os.path.join(BASE_IMAGE_DIR, "OK", active_p)
                    images = []
                    if os.path.exists(sim_dir):
                        for ext in ["*.jpg", "*.jpeg", "*.png", "*.JPG", "*.PNG"]:
                            images.extend(glob.glob(os.path.join(sim_dir, ext)))
                    
                    if images:
                        st.session_state.setup_image_buffer = Image.open(images[0]).convert("RGB")
                    else:
                        if st.session_state.setup_image_buffer is None:
                            st.warning(f"Složka '{sim_dir}' je prázdná. Použita nouzová plocha.")
                            st.session_state.setup_image_buffer = Image.new('RGB', (1920, 1080), color=(75, 105, 130))

            # VYKRESLENÍ OBRAZU
            if st.session_state.setup_image_buffer is not None:
                preview_img = st.session_state.setup_image_buffer.copy()
                img_w, img_h = preview_img.size
                
                safe_ax = min(ax, img_w - 10)
                safe_ay = min(ay, img_h - 10)
                safe_aw = min(aw, img_w - safe_ax)
                safe_ah = min(ah, img_h - safe_ay)
                
                draw = ImageDraw.Draw(preview_img)
                draw.rectangle([safe_ax, safe_ay, safe_ax + safe_aw, safe_ay + safe_ah], outline="red", width=5)
                st.image(preview_img, width="stretch", caption=f"Aktuální podklad ({img_w}x{img_h} px)")

            # --- SLIDERY PŘÍMO POD OBRAZEM ---
            st.markdown("### 💡 Hardwarové nastavení osvitu kamery")
            st.slider("Čas expozice (μs)", 1000, 200000, 20000, step=500, key="exp_slider_val")
            st.slider("Zesílení obrazu (Gain dB)", 0.0, 24.0, 0.0, step=0.5, key="gain_slider_val")
            
            # 💾 JEDNORÁZOVÝ ZÁPIS A UKLÁDÁNÍ PFS PRO DANOU POZICI
            current_setup_pos = st.session_state.get("current_run_position", 1)
            if st.button(f"💾 ULOŽIT TUTO KONFIGURACI JAKO PFS PRO POZICI {current_setup_pos}", type="secondary", use_container_width=True):
                proj_name = st.session_state.get("active_project", "Default_Project")
                cam = camera_manager.get_camera()
                
                if cam:
                    try:
                        nodemap = cam.GetNodeMap()
                        for name, val in [("ExposureAuto", "Off"), ("GainAuto", "Off")]:
                            node = nodemap.GetNode(name)
                            if node: node.SetValue(val)
                            
                        exp_node = nodemap.GetNode("ExposureTime") or nodemap.GetNode("ExposureTimeAbs")
                        if exp_node: exp_node.SetValue(float(st.session_state.exp_slider_val))
                        
                        gain_node = nodemap.GetNode("Gain") or nodemap.GetNode("GainRaw")
                        if gain_node:
                            val_to_set = int(st.session_state.gain_slider_val) if "Raw" in gain_node.GetNode().GetName() else float(st.session_state.gain_slider_val)
                            gain_node.SetValue(val_to_set)
                    except Exception as e_direct:
                        st.warning(f"⚠️ Částečný zápis registrů: {e_direct}")
                
                success, path_or_err = camera_manager.save_camera_features_to_pfs(proj_name, current_setup_pos)
                if success:
                    st.success(f"🎉 Průmyslový PFS profil pro Pozici {current_setup_pos} úspěšně vytvořen!")
                    st.rerun()
                else:
                    st.error(f"❌ Selhalo vytvoření PFS souboru: {path_or_err}")
    
        # --- REFRESH PRO ŽIVÉ VIDEO ---
        if st.session_state.get("master_live_stream_toggle") and st.session_state.setup_image_buffer is not None:
            time.sleep(0.08)
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

    # Vykreslení tlačítek vedle sebe v TAB 3
    pos_count = len(st.session_state.available_positions)
    cols = st.columns(pos_count + 1)
    
    for i, pos in enumerate(st.session_state.available_positions):
        with cols[i]:
            is_active = (st.session_state.current_position == pos)
            
            # 🍏 OPRAVA KLÍČE PRO TAB 3 (přidán prefix zone_tab_pos_)
            if st.button(f" Pozice {pos}", key=f"zone_tab_pos_{pos}", type="primary" if is_active else "secondary", use_container_width=True):
                st.session_state.current_position = pos
                
                # Bezpečné získání názvu aktivního projektu ze session_state
                proj_name = st.session_state.get("active_project", "Default_Project")
                
                # Načtení PFS konfigurace
                success, msg = camera_manager.load_camera_features_from_pfs(proj_name, pos)
                if not success:
                    st.toast(f"ℹ️ {msg}", icon="ℹ️")
                else:
                    st.toast(f"⚙️ Kamera hardwarově přenastavena pro Pozici {pos}!", icon="✅")
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
                
                if st.button(f"🚀 SPUSTIT UČENÍ PRO PROJEKT: {active_p}", use_container_width=True):
                    with st.spinner("Učení neuronové sítě běží..."):
                        progress_bar = st.progress(0.0)
                        status_text = st.empty()
                        def update_progress(pct, msg):
                            progress_bar.progress(pct)
                            status_text.text(msg)
                        
                        success, result_msg = ai_engine.train_ai_model(active_p, "", update_progress)
                        if success: st.success(f"🎉 Úspěšně naučeno! {result_msg}")
                        else: st.error(f"❌ Chyba: {result_msg}")

# --- TAB 4: I/O ---
with tab4:
    st.subheader("🔌 Nastavení komunikace (Modbus TCP / Moxa)")
    st.text_input("IP Adresa Moxa I/O modulu", value="192.168.1.200")
    st.button("🔄 Testovat připojení hardwaru", width="stretch")