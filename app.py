import streamlit as st
import styles, logic, database

# Nastavení stránky musí být jako první
st.set_page_config(
    page_title="HMI Panel - Kontrola kvality", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Inicializace databáze a aplikace stylů
database.init_db()
styles.apply_custom_css()

# --- SIDEBAR (Administrace a přihlášení) ---
with st.sidebar:
    st.markdown("### 🔐 PŘIHLÁŠENÍ")
    user = st.text_input("Uživatel", value="Operátor 1")
    pin = st.text_input("PIN", type="password")
    
    st.divider()
    
    st.markdown("### 🛠️ MENU")
    menu = st.radio("Navigace", ["🏠 Monitor", "📊 Statistiky", "⚙️ Nastavení"])
    
    st.divider()
    if st.button("Odhlásit se"):
        st.info("Uživatel odhlášen")

# --- HORNÍ LIŠTA (Header) ---
head_col1, head_col2, head_col3 = st.columns([5, 2, 2])

with head_col1:
    # Název produktu s fixní výškou
    st.markdown("<h2 style='margin:0; color:#1e293b; white-space: nowrap;'>🛠️ MQB Skříň ventilátoru L</h2>", unsafe_allow_html=True)

with head_col2:
    # Přepínač režimů
    mode = st.radio("Režim", ["AUTO", "MANUAL"], horizontal=True, label_visibility="collapsed")

with head_col3:
    # Indikátory posledních kontrol (zelené/červené body)
    history_dots = database.get_history(limit=15)
    if history_dots:
        circles = "".join(["🟢" if r[4] == "OK" else "🔴" for r in history_dots])
        st.markdown(f"<div style='font-size:22px; text-align:right;'>{circles}</div>", unsafe_allow_html=True)

st.divider()

# --- HLAVNÍ MONITOROVACÍ PLOCHA ---
if menu == "🏠 Monitor":
    col_left, col_right = st.columns([4, 1.2])

    with col_left:
        # Získání posledních 4 výsledků z databáze
        latest_results = database.get_history(limit=4)
        
        if latest_results:
            # Rozdělení do 2 sloupců (matice 2x2), aby se předešlo rolování
            c1, c2 = st.columns(2)
            for i, res in enumerate(latest_results):
                # i=0,1 jde do c1 | i=2,3 jde do c2
                target_col = c1 if i < 2 else c2
                with target_col:
                    # Získání base64 obrázku z logic.py
                    b64_img = logic.get_real_image_base64(res[2], res[4])
                    # Barva podle statusu
                    status_color = "#22c55e" if res[4] == "OK" else "#ef4444"
                    # Vykreslení karty ze styles.py
                    styles.draw_roi_card(res[2], res[3], res[4], status_color, b64_img)
        else:
            st.info("Čekám na první data z kontroly... Spusťte test tlačítkem START.")

    with col_right:
        # Velký stavový semafor (Celkový výsledek)
        current_status = latest_results[0][4] if latest_results else "WAIT"
        bg_color = "#22c55e" if current_status == "OK" else "#ef4444"
        if current_status == "WAIT": bg_color = "#64748b"

        st.markdown(f"""
            <div style="background:{bg_color}; color:white; padding:40px; border-radius:12px; text-align:center; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <p style="margin:0; opacity:0.8; font-weight:bold;">CELKOVÝ STAV</p>
                <h1 style="font-size:70px; margin:0;">{current_status}</h1>
            </div>
        """, unsafe_allow_html=True)
        
        st.write("") # Mezera
        
        # Ovládání v MANUAL režimu
        if mode == "MANUAL":
            st.markdown("### 🎮 RUČNÍ OVLÁDÁNÍ")
            if st.button("🚀 START INSPEKCE", use_container_width=True, type="primary"):
                # Simulace/Spuštění kontroly pro 4 ROI body
                for roi_name in ["Odtok A", "Zebro B", "Domecek C", "Kolicek D"]:
                    conf, stat, _ = logic.get_ai_prediction(roi_name)
                    # Uložení do databáze
                    database.save_result("MQB L", roi_name, conf, stat, f"img/guma_{stat.lower()}.jpg")
                st.rerun()
        else:
            st.success("🤖 Režim AUTO aktivní")
            st.caption("Čekám na signál z PLC...")

elif menu == "📊 Statistiky":
    st.header("Statistiky výroby")
    all_data = database.get_history(limit=50)
    if all_data:
        st.table(all_data)
    else:
        st.write("Žádná data k dispozici.")

else:
    st.header("Nastavení systému")
    st.write("Zde můžete konfigurovat ROI zóny a prahy citlivosti.")