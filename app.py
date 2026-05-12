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
    # Změna poměru na 75% : 25%
    col_left, col_right = st.columns([3, 1])

    with col_left:
        latest_results = database.get_history(limit=4)
        if latest_results:
            # Matice 2x2 pomocí vnořených sloupců
            row1_col1, row1_col2 = st.columns(2)
            row2_col1, row2_col2 = st.columns(2)
            
            # Mapování výsledků do buněk
            slots = [row1_col1, row1_col2, row2_col1, row2_col2]
            
            for i, res in enumerate(latest_results):
                with slots[i]:
                    b64_img = logic.get_real_image_base64(res[2], res[4])
                    status_color = "#22c55e" if res[4] == "OK" else "#ef4444"
                    styles.draw_roi_card(res[2], res[3], res[4], status_color, b64_img)

    with col_right:
        # Kompaktní stavový box
        current_status = latest_results[0][4] if latest_results else "WAIT"
        bg_color = "#22c55e" if current_status == "OK" else "#ef4444"
        
        st.markdown(f"""
            <div style="background:{bg_color}; color:white; padding:20px; border-radius:10px; text-align:center;">
                <h1 style="font-size:45px; margin:0;">{current_status}</h1>
                <p style="margin:0; font-size:12px;">STATUS</p>
            </div>
        """, unsafe_allow_html=True)
        
        # Ovládání (v MANUAL režimu)
        if mode == "MANUAL":
            st.write("")
            if st.button("🚀 START", use_container_width=True):
                # Tady volání tvé logiky
                st.rerun()

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