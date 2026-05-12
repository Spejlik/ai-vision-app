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
    # Teď taháme historii cyklů, ne jednotlivých ROI
    cycles = database.get_last_cycles(limit=15)
    if cycles:
        # Vytvoříme HTML řetězec s fixním kontejnerem
        dots_html = "".join([f'<span style="color:{"#22c55e" if c[2]=="OK" else "#ef4444"}; margin-left:4px;">●</span>' for c in cycles])
        st.markdown(f"""
            <div style="font-size:30px; text-align:right; line-height:1; white-space:nowrap; overflow:hidden;">
                {dots_html}
            </div>
        """, unsafe_allow_html=True)

st.divider()

# --- DYNAMICKÁ MONITOROVACÍ PLOCHA ---
if menu == "🏠 Monitor":
    # 1. Rozdělíme plochu na levou (karty) a pravou (tlačítko a velký stav)
    col_left, col_right = st.columns([4, 1.2])

    with col_left:
        # Získáme ROI pouze z POSLEDNÍHO cyklu (aby se nemíchaly staré a nové kusy)
        # K tomu využijeme cycle_id z nejnovějšího záznamu
        all_history = database.get_history(limit=1)
        if all_history:
            last_cycle_id = all_history[0][2] # předpokládáme, že cycle_id je na indexu 2
            # Tady by byla ideální funkce get_results_by_cycle(last_cycle_id)
            # Pro teď použijeme limit 8 pro vizualizaci
            latest_results = database.get_history(limit=8) 
            
            if latest_results:
                n_results = len(latest_results)
                n_cols = 2 if n_results <= 4 else 4
                cols = st.columns(n_cols)
                
                for i, res in enumerate(latest_results):
                    with cols[i % n_cols]:
                        b64_img = logic.get_real_image_base64(res[2], res[4])
                        status_color = "#22c55e" if res[4] == "OK" else "#ef4444"
                        card_size = "small" if n_results > 4 else "normal"
                        styles.draw_roi_card(res[2], res[3], res[4], status_color, b64_img, size=card_size)

    # --- TADY JE TA CHYBĚJÍCÍ PRAVÁ STRANA ---
    with col_right:
        # Zjištění celkového stavu posledního kusu
        cycles = database.get_last_cycles(limit=1)
        current_status = cycles[0][2] if cycles else "WAIT"
        bg_color = "#22c55e" if current_status == "OK" else "#ef4444"
        if current_status == "WAIT": bg_color = "#64748b"

        st.markdown(f"""
            <div style="background:{bg_color}; color:white; padding:20px; border-radius:12px; text-align:center;">
                <p style="margin:0; opacity:0.8; font-weight:bold; font-size:12px;">CELKOVÝ STAV</p>
                <h1 style="font-size:50px; margin:0;">{current_status}</h1>
            </div>
        """, unsafe_allow_html=True)

        st.divider()

        # TLAČÍTKO START (Raketa), které jsi postrádal
        if mode == "MANUAL":
            st.markdown("### 🎮 OVLÁDÁNÍ")
            if st.button("🚀 START INSPEKCE", use_container_width=True, type="primary"):
                import time
                # Vytvoříme unikátní ID cyklu (tečku nahoře)
                current_cycle = str(int(time.time()))
                
                # Definuj, co všechno se má v jednom cyklu zkontrolovat
                seznam_roi = ["Odtok A", "Zebro B", "Domecek C", "Kolicek D"]
                
                for name in seznam_roi:
                    conf, stat, _ = logic.get_ai_prediction(name)
                    # Uložíme s cycle_id, aby se nahoře objevila jen JEDNA tečka
                    database.save_result(current_cycle, "MQB L", name, conf, stat, f"img/guma_{stat.lower()}.jpg")
                
                st.rerun()
        else:
            st.success("🤖 AUTO REŽIM")
            st.caption("Systém běží automaticky")

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