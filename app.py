from PIL import Image
from streamlit_cropper import st_cropper
import streamlit as st
import styles    # <--- TOTO JE TEN IMPORT
import logic     # <--- TOTO TAKY, ABY FUNGOVALO OŘEZÁVÁNÍ
import database  # <--- TOTO, ABY SE UKLÁDALY ROI

# 1. Nastavení stránky
st.set_page_config(
    page_title="Lis 1300/7A - Kontrola", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# 2. Inicializace databáze a stylů
database.init_db()
styles.apply_custom_css()

# --- SIDEBAR ---
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

# --- HEADER ---
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

# --- LOGIKA STRÁNEK ---

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
                    styles.draw_roi_card(res[4], res[5], res[6], status_color, b64_img, size="small" if n_results > 4 else "normal")
        else:
            st.info("Systém připraven. Spusťte kontrolu tlačítkem START.")
    with col_right:
        cycles_for_status = database.get_last_cycles(limit=1)
        current_status = cycles_for_status[0][2] if cycles_for_status else "WAIT"
        bg_color = "#22c55e" if current_status == "OK" else "#ef4444"
        if current_status == "WAIT": bg_color = "#64748b"
        st.markdown(f'<div style="background:{bg_color}; color:white; padding:25px; border-radius:12px; text-align:center;"><p style="margin:0; opacity:0.8; font-weight:bold; font-size:12px;">CELKOVÝ STAV</p><h1 style="font-size:60px; margin:0;">{current_status}</h1></div>', unsafe_allow_html=True)
        if mode == "MANUAL":
            st.write("")
            if st.button("🚀 START INSPEKCE", use_container_width=True, type="primary"):
                current_cycle = str(int(time.time()))
            
                # 1. TADY JE TA ZMĚNA: Načteme si šablony, které jsi nakreslil v nastavení
                # "MQB L" musí odpovídat názvu produktu v nastavení
                templates = database.get_roi_templates("MQB Skříň ventilátoru L")
            
                if not templates:
                    st.error("❌ Nejdříve nastavte ROI zóny v sekci Nastavení!")
                else:
                    for t in templates:
                        # t[2] je název ROI (třeba 'Zebro_P1'), t[3]-t[6] jsou souřadnice
                        roi_name = t[2]
                    
                        # 2. Spustíme AI predikci pro konkrétní ROI
                        conf, stat, _ = logic.get_ai_prediction(roi_name)
                    
                        # 3. Uložíme výsledek
                        database.save_result(current_cycle, "MQB L", roi_name, conf, stat, f"img/guma_{stat.lower()}.jpg")
                
                st.rerun()

elif menu == "⚙️ Nastavení":
    st.title("⚙️ Konfigurace inspekcí")
    
    # 1. Výběr produktu
    produkt = st.selectbox("Vyberte produkt", ["MQB Skříň ventilátoru L", "Octavia III - Kryt"])
    
    # 2. Nahrání fotky (Master)
    master_file = st.file_uploader("Nahrajte Master snímek", type=["jpg", "png"])
    
    if master_file:
        img = Image.open(master_file)
        
        # Rozdělíme obrazovku na dvě části
        col_foto, col_nastaveni = st.columns([3, 1])
        with col_foto:
            st.write("### 🖱️ 1. Nakreslete oblast (ROI)")
            # PŘIDÁME: realtime_update=True a zachycení objektu
            roi_obj = st_cropper(img, realtime_update=True, box_color='#FF9800', aspect_ratio=None, key="main_cropper")
            
        with col_nastaveni:
            st.write("### 📝 2. Uložte oblast")
            st.image(roi_obj, use_container_width=True, caption="Náhled")
            new_roi_name = st.text_input("Název inspekce", placeholder="např. ot2", key="roi_name_input")
            
            if st.button("➕ PŘIDAT INSPEKCI", use_container_width=True, type="primary"):
                # ZÍSKÁNÍ SOUŘADNIC: st_cropper ukládá data do session_state pod klíčem 'main_cropper'
                if 'main_cropper' in st.session_state and st.session_state['main_cropper']:
                    coords = st.session_state['main_cropper']['coords']
                    x, y, w, h = coords['left'], coords['top'], coords['width'], coords['height']
                    
                    if new_roi_name:
                        # Uložení skutečných souřadnic z obrázku image_d448f2.jpg
                        database.save_roi_template(produkt, new_roi_name, x, y, w, h)
                        st.success(f"Zóna {new_roi_name} byla úspěšně přidána!")
                        st.rerun()
                    else:
                        st.error("Chybí název inspekce!")
                else:
                    st.error("Nepodařilo se načíst souřadnice z ořezu.")
                    st.divider()
    st.subheader(f"📋 Aktivní kontroly pro: {produkt}")
    
    # 1. Načteme uložené šablony z databáze
    current_templates = database.get_roi_templates(produkt)
    
    if current_templates:
        # 2. Vykreslíme každou šablonu jako řádek v seznamu
        for t in current_templates:
            # t[0]=id, t[1]=produkt, t[2]=název, t[3-6]=x,y,w,h
            with st.container():
                c1, c2, c3 = st.columns([3, 2, 1])
                c1.write(f"🟢 **{t[2]}**") # Název ROI
                c2.write(f"Pozice: {t[3]},{t[4]} | Rozměr: {t[5]}x{t[6]}")
                if c3.button("🗑️ Smazat", key=f"del_{t[0]}"):
                    database.delete_roi_template(t[0])
                    st.rerun()
    else:
        st.info("Zatím zde nejsou žádné definované kontroly. Použijte tlačítko PŘIDAT INSPEKCI výše.")
    # 3. Seznam už uložených věcí
    st.divider()
    st.subheader("📋 Aktivní kontroly v projektu")
    templates = database.get_roi_templates(produkt)
    if templates:
        for t in templates:
            with st.expander(f"🔍 {t[2]}"):
                if st.button(f"Smazat {t[2]}", key=f"del_{t[0]}"):
                    database.delete_roi_template(t[0])
                    st.rerun()

elif menu == "📂 Historie inspekcí":
    st.markdown("## 📂 Historie inspekcí")
    # Zde kód pro historii...

elif menu == "⚙️ Nastavení":
    st.title("⚙️ Konfigurátor projektu")
    
    # Výběr nebo vytvoření nového produktu
    produkt = st.selectbox("Aktivní produkt", ["MQB Skříň ventilátoru L", "Octavia III - Kryt"])
    
    st.divider()
    
    # Nahrání Master snímku
    uploaded_master = st.file_uploader("Nahrajte Master snímek", type=["jpg", "png"])
    
    # Uložíme obrázek do session_state, aby nezmizel
    if uploaded_master:
        st.session_state.master_img = Image.open(uploaded_master)

    if 'master_img' in st.session_state:
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.info("🖱️ Označ oblast a vpravo ji pojmenuj. Můžeš přidávat jednu za druhou.")
            # Cropper pro výběr ROI
            roi_crop = st_cropper(st.session_state.master_img, realtime_update=True, box_color='#FF9800', aspect_ratio=None)
            
        with col2:
            new_roi_name = st.text_input("Název nové inspekce", placeholder="např. klapka 1")
            
            if st.button("➕ PŘIDAT DO PROJEKTU"):
                if new_roi_name:
                    # Zde získáme souřadnice z aktuálního výřezu
                    # (Pro zjednodušení ukládáme název, v praxi i x,y,w,h)
                    database.save_roi_template(produkt, new_roi_name, 0, 0, 100, 100)
                    st.success(f"Přidáno: {new_roi_name}")
                    time.sleep(1)
                    st.rerun() # Stránka se obnoví a můžeš kreslit další ROI na stejné fotce
                else:
                    st.error("Zadejte název!")

    # Seznam už vytvořených ROI (to, co jsi chtěl vidět)
    st.divider()
    st.subheader("📋 Seznam hlídaných pozic")
    current_rois = database.get_roi_templates(produkt)
    
    if current_rois:
        for r in current_rois:
            # Každá ROI má svůj řádek s tlačítkem smazat
            with st.container():
                c1, c2 = st.columns([4, 1])
                c1.markdown(f"🟢 **{r[2]}**")
                if c2.button("🗑️", key=f"del_{r[0]}"):
                    database.delete_roi_template(r[0])
                    st.rerun()