from PIL import Image
from streamlit_cropper import st_cropper
import streamlit as st
import os
import database, logic

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

elif menu == "🧠 Učení a Trénink":
    st.markdown("## 🧠 Správa učících dat")
    tab1, tab2, tab3 = st.tabs(["🔄 Z cyklu", "🛠️ Ze seřízení (Master)", "📤 Import testů"])
    
    with tab1:
        st.info("Vyberte fotky z historie pro zpřesnění modelu.")

    with tab2:
        if st.button("📸 VYFOTIT AKTUÁLNÍ STAV"):
            st.success("Snímek ze seřízení uložen.")

    with tab3:
        st.subheader("Import a Anotace")
        upl = st.file_uploader("Nahrajte soubory", accept_multiple_files=True)
        if upl:
            for file in upl:
                save_p = os.path.join("training_data", "external", file.name)
                os.makedirs(os.path.dirname(save_p), exist_ok=True)
                with open(save_p, "wb") as f: f.write(file.getbuffer())
            st.success("Soubory uloženy.")

        ext_path = "training_data/external/"
        if os.path.exists(ext_path):
            files = [f for f in os.listdir(ext_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            if files:
                img_cols = st.columns(5)
                for idx, f_name in enumerate(files):
                    with img_cols[idx % 5]:
                        st.image(os.path.join(ext_path, f_name), use_container_width=True)
                        if st.button("🔍 Detail", key=f"sel_{f_name}"):
                            st.session_state.annot_img = f_name

                if 'annot_img' in st.session_state:
                    st.divider()
                    img_p = os.path.join(ext_path, st.session_state.annot_img)
                    img = Image.open(img_p)
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        cropped_img = st_cropper(img, realtime_update=True, box_color='#FF0000', aspect_ratio=None)
                    with c2:
                        st.image(cropped_img, use_container_width=True)
                        roi_name = st.text_input("Název ROI", value="Zebro_P1")
                        label = st.radio("Výsledek:", ["OK", "NOK"])
                        if st.button("💾 ULOŽIT DO UČENÍ", use_container_width=True):
                            # Zde je opravené odsazení!
                            path = logic.save_cropped_image(cropped_img, roi_name, label)
                            # Automatické získání souřadnic z ořezu
                            x, y, w, h = 0, 0, cropped_img.width, cropped_img.height
                            database.save_roi_template("MQB L", roi_name, x, y, w, h)
                            st.success(f"Uloženo!")

elif menu == "📂 Historie inspekcí":
    st.markdown("## 📂 Historie inspekcí")
    # Zde kód pro historii...

elif menu == "⚙️ Nastavení":
    st.title("⚙️ Konfigurátor inspekcí")
    
    # 1. Výběr produktu (Název projektu)
    projekt = st.selectbox("Vyberte projekt (produkt)", 
                           ["MQB Skříň ventilátoru L", "Octavia III - Kryt"], 
                           key="cfg_prod")
    
    st.divider()
    
    # 2. Definiční zóna (Master fotka a Cropper)
    st.subheader("🖼️ Definice šablon (Master snímek)")
    master_file = st.file_uploader("Nahrajte Master snímek z kamery", type=["jpg", "jpeg", "png"], key="cfg_master")
    
    # Lokální proměnná, do které uložíme souřadnice z cropperu
    box_data = None

    if master_file:
        img_master = Image.open(master_file)
        
        c1, c2 = st.columns([3, 1])
        
        with c1:
            st.info("🖱️ Nakreslete na fotce oblast zájmu (ROI).")
            # --- ZDE JE TEN ROZDÍL ---
            # realtime_update=False zajistí, že se data z cropperu neposílají při každém pixelu, ale až při uložení
            roi_crop = st_cropper(img_master, realtime_update=False, box_color='#FF9800', aspect_ratio=None, key="cfg_cropper")
            
            # Stáhneme data o pozici boxu
            if hasattr(st.session_state, 'cfg_cropper') and st.session_state.cfg_cropper:
                box_data = st.session_state.cfg_cropper['coords']

        with c2:
            st.write("### ➕ Přidat novou ROI")
            # Náhled ořezu
            st.image(roi_crop, use_container_width=True, caption="Náhled ořezu")
            
            # Formulář pro uložení
            new_roi_name = st.text_input("Název této inspekce", placeholder="např. Kontrola_količka", key="cfg_new_name")
            
            if st.button("➕ PŘIDAT INSPEKCI", use_container_width=True, type="primary"):
                # Kontrola dat
                if not box_data or not new_roi_name:
                    st.error("❌ Musíte nakreslit ROI a zadat název!")
                else:
                    # Uložíme šablonu (předpis) do DB
                    database.save_roi_template(
                        projekt, 
                        new_roi_name, 
                        box_data['left'], 
                        box_data['top'], 
                        box_data['width'], 
                        box_data['height']
                    )
                    st.success(f"Inspekce '{new_roi_name}' byla uložena do šablony.")
                    st.toast(f"Propsáno do databáze ✅")
                    # Po uložení stránku obnovíme, aby se ROI ukázala v seznamu níže
                    st.rerun()

    # 3. Seznam existujících inspekcí (Vizuální potvrzení)
    st.divider()
    st.subheader(f"📋 Aktivní inspekce pro: `{projekt}`")
    
    # Načteme šablony z DB
    templates = database.get_roi_templates(projekt)
    
    if templates:
        for t in templates:
            # t[0]=id, t[2]=název, t[3-6]=x,y,w,h
            with st.expander(f"🟢 {t[2]} (Pozice: {t[3]}, {t[4]})"):
                col_a, col_b = st.columns([3, 1])
                col_a.write(f"Rozměry: **{t[5]}x{t[6]}** px")
                if col_b.button("🗑️ Smazat", key=f"del_{t[0]}"):
                    database.delete_roi_template(t[0])
                    st.rerun()
    else:
        st.info("Zatím nejsou definovány žádné ROI zóny. Nakreslete je na Master snímku výše.")