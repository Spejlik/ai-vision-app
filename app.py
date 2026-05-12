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

# --- DYNAMICKÁ MONITOROVACÍ PLOCHA ---
if menu == "🏠 Monitor":
    col_left, col_right = st.columns([4, 1.2])

    with col_left:
        # Získáme všechny ROI pro aktuální kontrolu (např. 4, 6 nebo 8)
        latest_results = database.get_history(limit=8) # Zde limit podle max kapacity obrazovky
        
        if latest_results:
            n_results = len(latest_results)
            
            # STRIKTNÍ LOGIKA MŘÍŽKY:
            # 1-4 inspekce -> 2 sloupce
            # 5-8 inspekcí -> 4 sloupce
            # 9+ inspekcí -> 4 sloupce + zmenšení karet
            n_cols = 2 if n_results <= 4 else 4
            
            cols = st.columns(n_cols)
            
            for i, res in enumerate(latest_results):
                with cols[i % n_cols]:
                    b64_img = logic.get_real_image_base64(res[2], res[4])
                    status_color = "#22c55e" if res[4] == "OK" else "#ef4444"
                    
                    # Předáme dynamickou velikost do stylu (menší pro více karet)
                    card_size = "small" if n_results > 4 else "normal"
                    styles.draw_roi_card(res[2], res[3], res[4], status_color, b64_img, size=card_size)

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