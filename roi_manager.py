import streamlit as st
import database
import time
import os
import glob
import sqlite3
from PIL import Image, ImageDraw

def render_roi_tab(m_id, m_name, m_path, active_p, current_position):
    """
    Izolovaný průmyslový modul pro správu a vrstvení ROI.
    Kompletně odstíněn od hlavního app.py.
    """
    img_roi = Image.open(m_path).convert("RGB")
    W, H = img_roi.size

    # Načtení uložených ROI pro tento master a pozici z SQL
    all_rois = database.get_rois(m_id, active_p, current_position)
    seznam_roi_v_db = [str(r[3]).strip() for r in all_rois] if all_rois else []

    # --- INICIALIZACE STAVU VÝBÊRU ---
    if "selected_roi_identity" not in st.session_state:
        st.session_state["selected_roi_identity"] = "➕ Přidat nové ROI"

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
                st.session_state["st_roi_x"] = 100
                st.session_state["st_roi_y"] = 100
                st.session_state["st_roi_w"] = 150
                st.session_state["st_roi_h"] = 150
                st.session_state["st_roi_tol"] = 20
                st.session_state["st_roi_name"] = f"p1_{len(all_rois) + 1}"
                st.rerun()
                
        with btn_col2:
            st.toggle("PŘEJMEN.", key="mod_toggle_rename_isolated")
        with btn_col3:
            if st.button("SMAZAT VŠE", use_container_width=True, type="secondary", key="mod_purge_all_rois_btn"):
                if all_rois:
                    for r in all_rois: database.delete_roi(r[0])
                    st.session_state["selected_roi_identity"] = "➕ Přidat nové ROI"
                    st.rerun()

        st.write("---")

        # --- ROZBALOVACÍ SELEKTOR ---
        moznosti_selectboxu = ["➕ Přidat nové ROI"] + seznam_roi_v_db
        index_vyberu = moznosti_selectboxu.index(st.session_state["selected_roi_identity"])

        def sync_sliders_to_selected():
            target = st.session_state["roi_selector_component_final"]
            st.session_state["selected_roi_identity"] = target
            
            if target == "➕ Přidat nové ROI":
                st.session_state["st_roi_x"] = 100
                st.session_state["st_roi_y"] = 100
                st.session_state["st_roi_w"] = 150
                st.session_state["st_roi_h"] = 150
                st.session_state["st_roi_tol"] = 20
                st.session_state["st_roi_name"] = f"p1_{len(all_rois) + 1}"
            else:
                found = next((r for r in all_rois if str(r[3]).strip() == target), None)
                if found:
                    st.session_state["st_roi_name"] = found[3]
                    st.session_state["st_roi_x"] = found[4]
                    st.session_state["st_roi_y"] = found[5]
                    st.session_state["st_roi_w"] = found[6]
                    st.session_state["st_roi_h"] = found[7]
                    st.session_state["st_roi_nok"] = range(1, 9)[int(found[8]) - 1]
                    st.session_state["st_roi_tol"] = found[9] if len(found) > 9 else 20

        vybrany_u = st.selectbox(
            "🎯 Vyberte ROI k úpravě polohy nebo založte nové:",
            options=moznosti_selectboxu,
            index=index_vyberu,
            key="roi_selector_component_final",
            on_change=sync_sliders_to_selected
        )

        if "st_roi_x" not in st.session_state:
            if vybrany_u == "➕ Přidat nové ROI":
                st.session_state["st_roi_name"] = f"p1_{len(all_rois) + 1}"
                st.session_state["st_roi_x"], st.session_state["st_roi_y"] = 100, 100
                st.session_state["st_roi_w"], st.session_state["st_roi_h"] = 150, 150
                st.session_state["st_roi_tol"] = 20
            else:
                found = next((r for r in all_rois if str(r[3]).strip() == vybrany_u), None)
                if found:
                    st.session_state["st_roi_name"] = found[3]
                    st.session_state["st_roi_x"], st.session_state["st_roi_y"] = found[4], found[5]
                    st.session_state["st_roi_w"], st.session_state["st_roi_h"] = found[6], found[7]
                    st.session_state["st_roi_tol"] = found[9] if len(found) > 9 else 20

        roi_id_db = None
        nok_val_idx = 0
        if vybrany_u != "➕ Přidat nové ROI":
            found = next((r for r in all_rois if str(r[3]).strip() == vybrany_u), None)
            if found:
                roi_id_db = found[0]
                nok_val_idx = int(found[8]) - 1

        # --- STABILNÍ PRVKY ROZHRANÍ ---
        zn = st.text_input("📝 Popis / Název ROI (bez diakritiky):", key="st_roi_name").strip()
        nok_val = st.selectbox("Přiřazení chyby lisu (NOK 1-8)", range(1, 9), index=max(0, nok_val_idx), key="st_roi_nok")
        
        zx = st.slider("X poloha", 0, W, key="st_roi_x")
        zy = st.slider("Y poloha", 0, H, key="st_roi_y")
        zw = st.slider("Šířka", 10, W, key="st_roi_w")
        zh = st.slider("Výška", 10, H, key="st_roi_h")
        ztol = st.slider("Tolerance odchylky AI", 1, 100, key="st_roi_tol")

        st.write("")

        # --- OSTRÉ UKLÁDACÍ TLAČÍTKO S PODPOROU EDITACE ---
        if st.button("💾 ULOŽIT OBLAST ZÁJMU DO SQL", type="primary", use_container_width=True, key="execute_save_roi_final_btn"):
            if not zn:
                st.error("❌ Popis ROI nesmí být prázdný!")
            else:
                try:
                    # Pokud upravujeme vybrané ROI z menu, smažeme starou verzi podle ID
                    if vybrany_u != "➕ Přidat nové ROI" and roi_id_db is not None:
                        database.delete_roi(roi_id_db)
                    
                    # Pojistka: Pokud technik přepsal název ručně v textovém poli a jméno už v DB existuje, smažeme ho (přepis/editace)
                    duplicitni = next((r for r in all_rois if str(r[3]).strip() == zn), None)
                    if duplicitni: 
                        database.delete_roi(duplicitni[0])
                    
                    # Bezpečný zápis s aktualizovanou pozicí
                    database.save_roi(m_id, active_p, zn, int(zx), int(zy), int(zw), int(zh), int(nok_val), int(ztol), current_position)
                    
                    st.session_state["selected_roi_identity"] = zn
                    st.toast(f"💾 ROI '{zn}' úspěšně uloženo/upraveno!", icon="✅")
                    time.sleep(0.1)
                    st.rerun()
                except Exception as db_error:
                    st.error(f"❌ Chyba zápisu při editaci: {db_error}")

    with c_viz:
        draw = ImageDraw.Draw(img_roi)
        line_w = max(2, int(W * 0.006))
        
        if all_rois:
            for r in all_rois:
                r_name_loop = str(r[3]).strip()
                if r_name_loop != zn:
                    rx, ry, rw, rh = int(r[4]), int(r[5]), int(r[6]), int(r[7])
                    draw.rectangle([rx, ry, rx+rw, ry+rh], outline="#00FF00", width=line_w)
                    draw.text((rx + 8, ry + 8), r_name_loop, fill="#00FF00")
        
        draw.rectangle([zx, zy, zx+zw, zy+zh], outline="orange", width=line_w + 3)
        draw.text((zx + 8, zy + 8), f"-> {zn} (LADENI)", fill="orange")
        st.image(img_roi, use_container_width=True, caption="Plátno Masteru (Zelená = Uložená ROI, Oranžová = Právě laděný výřez)")