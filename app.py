import os
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
import sqlite3

# Inicializace tabulky modelů při startu aplikace
conn = sqlite3.connect("vision_system.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS model_registry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_name TEXT,
    model_name TEXT,
    accuracy TEXT,
    created_at TEXT,
    engineering_notes TEXT
)
""")
conn.commit()
conn.close()

# --- ODSTRANĚNÍ CACHE HARDWAROVÉHO MODULU Z RAM ---
import importlib
importlib.reload(camera_manager)

# --- JEDNORÁZOVÁ PRŮMYSLOVÁ POJISTKA PRO ROZŠÍŘENHO DATABÁZE (ELVAC STANDARD) ---
def check_database_structure():
    import sqlite3
    try:
        conn = sqlite3.connect("vision_system.db")
        cursor = conn.cursor()
        cursor.execute("ALTER TABLE rois ADD COLUMN position_num INTEGER DEFAULT 1")
        conn.commit()
        conn.close()
        print("📊 Databáze úspěšně rozšířena o sloupec position_num.")
    except Exception:
        pass

check_database_structure()

# 1. GLOBÁLNÍ KONFIGURACE A CESTY
st.set_page_config(layout="wide", page_title="Vision System Terminal")
BASE_IMAGE_DIR = "C:/Image"

# 2. INICIALIZACE DATABÁZE
database.init_db()

if 'setup_image_buffer' not in st.session_state:
    st.session_state.setup_image_buffer = None
if 'active_project' not in st.session_state:
    st.session_state.active_project = None
if 'selected_master_id' not in st.session_state:
    st.session_state.selected_master_id = None

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
        
        # 🔴 JEDNOTNÉ TLAČÍTKO PRO SMAZÁNÍ AKTIVNÍHO PROJEKTU
        active_p_to_del = st.session_state.active_project
        if active_p_to_del:
            st.write("") 
            if st.button(f"🗑️ SMAZAT PROJEKT {active_p_to_del}", use_container_width=True, type="secondary", key="del_project_sidebar_btn"):
                conn_p_del = sqlite3.connect("vision_system.db")
                cur_p_del = conn_p_del.cursor()
                
                cur_p_del.execute("PRAGMA table_info(rois)")
                rois_cols = [c[1] for c in cur_p_del.fetchall()]
                c_proj_r = "project" if "project" in rois_cols else "project_name"
                
                cur_p_del.execute(f"DELETE FROM rois WHERE {c_proj_r}=?", (active_p_to_del,))
                
                cur_p_del.execute("PRAGMA table_info(model_registry)")
                mod_cols = [c[1] for c in cur_p_del.fetchall()]
                c_proj_m = "project_name" if "project_name" in mod_cols else "project"
                cur_p_del.execute(f"DELETE FROM model_registry WHERE {c_proj_m}=?", (active_p_to_del,))
                
                cur_p_del.execute("PRAGMA table_info(history)")
                history_cols = [c[1] for c in cur_p_del.fetchall()]
                c_proj_h = "project" if "project" in history_cols else "project_name"
                cur_p_del.execute(f"DELETE FROM history WHERE {c_proj_h}=?", (active_p_to_del,))
                
                try:
                    cur_p_del.execute("DELETE FROM projects WHERE name=?", (active_p_to_del,))
                except Exception as e:
                    try:
                        cur_p_del.execute("DELETE FROM projects WHERE project_name=?", (active_p_to_del,))
                    except Exception:
                        pass
                
                conn_p_del.commit()
                conn_p_del.close()
                
                if "active_project" in st.session_state:
                    st.session_state.active_project = None
                
                st.toast(f"Projekt {active_p_to_del} byl kompletně vymazán ze systému.", icon="🗑️")
                st.rerun()
                
    else:
        st.warning("⚠️ Nejdříve vytvořte projekt")
        st.session_state.active_project = None

# --- DEFINICE TABŮ ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🚀 BĚH", "🎯 MASTER", "🔍 ZÓNY", "🔌 I/O", "📜 HISTORIE"])

# --- TAB 1: BĚH ---
with tab1:
    if st.session_state.active_project:
        active_p = st.session_state.active_project
        
        if "current_run_position" not in st.session_state:
            st.session_state.current_run_position = 1
            
        avail_pos = st.session_state.get("available_positions", [1, 2])
        
        run_pos_cols = st.columns(len(avail_pos) + 2)
        with run_pos_cols[0]:
            st.markdown("<p style='padding-top:25px; font-weight:bold; margin:0;'>📍 Krok sekvence:</p>", unsafe_allow_html=True)
            
        for idx, pos in enumerate(avail_pos):
            with run_pos_cols[idx + 1]:
                st.write("") 
                is_active = (st.session_state.current_run_position == pos)
                
                if st.button(f"Pozice {pos}", key=f"run_tab_pos_{pos}", type="primary" if is_active else "secondary", use_container_width=True):
                    st.session_state.current_run_position = pos
                    proj_name = st.session_state.get("active_project", "Default_Project")
                    
                    success, msg = camera_manager.load_camera_features_from_pfs(proj_name, pos)
                    if not success:
                        st.toast(f"ℹ️ {msg}", icon="ℹ️")
                    else:
                        st.toast(f"⚙️ Kamera hardwarově přenastavena pro Pozici {pos}!", icon="✅")
                    st.rerun()
                    
        st.divider()

        all_masters = database.get_all_masters(active_p)
        all_active_rois = []
        
        if all_masters:
            for m in all_masters:
                rois = database.get_rois(m[0], active_p)
                for r in rois:
                    r_pos = r[10] if len(r) > 10 else 1
                    if r_pos == st.session_state.current_run_position:
                        all_active_rois.append((m, r))

        col_run_1, col_run_2 = st.columns([2.2, 1])
        
        with col_run_1:
            st.markdown("### 📺 Živé náhledy kamer lisu")
            run_engine = st.toggle("▶️ SPUSTIT ŽIVOU INSPEKCI VÝLISKŮ", key="run_engine_toggle")
            st.write("")
            
            roi_placeholders = {}
            if not all_active_rois:
                st.info(f"ℹ️ Pro Pozici {st.session_state.current_run_position} nejsou v tomto kroku sekvence definovány žádné zóny.")
            else:
                roi_cols = st.columns(3)
                for i, (m, r) in enumerate(all_active_rois):
                    r_id, r_name = r[0], r[3]
                    with roi_cols[i % 3]:
                        with st.container(border=True):
                            roi_placeholders[r_id] = st.empty()

        with col_run_2:
            st.markdown("### 📋 Výsledky inspekce")
            global_status_placeholder = st.empty()
            st.write("")
            
            st.markdown("**🛡️ Stav jednotlivých kontrol:**")
            control_placeholders = {}
            for i, (m, r) in enumerate(all_active_rois):
                control_placeholders[r[0]] = st.empty()
                
        current_outputs = {i: False for i in range(1, 9)}
        
        if run_engine:
            import communication_manager
            
            if "lis_modbus" not in st.session_state:
                st.session_state.lis_modbus = communication_manager.LisModbusManager(ip_address="10.42.0.167")
                if st.session_state.lis_modbus.connect():
                    st.toast("🔌 Úspěšně připojeno k Moxa I/O modulu lisu!", icon="✅")
                else:
                    st.toast("⚠️ Moxa neodpovídá. Systém běží v simulačním režimu.", icon="ℹ️")

            max_pos_count = len(st.session_state.get("available_positions", [1, 2]))
            is_triggered, target_pos = st.session_state.lis_modbus.check_trigger_and_sequence(max_pos_count)
            
            if is_triggered:
                st.session_state.current_run_position = target_pos
                st.toast(f"⚡ Lis odtriggeroval! Spouštím kontrolu pro Pozici {target_pos}", icon="📸")
                
                is_entire_mold_ok = True
                
                for m, r in all_active_rois:
                    plny_nazev_masteru = str(m[2]).strip()
                    
                    # 🍏 Pokud název obsahuje mřížku, bezpečně z něj vytáhneme hardwarový cíl kamery
                    if "#" in plny_nazev_masteru:
                        lidsky_popis, camera_target_name = plny_nazev_masteru.split("#", 1)
                    else:
                        # Fallback pro starší záznamy
                        camera_target_name = plny_nazev_masteru 
                    
                    r_id, r_name, r_nok = r[0], r[3], r[8]
                    
                    # Vystřelení exkluzivního příkazu pro focení konkrétní kamery lisu
                    live_full_img, pylon_camera_name = camera_manager.capture_live_frame(device_name=camera_target_name.strip())
                    
                    # 🍏 Funkci natvrdo předáme cíl, aby vyfotila tu správnou kameru
                    live_full_img, pylon_camera_name = camera_manager.capture_live_frame(device_name=camera_target_name)
                    
                    if live_full_img is not None:
                        timestamp = int(time.time())
                        ulozeny_raw_soubor = f"C:/Image/Unsorted/{active_p}/basler_{pylon_camera_name}_{timestamp}.jpg"
                        os.makedirs(os.path.dirname(ulozeny_raw_soubor), exist_ok=True)
                        live_full_img.save(ulozeny_raw_soubor, "JPEG", quality=95)
                        
                        database.save_to_history(active_p, r_name, ulozeny_raw_soubor, "Neroztříděno")
                        os.makedirs(os.path.dirname(ulozeny_raw_soubor), exist_ok=True)
                        live_full_img.save(ulozeny_raw_soubor, "JPEG", quality=95)
                        
                        database.save_to_history(active_p, r_name, ulozeny_raw_soubor, "Neroztříděno")
                        
                        try:
                            live_crop = live_full_img.crop((r[4], r[5], r[4]+r[6], r[5]+r[7]))
                            live_roi_img = live_crop.resize((500, 500), Image.Resampling.LANCZOS)
                        except Exception:
                            live_roi_img = Image.new('RGB', (500, 500), color=(30, 30, 30))
                    else:
                        pylon_camera_name = "Chyba Kamery"
                        live_roi_img = Image.new('RGB', (500, 500), color=(30, 30, 30))
                    
                    active_model = None
                    try:
                        conn_inf = sqlite3.connect("vision_system.db")
                        cur_inf = conn_inf.cursor()
                        cur_inf.execute("SELECT model_name FROM model_registry WHERE project_name=? ORDER BY id DESC LIMIT 1", (active_p,))
                        row_m = cur_inf.fetchone()
                        conn_inf.close()
                        if row_m and os.path.exists(f"models/{row_m[0]}"):
                            active_model = f"models/{row_m[0]}"
                    except Exception:
                        pass
                    
                    if not active_model:
                        model_path = f"models/model_ai_{active_p}_{r_name}.pth"
                        universal_model_path = f"models/model_ai_{active_p}_Univerzalni_Sit.pth"
                        active_model = model_path if os.path.exists(model_path) else (universal_model_path if os.path.exists(universal_model_path) else None)
                    
                    if active_model:
                        is_zone_ok, ai_confidence = ai_engine.predict_with_ai(active_model, live_roi_img)
                        status_text = "OK" if is_zone_ok else "NOK"
                        caption_str = f"✨ AI Jistota: {int(ai_confidence * 100)}%"
                    else:
                        is_zone_ok = True
                        status_text = "OK (Bez AI)"
                        caption_str = "📐 Čeká na model"
                    
                    if not is_zone_ok:
                        current_outputs[r_nok] = True
                        is_entire_mold_ok = False
                    
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
                    
                    if is_zone_ok:
                        control_placeholders[r_id].markdown(f"🍏 **Kontrola {r_name}** — `OK`", unsafe_allow_html=True)
                    else:
                        control_placeholders[r_id].markdown(f"🍎 <span style='color:#FF4B4B;'>**Kontrola {r_name}** — `NOK (Výstup {r_nok})`</span>", unsafe_allow_html=True)

                if st.session_state.lis_modbus.client and st.session_state.lis_modbus.client.is_socket_open():
                    stav_pro_moxu = 1 if is_entire_mold_ok else 2
                    st.session_state.lis_modbus.client.write_single_register(address=0, value=stav_pro_moxu)
                
                if is_entire_mold_ok:
                    global_status_placeholder.markdown("<div style='background-color:#007D2F; color:white; padding:30px; border-radius:8px; text-align:center; font-size:55px; font-weight:bold;'>OK</div>", unsafe_allow_html=True)
                else:
                    global_status_placeholder.markdown("<div style='background-color:#C80000; color:white; padding:30px; border-radius:8px; text-align:center; font-size:55px; font-weight:bold;'>NOK</div>", unsafe_allow_html=True)
            
            time.sleep(0.1)
            st.rerun()
    else:
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
        
        # 🍏 1. DYNAMICKÝ INTEGRÁLNÍ SCAN SÍTĚ PRO VŠECHNY KAMERY
        try:
            from pypylon import pylon
            online_devices = [d.GetUserDefinedName() for d in pylon.TlFactory.GetInstance().EnumerateDevices() if d.GetUserDefinedName()]
            if not online_devices: 
                online_devices = ["Kamera1", "Kamera2"]
        except Exception:
            online_devices = ["Kamera1", "Kamera2"]

        # Rozdělení obrazovky na dva čisté sloupce (Ovládání vlevo, Hardware a náhled vpravo)
        col_ctrl, col_img = st.columns([1, 2])
        
        # --- LEVÝ PANEL: DEFINICE VÝŘEZŮ A UKLÁDÁNÍ ---
        with col_ctrl:
            st.markdown("### 🔌 Zdroj obrázku")
            source_type = st.radio(
                "Vyberte, jak chcete nahrát podkladový snímek:",
                ["📷 Simulovat z kamery lisu (Složka OK)", "📁 Nahrát soubor z disku (Příprava dopředu)"],
                key="master_src_radio_unique"
            )
            
            st.divider()
            st.write("### ✂️ Definice výřezu")
            m_id_name = st.text_input("Název Masteru (např. Pozice 1)", key="master_name_field_unique")
            
            ax = st.slider("X začátek", 0, 2000, 0, key="slider_ax_u")
            ay = st.slider("Y začátek", 0, 2000, 0, key="slider_ay_u")
            aw = st.slider("Šířka výřezu", 10, 2000, 500, key="slider_aw_u")
            ah = st.slider("Výška výřezu", 10, 2000, 500, key="slider_ah_u")

            if st.button("💾 ULOŽIT MASTER", type="primary", use_container_width=True, key="btn_save_master_final"):
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
                    
                    # 🍏 SKRYTÁ VAZBA PRO ROBOTA: Propojíme lidský popis s hardwarovým ID ze session state
                    hw_target = st.session_state.get("current_hardware_target", "Kamera1")
                    kombinovany_nazev = f"{m_id_name}#{hw_target}"
                    
                    database.add_master(active_p, kombinovany_nazev, filename, ax, ay, aw, ah)
                    st.success(f"Master '{m_id_name}' úspěšně svázán se zařízením {hw_target}!")
                    time.sleep(0.4)
                    st.rerun()
                else:
                    st.error("❌ Pro uložení musíte zadat název a mít načtený obrázek!")

        # --- PRAVÝ PANEL: LIVE STREAM A HARDWAROVÉ REGISTRY ---
        with col_img:
            st.markdown("### 📷 Výběr aktivního hardwaru")
            selected_cam_device = st.selectbox(
                "Zvolte kameru pro uložení Master snímku:",
                options=sorted(online_devices),
                key="master_camera_hardware_select"
            )
            st.session_state["current_hardware_target"] = selected_cam_device
            
            st.write("") 
            
            # JEDINÁ chráněná instance živého přepínače na stránce
            live_stream_active = st.toggle("🎥 SPUSTIT ŽIVÝ STREAM", key="master_live_stream_toggle")
            
            if live_stream_active:
                live_full_img, error_msg = camera_manager.capture_live_frame(device_name=st.session_state["current_hardware_target"])
                
                if live_full_img:
                    st.session_state.setup_image_buffer = live_full_img
                    camera_manager.set_hardware_parameters(
                        st.session_state.get("exp_slider_val", 40005),
                        st.session_state.get("gain_slider_val", 3),
                        device_name=st.session_state["current_hardware_target"]
                    )
                else:
                    st.error(f"❌ {error_msg}")
            else:
                sim_dir = os.path.join(BASE_IMAGE_DIR, "OK", active_p)
                if "Složka OK" in source_type:
                    images = []
                    if os.path.exists(sim_dir):
                        for ext in ["*.jpg", "*.jpeg", "*.png", "*.JPG", "*.PNG"]:
                            images.extend(glob.glob(os.path.join(sim_dir, ext)))
                    if images:
                        st.session_state.setup_image_buffer = Image.open(images[0]).convert("RGB")
                    else:
                        if st.session_state.setup_image_buffer is None:
                            st.session_state.setup_image_buffer = Image.new('RGB', (1920, 1080), color=(75, 105, 130))

            if st.session_state.setup_image_buffer is not None:
                preview_img = st.session_state.setup_image_buffer.copy()
                img_w, img_h = preview_img.size
                
                safe_ax = min(ax, img_w - 10)
                safe_ay = min(ay, img_h - 10)
                
                draw = ImageDraw.Draw(preview_img)
                draw.rectangle([safe_ax, safe_ay, safe_ax + 500, safe_ay + 500], outline="red", width=5)
                st.image(preview_img, use_container_width=True, caption=f"Aktuální podklad ({img_w}x{img_h} px)")

            st.slider("Elektronická uzávěrka (Anti-Flicker 50Hz takty)", min_value=19985, max_value=159985, value=40005, step=19985, key="exp_slider_val")
            st.slider("Zesílení obrazu (Gain Raw index)", 0, 18, 3, step=1, key="gain_slider_val")
            st.text_input("📝 Označení konfigurace (např. Číslo_P1):", value="281_P1", key="pfs_custom_description")

            current_setup_pos = st.session_state.get("current_run_position", 1)
            if st.button(f"💾 ULOŽIT TUTO KONFIGURACI JAKO PFS PRO POZICI {current_setup_pos}", type="primary", use_container_width=True, key="btn_save_pfs_final"):
                proj_name = st.session_state.get("active_project", "Default_Project")
                success, path_or_err = camera_manager.save_camera_features_to_pfs(proj_name, current_setup_pos, device_name=st.session_state["current_hardware_target"])
                if success:
                    st.success(f"🎉 Průmyslový PFS profil pro Pozici {current_setup_pos} úspěšně vytvořen!")
                    st.rerun()
                else:
                    st.error(f"❌ Selhalo vytvoření PFS souboru: {path_or_err}")

        # 🍏 AKTIVNÍ VIDEO REFRESHE (Mimo vnitřní cykly sloupců)
        if st.session_state.get("master_live_stream_toggle", False):
            time.sleep(0.04)
            st.rerun()

# --- TAB 3: ZÓNY ---
with tab3:
    active_p = st.session_state.active_project
    st.info(f"🏗️ Nastavení zón pro projekt: **{active_p}**")
    st.write("---")
    st.markdown("### 🗺️ Vyberte pozici pro úpravu (Sekvence lisu)")
    
    if "available_positions" not in st.session_state:
        st.session_state.available_positions = [1, 2]
    if "current_position" not in st.session_state:
        st.session_state.current_position = 1

    pos_count = len(st.session_state.available_positions)
    cols = st.columns(pos_count + 1)
    
    for i, pos in enumerate(st.session_state.available_positions):
        with cols[i]:
            is_active = (st.session_state.current_position == pos)
            if st.button(f" Pozice {pos}", key=f"zone_tab_pos_{pos}", type="primary" if is_active else "secondary", use_container_width=True):
                st.session_state.current_position = pos
                proj_name = st.session_state.get("active_project", "Default_Project")
                
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

        st.write("### 🔑 Výber podkladového Masteru / kamery:")
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
                                r_name = r[3]
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
                
                os.makedirs("models", exist_ok=True)
                existing_models = [os.path.basename(f) for f in glob.glob("models/*.pth")]
                model_options = ["✨ Trénovat zcela novou síť"] + existing_models
                
                selected_model_option = st.selectbox(
                    "🔗 Použít stávající neuronovou síť (např. z jiné formy/projektu):",
                    options=model_options,
                    key=f"model_reuse_select_{zn}"
                )
                
                if selected_model_option != "✨ Trénovat zcela novou síť":
                    if "Univerzalni_Sit" in selected_model_option:
                        st.caption("🔒 *Univerzální síť systému je uzamčena proti smazání.*")
                    else:
                        if st.button(f"🗑️ SMAZAT MODEL {selected_model_option} Z DISKU", use_container_width=True, type="secondary"):
                            model_to_delete_path = f"models/{selected_model_option}"
                            if os.path.exists(model_to_delete_path):
                                os.remove(model_to_delete_path)
                            
                            conn_del = sqlite3.connect("vision_system.db")
                            cur_del = conn_del.cursor()
                            cur_del.execute("DELETE FROM model_registry WHERE model_name=?", (selected_model_option,))
                            conn_del.commit()
                            conn_del.close()
                            
                            st.toast(f"Model {selected_model_option} byl trvale smazán", icon="🗑️")
                            time.sleep(0.5)
                            st.rerun()

                st.write("") 
                
                default_custom_name = f"model_ai_{active_p}_{zn.replace(' ', '_')}"
                custom_model_name = st.text_input(
                    "📝 Vlastní název pro ukládanou neuronovou síť (bez přípony .pth):",
                    value=default_custom_name,
                    key=f"custom_model_name_input_{zn}"
                ).strip()
                
                clean_model_filename = "".join([c for c in custom_model_name if c.isalnum() or c in ["_", "-"]]) + ".pth"

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

                if selected_model_option != "✨ Trénovat zcela novou síť":
                    if st.button(f"🔗 PROPOJIT ZÓNU SE STÁVAJÍCÍ SÍTÍ: {selected_model_option}", use_container_width=True, type="secondary"):
                        import datetime
                        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        conn_reg = sqlite3.connect("vision_system.db")
                        cur_reg = conn_reg.cursor()
                        cur_reg.execute("""
                            INSERT INTO model_registry (project_name, model_name, accuracy, created_at, engineering_notes)
                            VALUES (?, ?, ?, ?, ?)
                        """, (active_p, selected_model_option, "Kopie / Link", current_time, f"Převzatý model ze sdílené klapky. Soubor: {selected_model_option}"))
                        conn_reg.commit()
                        conn_reg.close()
                        
                        st.success(f"✅ Zóna úspěšně propojena se sítě {selected_model_option}!")
                        time.sleep(0.5)
                        st.rerun()
                else:
                    if st.button(f"🚀 SPUSTIT UČENÍ S NÁZVEM: {clean_model_filename}", use_container_width=True, type="primary"):
                        with st.spinner("Učení neuronové sítě běží..."):
                            progress_bar = st.progress(0.0)
                            status_text = st.empty()
                            def update_progress(pct, msg):
                                progress_bar.progress(pct)
                                status_text.text(msg)
                            
                            success, result_msg = ai_engine.train_ai_model(active_p, clean_model_filename, update_progress)
                            if success: 
                                st.success(f"🎉 Úspěšně naučeno! {result_msg}")
                                
                                try:
                                    import datetime
                                    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    conn_reg = sqlite3.connect("vision_system.db")
                                    cur_reg = conn_reg.cursor()
                                    cur_reg.execute("""
                                        INSERT INTO model_registry (project_name, model_name, accuracy, created_at, engineering_notes)
                                        VALUES (?, ?, ?, ?, ?)
                                    """, (active_p, clean_model_filename, "100%", current_time, "Výchozí trénování s vlastním pojmenováním."))
                                    conn_reg.commit()
                                    conn_reg.close()
                                except Exception as db_err:
                                    print(f"⚠️ Chyba zápisu modelu: {db_err}")
                                    
                                time.sleep(0.5)
                                st.rerun()
                            else: 
                                st.error(f"❌ Chyba: {result_msg}")

                st.markdown("---")
                st.subheader("🧠 Přehled a správa naučených neuronových sítí")
                
                conn_view = sqlite3.connect("vision_system.db")
                cur_view = conn_view.cursor()
                cur_view.execute("PRAGMA table_info(model_registry)")
                cols_m = [c[1] for c in cur_view.fetchall()]
                c_proj_m = "project_name" if "project_name" in cols_m else "project"
                
                cur_view.execute(f"SELECT id, model_name, created_at, accuracy, engineering_notes FROM model_registry WHERE {c_proj_m}=? ORDER BY id DESC", (active_p,))
                saved_models = cur_view.fetchall()
                conn_view.close()
                
                if not saved_models:
                    st.caption("ℹ️ V tomto projektu zatím nebyly uloženy žádné verze neuronových sítí.")
                else:
                    for m_id, m_name, m_date, m_acc, m_notes in saved_models:
                        with st.container(border=True):
                            col_info, col_notes = st.columns([2, 3])
                            
                            with col_info:
                                st.markdown(f"🤖 **Název:** `{m_name}`")
                                st.caption(f"📅 Vytvořeno: {m_date}")
                                st.markdown(f"🎯 Přesnost: :green[{m_acc}]")
                                
                            with col_notes:
                                note_key = f"note_{m_id}_{active_p}"
                                new_note = st.text_input(
                                    "Inženýrská poznámka k verzi:", 
                                    value=m_notes, 
                                    key=note_key,
                                    label_visibility="collapsed" if m_notes else "visible"
                                )
                                
                                if new_note != m_notes:
                                    conn_up = sqlite3.connect("vision_system.db")
                                    cur_up = conn_up.cursor()
                                    cur_up.execute("UPDATE model_registry SET engineering_notes=? WHERE id=?", (new_note, m_id))
                                    conn_up.commit()
                                    conn_up.close()
                                    st.toast("Poznámka k síti aktualizována", icon="💾")
                                    time.sleep(0.1)
                                    st.rerun()

# --- TAB 4: I/O ---
with tab4:
    st.subheader("🔌 Nastavení komunikace (Modbus TCP / Moxa)")
    st.text_input("IP Adresa Moxa I/O modulu", value="192.168.1.200")
    st.button("🔄 Testovat připojení hardwaru", use_container_width=True)
    
# --- TAB 5: HISTORIE ---
with tab5:
    st.subheader("📜 Historie kontrol a snímků")
    
    if st.button("📸 VYFOTIT A ULOŽIT TESTOVACÍ SNÍMEK DO HISTORIE", type="primary", key="manual_capture_tab5"):
        import camera_manager
        live_full_img, pylon_camera_name = camera_manager.capture_live_frame()
        
        if live_full_img is not None:
            active_p = st.session_state.get("active_project", "Default_Project")
            timestamp = int(time.time())
            
            test_path = f"C:/Image/Unsorted/{active_p}/manual_{timestamp}.jpg"
            os.makedirs(os.path.dirname(test_path), exist_ok=True)
            
            live_full_img.save(test_path, "JPEG", quality=95)
            database.save_to_history(active_p, "Manualni_Test", test_path, "Neroztříděno")
            st.success(f"✅ Snímek úspěšně zapsán na disk a uložen do SQL databáze!")
            time.sleep(0.5)
            st.rerun()
        else:
            st.error("❌ Kamera nevrátila žádný snímek. Zkontrolujte, zda běží stream v TAB 2.")

    st.divider()

    active_p = st.session_state.get("active_project")
    if active_p:
        import sqlite3
        conn = sqlite3.connect("vision_system.db")
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(history)")
        columns = [col[1] for col in cursor.fetchall()]
        
        c_proj = "project" if "project" in columns else ("project_name" if "project_name" in columns else columns[1])
        c_roi = "roi_name" if "roi_name" in columns else ("zone_name" if "zone_name" in columns else columns[2])
        c_path = "image_path" if "image_path" in columns else ("img_path" if "img_path" in columns else ("file_path" if "file_path" in columns else "path"))
        
        query = f"SELECT id, {c_roi}, {c_path}, status FROM history WHERE {c_proj}=? AND status='Neroztříděno' ORDER BY id DESC"
        cursor.execute(query, (active_p,))
        unassigned_records = cursor.fetchall()
        conn.close()
        
        if not unassigned_records:
            st.info("⏳ Všechny snímky jsou roztříděny. Dataset pro AI je připraven!")
        else:
            st.markdown(f"### 📥 Snímky čekající na roztřídění ({len(unassigned_records)}x)")
            
            h_cols = st.columns(4)
            displayed_count = 0
            
            for idx, record in enumerate(unassigned_records):
                if displayed_count >= 12: 
                    break
                    
                r_id, r_zone, r_path, r_status = record[0], record[1], record[2], record[3]
                
                if not os.path.exists(r_path):
                    continue
                
                with h_cols[displayed_count % 4]:
                    with st.container(border=True):
                        st.caption(f"📍 Zdroj: {r_zone}")
                        st.image(r_path, use_container_width=True)
                        
                        btn_col1, btn_col2 = st.columns(2)
                        
                        with btn_col1:
                            if st.button("🍏 OK", key=f"btn_ok_{r_id}_{idx}", use_container_width=True):
                                target_dir = f"C:/Image/OK/{active_p}"
                                os.makedirs(target_dir, exist_ok=True)
                                target_path = os.path.join(target_dir, os.path.basename(r_path))
                                os.rename(r_path, target_path)
                                
                                conn = sqlite3.connect("vision_system.db")
                                cursor = conn.cursor()
                                cursor.execute(f"UPDATE history SET status='OK', {c_path}=? WHERE id=?", (target_path, r_id))
                                conn.commit()
                                conn.close()
                                st.toast(f"Uloženo do složky OK", icon="✅")
                                time.sleep(0.1)
                                st.rerun()
                                
                        with btn_col2:
                            if st.button("🍎 NOK", key=f"btn_nok_{r_id}_{idx}", use_container_width=True):
                                target_dir = f"C:/Image/NOK/{active_p}"
                                os.makedirs(target_dir, exist_ok=True)
                                target_path = os.path.join(target_dir, os.path.basename(r_path))
                                os.rename(r_path, target_path)
                                
                                conn = sqlite3.connect("vision_system.db")
                                cursor = conn.cursor()
                                cursor.execute(f"UPDATE history SET status='NOK', {c_path}=? WHERE id=?", (target_path, r_id))
                                conn.commit()
                                conn.close()
                                st.toast(f"Uloženo do složky NOK", icon="🚨")
                                time.sleep(0.1)
                                st.rerun()
                
                displayed_count += 1

        st.markdown("---")
        st.subheader("📂 Kontrola a revize datasetu")
        st.info("Zde si můžete zkontrolovat snímky v trénovacích složkách.")
        
        rev_folder = st.radio("Vyberte složku ke kontrole:", ["Zobrazit složku OK", "Zobrazit složku NOK"], horizontal=True, key="rev_folder_select")
        target_status = "OK" if "Zobrazit složku OK" in rev_folder else "NOK"
        opp_status = "NOK" if target_status == "OK" else "OK"
        opp_color = "🍎 Změnit na NOK" if target_status == "OK" else "🍏 Změnit na OK"
        
        conn = sqlite3.connect("vision_system.db")
        cursor = conn.cursor()
        cursor.execute(f"SELECT id, {c_roi}, {c_path} FROM history WHERE {c_proj}=? AND status=? ORDER BY id DESC", (active_p, target_status))
        reviewed_records = cursor.fetchall()
        conn.close()
        
        if not reviewed_records:
            st.caption(f"Složka {target_status} je prázdná.")
        else:
            st.markdown(f"**Vzorky ve složce {target_status} ({len(reviewed_records)}x):**")
            
            rev_cols = st.columns(4)
            for r_idx, r_rec in enumerate(reviewed_records[:8]):
                rev_id, rev_zone, rev_path = r_rec[0], r_rec[1], r_rec[2]
                
                with rev_cols[r_idx % 4]:
                    with st.container(border=True):
                        st.caption(f"📍 {rev_zone}")
                        
                        if os.path.exists(rev_path):
                            st.image(rev_path, use_container_width=True)
                        else:
                            st.caption("⚠️ Soubor přesunut nebo smazán")
                            
                        if st.button(opp_color, key=f"rev_flip_{rev_id}_{r_idx}", use_container_width=True):
                            new_dir = f"C:/Image/{opp_status}/{active_p}"
                            os.makedirs(new_dir, exist_ok=True)
                            new_path = os.path.join(new_dir, os.path.basename(rev_path))
                            
                            if os.path.exists(rev_path):
                                os.rename(rev_path, new_path)
                                
                            conn = sqlite3.connect("vision_system.db")
                            cursor = conn.cursor()
                            cursor.execute(f"UPDATE history SET status=?, {c_path}=? WHERE id=?", (opp_status, new_path, rev_id))
                            conn.commit()
                            conn.close()
                            
                            st.toast(f"Přesunuto do složky {opp_status}", icon="🔄")
                            time.sleep(0.1)
                            st.rerun()