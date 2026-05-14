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