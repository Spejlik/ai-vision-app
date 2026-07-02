import streamlit as st
import database
import time
from PIL import Image, ImageDraw

def render_roi_tab(m_id, m_name, m_path, active_p, current_position):
    """
    Stabilní průmyslový modul pro správu ROI bez zacyklení sliderů.
    """
    img_roi = Image.open(m_path).convert("RGB")
    W, H = img_roi.size

    # Načtení reálných dat z SQL
    all_rois = database.get_rois(m_id, active_p, current_position)
    seznam_roi_v_db = [str(r[3]).strip() for r in all_rois] if all_rois else []
    moznosti_selectboxu = seznam_roi_v_db + ["➕ Přidat nové ROI"]

    # 1. Hlídání změny vybrané položky (aby se slidery nepřepisovaly při pohybu)
    if "last_selected_roi" not in st.session_state:
        st.session_state["last_selected_roi"] = moznosti_selectboxu[0]

    vybrany_u = st.selectbox(
        "🎯 Vyberte ROI k úpravě polohy nebo založte nové:",
        options=moznosti_selectboxu,
        index=moznosti_selectboxu.index(st.session_state["last_selected_roi"]),
        key="roi_selector_core"
    )

    # 2. Jednorázový přepínač hodnot POUZE při změně selectboxu nebo při prvním startu
    if (vybrany_u != st.session_state["last_selected_roi"]) or ("roi_initialized" not in st.session_state):
        st.session_state["last_selected_roi"] = vybrany_u
        st.session_state["roi_initialized"] = True
        
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

    # Najdeme ID pro případné smazání/úpravu
    roi_id_db = None
    if vybrany_u != "➕ Přidat nové ROI":
        found = next((r for r in all_rois if str(r[3]).strip() == vybrany_u), None)
        if found:
            roi_id_db = found[0]

    # --- ROZHRANÍ PRO OVLÁDÁNÍ ---
    c_ctrl, c_viz = st.columns([1, 1.8])
    
    with c_ctrl:
        st.markdown(f"### 🔧 Správa: {m_name.split('#')[0]}")
        
        # Ovládací prvky navázané na stabilní vnitřní stav
        zn = st.text_input("📝 Název ROI:", key="val_roi_name").strip()
        nok_val = st.selectbox("Přiřazení chyby lisu (NOK 1-8)", range(1, 9), index=int(st.session_state.get("val_roi_nok", 1)) - 1, key="val_roi_nok_select")
        
        zx = st.slider("X poloha", 0, W, key="val_roi_x")
        zy = st.slider("Y poloha", 0, H, key="val_roi_y")
        zw = st.slider("Šířka", 10, W, key="val_roi_w")
        zh = st.slider("Výška", 10, H, key="val_roi_h")
        ztol = st.slider("Tolerance odchylky AI", 1, 100, key="val_roi_tol")

        # Tlačítka pro akce
        b_col1, b_col2 = st.columns(2)
        with b_col1:
            if st.button("💾 ULOŽIT / UPRAVIT", type="primary", use_container_width=True):
                if not zn:
                    st.error("❌ Název nesmí být prázdný!")
                else:
                    try:
                        # Pokud upravujeme vybrané, odstraníme starý záznam
                        if vybrany_u != "➕ Přidat nové ROI" and roi_id_db is not None:
                            database.delete_roi(roi_id_db)
                        else:
                            # Pojistka proti duplicitnímu jménu při zakládání nového
                            duplicitni = next((r for r in all_rois if str(r[3]).strip() == zn), None)
                            if duplicitni: database.delete_roi(duplicitni[0])
                        
                        database.save_roi(m_id, active_p, zn, int(zx), int(zy), int(zw), int(zh), int(nok_val), int(ztol), current_position)
                        st.session_state["last_selected_roi"] = zn
                        st.toast(f"✅ ROI {zn} uloženo!", icon="💾")
                        time.sleep(0.2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Chyba: {e}")
                        
        with b_col2:
            if st.button("🗑️ SMAZAT TOTO ROI", type="secondary", use_container_width=True):
                if vybrany_u != "➕ Přidat nové ROI" and roi_id_db is not None:
                    database.delete_roi(roi_id_db)
                    st.session_state["last_selected_roi"] = "➕ Přidat nové ROI"
                    st.toast("🗑️ ROI smazáno!")
                    time.sleep(0.2)
                    st.rerun()

    with c_viz:
        draw = ImageDraw.Draw(img_roi)
        line_w = max(2, int(W * 0.005))
        
        # Vykreslení všech ostaních uložených zón zeleně
        if all_rois:
            for r in all_rois:
                r_name = str(r[3]).strip()
                if r_name != vybrany_u:
                    rx, ry, rw, rh = int(r[4]), int(r[5]), int(r[6]), int(r[7])
                    draw.rectangle([rx, ry, rx+rw, ry+rh], outline="#00FF00", width=line_w)
                    draw.text((rx + 6, ry + 6), r_name, fill="#00FF00")
        
        # Vykreslení aktivně laděné zóny (oranžová / žlutá)
        draw.rectangle([zx, zy, zx+zw, zy+zh], outline="orange", width=line_w + 2)
        draw.text((zx + 6, zy + 6), f"✏️ {zn} (AKTIVNÍ)", fill="orange")
        
        st.image(img_roi, use_container_width=True, caption="Zelená = Uložená ROI, Oranžová = Aktuálně ovládané souřadnice pomocí sliderů")