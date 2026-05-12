import streamlit as st
import styles, logic, database
import time

# 1. Nastavení stránky (Musí být jako první řádek kódu)
st.set_page_config(
    page_title="Lis 1300/7A - Kontrola", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# 2. Inicializace databáze a aplikace CSS stylů
database.init_db()
styles.apply_custom_css()

# --- SIDEBAR (Levý panel) ---
with st.sidebar:
    st.markdown("### 🔐 PŘIHLÁŠENÍ")
    user = st.text_input("Uživatel", value="Elvac Admin")
    pin = st.text_input("PIN", type="password")
    
    st.divider()
    
    st.markdown("### 🛠️ MENU")
    menu = st.radio("Navigace", ["🏠 Monitor", "🧠 Učení a Trénink", "📂 Historie inspekcí", "⚙️ Nastavení"])
    
    st.divider()
    if st.button("Odhlásit se"):
        st.info("Uživatel odhlášen")

# --- HORNÍ LIŠTA (Header) ---
head_col1, head_col2, head_col3 = st.columns([4, 2, 3])

with head_col1:
    st.markdown("<h3 style='margin:0; color:#1e293b; white-space: nowrap;'>🛠️ MQB Skříň ventilátoru L</h3>", unsafe_allow_html=True)

with head_col2:
    mode = st.radio("Režim", ["AUTO", "MANUAL"], horizontal=True, label_visibility="collapsed")

with head_col3:
    cycles = database.get_last_cycles(limit=15)
    if cycles:
        dots_html = "".join([f'<span style="color:{"#22c55e" if c[2]=="OK" else "#ef4444"};">●</span>' for c in cycles])
        st.markdown(f'<div class="dots-container">{dots_html}</div>', unsafe_allow_html=True)

st.divider()

# --- HLAVNÍ LOGIKA PŘEPÍNÁNÍ STRÁNEK ---

if menu == "🏠 Monitor":
    col_left, col_right = st.columns([4, 1.2])

    with col_left:
        latest_results = database.get_history(limit=8)
        if latest_results:
            n_results = len(latest_results)
            n_cols = 2 if n_results <= 4 else 4
            cols = st.columns(n_cols)
            for i, res in enumerate(latest_results):
                with cols[i % n_cols]:
                    b64_img = logic.get_real_image_base64(res[4], res[6])
                    status_color = "#22c55e" if res[6] == "OK" else "#ef4444"
                    styles.draw_roi_card(
                        name=res[4],
                        confidence=res[5],
                        status=res[6],
                        color=status_color,
                        img_path=b64_img,
                        size="small" if n_results > 4 else "normal"
                    )
        else:
            st.info("Systém připraven. Spusťte kontrolu tlačítkem START.")

    with col_right:
        cycles_for_status = database.get_last_cycles(limit=1)
        current_status = cycles_for_status[0][2] if cycles_for_status else "WAIT"
        bg_color = "#22c55e" if current_status == "OK" else "#ef4444"
        if current_status == "WAIT": bg_color = "#64748b"

        st.markdown(f"""
            <div style="background:{bg_color}; color:white; padding:25px; border-radius:12px; text-align:center;">
                <p style="margin:0; opacity:0.8; font-weight:bold; font-size:12px;">CELKOVÝ STAV</p>
                <h1 style="font-size:60px; margin:0;">{current_status}</h1>
            </div>
        """, unsafe_allow_html=True)

        if mode == "MANUAL":
            st.write("")
            st.markdown("### 🎮 OVLÁDÁNÍ")
            if st.button("🚀 START INSPEKCE", use_container_width=True, type="primary"):
                current_cycle = str(int(time.time()))
                seznam_roi = ["Kolicek D", "Domecek C", "Zebro B", "Odtok A"]
                for name in seznam_roi:
                    conf, stat, _ = logic.get_ai_prediction(name)
                    database.save_result(current_cycle, "MQB L", name, conf, stat, f"img/guma_{stat.lower()}.jpg")
                st.rerun()
        else:
            st.success("🤖 AUTO REŽIM")

elif menu == "🧠 Učení a Trénink":
    st.markdown("## 🧠 Správa učících dat")
    tab1, tab2, tab3 = st.tabs(["🔄 Z cyklu", "🛠️ Ze seřízení (Master)", "📤 Import testů"])

    with tab1:
        st.subheader("Příprava trénovací sady")
        # Zobrazení nahrané/vybrané NOK fotky
        if st.button("⚖️ Vyvážit dataset (1x NOK -> 10x NOK)"):
            # 1. Vezmeme tu jednu NOK fotku
            # 2. Spustíme logic.augment_image(img, count=10)
            # 3. Uložíme do training_data/NOK/
            st.success("Dataset vyvážen. Nyní máte 10 variant chyby pro učení.")

    with tab2:
        st.subheader("Manuální focení a nastavení")
        if st.button("📸 VYFOTIT A ULOŽIT JAKO VZOR"):
            st.success("Snímek ze seřízení uložen do složky /setup.")

    with tab3:
        st.subheader("Import externích fotek")
        st.caption("Pro testování dat z jiných lisů nebo starších sérií.")
        upl = st.file_uploader("Vyberte soubory", accept_multiple_files=True)
        if upl:
            import os
            for file in upl:
                # Cesta, kam se soubor uloží
                save_path = os.path.join("training_data", "external", file.name)
                # Zápis souboru na disk
                with open(save_path, "wb") as f:
                    f.write(file.getbuffer())
            st.success(f"✅ Úspěšně uloženo {len(upl)} souborů do training_data/external/")

elif menu == "📂 Historie inspekcí":
    st.markdown("## 📂 Historie inspekcí")
    # Zde zavolej svou funkci pro zobrazení historie
    cycles_hist = database.get_last_cycles(limit=12)
    if cycles_hist:
        st.write("Seznam posledních cyklů nalezen.")
        # Tady můžeš pokračovat kódem pro mřížku historie

elif menu == "⚙️ Nastavení":
    st.header("⚙️ Nastavení systému")
    st.write("Konfigurace ROI a limitů.")