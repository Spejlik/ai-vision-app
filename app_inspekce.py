import streamlit as st
import time
import numpy as np
import os
import cv2
from datetime import datetime

# 1. NASTAVENÍ STRÁNKY A CESTY Pro UKLÁDÁNÍ
st.set_page_config(layout="wide", page_title="Lis 1300/20 - Kontrola výlisků")

CESTA_UKLADANI = r"C:\Inspekce\Foto\test"
os.makedirs(CESTA_UKLADANI, exist_ok=True)

# 2. INICIALIZACE HISTORIE (Zůstává v paměti Streamlitu)
if "historie" not in st.session_state:
    st.session_state.historie = [1] * 28 + [0] + [1]  # Mock historie (1=OK, 0=NOK)
    st.session_state.pocitadlo = 9008

# Pomocná funkce pro simulaci snímku z Basler kamery
def get_mock_image():
    img = np.full((300, 300), 40, dtype=np.uint8)
    img[80:220, 80:220] = 180  # Světlejší čtverec jako výlisek
    return img

# 3. ROZVRŽENÍ STRÁNKY (LAYOUT)
st.markdown("### Lis 1300/20 - Kontrola výlisků")

col_kamery, col_vysledky = st.columns([3, 1])

# Levý panel: Mřížka kamer 2x2
with col_kamery:
    st.caption("326 Air Inlet Set 2")
    r1_c1, r1_c2 = st.columns(2)
    r2_c1, r2_c2 = st.columns(2)
    
    # Placeholdery pro dynamické vkládání snímků
    p1_box = r1_c1.empty()
    p2_box = r1_c2.empty()
    p3_box = r2_c1.empty()
    p4_box = r2_c2.empty()

# Pravý panel: Výsledky a historie
with col_vysledky:
    st.write("**Výsledky inspekce - kompletní**")
    
    # Vykreslení čárek historie (zelená/červená)
    cols_hist = st.columns(len(st.session_state.historie) + 1)
    for i, stav in enumerate(st.session_state.historie):
        barva = "🟩" if stav == 1 else "🟥"
        cols_hist[i].write(barva)
    cols_hist[-1].write(f"**{st.session_state.pocitadlo}**")
    
    st.write("---")
    st.write(f"**Produkt:** 326 Air Inlet Set 2")
    
    # Placeholdery pro textové stavy pozic
    stav_celkovy = st.empty()
    stav_p1 = st.empty()
    stav_p2 = st.empty()
    stav_p3 = st.empty()
    stav_p4 = st.empty()
    
    st.write("---")
    velky_banner = st.empty()

# 4. SPOUŠTĚČ CYKLU (Simulace lisu)
if st.button("Simulovat nový cyklus lisu"):
    
    # Časové razítko a ID pro pojmenování fotek v tomto cyklu
    cas_cyklu = datetime.now().strftime("%Y%m%d_%H%M%S")
    id_kusu = st.session_state.pocitadlo
    
    # Výchozí stav: Všechny pozice čekají (Oranžová)
    stav_celkovy.write("**Výsledek:** ⏳ Probíhá...")
    stav_p1.markdown("🟠 **326Kolicek P1** (Čeká)")
    stav_p2.markdown("🟠 **326 Kolíček_P2** (Čeká)")
    stav_p3.markdown("🟠 **326 okoHranateP3** (Čeká)")
    stav_p4.markdown("🟠 **326 Oko Hranaté P4** (Čeká)")
    
    p1_box.image(np.zeros((300, 300)), caption="P1 - Čeká na snímek...")
    p2_box.image(np.zeros((300, 300)), caption="P2 - Čeká na snímek...")
    p3_box.image(np.zeros((300, 300)), caption="P3 - Čeká na snímek...")
    p4_box.image(np.zeros((300, 300)), caption="P4 - Čeká na snímek...")
    
    # --- KROK 1: Kamera P1 ---
    time.sleep(0.6)
    img_p1 = get_mock_image()
    p1_box.image(img_p1, caption="P1Cav1 - OK 100%")
    stav_p1.markdown("🟢 **326Kolicek P1** (OK)")
    cv2.imwrite(os.path.join(CESTA_UKLADANI, f"{cas_cyklu}_{id_kusu}_P1.jpg"), img_p1)
    
    # --- KROK 2: Kamera P2 ---
    time.sleep(0.5)
    img_p2 = get_mock_image()
    p2_box.image(img_p2, caption="P2Cav2 - OK 100%")
    stav_p2.markdown("🟢 **326 Kolíček_P2** (OK)")
    cv2.imwrite(os.path.join(CESTA_UKLADANI, f"{cas_cyklu}_{id_kusu}_P2.jpg"), img_p2)
    
    # --- KROK 3: Kamera P3 ---
    time.sleep(0.7)
    img_p3 = get_mock_image()
    p3_box.image(img_p3, caption="P3Cav2 - OK 99.41%")
    stav_p3.markdown("🟢 **326 okoHranateP3** (OK)")
    cv2.imwrite(os.path.join(CESTA_UKLADANI, f"{cas_cyklu}_{id_kusu}_P3.jpg"), img_p3)
    
    # --- KROK 4: Kamera P4 ---
    time.sleep(0.4)
    img_p4 = get_mock_image()
    p4_box.image(img_p4, caption="P4Cav1 - OK 99.91%")
    stav_p4.markdown("🟢 **326 Oko Hranaté P4** (OK)")
    cv2.imwrite(os.path.join(CESTA_UKLADANI, f"{cas_cyklu}_{id_kusu}_P4.jpg"), img_p4)
    
    # --- KROK 5: Finální vyhodnocení ---
    stav_celkovy.write("**Výsledek:** 🟢 OK")
    velky_banner.markdown(
        """
        <div style="background-color:#004d00; padding:25px; border-radius:10px; text-align:center;">
            <h1 style="color:#00ff00; margin:0; font-size:55px; font-family:sans-serif;">OK</h1>
        </div>
        """, 
        unsafe_allowed_html=True
    )
    
    # Aktualizace stavu a restart pro překreslení horní historie
    st.session_state.historie.pop(0)
    st.session_state.historie.append(1)
    st.session_state.pocitadlo += 1
    st.rerun()