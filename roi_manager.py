import streamlit as st
import database
import time
from PIL import Image, ImageDraw

def render_roi_tab(m_id, m_name, m_path, active_p, current_position):
    """
    Průmyslový ROI modul s fixovanou pamětí stavů proti samovolnému generování nových zón.
    """
    img_roi = Image.open(m_path).convert("RGB")
    W, H = img_roi.size

    # 1. Načtení aktuálního fondu zón z SQL
    all_rois = database.get_rois(m_id, active_p, current_position)
    seznam_roi_v_db = [str(r[3]).strip() for r in all_rois] if all_rois else []
    moznosti_selectboxu = seznam_roi_v_db + ["➕ Přidat nové ROI"]

    # 2. Bezpečná inicializace výchozího stavu v mezipaměti (spustí se jen jednou při startu projektu)
    if "last_selected_roi" not in st.session_state:
        st.session_state["last_selected_roi"] = moznosti_selectboxu[0]
        
    if "val_roi_name" not in st.session_state:
        if st.session_state["last_selected_roi"] == "➕ Přidat nové ROI":
            st.session_state["val_roi_name"] = f"p1_{len(all_rois) + 1}"
            st.session_state["val_roi_x"], st.session_state["val_roi_y"] = 100, 100
            st.session_state["val_roi_w"], st.session_state["val_roi_h"] = 150, 150
            st.session_state["val_roi_tol"] = 20
            st.session_state["val_roi_nok"] = 1
        else:
            found = next((r for r in all_rois if str(r[3]).strip() == st.session_state["last_selected_roi"]), None)
            if found:
                st.session_state["val_roi_name"] = found[3]
                st.session_state["val_roi_x"] = int(found[4])
                st.session_state["val_roi_y"] = int(found[5])
                st.session_state["val_roi_w"] = int(found[6])
                st.session_state["val_roi_h"] = int(found[7])
                st.session_state["val_roi_nok"] = int(found[8])
                st.session_state["val_roi_tol"] = int(found[9]) if len(found) > 9 else 20

    # 3. 🍏 CALLBACK: Spustí se výhradně a pouze tehdy, když technik fyzicky změní volbu v Selectboxu
    def on_roi_selection_change():
        novy_vyber = st.session_state["roi_selector_core"]
        st.session_state["last_selected_roi"] = novy_vyber
        
        if novy_vyber == "➕ Přidat nové ROI":
            st.session_state["val_roi_name"] = f"p1_{len(all_rois) + 1}"
            st.session_state["val_roi_x"] = 100
            st.session_state["val_roi_y"] = 100
            st.session_state["val_roi_w"] = 150
            st.session_state["val_roi_h"] = 150
            st.session_state["val_roi_tol"] = 20
            st.session_state["val_roi_nok"] = 1
        else:
            # Načteme čistá data z databáze do sliderů pro editaci
            found = next((r for r in all_rois if str(r[3]).strip() == novy_vyber), None)
            if found:
                st.session_state["val_roi_name"] = found[3]
                st.session_state["val_roi_x"] = int(found[4])
                st.session_state["val_roi_y"] = int(found[5])
                st.session_state["val_roi_w"] = int(found[6])
                st.session_state["val_roi_h"] = int(found[7])
                st.session_state["val_roi_nok"] = int(found[8])
                st.session_state["val_roi_tol"] = int(found[9]) if len(found) > 9 else 20

    # Ošetření indexu pro bezpečné zobrazení
    if st.session_state["last_selected_roi"] not in moznosti_selectboxu:
        st.session_state["last_selected_roi"] = moznosti_selectboxu[0]
    idx_selectboxu = moznosti_selectboxu.index(st.session_state["last_selected_roi"])

    # Samotný selektor s navázaným callbackem
    vybrany_u = st.selectbox(
        "🎯 Vyberte ROI k úpravě polohy nebo založte nové:",
        options=moznosti_selectboxu,
        index=idx_selectboxu,
        key="roi_selector_core",
        on_change=on_roi_selection_change
    )

    # Získání reálného ID z DB
    roi_id_db = None
    if vybrany_u != "➕ Přidat nové ROI":
        found = next((r for r in all_rois if str(r[3]).strip() == vybrany_u), None)
        if found: roi_id_db = found[0]

    # --- ROZHRANÍ OVLÁDÁNÍ ---
    c_ctrl, c_viz = st.columns([1, 1.8])
    
    with c_ctrl:
        st.markdown(f"### 🔧 Správa: {m_name.split('#')[0]}")
        
        # Prvky pevně svázané se stabilním vnitřním stavem v RAM
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
                        # Pokud šlo o editaci existujícího, odmažeme předchozí souřadnice z DB
                        if vybrany_u != "➕ Přidat nové ROI" and roi_id_db is not None:
                            database.delete_roi(roi_id_db)
                        else:
                            duplicitni = next((r for r in all_rois if str(r[3]).strip() == zn), None)
                            if duplicitni: database.delete_roi(duplicitni[0])
                        
                        # Ostrý zápis do SQL
                        database.save_roi(m_id, active_p, zn, int(zx), int(zy), int(zw), int(zh), int(nok_val), int(ztol), current_position)
                        
                        # 🍏 KLÍČOVÝ FIX: Uzamkneme volbu natvrdo na uložený název a zamezíme samovolné inicializaci nového
                        st.session_state["last_selected_roi"] = zn
                        
                        st.toast(f"✅ ROI {zn} úspěšně zafixováno v SQL!", icon="💾")
                        time.sleep(0.1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Chyba zápisu: {e}")
                        
        with b_col2:
            if st.button("🗑️ SMAZAT TOTO ROI", type="secondary", use_container_width=True, key="delete_roi_btn_final_fix"):
                if vybrany_u != "➕ Přidat nové ROI" and roi_id_db is not None:
                    try:
                        database.delete_roi(roi_id_db)
                        st.session_state["last_selected_roi"] = "➕ Přidat nové ROI"
                        # Reset hodnot sliderů na default po smazání zóny
                        st.session_state["val_roi_name"] = f"p1_{len(all_rois)}"
                        st.session_state["val_roi_x"], st.session_state["val_roi_y"] = 100, 100
                        st.session_state["val_roi_w"], st.session_state["val_roi_h"] = 150, 150
                        st.session_state["val_roi_tol"] = 20
                        
                        st.toast("🗑️ ROI vymazáno z databáze!", icon="🗑️")
                        time.sleep(0.1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Chyba smazání: {e}")

    with c_viz:
        draw = ImageDraw.Draw(img_roi)
        line_w = max(2, int(W * 0.005))
        
        # Vykreslení všech ostaních uložených zón z SQL zeleně
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