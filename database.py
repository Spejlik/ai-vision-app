import sqlite3

def init_db():
    conn = sqlite3.connect('inspections.db')
    c = conn.cursor()
    # Tabulka projektů
    c.execute('''CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY, name TEXT UNIQUE)''')
    # Tabulka master snímků a ořezů kamery (AOI)
    c.execute('''CREATE TABLE IF NOT EXISTS masters 
                 (id INTEGER PRIMARY KEY, project_id INTEGER, name TEXT, 
                  cam_id TEXT, aoi_x INTEGER, aoi_y INTEGER, aoi_w INTEGER, aoi_h INTEGER,
                  img_path TEXT)''')
    # Tabulka inspekčních zón (ROI)
    c.execute('''CREATE TABLE IF NOT EXISTS rois 
                 (id INTEGER PRIMARY KEY, master_id INTEGER, name TEXT, 
                  x INTEGER, y INTEGER, w INTEGER, h INTEGER)''')
    conn.commit()
    conn.close()

def save_roi(master_id, name, x, y, w, h):
    conn = sqlite3.connect('inspections.db')
    c = conn.cursor()
    c.execute("INSERT INTO rois (master_id, name, x, y, w, h) VALUES (?, ?, ?, ?, ?, ?)",
              (master_id, name, x, y, w, h))
    conn.commit()
    conn.close()

def get_rois(master_id):
    conn = sqlite3.connect('inspections.db')
    c = conn.cursor()
    c.execute("SELECT id, name, x, y, w, h FROM rois WHERE master_id = ?", (master_id,))
    data = c.fetchall()
    conn.close()
    return data
 
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

def save_master(proj_name, name, x, y, w, h, path):
    conn = sqlite3.connect('inspections.db')
    c = conn.cursor()
    # Zjistíme ID projektu
    c.execute("SELECT id FROM projects WHERE name = ?", (proj_name,))
    p_id = c.fetchone()[0]
    c.execute("INSERT INTO masters (project_id, name, aoi_x, aoi_y, aoi_w, aoi_h, img_path) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (p_id, name, x, y, w, h, path))
    conn.commit()
    conn.close()

def get_masters(proj_name):
    conn = sqlite3.connect('inspections.db')
    c = conn.cursor()
    c.execute("SELECT m.* FROM masters m JOIN projects p ON m.project_id = p.id WHERE p.name = ?", (proj_name,))
    data = c.fetchall()
    conn.close()
    return data 