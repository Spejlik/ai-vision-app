@ -121,11 +121,8 @@ if menu == "Konfigurace":

    # KROK 3: ROI DEFINICE
    elif st.session_state.step == 3:
        # --- POJISTKA: Inicializace proměnných, aby to nepadalo ---
        if 'edit_roi_id' not in st.session_state:
            st.session_state.edit_roi_id = None
        if 'manual_add_active' not in st.session_state:
            st.session_state.manual_add_active = False
        if 'edit_roi_id' not in st.session_state: st.session_state.edit_roi_id = None
        if 'manual_add_active' not in st.session_state: st.session_state.manual_add_active = False

        masters = database.get_masters(st.session_state.active_project)
        if not masters:
@ -144,14 +141,12 @@ if menu == "Konfigurace":
            with col_side:
                st.subheader("➕ Správa zón")
                
                # Tlačítko pro novou zónu
                if not st.session_state.manual_add_active:
                    if st.button("✨ VYTVOŘIT NOVOU ZÓNU", use_container_width=True, type="primary"):
                        st.session_state.manual_add_active = True
                        st.session_state.edit_roi_id = None
                        st.rerun()

                # Formulář se slidery
                rx, ry, rw, rh = 0, 0, 100, 100
                if st.session_state.manual_add_active:
                    with st.container(border=True):
@ -179,7 +174,6 @@ if menu == "Konfigurace":
                            st.session_state.edit_roi_id = None
                            st.rerun()

                # --- TADY BYLA CHYBA (nyní správně odsazeno vpravo) ---
                st.divider()
                st.subheader("📋 Seznam zón")
                for r in old_rois:
@ -196,67 +190,29 @@ if menu == "Konfigurace":

            with col_main:
                draw = ImageDraw.Draw(img)
                # Kreslení uložených
                for r in old_rois:
                    if r[0] != st.session_state.edit_roi_id:
                        draw.rectangle([r[2], r[3], r[2]+r[4], r[3]+r[5]], outline="#97BE0D", width=5)
                
                # Kreslení náhledu (oranžová)
                if st.session_state.manual_add_active:
                    draw.rectangle([rx, ry, rx+rw, ry+rh], outline="#FF9800", width=6)
                
                st.image(img, use_container_width=True)
                
                # FORMULÁŘ PRO EDITACI / PŘIDÁVÁNÍ
                if st.session_state.get('manual_add_active', False):
                    with st.container(border=True):
                        st.write("**Nastavení zóny**")
                        name = st.text_input("Název:", f"Zóna {len(old_rois)+1}")
                        rx = st.slider("X pozice", 0, W, W//3)
                        ry = st.slider("Y pozice", 0, H, H//3)
                        rw = st.slider("Šířka", 10, 500, 150)
                        rh = st.slider("Výška", 10, 500, 150)
                        nok = st.selectbox("Typ vady:", range(1, 11), format_func=lambda x: f"NOK {x}")
                        
                        # Vykreslení oranžového náhledu (vynucený překres)
                        draw.rectangle([rx, ry, rx+rw, ry+rh], outline=orange, width=6)
                        
                        c1, c2 = st.columns(2)
                        if c1.button("💾 ULOŽIT", type="primary", use_container_width=True):
                            database.save_roi(curr_m[0], name, rx, ry, rw, rh, nok)
                            st.session_state.manual_add_active = False
                            st.rerun()
                        if c2.button("✖ ZRUŠIT", use_container_width=True):
                            st.session_state.manual_add_active = False
                            st.rerun()

                st.divider()
                st.subheader("📋 Seznam zón")
                if not old_rois:
                    st.caption("Žádné zóny nenalezeny.")
                else:
                    for r in old_rois:
                        with st.container(border=True):
                            c1, c2, c3 = st.columns([3, 1, 1])
                            c1.markdown(f"**{r[1]}**")
                            c1.caption(f"NOK {r[6]}")
                            
                            # TLAČÍTKO EDITACE (Tužka)
                            if c2.button("📝", key=f"edit_{r[0]}", help="Upravit zónu"):
                                # Načteme hodnoty zóny do session_state pro slidery
                                st.session_state.manual_add_active = True
                                st.session_state.edit_id = r[0] # Uložíme si, kterou zónu ladíme
                                # Přednastavíme hodnoty pro slidery (pokud je v kódu používáš jako defaulty)
                                st.rerun()

                            # TLAČÍTKO SMAZÁNÍ (Koš)
                            if c3.button("🗑️", key=f"del_{r[0]}", help="Smazat"):
                                database.delete_roi(r[0])
                                st.rerun()                        
    # KROK 4: I/O MONITOR (PŘIDÁNO)
    elif st.session_state.step == 4:
        st.subheader("🔌 I/O Monitor & PLC Komunikace")
        c1, c2 = st.columns(2)
        with c1:
            st.info("Vstupy z PLC")
            st.toggle("Trigger signál", disabled=True)
        with c2:
            st.info("Výstupy do PLC")
            st.write("🔴 PASS")
            st.write("🔴 FAIL")

# ... (zbytek monitoring sekce)
# --- KONEC KONFIGURACE, START MONITORINGU ---

elif menu == "Monitoring":
    st.title("📊 Živý monitoring")
    st.write("Zde se zobrazují výsledky inspekce.")
    # Zde pak doděláme tu mřížku detailů (krok 4)
    st.write("Zde se zobrazují výsledky inspekce.")