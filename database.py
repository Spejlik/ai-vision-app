import sqlite3

def init_db():
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    # Tabulka pro projekty
    c.execute('CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY, name TEXT UNIQUE)')
    
    # Tabulka pro Mastery - musí obsahovat project, name, image_path a souřadnice
    c.execute('''CREATE TABLE IF NOT EXISTS masters
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  project TEXT, 
                  name TEXT, 
                  image_path TEXT,
                  x INTEGER, y INTEGER, w INTEGER, h INTEGER)''')
    
    # Tabulka pro ROI zóny
    c.execute('''CREATE TABLE IF NOT EXISTS rois
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  master_id INTEGER, 
                  name TEXT, 
                  x INTEGER, y INTEGER, w INTEGER, h INTEGER, 
                  nok_type INTEGER)''')
    conn.commit()
    conn.close()
    
def add_project(name):
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    # Ukládáme POUZE do tabulky projects
    c.execute("INSERT OR IGNORE INTO projects (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()
        
def save_project(name):
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    c.execute("INSERT INTO masters (name, image_path) VALUES (?, '')", (name,))
    conn.commit()
    conn.close()

# Funkce pro Projekty (vlevo v sidebaru)
def get_projects():
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    # Taháme POUZE z tabulky projects
    c.execute("SELECT name FROM projects")
    data = [row[0] for row in c.fetchall()]
    conn.close()
    return data

def add_master(name, image_path, x, y, w, h):
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    # image_path by mělo být např. "masters/P1.png"
    c.execute("INSERT INTO masters (name, image_path, x, y, w, h) VALUES (?, ?, ?, ?, ?, ?)",
              (name, image_path, x, y, w, h))
    conn.commit()
    conn.close()

# Funkce pro Mastery (horizontální galerie)
def get_all_masters():
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    # Taháme jen z tabulky masters!
    c.execute("SELECT id, name, image_path FROM masters")
    data = c.fetchall()
    conn.close()
    return data
    
def save_roi(master_id, project_name, name, x, y, w, h, nok):
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    c.execute("INSERT INTO rois (master_id, project, name, x, y, w, h, nok_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
              (master_id, project_name, name, x, y, w, h, nok))
    conn.commit()
    conn.close()

def get_rois(master_id, project_name):
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    # Filtrujeme podle Masteru I podle Projektu
    c.execute("SELECT * FROM rois WHERE master_id = ? AND project = ?", (master_id, project_name))
    data = c.fetchall()
    conn.close()
    return data

def delete_roi(roi_id):
    """Smaže konkrétní zónu."""
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    c.execute("DELETE FROM rois WHERE id=?", (roi_id,))
    conn.commit()
    conn.close()

### 2. V `app.py` v Tabu "Zóny" použij tento kód:
def get_rois(master_id):
    """Načte všechny inspekční zóny pro daný Master/Projekt."""
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
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
    
def delete_project(project_name):
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    # Získáme ID projektu
    c.execute("SELECT id FROM masters WHERE name=?", (project_name,))
    p_id = c.fetchone()
    if p_id:
        # Smažeme zóny a pak projekt
        c.execute("DELETE FROM rois WHERE master_id=?", (p_id[0],))
        c.execute("DELETE FROM masters WHERE id=?", (p_id[0],))
    conn.commit()
    conn.close()

def duplicate_project(old_name, new_name):
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    # 1. Načteme starý projekt
    c.execute("SELECT image_path, x, y, w, h FROM masters WHERE name=?", (old_name,))
    old_data = c.fetchone()
    if old_data:
        # 2. Vytvoříme nový projekt se stejnými daty
        c.execute("INSERT INTO masters (name, image_path, x, y, w, h) VALUES (?, ?, ?, ?, ?, ?)",
                  (new_name, old_data[0], old_data[1], old_data[2], old_data[3], old_data[4]))
        new_id = c.lastrowid
        # 3. Zkopírujeme i zóny
        c.execute("SELECT id FROM masters WHERE name=?", (old_name,))
        old_id = c.fetchone()[0]
        c.execute("SELECT name, x, y, w, h, nok_type FROM rois WHERE master_id=?", (old_id,))
        rois = c.fetchall()
        for r in rois:
            c.execute("INSERT INTO rois (master_id, name, x, y, w, h, nok_type) VALUES (?, ?, ?, ?, ?, ?, ?)",
                      (new_id, r[0], r[1], r[2], r[3], r[4], r[5]))
def update_roi(roi_id, name, x, y, w, h, nok):
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    c.execute("UPDATE rois SET name=?, x=?, y=?, w=?, h=?, nok_type=? WHERE id=?",
              (name, x, y, w, h, nok, roi_id))
    conn.commit()
    conn.close()

def delete_roi(roi_id):
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    c.execute("DELETE FROM rois WHERE id=?", (roi_id,))
    conn.commit()
    conn.close()    