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