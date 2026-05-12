import streamlit as st
import styles, logic, database

st.set_page_config(page_title="Lis 1300/7A - Kontrola", layout="wide")
database.init_db()
styles.apply_custom_css()

# --- SIDEBAR (Přihlášení) ---
with st.sidebar:
    st.markdown("### 🔐 Přihlášení")
    user = st.text_input("Uživatel", value="Elvac Admin")
    pin = st.text_input("PIN", type="password")
    if st.button("Log In"):
        st.success(f"Přihlášen: {user}")
    
    st.divider()
    menu = st.radio("Navigace", ["🏠 Hlavní obrazovka", "📊 Statistiky", "⚙️ Nastavení"])

# --- HORNÍ LIŠTA (Header) ---
head_col1, head_col2, head_col3 = st.columns([3, 2, 2])
with head_col1:
    st.markdown(f"## 🛠️ MQB Skříň ventilátoru L")
with head_col2:
    # Přepínač AUTO/MANUAL
    mode = st.segmented_control(
        "Režim stroje", ["AUTO", "MANUAL"], default="MANUAL"
    )
with head_col3:
    # Grafické znázornění posledních kontrol (indikátory nahoře)
    history = database.get_history(limit=20)
    if history:
        # Vytvoříme řadu malých barevných čtverečků
        circles = "".join(["🟢" if r[4] == "OK" else "🔴" for r in history])
        st.markdown(f"**Poslední výsledky:**\n\n{circles}")

st.divider()

# --- HLAVNÍ OBSAH ---
if menu == "🏠 Hlavní obrazovka":
    col_main, col_info = st.columns([4, 1.5])
    
    with col_main:
        # Tlačítko pro manuální test (jen v MANUAL režimu)
        if mode == "MANUAL":
            if st.button("🚀 SPUSTIT INSPECKE"):
                # Tady proběhne tvá OpenCV logika
                for name in ["Odtok", "Žebro", "Domeček", "Kolíček"]:
                    conf, status, color = logic.get_ai_prediction(name)
                    database.save_result("MQB L", name, conf, status, f"img/guma_{status.lower()}.jpg")
                st.rerun()

        # Zobrazení karet ROI (Dlaždice jako na tvé předloze)
        latest_results = database.get_history(limit=4)
        if latest_results:
            cols = st.columns(2) # 2x2 matice
            for i, res in enumerate(latest_results):
                with cols[i % 2]:
                    b64 = logic.get_real_image_base64(res[2], res[4])
                    styles.draw_roi_card(res[2], res[3], res[4], "#44ff44" if res[4]=="OK" else "#ff4444", b64)
    
    with col_info:
        # Velký stavový indikátor
        last_status = latest_results[0][4] if latest_results else "WAIT"
        st.markdown(f"""
            <div style="background:#1A1C24; padding:40px; border-radius:15px; text-align:center; border: 2px solid {'#44ff44' if last_status == 'OK' else '#ff4444'}">
                <h1 style="color:{'#44ff44' if last_status == 'OK' else '#ff4444'}; font-size: 80px;">{last_status}</h1>
                <p>Výsledky inspekce - kompletní</p>
            </div>
        """, unsafe_allow_html=True)

else:
    st.write("Sekce ve výstavbě...")