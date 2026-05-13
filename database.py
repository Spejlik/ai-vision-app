import sqlite3

def init_db():
    conn = sqlite3.connect('inspections.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY, name TEXT UNIQUE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS masters 
                 (id INTEGER PRIMARY KEY, project_id INTEGER, name TEXT, 
                  cam_id TEXT, aoi_x INTEGER, aoi_y INTEGER, aoi_w INTEGER, aoi_h INTEGER,
                  img_path TEXT)''')
    # PŘIDÁN error_code
    c.execute('''CREATE TABLE IF NOT EXISTS rois 
                 (id INTEGER PRIMARY KEY, master_id INTEGER, name TEXT, 
                  x INTEGER, y INTEGER, w INTEGER, h INTEGER, error_code INTEGER)''')
    conn.commit()
    conn.close()

def save_roi(master_id, name, x, y, w, h, error_code):
    conn = sqlite3.connect('inspections.db')
    c = conn.cursor()
    c.execute("INSERT INTO rois (master_id, name, x, y, w, h, error_code) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (master_id, name, x, y, w, h, error_code))
    conn.commit()
    conn.close()

def get_rois(master_id):
    conn = sqlite3.connect('inspections.db')
    c = conn.cursor()
    c.execute("SELECT id, name, x, y, w, h, error_code FROM rois WHERE master_id = ?", (master_id,))
    data = c.fetchall()
    conn.close()
    return data

# ... (ostatní funkce pro projekty a mastery zůstávají stejné)