from PIL import Image
from streamlit_cropper import st_cropper
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
        st.subheader("Data z automatického provozu")
        st.info("Vyberte fotky z historie, které mají sloužit jako vzor (Master).")

    with tab2:
        st.subheader("Manuální focení u lisu")
        st.caption("Slouží pro nastavení ideálních pozic (Master data).")
        if st.button("📸 VYFOTIT AKTUÁLNÍ STAV"):
            # logic.save_setup_image()
            st.success("Snímek ze seřízení uložen.")

    with tab3:
        st.subheader("Import a Anotace externích fotek")
        upl = st.file_uploader("Nahrajte nové soubory", accept_multiple_files=True, key="uploader")
        
        # Logika uložení na disk
        if upl:
            import os
            for file in upl:
                save_path = os.path.join("training_data", "external", file.name)
                if not os.path.exists("training_data/external"):
                    os.makedirs("training_data/external")
                with open(save_path, "wb") as f:
                    f.write(file.getbuffer())
            st.success(f"Nahráno {len(upl)} souborů.")

        # Galerie a ořez
        import os
        ext_path = "training_data/external/"
        if os.path.exists(ext_path):
            files = [f for f in os.listdir(ext_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            
            if files:
                st.write("### 🖼️ Galerie snímků")
                img_cols = st.columns(5)
                for idx, f_name in enumerate(files):
                    with img_cols[idx % 5]:
                        st.image(os.path.join(ext_path, f_name), use_container_width=True)
                        if st.button("🔍 Detail", key=f"sel_{f_name}"):
                            st.session_state.annot_img = f_name

                # Interaktivní ořez ROI
                if 'annot_img' in st.session_state:
                    st.divider()
                    st.markdown(f"#### 📐 Nastavení ROI pro: `{st.session_state.annot_img}`")
                    img_p = os.path.join(ext_path, st.session_state.annot_img)
                    img = Image.open(img_p)

                    col_img, col_form = st.columns([3, 1])
                    with col_img:
                        st.info("🖱️ Táhni myší v obrázku pro výběr oblasti (ROI)")
                        cropped_img = st_cropper(img, realtime_update=True, box_color='#FF0000', aspect_ratio=None)
                        
                    with col_form:
                        st.write("**📐 Náhled výřezu:**")
                        st.image(cropped_img, use_container_width=True)
                        roi_name = st.text_input("Název této ROI", value="Zebro_P1")
                        label = st.radio("Výsledek ROI:", ["OK", "NOK"])
                        if st.button("💾 ULOŽIT DO UČENÍ", use_container_width=True):
                        import logic
                        # 1. Uložíme výřez jako obrázek pro trénink AI (to už máš)
                        logic.save_cropped_image(cropped_img, roi_name, label)
                        
                        # 2. Získáme souřadnice z cropperu (tohle je to nové!)
                        # st_cropper vrací box s údaji o levém horním rohu a rozměrech
                        # Pokud používáš st_cropper, souřadnice jsou v 'cropped_img' nebo v datech z cropperu
                        # Pro zjednodušení: získáme info o boxu
                        box = cropped_img.getbbox() # PIL funkce pro získání rozměrů
                        
                        # 3. Uložíme "předpis" do databáze
                        # Abychom věděli, kde na velké fotce količek je
                        # (Předpokládáme, že produkt je ten, co máš vybraný nahoře)
                        database.save_roi_template("MQB L", roi_name, 0, 0, 0, 0) # Sem doplníme reálná data z cropperu
                        
                        st.success(f"ROI '{roi_name}' uložena do databáze i do složky pro učení!")

elif menu == "📂 Historie inspekcí":
    st.markdown("## 📂 Historie inspekcí")
    # Zde doplň kód pro historii, který jsme psali dříve (get_last_cycles atd.)

elif menu == "⚙️ Nastavení":
    st.title("⚙️ Konfigurace inspekcí")
    
    # 1. KROK - VÝBĚR PRODUKTU
    produkt = st.selectbox("Vyberte produkt pro úpravu", ["MQB Skříň ventilátoru L", "Octavia III - Kryt"])
    
    st.divider()
    
    # 2. KROK - NASTAVENÍ POZICE / MASTER SNÍMEK
    st.subheader("Vytvoření master snímku")
    master_file = st.file_uploader("Nahrajte Master snímek z kamery", type=["jpg", "png"])
    
    if master_file:
        img_master = Image.open(master_file)
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.info("🖱️ Nakreslete na Master snímku novou oblast zájmu (ROI)")
            # Použijeme náš cropper pro definici šablony
            from streamlit_cropper import st_cropper
            roi_crop = st_cropper(img_master, realtime_update=True, box_color='#FF9800', aspect_ratio=None)
            
        with col2:
            st.write("### Nastavení ROI")
            new_roi_name = st.text_input("Název nové inspekce", placeholder="např. Kontrola količka")
            
            if st.button("➕ PŘIDAT INSPEKCI"):
                # Tady uložíme souřadnice z cropperu do tabulky roi_templates
                # V reálné aplikaci bysme zde vytáhli box_data z cropperu
                st.success(f"Inspekce '{new_roi_name}' byla uložena do šablony.")
                
    # 3. KROK - SEZNAM EXISTUJÍCÍCH INSPEKCÍ (jako na screenshotu 3)
    st.divider()
    st.subheader("Aktivní inspekce pro tento produkt")
    # Zde by se vypsaly ROI z databáze s možností "SMAZAT" nebo "ZMĚNIT"