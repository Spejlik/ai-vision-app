import streamlit as st
import database
import time
from PIL import Image, ImageDraw

def render_roi_tab(m_id, m_name, m_path, active_p, current_position):
    """
    Stabilní průmyslový ROI modul.
    Zajišťuje bezpečné ukládání, editaci a mazání bez kolizí v session_state.
    """
    img_roi = Image.open(m_path).convert("RGB")
    W, H = img_roi.size

    # 1. Načtení aktuálního fondu zón z SQL
    all_rois = database.get_rois(m_id, active_p, current_position)
    seznam_roi_v_db = [str(r[3]).strip() for r in all_rois] if all_rois else []
    moznosti_selectboxu = seznam_roi_v_db + ["➕ Přidat nové ROI"]

    # 2. Inicializace výchozího stavu volby
    if "last_selected_roi" not in st.session_state:
        if seznam_roi_v_db:
            st.session_state["last_selected_roi"] = seznam_roi_v_db[0]
        else:
            st.session_state["last_selected_roi"] = "➕ Přidat nové ROI"

    if st.session_state["last_selected_roi"] not in moznosti_selectboxu:
        if seznam_roi_v_db:
            st.session_state["last_selected_roi"] = seznam_roi_v_db[0]
        else:
            st.session_state["last_selected_roi"] = "➕ Přidat nové ROI"

    # 3. Bezpečné naplnění hodnot do session_state PŘED vykreslením widgetů
    vybrany_u = st.session_state["last_selected_roi"]
    
    if "val_roi_name" not in st.session_state or st.session_state.get("roi_refresh_trigger", False):
        st.session_state["roi_refresh_trigger"] = False
        if vybrany_u == "➕ Přidat nové ROI":
            st.session_state["val_roi_name"] = f"p1_{len(all_rois) + 1}"
            st.session_state["val_roi_x"] = 100
            st.session_state["val_roi_y"] = 100
            st.session_state["val_roi_w"] = 150
            st.session_state["val_roi_h"] = 150
            st.session_state["val_roi_tol"] = 20
            st.session_state["val_roi_nok"] = 1
        else:
            found = next((r for r in all_rois if str(r[3]).strip() == vybrany_u), None)
            if found:
                st.session_state["val_roi_name"] = found[3]
                st.session_state["val_roi_x"] = int(found[4])
                st.session_state["val_roi_y"] = int(found[5])
                st.session_state["val_roi_w"] = int(found[6])
                st.session_state["val_roi_h"] = int(found[7])
                st.session_state["val_roi_nok"] = int(found[8])
                st.session_state["val_roi_tol"] = int(found[9]) if len(found) > 9 else 20

    # 4. CALLBACK: 🍏 Opraveno na dynamický klíč s m_id
    def on_roi_selection_change():
        st.session_state["last_selected_roi"] = st.session_state[f"roi_selector_core_{m_id}"]
        st.session_state["roi_refresh_trigger"] = True

    # 🍏 KOREKCE: Výpočet chybějícího indexu před selectboxem
    idx_selectboxu = moznosti_selectboxu.index(st.session_state["last_selected_roi"])

    # Rozbalovací selektor
    st.selectbox(
        "🎯 Vyberte ROI k úpravě polohy nebo založte nové:",
        options=moznosti_selectboxu,
        index=idx_selectboxu,
        key=f"roi_selector_core_{m_id}",  
        on_change=on_roi_selection_change
    )

    # Načtení ID z databáze pro vybranou zónu
    roi_id_db = None
    if vybrany_u != "➕ Přidat nové ROI":
        found = next((r for r in all_rois if str(r[3]).strip() == vybrany_u), None)
        if found: roi_id_db = found[0]

    # --- ROZHRANÍ OVLÁDÁNÍ ---
    c_ctrl, c_viz = st.columns([1, 1.8])
    
    with c_ctrl:
        st.markdown(f"### 🔧 Správa: {m_name.split('#')[0]}")
        
        # Pevné navázání prvků na předpřipravený session_state
        zn = st.text_input("📝 Název ROI:", key="val_roi_name").strip()
        nok_val = st.selectbox("Přiřazení chyby lisu (NOK 1-8)", range(1, 9), index=int(st.session_state.get("val_roi_nok", 1)) - 1, key="val_roi_nok_select")
        
        zx = st.slider("X poloha", 0, W, key="val_roi_x")
        zy = st.slider("Y poloha", 0, H, key="val_roi_y")
        zw = st.slider("Šířka", 10, W, key="val_roi_w")
        zh = st.slider("Výška", 10, H, key="val_roi_h")
        ztol = st.slider("Tolerance odchylky AI", 1, 100, key="val_roi_tol")

        st.write("")
        b_col1, b_col2 = st.columns(2)
        
        with b_col1:
            if st.button("💾 ULOŽIT / UPRAVIT", type="primary", use_container_width=True, key="save_roi_btn_final_fix"):
                if not zn:
                    st.error("❌ Název nesmí být prázdný!")
                else:
                    try:
                        # Odmazání staré verze z DB při editaci
                        if vybrany_u != "➕ Přidat nové ROI" and roi_id_db is not None:
                            database.delete_roi(roi_id_db)
                        else:
                            duplicitni = next((r for r in all_rois if str(r[3]).strip() == zn), None)
                            if duplicitni: database.delete_roi(duplicitni[0])
                        
                        # Zápis do SQLite
                        database.save_roi(m_id, active_p, zn, int(zx), int(zy), int(zw), int(zh), int(nok_val), int(ztol), current_position)
                        
                        # Zafixujeme stav na uložené zóně a vynutíme bezpečné přeladění hodnot
                        st.session_state["last_selected_roi"] = zn
                        st.session_state["roi_refresh_trigger"] = True
                        
                        st.toast(f"✅ ROI {zn} úspěšně uloženo!", icon="💾")
                        time.sleep(0.1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Chyba zápisu: {e}")
                        
        with b_col2:
            if st.button("🗑️ SMAZAT TOTO ROI", type="secondary", use_container_width=True, key="delete_roi_btn_final_fix"):
                if vybrany_u != "➕ Přidat nové ROI" and roi_id_db is not None:
                    try:
                        # Smazání z databáze
                        database.delete_roi(roi_id_db)
                        
                        # 🍏 BEZPEČNÝ RESET: Vyčistíme staré klíče z paměti dřív, než Streamlit stihne protestovat
                        for k in ["val_roi_name", "val_roi_x", "val_roi_y", "val_roi_w", "val_roi_h", "val_roi_nok", "val_roi_tol"]:
                            if k in st.session_state: del st.session_state[k]
                        
                        # Přepneme zobrazení na výchozí bod
                        st.session_state["last_selected_roi"] = "➕ Přidat nové ROI"
                        st.session_state["roi_refresh_trigger"] = True
                        
                        st.toast("🗑️ ROI vymazáno z databáze!", icon="🗑️")
                        time.sleep(0.1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Chyba smazání: {e}")

    with c_viz:
        draw = ImageDraw.Draw(img_roi)
        line_w = max(2, int(W * 0.005))
        
        # Vykreslení všech uložených zón z SQL zeleně
        if all_rois:
            for r in all_rois:
                r_name = str(r[3]).strip()
                if r_name != vybrany_u:
                    rx, ry, rw, rh = int(r[4]), int(r[5]), int(r[6]), int(r[7])
                    draw.rectangle([rx, ry, rx+rw, ry+rh], outline="#00FF00", width=line_w)
                    draw.text((rx + 6, ry + 6), r_name, fill="#00FF00")
        
        # Vykreslení aktivně ovládané zóny oranžově
        draw.rectangle([zx, zy, zx+zw, zy+zh], outline="orange", width=line_w + 2)
        draw.text((zx + 6, zy + 6), f"✏️ {zn} (AKTIVNÍ)", fill="orange")
        
        st.image(img_roi, use_container_width=True, caption="Zelená = Uložená zóna v SQL, Oranžová = Aktuálně upravovaný výřez")