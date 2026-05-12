import streamlit as st
import styles
import logic
import database

st.set_page_config(page_title="AI Vision Hunter", layout="wide")
database.init_db()
styles.apply_custom_css()

# SIDEBAR
with st.sidebar:
    st.markdown("<h2 style='text-align:center;'>👁️ AI Vision</h2>", unsafe_allow_html=True)
    st.divider()
    menu = st.radio("Navigace", ["📷 Monitor", "📂 Historie"])
    st.divider()
    projekt = st.selectbox("Produkt", ["361 MEB Housing"])

# OBSAH
if menu == "📷 Monitor":
    col_main, col_status = st.columns([4, 1.2])

    with col_main:
        st.write(f"### Aktivní projekt: {projekt}")
        
        if st.button("🚀 Spustit novou kontrolu"):
            rois = ["Konektor", "Zobáček P1", "Zobáček P2", "Zámek"]
            for name in rois:
                conf, status, color = logic.get_ai_prediction(name)
                # Uložíme cestu (v DB necháme cestu, v náhledu base64)
                img_path = f"img/{name}_{status}.jpg" # zjednodušeno pro DB
                database.save_result(projekt, name, conf, status, img_path)
            st.rerun()

        # ZOBRAZENÍ KARET
        cols = st.columns(4)
        history = database.get_history(limit=4)
        if history:
            for i, record in enumerate(reversed(history)):
                with cols[i % 4]:
                    # record: (timestamp, projekt, roi_name, confidence, status, img_path)
                    b64_img = logic.get_real_image_base64(record[2], record[4])
                    color = "#44ff44" if record[4] == "OK" else "#ff4444"
                    styles.draw_roi_card(record[2], record[3], record[4], color, b64_img)

    with col_status:
        st.markdown(f"""
            <div style="background-color: #1A1C24; padding: 20px; border-radius: 12px; border-left: 4px solid #38bdf8; margin-top: 50px;">
                <h4 style="margin-top:0;">🔄 Průběh cyklu</h4>
                <p>✅ <b>Pozice 1</b>: OK</p>
                <p style="color:#38bdf8;">🔵 <b>Pozice 2</b>: Active</p>
                <div style="background-color:#000; border-radius:10px; height:8px; width:100%;">
                    <div style="background-color:#38bdf8; width:65%; height:8px; border-radius:10px;"></div>
                </div>
                <hr style="opacity:0.1;">
                <small>Cycle Time</small><br><b>4.2s</b>
            </div>
        """, unsafe_allow_html=True)

else:
    st.write("### 📂 Historie")
    # Zde můžete nechat tabulku nebo upravit náhledy