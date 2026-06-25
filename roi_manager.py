import streamlit as st
import database
import time
import os
import glob
import sqlite3
from PIL import Image, ImageDraw

def render_roi_tab(m_id, m_name, m_path, active_p):
    """
    Izolovaný průmyslový modul pro správu a vrstvení ROI.
    Kompletně odstíněn od hlavního app.py.
    """
    img_roi = Image.open(m_path).convert("RGB")
    W, H = img_roi.size

    # --- INICIALIZACE STAVU PRO MULTI-ROI ---
    if "selected_roi_identity" not in st.session_state:
        st.session_state["selected_roi_identity"] = "➕ Přidat nové ROI"
    if "slider_x" not in st.session_state: st.session_state["slider_x"] = 100
    if "slider_y" not in st.session_state: st.session_state["slider_y"] = 100
    if "slider_w" not in st.session_state: st.session_state["slider_w"] = 150
    if "slider_h" not in st.session_state: st.session_state["slider_h"] = 150

    # Načtení všech uložených ROI z SQL pro tento master podklad
    all_rois = database.get_rois(m_id, active_p)
    seznam_roi_v_db = [str(r[3]).strip() for r in all_rois] if all_rois else []
    
    if st.session_state["selected_roi_identity"] != "➕ Přidat nové ROI" and st.session_state["selected_roi_identity"] not in seznam_roi_v_db:
        st.session_state["selected_roi_identity"] = "➕ Přidat nové ROI"

    c_ctrl, c_viz = st.columns([1, 1.8])
    with c_ctrl:
        st.markdown(f"### 🔧 Oblasti zájmu pro Master: {m_name.split('#')[0]}")
        
        # --- AKČNÍ LIŠTA TLAČÍTEK ---
        btn_col1, btn_col2, btn_col3 = st.columns(3)
        with btn_col1:
            if st.button("➕ + ROI", use_container_width=True, key="mod_append_new_roi_btn"):
                st.session_state["selected_roi_identity"] = "➕ Přidat nové ROI"
                st.session_state["slider_x"], st.session_state["slider_y"] = 100, 100
                st.session_state["slider_w"], st.session_state["slider_h"] = 150, 150
                st.rerun()
        with btn_col2:
            přejmenovat_aktivni = st.toggle("PŘEJMEN.", key="mod_toggle_rename_isolated")
        with btn_col3:
            if st.button("SMAZAT VŠE", use_container_width=True, type="secondary", key="mod_purge_all_rois_btn"):
                if all_rois:
                    for r in all_rois: database.delete_roi(r[0])
                    st.session_state["selected_roi_identity"] = "➕ Přidat nové ROI"
                    st.toast("💥 Všechny výřezy z plátna vymazány.", icon="🗑️")
                    time.sleep(0.2)
                    st.rerun()

        st.write("---")

        # Rozbalovací selektor
        moznosti_selectboxu = ["➕ Přidat nové ROI"] + seznam_roi_v_db
        index_vyberu = 0
        if st.session_state["selected_roi_identity"] in moznosti_selectboxu:
            index_vyberu = moznosti_selectboxu.index(st.session_state["selected_roi_identity"])

        vybrany_u = st.selectbox(
            "🎯 Vyberte ROI k úpravě polohy nebo založte nové:",
            options=moznosti_selectboxu,
            index=index_vyberu,
            key="mod_selector_active_roi"
        )
        st.session_state["selected_roi_identity"] = vybrany_u

        roi_id_db = None
        nok_val_idx = 0
        ztol_val = 20

        if vybrany_u == "➕ Přidat nové ROI":
            zn_default = f"p1_{len(all_rois) + 1}"
            zx_val = st.session_state["slider_x"]
            zy_val = st.session_state["slider_y"]
            zw_val = st.session_state["slider_w"]
            zh_val = st.session_state["slider_h"]
        else:
            stajici_roi = next((r for r in all_rois if str(r[3]).strip() == vybrany_u), None)
            if stajici_roi:
                roi_id_db = stajici_roi[0]
                zn_default = stajici_roi[3]
                zx_val = stajici_roi[4]
                zy_val = stajici_roi[5]
                zw_val = stajici_roi[6]
                zh_val = stajici_roi[7]
                nok_val_idx = int(stajici_roi[8]) - 1
                ztol_val = stajici_roi[9] if len(stajici_roi) > 9 else 20

        # Formulářové prvky
        zn = st.text_input("📝 Popis / Název ROI (bez diakritiky):", value=zn_default, key=f"mod_name_field_{vybrany_u}").strip()
        nok_val = st.selectbox("Přiřazení chyby lisu (NOK 1-8)", range(1, 9), index=max(0, nok_val_idx), key=f"mod_nok_field_{vybrany_u}")
        
        # --- CHROMÉ POSUVNÍKY SOUŘADNIC ---
        zx = st.slider("X poloha", 0, W, int(zx_val), key=f"mod_slide_x_{vybrany_u}")
        zy = st.slider("Y poloha", 0, H, int(zy_val), key=f"mod_slide_y_{vybrany_u}")
        zw = st.slider("Šířka", 10, W, int(zw_val), key=f"mod_slide_w_{vybrany_u}")
        zh = st.slider("Výška", 10, H, int(zh_val), key=f"mod_slide_h_{vybrany_u}")
        ztol = st.slider("Tolerance odchylky AI", 1, 100, int(ztol_val), key=f"mod_slide_tol_{vybrany_u}")
        
        if vybrany_u == "➕ Přidat nové ROI":
            st.session_state["slider_x"] = zx
            st.session_state["slider_y"] = zy
            st.session_state["slider_w"] = zw
            st.session_state["slider_h"] = zh

        if st.button("💾 ULOŽIT OBLAST ZÁJMU DO SQL", type="primary", use_container_width=True, key="mod_save_roi_btn"):
            if not zn:
                st.error("❌ Popis ROI nesmí být prázdný!")
            else:
                try:
                    if vybrany_u != "➕ Přidat nové ROI" and roi_id_db is not None:
                        database.delete_roi(roi_id_db)
                    else:
                        duplicitni = next((r for r in all_rois if str(r[3]).strip() == zn), None)
                        if duplicitni: database.delete_roi(duplicitni[0])
                        
                    database.save_roi(m_id, active_p, zn, int(zx), int(zy), int(zw), int(zh), int(nok_val), int(ztol))
                    st.session_state["selected_roi_identity"] = zn
                    st.success(f"🎉 ROI '{zn}' úspěšně zapsáno do SQL databáze!")
                    time.sleep(0.3)
                    st.rerun()
                except Exception as db_error:
                    st.error(f"❌ Chyba při zápisu: {db_error}")

    with c_viz:
        draw = ImageDraw.Draw(img_roi)
        line_w = max(2, int(W * 0.006))
        
        # Vykreslení uložených zelených ROI
        if all_rois:
            for r in all_rois:
                r_name_loop = str(r[3]).strip()
                if r_name_loop != zn:
                    rx, ry, rw, rh = int(r[4]), int(r[5]), int(r[6]), int(r[7])
                    draw.rectangle([rx, ry, rx+rw, ry+rh], outline="#00FF00", width=line_w)
                    draw.text((rx + 8, ry + 8), r_name_loop, fill="#00FF00")
        
        # Vykreslení laděného výřezu (oranžově)
        draw.rectangle([zx, zy, zx+zw, zy+zh], outline="orange", width=line_w + 3)
        draw.text((zx + 8, zy + 8), f"-> {zn} (LADENI)", fill="orange")
        
        st.image(img_roi, use_container_width=True, caption="Plátno Masteru (Zelená = Uložená ROI v SQL, Oranžová = Právě laděný výřez)")
        
        # --- INTEGRACE SÍTÍ JEDE POD TÍMTO ---
        st.divider()
        st.markdown("### 🧠 Řízení sítě projektu")
        
        os.makedirs("models", exist_ok=True)
        existing_models = [os.path.basename(f) for f in glob.glob("models/*.pth")]
        model_options = ["✨ Trénovat zcela novou síť"] + existing_models
        
        selected_model_option = st.selectbox(
            "🔗 Použít stávající neuronovou síť:",
            options=model_options,
            key=f"mod_model_reuse_{zn}"
        )
        
        if selected_model_option != "✨ Trénovat zcela novou síť" and "Univerzalni_Sit" not in selected_model_option:
            if st.button(f"🗑️ SMAZAT MODEL {selected_model_option} Z DISKU", use_container_width=True, type="secondary", key=f"mod_del_model_{zn}"):
                model_to_delete_path = f"models/{selected_model_option}"
                if os.path.exists(model_to_delete_path): os.remove(model_to_delete_path)
                
                conn_del = sqlite3.connect("vision_system.db")
                cur_del = conn_del.cursor()
                cur_del.execute("DELETE FROM model_registry WHERE model_name=?", (selected_model_option,))
                conn_del.commit()
                conn_del.close()
                st.toast(f"Model {selected_model_option} smazán", icon="🗑️")
                time.sleep(0.5)
                st.rerun()

        st.write("") 
        default_custom_name = f"model_ai_{active_p}_{zn.replace(' ', '_')}"
        custom_model_name = st.text_input("📝 Vlastní název pro neuronovou síť:", value=default_custom_name, key=f"mod_custom_model_name_{zn}").strip()
        clean_model_filename = "".join([c for c in custom_model_name if c.isalnum() or c in ["_", "-"]]) + ".pth"

        import ai_engine
        ok_dir_check = os.path.join("C:/Image", "OK", active_p)
        nok_dir_check = os.path.join("C:/Image", "NOK", active_p)
        count_ok = len(glob.glob(os.path.join(ok_dir_check, "*"))) if os.path.exists(ok_dir_check) else 0
        count_nok = len(glob.glob(os.path.join(nok_dir_check, "*"))) if os.path.exists(nok_dir_check) else 0
        
        if count_ok < 4 or count_nok < 4:
            st.warning(f"⚠️ Nedostatečné množství dat: {count_ok}x OK a {count_nok}x NOK vzorků.")
        else:
            st.info(f"📊 Dataset obsahuje: {count_ok}x OK a {count_nok}x NOK vzorků.")

        if selected_model_option != "✨ Trénovat zcela novou síť":
            if st.button(f"🔗 PROPOJIT ROI SE STÁVAJÍCÍ SÍTÍ", use_container_width=True, type="secondary", key=f"mod_link_model_{zn}"):
                import datetime
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                conn_reg = sqlite3.connect("vision_system.db")
                cur_reg = conn_reg.cursor()
                cur_reg.execute("INSERT INTO model_registry (project_name, model_name, accuracy, created_at, engineering_notes) VALUES (?, ?, ?, ?, ?)", 
                                (active_p, selected_model_option, "Link", current_time, "Propojený model."))
                conn_reg.commit()
                conn_reg.close()
                st.success("✅ Propojeno!")
                time.sleep(0.5)
                st.rerun()
        else:
            if st.button(f"🚀 SPUSTIT UČENÍ S NÁZVEM: {clean_model_filename}", use_container_width=True, type="primary", key=f"mod_train_btn_{zn}"):
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
                            cur_reg.execute("INSERT INTO model_registry (project_name, model_name, accuracy, created_at, engineering_notes) VALUES (?, ?, ?, ?, ?)", 
                                            (active_p, clean_model_filename, "100%", current_time, "Výchozí trénování."))
                            conn_reg.commit()
                            conn_reg.close()
                        except Exception: pass
                        time.sleep(0.5)
                        st.rerun()
                    else: 
                        st.error(f"❌ Chyba: {result_msg}")