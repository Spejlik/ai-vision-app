import sqlite3

def init_db():
    conn = sqlite3.connect('inspections.db')
    c = conn.cursor()
    
    # 1. Tabulka projektů
    c.execute('''CREATE TABLE IF NOT EXISTS projects 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)''')
    
    # 2. Tabulka MASTERŮ (Sjednocená verze)
    c.execute('''CREATE TABLE IF NOT EXISTS masters
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  project_name TEXT,
                  master_name TEXT,
                  x INTEGER, y INTEGER, w INTEGER, h INTEGER,
                  img_path TEXT)''')
    
    # 3. Tabulka ROI (Zóny)
    c.execute('''CREATE TABLE IF NOT EXISTS rois
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  master_id INTEGER,
                  name TEXT,
                  x INTEGER, y INTEGER, w INTEGER, h INTEGER,
                  error_code INTEGER)''')
    
    conn.commit()
    conn.close()

# --- FUNKCE ---

def save_project(name):
    conn = sqlite3.connect('inspections.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO projects (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()

def get_projects():
    conn = sqlite3.connect('inspections.db')
    c = conn.cursor()
    c.execute("SELECT * FROM projects")
    data = c.fetchall()
    conn.close()
    return data

def add_master(project_name, master_name, x, y, w, h, path):
    conn = sqlite3.connect('inspections.db')
    c = conn.cursor()
    c.execute('''INSERT INTO masters 
                 (project_name, master_name, x, y, w, h, img_path) 
                 VALUES (?, ?, ?, ?, ?, ?, ?)''', 
              (project_name, master_name, x, y, w, h, path))
    conn.commit()
    conn.close()

def get_masters(proj_name):
    conn = sqlite3.connect('inspections.db')
    c = conn.cursor()
    c.execute("SELECT * FROM masters WHERE project_name = ?", (proj_name,))
    data = c.fetchall()
    conn.close()
    return data

def save_roi(master_id, name, x, y, w, h, nok, roi_id=None):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    if roi_id:
        # AKTUALIZACE STÁVAJÍCÍ
        cursor.execute("UPDATE rois SET name=?, x=?, y=?, w=?, h=?, nok=? WHERE id=?",
                       (name, x, y, w, h, nok, roi_id))
    else:
        # NOVÁ ZÓNA
        cursor.execute("INSERT INTO rois (master_id, name, x, y, w, h, nok) VALUES (?,?,?,?,?,?,?)",
                       (master_id, name, x, y, w, h, nok))
    conn.commit()
    conn.close()

def get_rois(master_id):
    conn = sqlite3.connect('inspections.db')
    c = conn.cursor()
    c.execute("SELECT id, name, x, y, w, h, error_code FROM rois WHERE master_id = ?", (master_id,))
    data = c.fetchall()
    conn.close()
    return data

def delete_roi(roi_id):
    conn = sqlite3.connect('inspections.db')
    c = conn.cursor()
    c.execute("DELETE FROM rois WHERE id = ?", (roi_id,))
    conn.commit()
    conn.close()

def update_roi_nok(roi_id, new_nok):
    conn = sqlite3.connect('inspections.db')
    c = conn.cursor()
    c.execute("UPDATE rois SET error_code = ? WHERE id = ?", (new_nok, roi_id))
    conn.commit()
    conn.close()

def update_roi_position(roi_id, x, y, w, h):
    conn = sqlite3.connect('inspections.db')
    c = conn.cursor()
    c.execute("UPDATE rois SET x=?, y=?, w=?, h=? WHERE id=?", (x, y, w, h, roi_id))
    conn.commit()
    conn.close()