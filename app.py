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
    # Tady definujeme JEDNU navigaci se správným názvem
    menu = st.radio("Navigace", ["🏠 Monitor", "🧠 Učení a Trénink", "📂 Historie inspekcí", "⚙️ Nastavení"])
    
    st.divider()
    if st.button("Odhlásit se"):
        st.info("Uživatel odhlášen")

# --- HORNÍ LIŠTA (Header) ---
head_col1, head_col2, head_col3 = st.columns([4, 2, 3])

with head_col1:
    # Název projektu - bílá barva a zákaz zalomení
    st.markdown("<h3 style='margin:0; color:#1e293b; white-space: nowrap;'>🛠️ MQB Skříň ventilátoru L</h3>", unsafe_allow_html=True)

with head_col2:
    # Přepínač AUTO/MANUAL
    mode = st.radio("Režim", ["AUTO", "MANUAL"], horizontal=True, label_visibility="collapsed")

with head_col3:
    # Zobrazení teček jako CELÝCH CYKLŮ (z database.get_last_cycles)
    cycles = database.get_last_cycles(limit=15)
    if cycles:
        # Používáme CSS třídu dots-container ze styles.py
        dots_html = "".join([f'<span style="color:{"#22c55e" if c[2]=="OK" else "#ef4444"};">●</span>' for c in cycles])
        st.markdown(f'<div class="dots-container">{dots_html}</div>', unsafe_allow_html=True)

st.divider()

# --- HLAVNÍ PLOCHA MONITORU ---
if menu == "🏠 Monitor":
    col_left, col_right = st.columns([4, 1.2])

    with col_left:
        # Načteme historii pro zobrazení karet (ROI)
        latest_results = database.get_history(limit=8)
        
        if latest_results:
            n_results = len(latest_results)
            # Dynamická mřížka: 1-4 karty = 2 sloupce, 5+ karet = 4 sloupce
            n_cols = 2 if n_results <= 4 else 4
            cols = st.columns(n_cols)
            
            for i, res in enumerate(latest_results):
                with cols[i % n_cols]:
                    # Indexy v DB: 4=roi_name, 5=confidence, 6=status
                    b64_img = logic.get_real_image_base64(res[4], res[6])
                    status_color = "#22c55e" if res[6] == "OK" else "#ef4444"
                    
                    # Vykreslení karty přes styles.py
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
        # Velký stavový box (Celkový výsledek posledního kusu)
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

        st.write("") # Mezera

        # Tlačítko pro spuštění inspekce v MANUAL režimu
        if mode == "MANUAL":
            st.markdown("### 🎮 OVLÁDÁNÍ")
            if st.button("🚀 START INSPEKCE", use_container_width=True, type="primary"):
                # Vygenerujeme unikátní ID cyklu pro jednu tečku nahoře
                current_cycle = str(int(time.time()))
                
                # Definice bodů, které chceme zkontrolovat
                seznam_roi = ["Kolicek D", "Domecek C", "Zebro B", "Odtok A"]
                
                for name in seznam_roi:
                    # Získání dat z logiky
                    conf, stat, _ = logic.get_ai_prediction(name)
                    # Uložení do databáze i s cycle_id
                    database.save_result(current_cycle, "MQB L", name, conf, stat, f"img/guma_{stat.lower()}.jpg")
                
                st.rerun()
        else:
            st.success("🤖 AUTO REŽIM")
            st.caption("Čekám na signál z lisu...")

elif menu == "📂 Historie inspekcí":
    st.markdown("<h2 style='color:#1e293b;'>📂 Historie inspekcí</h2>", unsafe_allow_html=True)
    # ... tvůj kód pro historii (get_last_cycles atd.) ...
    
    # 1. Načtení seznamu unikátních cyklů (teček)
    cycles = database.get_last_cycles(limit=12)
    
    if cycles:
        # Vytvoření mřížky 3x4 pro náhledy cyklů
        cols = st.columns(3)
        for i, cyc in enumerate(cycles):
            c_id = cyc[0]      # unikátní ID cyklu
            c_time = cyc[1]    # čas uložení
            c_status = cyc[2]  # celkový stav OK/NOK
            
            with cols[i % 3]:
                color = "#22c55e" if c_status == "OK" else "#ef4444"
                # Rámeček cyklu
                st.markdown(f"""
                    <div style="border: 2px solid {color}; border-radius: 10px; padding: 10px; background: white; margin-bottom:10px;">
                        <p style="margin:0; font-size:11px; color:gray;">{c_time}</p>
                        <b style="color:{color}; font-size:16px;">VÝSLEDEK: {c_status}</b>
                    </div>
                """, unsafe_allow_html=True)
                
                # Tlačítko pro výběr cyklu
                if st.button(f"🔎 Detail {c_id[-4:]}", key=f"btn_{c_id}", use_container_width=True):
                    st.session_state.selected_cycle = c_id

        # 2. ZOBRAZENÍ DETAILU (pokud je vybrán)
        if 'selected_cycle' in st.session_state:
            st.markdown("---")
            st.subheader(f"🔍 Detail měření: {st.session_state.selected_cycle}")
            
            # Načtení dat pro vybraný cyklus
            details = database.get_cycle_details(st.session_state.selected_cycle)
            
            det_col1, det_col2 = st.columns([2, 3])
            
            with det_col1:
                st.write("**Seznam inspekcí:**")
                for d in details:
                    # Indexy: 4=roi_name, 5=confidence, 6=status, 7=image_path
                    roi_name, conf, stat, img_p = d[4], d[5], d[6], d[7]
                    icon = "✅" if stat == "OK" else "❌"
                    
                    # Tlačítko pro zobrazení velké fotky
                    if st.button(f"{icon} {roi_name} ({conf}%)", key=f"roi_{d[0]}", use_container_width=True):
                        st.session_state.view_roi_img = img_p

            with det_col2:
                if 'view_roi_img' in st.session_state:
                    st.write("**Snímek z kamery:**")
                    # Zobrazení uložené fotky z cesty v DB
                    st.image(st.session_state.view_roi_img, use_container_width=True)
                else:
                    st.info("Zvolte inspekci vlevo pro náhled fotky.")
    else:
        st.warning("V databázi zatím nejsou žádné záznamy.")

else:
    st.header("Nastavení systému")
    st.write("Konfigurace ROI zón a limitů.")
    
elif menu == "🧠 Učení a Trénink":
    st.title("🧠 Správa učících dat")
    
    tab1, tab2, tab3 = st.tabs(["🔄 Data z cyklu", "🛠️ Data ze seřízení", "📤 Externí import"])

    with tab1:
        st.subheader("Fotky z automatického provozu")
        # Zde zobrazíme poslední fotky z DB a tlačítko "Přidat do učení"
        st.info("Vyberte fotky z historie, které mají sloužit jako vzor (Master).")

    with tab2:
        st.subheader("Manuální focení a nastavení")
        if st.button("📸 VYFOTIT A ULOŽIT JAKO VZOR"):
            # Tady logic.py vyfotí aktuální snímek a uloží ho do složky /setup
            st.success("Snímek uložen do složky pro seřizování.")

    with tab3:
        st.subheader("Import z jiného zařízení")
        uploaded_files = st.file_uploader("Nahrajte fotky (JPG/PNG)", accept_multiple_files=True)
        if uploaded_files:
            for file in uploaded_files:
                # Uložíme do složky /external
                with open(f"training_data/external/{file.name}", "wb") as f:
                    f.write(file.getbuffer())
            st.success(f"Nahráno {len(uploaded_files)} snímků pro testování.")