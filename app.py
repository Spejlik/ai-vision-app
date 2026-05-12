import streamlit as st
import styles, logic, database

st.set_page_config(page_title="AI Vision Hunter", layout="wide")
database.init_db()
st.write("### 👁️ Monitorovací systém")
styles.apply_custom_css()

with st.sidebar:
    st.markdown("## 👁️ AI Vision")
    menu = st.radio("Navigace", ["📷 Monitor", "📂 Historie"])
    projekt = st.selectbox("Produkt", ["361 MEB Housing"])

if menu == "📷 Monitor":
    col_main, col_status = st.columns([4, 1.2])
    with col_main:
        st.write(f"### Projekt: {projekt}")
        if st.button("🚀 Spustit novou kontrolu"):
            for name in ["Konektor", "Zobáček P1", "Zobáček P2", "Zámek"]:
                conf, status, color = logic.get_ai_prediction(name)
                img_path = f"img/guma_{status.lower()}.jpg"
                database.save_result(projekt, name, conf, status, img_path)
            st.rerun()

        cols = st.columns(4)
        history = database.get_history(limit=4)
        if history:
            for i, record in enumerate(reversed(history)):
                with cols[i % 4]:
                    b64 = logic.get_real_image_base64(record[2], record[4])
                    color = "#44ff44" if record[4] == "OK" else "#ff4444"
                    styles.draw_roi_card(record[2], record[3], record[4], color, b64)
        else:
            st.info("Spusťte kontrolu raketou.")

    with col_status:
        st.markdown('<div style="background:#1A1C24;padding:20px;border-radius:12px;border-left:4px solid #38bdf8;margin-top:50px;"><h4>🔄 Průběh</h4><p>✅ Pozice 1</p><p style="color:#38bdf8;">🔵 Pozice 2</p><div style="background:#000;height:8px;width:100%;border-radius:10px;"><div style="background:#38bdf8;width:65%;height:8px;border-radius:10px;"></div></div><hr style="opacity:0.1;"><b>Cycle: 4.2s</b></div>', unsafe_allow_html=True)
else:
    st.write("### 📂 Historie")
    st.table(database.get_history(limit=20))