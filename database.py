import sqlite3

def init_db():
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS masters 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, image_path TEXT,
                  x INTEGER, y INTEGER, w INTEGER, h INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS rois 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, master_id INTEGER, name TEXT, 
                  x INTEGER, y INTEGER, w INTEGER, h INTEGER, nok_type INTEGER)''')
    conn.commit()
    conn.close()

def save_project(name):
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    c.execute("INSERT INTO masters (name, image_path) VALUES (?, '')", (name,))
    conn.commit()
    conn.close()

def get_projects():
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    c.execute("SELECT id, name FROM masters")
    data = c.fetchall()
    conn.close()
    return data

def add_master(project_name, path, x, y, w, h):
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    c.execute("UPDATE masters SET image_path=?, x=?, y=?, w=?, h=? WHERE name=?", 
              (path, x, y, w, h, project_name))
    conn.commit()
    conn.close()

def get_masters(project_name):
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    c.execute("SELECT id, name, image_path FROM masters WHERE name=?", (project_name,))
    data = c.fetchall()
    conn.close()
    return data
    
def get_rois(master_id):
    """Načte všechny inspekční zóny pro daný Master/Projekt."""
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    # Vrátíme ID, název a souřadnice
    c.execute("SELECT id, name, x, y, w, h, nok_type FROM rois WHERE master_id=?", (master_id,))
    rois = c.fetchall()
    conn.close()
    return rois

def save_roi(master_id, name, x, y, w, h, nok):
    """Uloží novou inspekční zónu k danému Masteru."""
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    c.execute("INSERT INTO rois (master_id, name, x, y, w, h, nok_type) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (master_id, name, int(x), int(y), int(w), int(h), nok))
    conn.commit()
    conn.close()

def delete_roi(roi_id):
    """Smaže konkrétní zónu."""
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    c.execute("DELETE FROM rois WHERE id=?", (roi_id,))
    conn.commit()
    conn.close()

### 2. V `app.py` v Tabu "Zóny" použij tento kód:
Tento kód otevře tvůj oříznutý Master a umožní ti na něm plynule kreslit zóny.

```python
# --- TAB 3: ZÓNY (ROI DEFINICE) ---
with tab3:
    # 1. Najdeme ID projektu a jeho Mastera
    masters = database.get_masters(st.session_state.active_project)
    
    if not masters or masters[0][2] == "":
        st.warning("⚠️ Nejdříve vytvořte Master snímek v předchozí záložce!")
    else:
        master_id, m_name, m_path = masters[0][0], masters[0][1], masters[0][2]
        
        # Načteme oříznutý obrázek z disku
        img = Image.open(m_path).convert("RGB")
        W, H = img.size
        
        col_m, col_s = st.columns([2, 1])
        
        with col_s:
            st.subheader("➕ Nová zóna")
            r_name = st.text_input("Název zóny:", "Spona_1")
            rx = st.slider("X pozice", 0, W, W//4)
            ry = st.slider("Y pozice", 0, H, H//4)
            rw = st.slider("Šířka zóny", 10, W, 100)
            rh = st.slider("Výška zóny", 10, H, 100)
            nok = st.selectbox("Přiřadit NOK registr:", range(1, 11))
            
            if st.button("💾 ULOŽIT ZÓNU", use_container_width=True, type="primary"):
                database.save_roi(master_id, r_name, rx, ry, rw, rh, nok)
                st.success(f"Zóna {r_name} uložena.")
                st.rerun()

            st.divider()
            st.subheader("📋 Seznam zón")
            current_rois = database.get_rois(master_id)
            for r in current_rois:
                c_a, c_b = st.columns([3, 1])
                c_a.write(f"**{r[1]}** (NOK {r[6]})")
                if c_b.button("🗑️", key=f"del_{r[0]}"):
                    database.delete_roi(r[0])
                    st.rerun()

        with col_m:
            # Vykreslení uložených zón na Mastera
            draw = ImageDraw.Draw(img)
            for r in current_rois:
                # Zelené čtverečky pro uložené zóny
                draw.rectangle([r[2], r[3], r[2]+r[4], r[3]+r[5]], outline="#deff9a", width=5)
            
            # Oranžový čtvereček pro zónu, kterou právě ladíš slidery
            draw.rectangle([rx, ry, rx+rw, ry+rh], outline="#f59e0b", width=3)
            
            st.image(img, use_container_width=True, caption=f"Editace zón na Masteru: {m_name}")

   