import sqlite3

def init_db():
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY, name TEXT UNIQUE)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS masters (
                    id INTEGER PRIMARY KEY, project TEXT, name TEXT, image_path TEXT, 
                    x INTEGER, y INTEGER, w INTEGER, h INTEGER)''')
                    
    c.execute('''CREATE TABLE IF NOT EXISTS rois (
                    id INTEGER PRIMARY KEY, master_id INTEGER, project TEXT, name TEXT, 
                    x INTEGER, y INTEGER, w INTEGER, h INTEGER, nok_type INTEGER, 
                    tolerance INTEGER DEFAULT 20)''')
                    
    # NOVÁ TABULKA PRO HISTORII SNÍMKŮ
    c.execute('''CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY, project TEXT, roi_name TEXT, 
                    image_path TEXT, timestamp TEXT, status TEXT)''')
    conn.commit()
    conn.close()

def add_project(name):
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO projects (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()

def get_projects():
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    c.execute("SELECT name FROM projects")
    return [row[0] for row in c.fetchall()]

def add_master(project_name, name, path, x, y, w, h): # <-- Přidán project_name
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    # Zapisujeme název projektu do nového sloupce
    c.execute("INSERT INTO masters (project, name, image_path, x, y, w, h) VALUES (?, ?, ?, ?, ?, ?, ?)", 
              (project_name, name, path, x, y, w, h))
    conn.commit()
    conn.close()

def get_all_masters(project_name):
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    # ZMĚNA: Taháme všechny sloupce (*), abychom měli ID, Projekt, Název, Cestu i Rozměry výřezu ax, ay, aw, ah
    c.execute("SELECT * FROM masters WHERE project = ?", (project_name,))
    data = c.fetchall()
    conn.close()
    return data

def get_rois(master_id, project_name):
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    c.execute("SELECT * FROM rois WHERE master_id = ? AND project = ?", (master_id, project_name))
    data = c.fetchall()
    conn.close()
    return data

def save_roi(master_id, project, name, x, y, w, h, nok_type, tolerance=20): # <-- Přidán parametr
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    c.execute("""
        INSERT INTO rois (master_id, project, name, x, y, w, h, nok_type, tolerance) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (master_id, project, name, x, y, w, h, nok_type, tolerance))
    conn.commit()
    conn.close()
    
def delete_roi(roi_id):
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    c.execute("DELETE FROM rois WHERE id = ?", (roi_id,))
    conn.commit()
    conn.close()

def delete_master(master_id):
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    
    # 1. Nejdřív zjistíme cestu k souboru, abychom ho smazali i z disku
    c.execute("SELECT image_path FROM masters WHERE id = ?", (master_id,))
    row = c.fetchone()
    if row and os.path.exists(row[0]):
        try:
            os.remove(row[0]) # Smaže fyzický .png soubor ze složky masters/
        except:
            pass
            
    # 2. Smažeme master z tabulky masters
    c.execute("DELETE FROM masters WHERE id = ?", (master_id,))
    # 3. Smažeme i všechny zóny, které k tomuto masteru patřily (úklid)
    c.execute("DELETE FROM rois WHERE master_id = ?", (master_id,))
    
    conn.commit()
    conn.close()

def update_roi(roi_id, name, x, y, w, h, nok_type, tolerance): # <-- Přidán parametr
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    c.execute("""
        UPDATE rois 
        SET name = ?, x = ?, y = ?, w = ?, h = ?, nok_type = ?, tolerance = ? 
        WHERE id = ?
    """, (name, x, y, w, h, nok_type, tolerance, roi_id))
    conn.commit()
    conn.close()
    
def save_to_history(project, roi_name, image_path, status):
    import datetime
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("""
        INSERT INTO history (project, roi_name, image_path, timestamp, status) 
        VALUES (?, ?, ?, ?, ?)
    """, (project, roi_name, image_path, now, status))
    conn.commit()
    conn.close()

def get_history(project_filter="Vše", status_filter="Vše", roi_filter="Vše"):
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    
    query = "SELECT * FROM history WHERE 1=1"
    params = []
    
    if project_filter and project_filter != "Vše":
        query += " AND project = ?"
        params.append(project_filter)
        
    if status_filter and status_filter != "Vše":
        query += " AND status = ?"
        params.append(status_filter)
        
    if roi_filter and roi_filter != "Vše":
        query += " AND roi_name = ?"
        params.append(roi_filter)
        
    query += " ORDER BY id DESC LIMIT 100"
    c.execute(query, tuple(params))
    data = c.fetchall()
    conn.close()
    return data    
    
def get_unique_projects_from_history():
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    c.execute("SELECT DISTINCT project FROM history ORDER BY project ASC")
    rows = c.fetchall()
    conn.close()
    # Převedeme seznam ntic [('MQB',), ('A0',)] na čistý seznam řetězců ['MQB', 'A0']
    return [r[0] for r in rows]

def get_unique_rois_from_history(project_filter="Vše"):
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    if project_filter == "Vše":
        c.execute("SELECT DISTINCT roi_name FROM history ORDER BY roi_name ASC")
    else:
        c.execute("SELECT DISTINCT roi_name FROM history WHERE project = ? ORDER BY roi_name ASC", (project_filter,))
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]    